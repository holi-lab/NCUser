#!/bin/bash

gpu_list=(3)
model_name="holi-lab/llama-3.2-3b-multiwoz-finetuned"

for gpu_number in "${gpu_list[@]}"; do
  port_number=$((8000 + gpu_number))
  
  tmux new-session -d -s "vllm_${gpu_number}" \
    "CUDA_VISIBLE_DEVICES=${gpu_number} python -m vllm.entrypoints.openai.api_server \
     --model ${model_name} \
     --tokenizer ${model_name} \
     --dtype float16 \
     --gpu-memory-utilization 0.90 \
     --host 0.0.0.0 \
     --port ${port_number}"
done