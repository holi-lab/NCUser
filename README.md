# Non-Collaborative User Simulators for Tool Agents

## TL;DR

This repository contains the complete source code for experiments on non-collaborative user simulation in tool agent environments. We conducted experiments on MultiWOZ and Tau-Bench, with separate directories and conda environments for each.

## Table of Contents
- [MultiWOZ](#multiwoz)
  - [Setup](#multiwoz-setup)
  - [Configuration](#multiwoz-configuration)
  - [Running Experiments](#multiwoz-running-experiments)
  - [Analysis](#multiwoz-analysis)
  - [Training](#multiwoz-training)
- [Tau-Bench](#tau-bench)
  - [Setup](#tau-bench-setup)
  - [Configuration](#tau-bench-configuration)
  - [Running Experiments](#tau-bench-running-experiments)
  - [Analysis](#tau-bench-analysis)

---

## MultiWOZ

### Setup

```bash
cd multiwoz_env
conda create -n multiwoz_env python=3.11
conda activate multiwoz_env
pip install -r requirements.txt
```

### Configuration

Before running experiments, configure the following settings:

#### 1. Number of Simulations

In `run_dialogue_simulation.sh` (lines 3-5):

```bash
N=4  # Number of simulations per scenario (we use N=4 in our paper)
M=40 # Fixed value. Do not modify
O=0  # 0: use all 89 test scenarios; 1 or 2: use subset
```

- `N`: Number of times each test scenario is simulated (we ran 89 scenarios × 4 times = 356 simulations)
- `O`: Whether to use all 89 scenarios or a subset

#### 2. Model Selection

In `run_dialogue_simulation.sh` (line 14), configure the `models` array:

```bash
models=(
    # "gpt-4.1-mini"
    "gpt-4.1-nano"
    # "qwen/qwen3-235b-a22b"
    # "qwen/qwen3-30b-a3b"
    # "meta-llama/llama-3.1-70b-instruct"
    
    # Fine-tuned models
    # "holi-lab/llama-3.2-3b-multiwoz-finetuned"
    # "holi-lab/qwen-2.5-3b-multiwoz-finetuned"
    # "holi-lab/qwen-2.5-7b-multiwoz-finetuned"
    # "holi-lab/qwen-2.5-3b-528_195"
    # "holi-lab/qwen-2.5-3b-4010101030"
)
```

**Notes:**
- Uncomment or add models you want to simulate
- `gpt-4.1-mini`, `gpt-4.1-nano`: OpenAI API
- `qwen/*`, `meta-llama/*`: OpenRouter API  
- `holi-lab/*`: Fine-tuned models we have trained (all available on HuggingFace). Use vLLM for inference.
- Parallel execution is supported across multiple models

#### 3. API Configuration

##### API Keys

In `custom_openai_client.py`:

```python
from openai import OpenAI

openai_client = OpenAI(
    api_key="<Your OpenAI API key>"
)

open_router_client = OpenAI(
    api_key="<Your OpenRouter API key>",
    base_url="https://openrouter.ai/api/v1"
)
```

Fill in the OpenAI API key in `<Your OpenAI API key>`. Since our user simulator uses GPT-4.1-mini, this field must always be completed.

Additionally, if you are using the tool agent model from OpenRouter, please fill in `<Your OpenRouter API key>` as well.

##### vLLM Server (Optional for Local Inference)

We support local inference using vLLM for MultiWOZ. Follow these steps:

**Step 1:** Set `is_vllm=1` in `run_dialogue_simulation.sh` (line 7):
```bash
is_vllm=1
```

**Step 2:** Configure GPU settings in `run_multi_inference.sh`:
```bash
gpu_list=(0 1)  # Specify GPU IDs to use
model_name="<MODEL_PATH>"  # Path to your model
```

Example: To use GPUs 0, 1, and 3 on a 4-GPU server:
```bash
gpu_list=(0 1 3)
```

**Step 3:** Start vLLM servers:
```bash
./run_multi_server.sh
```

**Step 4:** Verify all servers are running:
```bash
tmux a -t vllm_0
tmux a -t vllm_1
tmux a -t vllm_3  # if using GPU 3
```

Wait for all servers to fully initialize before proceeding to the next step.

#### 4. Non-Collaborative Behaviors

Five YAML configuration files are available in the `multiwoz_env` directory:

```bash
non_coll_emotional_acts.yaml      # Impatience
non_coll_fragment_dumping.yaml    # Incomplete utterance
non_coll_normal.yaml              # Collaborative (baseline)
non_coll_tangential.yaml          # Tangential
non_coll_unavailable_service.yaml # Unavailable service
```

**Usage:**
- Copy the desired mode YAML files to the `./non_coll_list/` folder
- Multiple behaviors can run in parallel

**YAML Structure:**

For single behavior simulation (e.g., `Tangential`):
```yaml
is_pbus: False

unavailable_service: False
tangential: True
emotional_acts: False
fragment_dumping: False
```

For multiple behaviors (e.g., `unavailable_service` + `tangential`):
```yaml
is_pbus: False

unavailable_service: True
tangential: True
emotional_acts: False
fragment_dumping: False
```

**Note:** Set `is_pbus: True` to use Prompt-Based User Simulator (PBUS) instead of our user simulator.

### Running Experiments

After completing all configuration steps (1-4):

```bash
./run_dialogue_simulation.sh
```

#### Example Configuration

To simulate `gpt-4.1-nano` and `qwen/qwen3-30b-a3b` in collaborative and impatience modes:

**In `run_dialogue_simulation.sh`:**
```bash
models=(
    "gpt-4.1-nano"
    "qwen/qwen3-30b-a3b"
)
```

**In `./non_coll_list/`:**
```bash
non_coll_emotional_acts.yaml
non_coll_normal.yaml
```

**⚠️ Warning:** All models and behaviors run in parallel. Due to API rate limits and resource constraints, we recommend limiting execution to **2 models and 2 behaviors simultaneously**.

#### Results Structure

Experimental results are saved in the following directory structure:

```
experiment_result/
├── ours/
│   └── {model_name}/
│       └── {behavior_mode}/
│           └── {testcase_idx}_{simulation_number}/
└── pbus/
    └── {model_name}/
        └── {behavior_mode}/
            └── {testcase_idx}_{simulation_number}/
```

Evaluation scores are saved in the `score_list/` folder as text files.

**Filename format:**
```
{default_path}_experiment_result_{ours_or_pbus}_{model_name}_{behavior_mode}.txt
```

**Content format:**
```
Attempt 1:
success_rate_mean: 90.730
success_rate_values: [87.64044943820225, 89.8876404494382, 94.3820224719101, 91.01123595505618]
pass_rate_mean: 95.131
pass_rate_values: [94.00749063670413, 93.82022471910115, 97.00374531835207, 95.69288389513109]
goal_align_mean: 98.315
goal_align_values: [98.87640449438202, 97.75280898876404, 98.87640449438202, 97.75280898876404]
total_graded_cnt: 356

Attempt 2:
success_rate_mean: 90.730
success_rate_values: [87.64044943820225, 89.8876404494382, 94.3820224719101, 91.01123595505618]
pass_rate_mean: 95.225
pass_rate_values: [94.00749063670413, 93.82022471910115, 97.37827715355805, 95.69288389513109]
goal_align_mean: 99.719
goal_align_values: [100.0, 98.87640449438202, 100.0, 100.0]
total_graded_cnt: 356

Attempt 3:
success_rate_mean: 90.730
success_rate_values: [87.64044943820225, 89.8876404494382, 94.3820224719101, 91.01123595505618]
pass_rate_mean: 95.225
pass_rate_values: [94.00749063670413, 93.82022471910115, 97.37827715355805, 95.69288389513109]
goal_align_mean: 100.000
goal_align_values: [100.0, 100.0, 100.0, 100.0]
total_graded_cnt: 356
```

The experiment performs multiple regeneration attempts to achieve 100% goal alignment. The regeneration logic is implemented in `run_dialogue_simulation.sh`.

### Analysis

#### Error Analysis

Follow these three steps for detailed evaluation analysis:

**Step 1:** Configure models and behaviors in `run_error_analysis.sh` (lines 6-10):
```bash
# Model names
models=("gpt-4.1-mini" "gpt-4.1-nano")

# YAML files
yaml_files=("non_coll_tangential.yaml" "non_coll_unavailable_service.yaml")
```

**Step 2:** Copy the YAML files to `./non_coll_list/`:
```bash
non_coll_tangential.yaml
non_coll_unavailable_service.yaml
```

**Step 3:** Run the analysis:
```bash
./run_error_analysis.sh
```

Results will be saved in the `result_of_error_analysis/` folder as text files.

#### Additional Analysis

For metrics reported in the paper's appendix (apology ratio, tangential complaints, API hallucination):

```bash
python additional_analysis.py
```

#### Full Experimental Results

All inference results used in our paper are available on Google Drive:

**For MultiWOZ:**
1. Download `experiment_result_multiwoz.zip`
2. Extract the `experiment_result` folder
3. Replace the existing `experiment_result` folder in the repository

[Google Drive Link](https://drive.google.com/drive/u/0/folders/1_UQZlT3fjg38gLqhzxQCMY-AQdWDQtC9)

### Training

We provide datasets and code for training tool agents on MultiWOZ.

#### Dataset Generation

We collected dialogue data through agent-simulator interactions using GPT-4.1-mini as a high-quality agent.

**Step 1:** Enable training mode in `run_dialogue_simulation.sh` (line 9):
```bash
is_train_mode=1  # 0: use testset; 1: use trainset
```

**Step 2:** Configure the `models` array and YAML files in `./non_coll_list/` according to the type of data you want to collect (same as the experiment setup).

**Step 3:** Run the simulation:
```bash
./run_dialogue_simulation.sh
```

**Step 4:** Organize training data:
After simulation completes, dialogue data will be generated in `experiment_result/`. Create a new folder in `train_datasets/` and collect the simulation result folders you want to use as training data.

The folder structure should be:
```
train_datasets/
└── {trainset_name}/
    └── {simulation_idx}/  # e.g., MUL0006.json_1, MUL0022.json_1
```

**Pre-configured Training Datasets:**

We include the training datasets used in our experiments:

- `multiwoz_train_dataset`: Used for agent training in Figure 4 of the paper
- `multiwoz_train_dataset_528_195`: Used for "Uniformly weighted" agent in Appendix D.2 Table 20
- `multiwoz_train_dataset_4010101030`: Used for "Non-uniformly weighted" agent in Appendix D.2 Table 20

When creating new training sets, reference these existing folders to maintain the same structure.

#### Agent Training

**Step 1:** Configure training parameters in `train_fin.py` (lines 179-181):

```python
parser.add_argument("--data_root", type=str, default="train_datasets/<trainset_name>")
parser.add_argument("--model_name", type=str, default="<base_model_repo>")
parser.add_argument("--output_dir", type=str, default="<output_directory>")
```

Example:
```python
parser.add_argument("--data_root", type=str, default="train_datasets/multiwoz_train_dataset")
parser.add_argument("--model_name", type=str, default="meta-llama/Llama-3.2-3B-Instruct")
parser.add_argument("--output_dir", type=str, default="./llama-3.2-3b-multiwoz-finetuned")
```

**Step 2:** Run training with specified GPUs:

```bash
CUDA_VISIBLE_DEVICES={gpu_numbers} accelerate launch --num_processes 2 --main_process_ip 127.0.0.1 --main_process_port 12345 train_fin.py --use_4bit
```

**Notes:**
- We use QLoRA by default
- After training, LoRA adapters are saved in `./<output_directory>/`
- For inference, merge the LoRA adapter with the non-quantized base model

---

## Tau-Bench

### Setup

```bash
cd tau_env
conda create -n tau_env python=3.11
conda activate tau_env
pip install -e .
```

### Configuration

Like MultiWOZ, Tau-Bench supports parallel execution. Configure the following settings before running experiments:

#### 1. Simulation Settings

In `run_dialogue_simulation.sh` (lines 3-11):

```bash
domain_list=("airline" "retail")
n_trial=4
models=(
    # "gpt-4.1-mini"
    "gpt-4.1-nano"
    # "qwen/qwen3-235b-a22b"
    "qwen/qwen3-30b-a3b"
    # "meta-llama/llama-3.1-70b-instruct"
)
```

- `domain_list`: Tau-Bench domains (`airline`, `retail`)
- `n_trial`: Number of simulations per scenario (same as `N` in MultiWOZ; we use 4 in our paper)
- `models`: Array of models to simulate
- Parallel execution is supported across domains, trials, and models

#### 2. Non-Collaborative Behaviors

Five YAML configuration files are available in the `tau_env` directory:

```bash
non_coll_emotional_acts.yaml      # Impatience
non_coll_fragment_dumping.yaml    # Incomplete utterance
non_coll_normal.yaml              # Collaborative (baseline)
non_coll_tangential.yaml          # Tangential conversation
non_coll_unavailable_service.yaml # Unavailable service requests
```

**Usage:**
- Copy desired YAML files to the `./non_coll_list/` folder
- Multiple behaviors can run in parallel
- YAML structure is the same as described in [MultiWOZ Configuration - Section 4](#4-non-collaborative-behaviors)

**⚠️ Warning:** All models and behaviors run in parallel. We recommend limiting execution to **2 models and 2 behaviors simultaneously** to avoid API rate limits and resource constraints.

#### 3. API Configuration

##### API Keys

In `custom_openai_client.py`:

```python
from openai import OpenAI

openai_client = OpenAI(
    api_key="<Your OpenAI API key>"
)

open_router_client = OpenAI(
    api_key="<Your OpenRouter API key>",
    base_url="https://openrouter.ai/api/v1"
)
```

Fill in the OpenAI API key in `<Your OpenAI API key>`. Since our user simulator uses GPT-4.1-mini, this field must always be completed.

Additionally, if you are using the tool agent model from OpenRouter, please fill in `<Your OpenRouter API key>` as well.

### Running Experiments

After completing configuration steps (1-3):

```bash
./run_dialogue_simulation.sh
```

#### Results Structure

Experimental results are saved in the same folder structure as MultiWOZ (see [MultiWOZ Results Structure](#results-structure)).

Evaluation scores are saved in the `score_list/` folder as text files.

**Filename format:**
```
experiment_result_{ours_or_pbus}_{model_name}_{behavior_mode}.txt
```

The content format is the same as MultiWOZ.

The experiment performs multiple regeneration attempts to achieve 100% goal alignment. The regeneration logic is implemented in `run_dialogue_simulation.sh`.

### Analysis

#### Error Analysis

Follow these three steps for detailed evaluation analysis:

**Step 1:** Configure models and behaviors in `run_error_analysis.sh` (lines 7-8):
```bash
models=("gpt-4.1-mini" "gpt-4.1-nano" "qwen3-235b-a22b" "qwen3-30b-a3b" "llama-3.1-70b-instruct")
yaml_files=("non_coll_emotional_acts.yaml" "non_coll_fragment_dumping.yaml" "non_coll_normal.yaml" "non_coll_tangential.yaml" "non_coll_unavailable_service.yaml")
```

**Step 2:** Copy the YAML files to `./non_coll_list/`:
```bash
# This is an example.
non_coll_tangential.yaml
non_coll_unavailable_service.yaml
```

**Step 3:** Run the analysis:
```bash
./run_error_analysis.sh
```

Results will be saved in the `result_of_error_analysis/` folder as text files.

#### Additional Analysis

For metrics reported in the paper's appendix (apology ratio, tangential complaints, API hallucination):

```bash
python additional_analysis.py
```

#### Full Experimental Results

All inference results used in our paper are available on Google Drive:

**For Tau-Bench:**
1. Download `experiment_result_tau.zip`
2. Extract the `experiment_result` folder
3. Replace the existing `experiment_result` folder in the repository

[Google Drive Link](https://drive.google.com/drive/u/0/folders/1_UQZlT3fjg38gLqhzxQCMY-AQdWDQtC9)

## Citation

```
@misc{shim2025noncollaborativeusersimulatorstool,
      title={Non-Collaborative User Simulators for Tool Agents}, 
      author={Jeonghoon Shim and Woojung Song and Cheyon Jin and Seungwon KooK and Yohan Jo},
      year={2025},
      eprint={2509.23124},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2509.23124}, 
}
```

