#!/usr/bin/env python3

# CUDA_VISIBLE_DEVICES=0,1 accelerate launch --num_processes 2 --main_process_ip 127.0.0.1 --main_process_port 12345 train_fin.py --use_4bit

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import argparse
import json
import os
from glob import glob
from pathlib import Path
from typing import List, Dict, Any, Tuple

import torch
from torch.utils.data import Dataset

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    Trainer,
    TrainingArguments,
    DataCollatorForLanguageModeling,
    BitsAndBytesConfig,
)

from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
)

from accelerate import Accelerator
accelerator = Accelerator()



# --------
# Data loader
# --------

def load_all_conversations(data_root: str) -> List[List[Dict[str, str]]]:
    """
    Load all dial_hist_system_list.json files under 'data_root'
    """
    pattern = str(Path(data_root).expanduser() / "**" / "dial_hist_system_list.json")
    files = glob(pattern, recursive=True)
    convos: List[List[Dict[str, str]]] = []

    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                conv = json.load(fp)
            # check whether conv is list of turns
            if isinstance(conv, list) and all(isinstance(m, dict) and "role" in m and "content" in m for m in conv):
                convos.append(conv)
        except Exception as e:
            print(f"[WARN] Failed to load {f}: {e}")
    print(f"[INFO] Loaded {len(convos)} conversations from {len(files)} files.")
    return convos


def split_into_sft_examples(conv: List[Dict[str, str]]) -> List[List[Dict[str, str]]]:
    """
    Make train sample for each 'assistant' turn in conv
    Each sample:
      - prompt: history before ith assistant turn(includes system+user+assistant)
      - target: ith assistant message
    """
    examples = []
    history: List[Dict[str, str]] = []
    for msg in conv:
        if msg["role"] == "assistant":
            example = history + [msg]
            examples.append(example)
        history = history + [msg]
    return examples


def build_all_examples(convos: List[List[Dict[str, str]]]) -> List[List[Dict[str, str]]]:
    all_ex = []
    for conv in convos:
        exs = split_into_sft_examples(conv)
        all_ex.extend(exs)
    print(f"[INFO] Built {len(all_ex)} SFT examples from {len(convos)} conversations.")
    return all_ex


# -----------------------
# Tokenize & Mask
# -----------------------


def tokenize_with_mask(tokenizer, example_chat, max_len):
    assert example_chat and example_chat[-1]["role"] == "assistant"
    context = example_chat[:-1]
    last_assistant = example_chat[-1]

    # 1) history before assistant turn
    ctx_ids = tokenizer.apply_chat_template(
        context,
        add_generation_prompt=True,
        tokenize=True,
        return_tensors="pt"
    )[0]  # (L_ctx,)


    # 2) context + last assistant turn
    full_ids = tokenizer.apply_chat_template(
        context + [last_assistant],
        add_generation_prompt=False,
        tokenize=True,
        return_tensors="pt"
    )[0]  # (L_full,)


    # 3) Last assistant span = full_ids[len(ctx_ids):]
    ctx_len = ctx_ids.size(0)
    last_ids = full_ids[ctx_len:]  

    # 4) Masking/Labeling
    input_ids = full_ids.clone()
    attention_mask = torch.ones_like(input_ids)
    labels = input_ids.clone()
    labels[:ctx_len] = -100  # -100 for history (only train assistant utterance)

    # 5) Front truncation logic to preserve last ids
    if input_ids.size(0) > max_len:
        overflow = input_ids.size(0) - max_len
        cut = min(overflow, ctx_len)  
        input_ids = input_ids[cut:]
        attention_mask = attention_mask[cut:]
        labels = labels[cut:]
        ctx_len = max(ctx_len - cut, 0)  

    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
    }


class ChatSFTDataset(Dataset):
    def __init__(self, examples: List[List[Dict[str, str]]], tokenizer: AutoTokenizer, max_length: int = 4096):
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        return tokenize_with_mask(self.tokenizer, self.examples[idx], self.max_length)


def collate_batch(features: List[Dict[str, torch.Tensor]]) -> Dict[str, torch.Tensor]:
    # pad to longest
    keys = ["input_ids", "attention_mask", "labels"]
    max_len = max(f["input_ids"].size(0) for f in features)
    out = {}
    for k in keys:
        pad_token_id = -100 if k == "labels" else 0
        dtype = torch.long
        padded = torch.full((len(features), max_len), pad_token_id, dtype=dtype)
        for i, f in enumerate(features):
            x = f[k]
            padded[i, : x.size(0)] = x
        out[k] = padded
    return out


# -------------
# Main Train Logic
# -------------

def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument("--data_root", type=str, default="train_datasets/multiwoz_train_dataset_4010101030")
    parser.add_argument("--model_name", type=str, default="meta-llama/Llama-3.2-3B-Instruct")
    parser.add_argument("--output_dir", type=str, default="./llama-3b-fullepoch_4010101030")
    
    parser.add_argument("--max_length", type=int, default=4096)
    parser.add_argument("--num_train_epochs", type=float, default=1)
    parser.add_argument("--per_device_train_batch_size", type=int, default=2)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=16)
    parser.add_argument("--learning_rate", type=float, default=2e-4)
    parser.add_argument("--weight_decay", type=float, default=0.0)
    parser.add_argument("--warmup_ratio", type=float, default=0.03)
    parser.add_argument("--logging_steps", type=int, default=10)
    parser.add_argument("--save_steps", type=int, default=500)
    parser.add_argument("--save_total_limit", type=int, default=3)
    parser.add_argument("--lora_r", type=int, default=4)
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--lora_dropout", type=float, default=0.05)
    parser.add_argument("--bf16", action="store_true")
    parser.add_argument("--fp16", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gradient_checkpointing", action="store_true")
    parser.add_argument("--use_4bit", action="store_true", help="(optional) QLoRA: 4-bit load")
    args = parser.parse_args()

    # 1) Data Prepararation
    convos = load_all_conversations(args.data_root)
    examples = build_all_examples(convos)

    # 2) Tokenizer/Model
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token


    if args.use_4bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if args.bf16 else torch.float16,
        )
        model = AutoModelForCausalLM.from_pretrained(
            args.model_name,
            quantization_config=bnb_config,
            device_map = {"": accelerator.process_index},
            torch_dtype=torch.bfloat16 if args.bf16 else (torch.float16 if args.fp16 else torch.float32),
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            args.model_name,
            torch_dtype=torch.bfloat16 if args.bf16 else (torch.float16 if args.fp16 else torch.float32),
        )


    if args.use_4bit:
        model = prepare_model_for_kbit_training(model)

    # 3) LoRA wrapper
    lora_cfg = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],  
    )
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()

    # 4) Dataset/Collator
    train_ds = ChatSFTDataset(examples, tokenizer, max_length=args.max_length)
    print("First 5 examples (tokenized):", [train_ds[i] for i in range(min(5, len(train_ds)))])


    # 5) Train
    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.num_train_epochs,
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=args.save_total_limit,
        bf16=args.bf16,
        fp16=args.fp16 and not args.bf16,
        dataloader_num_workers=4,
        optim="paged_adamw_32bit" if args.use_4bit else "adamw_torch",
        lr_scheduler_type="cosine",
        # report_to="none",
        prediction_loss_only=True,
        ddp_find_unused_parameters=False,  
        seed=args.seed,
        label_names=["labels"], 
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        tokenizer=tokenizer,
        data_collator=collate_batch,
    )

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    with open(os.path.join(args.output_dir, "cli_args.json"), "w") as f:
        json.dump(vars(args), f, indent=2)


    trainer.train()
    trainer.save_model(args.output_dir)
    accelerator.wait_for_everyone()

if __name__ == "__main__":
    main()