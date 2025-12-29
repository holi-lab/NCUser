# Non-Collaborative User Simulators for Tool Agents

## TL;DR

This work is about "non-collaborative user simulation" in tool agent environments, and this repository contains the complete source code for the experiments in our paper. We conducted our experiments on MultiWOZ and Tau-Bench, and have organized the repository into separate directories for each environment. We have also configured separate conda environments for each.

## MultiWOZ

### Setup

```bash

cd multiwoz_env
conda create -n multiwoz_env python=3.11
conda activate multiwoz_env
pip install -r requirements.txt

```

### Run

우리는 기본적으로 병렬 처리를 통한 실험을 진행한다. 실험을 진행하기 앞서, 아래의 네 가지 setting이 필요하다.

(1) Number of Simulation

`run_dialogue_simulation.sh` 의 `3-5` line에 아래와 같은 변수가 존재한다.

```bash
N=4 # Number of Simulation (In our paper, we use N=4)
M=40 # FIX Value. Do not modify
O=0 # if O == 0, use all 89 test scenarios. elif 1 or 2, use the subset from 89 test scenarios
```

`N`은 같은 test scenario를 몇 회 시뮬레이션 할지 determine 한다 (우리 paper에서 N=4로 총 89개의 scenario 를 4번씩 시물레이션하여 356개의 simulation으로 evaluation을 진행하였다).
`O`는 89개 scenario를 전부 시뮬레이션할지, subset만을 시뮬레이션 할지이다. 0이면 89개를 전부, 1이나 2면 일부 subset만으로 simulation을 진행한다.

(2) Model Name

`run_dialogue_simulation.sh` 의 `14` line에 `models` array 의 모델 이름들이 아래와 같이 기재되어 있다.

```bash
models=(
    # "gpt-4.1-mini"
    "gpt-4.1-nano"
    # "qwen/qwen3-235b-a22b"
    # "qwen/qwen3-30b-a3b"
    # "meta-llama/llama-3.1-70b-instruct"

    # "holi-lab/llama-3.2-3b-multiwoz-finetuned"
    # "holi-lab/qwen-2.5-3b-multiwoz-finetuned"
    # "holi-lab/qwen-2.5-7b-multiwoz-finetuned"

    # "holi-lab/qwen-2.5-3b-528_195"
    # "holi-lab/qwen-2.5-3b-4010101030"
)
```

- 여기서 시뮬레이션 하고자 하는 model들의 주석처리를 풀거나, 새로운 model 이름을 추가함으로써 시뮬레이션을 진행할 수 있다.
- 우리는 experiment에서 `gpt-4.1-mini, gpt-4.1-nano` 는 OpenAI API, `qwen/qwen3-235b-a22b, qwen/qwen3-30b-a3b, meta-llama/llama-3.1-70b-instruct`는 OpenRouter API를 이용하였다.
- `holi-lab` repo의 모델들은 fine-tuning된 model들로 vllm을 이용하였다. 우리는 huggingface에 우리가 experiment에서 fine tuning한 model들을 모두 공개한다.
- 우리 code는 병렬 실행이 지원된다. `models` 안에 여러 model들이 있을 경우, 각 model들에 대한 inference가 병렬적으로 실행된다.

(3) Setup

1) API KEY

- `custom_openai_client.py`에서 API key를 직접 입력하면 된다.

```python

from openai import OpenAI

openai_client = OpenAI(
    api_key="<Your Openai API key>"
)

open_router_client = OpenAI(
    api_key = "<Your OpenRouter API key>",
    base_url="https://openrouter.ai/api/v1"
)
```

- `models` array 안에 open router model이 없다면, `custom_openai_client.py`의 open router API key를 fill 할 필요 없고, GPT 계열의 model이 없을 시에는 Openai API key를 fill할 필요 없다.

2) VLLM Server

우리는 MultiWOZ에서 VLLM을 통한 local inference를 지원한다. 아래의 process에 따라 vllm을 통해 local로 model inference를 할 수 있다.

첫 번째로, `run_dialogue_simulation.sh`의 `7` line의 `is_vllm` 변수를 `1`로 설정하여라

```bash
is_vllm=1
```

다음으로 `run_multi_inference.sh` 파일의 `gpu_list`에 사용하고자 하는 GPU number를 채워넣고, `model_name`에 model path를 넣어라.

```bash
gpu_list=(0 1)
model_name= "<MODEL_PATH>"
```

만약 your 서버에 GPU가 4대가 있고, 0,1,3 번 GPU를 사용하고자 한다면 아래와 같이 `gpu_list` 변수를 채워야 한다.

```bash
gpu_list=(0 1 3)
```

그리고 `run_multi_server.sh` 를 실행하여라. 

```bash
./run_multi_server.sh
```

이렇게 하면 지정한 GPU에 vllm server를 각각 open 하게 된다. 아래 command를 통해 `gpu_list` 변수로 지정했던 GPU 내에 server들이 모두 open 되었는지 확인하여라.

```bash
tmux a -t vllm_${gpu_number}

# if gpu_list=(0 1 3),
tmux a -t vllm_0
tmux a -t vllm_1
tmux a -t vllm_3
```

모든 GPU에 vllm server가 open 된 후에 다음 step으로 넘어가라.

(4) Non-Collaborative Behavior

multiwoz_env 경로에는 아래의 5개 yaml file이 존재한다.

```bash
non_coll_emotional_acts.yaml # this is impatience
non_coll_fragment_dumping.yaml # this is incomplete utterenace
non_coll_normal.yaml # this is collaborative
non_coll_tangential.yaml
non_coll_unavailable_service.yaml
```

- 여기서 emotional_acts, fragment_dumping, normal은 우리 paper에서 각각 impatience, incomplete utterance, collaborartive 이다.
- `./non_coll_list ` 폴더 안에 simulation하고자 하는 behavior의 yaml 파일을 복사하여라. 만약 impatience model의 simulation을 진행하고 싶다면, `non_coll_emotional_acts.yaml` file을 non_coll_list 폴더 안에 paste하여라.
- 우리 code는 병렬 실행이 지원된다. `non_coll_list` 안에 여러 yaml들이 있을 경우, 각 behavior mode에서의 inference가 병렬적으로 실행된다.

**[YAML Structure]**

- 기본적으로 주어진 yaml은 single non-collaborative behavior simulation이다. 만약 한 번에 여러 behavior를 보이는 user simulation을 진행하고 싶다면 yaml file을 새로 만들고 안의 내용을 수정하여야 한다 (yaml file의 이름은 임의로 지어도 상관없음). yaml file은 기본적으로 아래와 같다.

```bash
is_pbus: False

unavailable_service: False # Done
tangential: False # Done
emotional_acts: False # Done
fragment_dumping: False # Doned
```

여기서 unavailable_service와 tangential을 한 번에 보이는 user simulation을 진행하고자 한다면, 아래와 같이 yaml file의 내용을 수정해야 한다.

```bash
is_pbus: False

unavailable_service: True # Done
tangential: True # Done
emotional_acts: False # Done
fragment_dumping: False # Doned
```

- 만약 our user simulator가 아닌 prompt-based user simulator (PBUS)를 이용하고자 한다면 `is_pbus` key를 True로 설정하면 된다.

---

(1), (2), (3), (4) 까지 마쳤다면 아래 command로 simulation을 실행하면 된다.

```bash
./run_dialogue_simulation.sh
```

예시로, 만약 `gpt-4.1-nano, qwen/qwen3-30b-a3b` model을 collaborative, impatience mode 에서 simulation하고자 한다면 아래와 같이 setting하여야 한다.

`run_dialogue_simulation.sh` 의 models는 아래와 같이 구성되어야 한다.

```bash
models=(
    "gpt-4.1-nano"
    "qwen/qwen3-30b-a3b"
)
```

그리고 non_coll_list 폴더 안에는 아래와 같이 yaml 파일이 구성되어야 한다.

```bash
non_coll_emotional_acts.yaml
non_coll_normal.yaml
```

**[Warning]**
- 모든 model들과 behavior들 대한 simulation은 parallel하게 돌아간다. API access rate limit이나 컴퓨터 사양 등을 고려하여 우리는 한 번에 최대 두 개 model과 두 개 behavior까지만 병렬 실행하는 것을 권장한다. 

(5) 실험 결과 저장

실험 결과는 experiment_result 폴더에 아래와 같은 폴더 구조로 저장된다.
```
experiment_result
└── ours
    └── {model_name}
        └── {behavior_mode}
            └── {testcase_idx}_{number_of_simulation}
└── pbus
    └── {model_name}
        └── {behavior_mode}
            └── {testcase_idx}_{number_of_simulation}
```

그리고 evaluation score는 score_list폴더에 txt 파일로 저장이 된다. 파일 이름 및 content 아래와 같은 형식이다.

```
# file name
{default_path}_experiment_result_{ours_or_pbus}_{model_name}_{behavior_mode}.txt

# content
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

우리 실험은 goal alignment를 100으로 맞추기 위해 여러 attempt를 통해 regeneration이 진행된다. Regeneration code는 `run_dialogue_simulation.sh` 에 작성되어 있다.

### Analysis

For Evaluation 결과에 대한 세부 analysis, 아래 세 step을 따르라.

(1)  `run_error_analysis.sh` 파일 내 `6-10` line 에 아래와 같은 변수들이 있다. 분석하고자 하는 model과 behavior에 맞게 변수를 아래 예제와 같이 구성하여라.

```bash
# Model names
models=("gpt-4.1-mini" "gpt-4.1-nano")

# YAML files
yaml_files=("non_coll_tangential.yaml" "non_coll_unavailable_service.yaml")
```

(2) `non_coll_list` 폴더 안에 `yaml_files` 변수에 있는 yaml file 들을 똑같이 넣어두어라. 위의 예제처럼 `yaml_files` 변수를 구성하였다면 `non_coll_list` 안에는 다음과 같은 file이 있어야 한다.

```bash
non_coll_tangential.yaml
non_coll_unavailable_service.yaml
```

(3) 아래 command를 실행하면 된다.

```bash
./run_error_analysis.sh
```

실행 후에 `result_of_error_analysis` 폴더의 txt 파일에서 내용을 확인하면 된다.

추가로, 우리 논문의 appendix에 기재된 apology ratio, tangential complain, API Results hallucination에 대한 analysis는 아래와 같이 실행할 수 있다.

```bash
python additional_analysis.py
```

우리는 논문 experiment results 기재에 사용한 모든 inference results 들은 아래 Google Drive의 zip 파일에 저장되어 있다.
For MultiWOZ, `experiment_result_multiwoz.zip` 파일의 압축을 풀어서 나온 `experiment_result` 폴더로 기존 repo 내의 `experiment_result` 폴더를 대체하면 된다.

https://drive.google.com/drive/u/0/folders/1_UQZlT3fjg38gLqhzxQCMY-AQdWDQtC9

### Train

우리는 MultiWOZ environment에서 tool agent training을 진행한 dataset 및 code를 같이 공개한다.

(1) Train Dataset Generation

우리는 user simulator와 agent 간 simulation을 통해 dialogue data를 수집하였다. Specifically, 우리는 GPT-4.1-mini agent를 통해 high quality의 데이터만을 수집하였다.

먼저 `run_dialogue_simulation.sh`의 `9` line의 `is_train_mode` 를 1로 바꾸어라.

```bash
is_train_mode=1 # if 0, use testset. Else, use trainset.
```

그 후 위에 기재된 것과 동일하게 `models` 변수, 그리고 `non_coll_list` 폴더 안에 yaml file을 채워넣어 수집하고 싶은 데이터에 맞게 setting을 설정하여라. 그리고 아래 command를 실행하여라.

```bash
./run_dialogue_simulation.sh
```

시뮬레이션이 끝나면 experiment_result에 지정한 model, 그리고 behavior에 맞는 대화 데이터가 생성되게 된다. 이후 `train_datasets`에 새 폴더를 만들고, 거기에 trainset으로 구성하고 싶은 데이터들을 모아서 paste 하여라. 이 때 데이터는 simulation 결과 폴더 전체여야 한다. 이에 따라 폴더 구조는 아래와 같아야 한다.

```
train_datasets
└── {trainset_name}
    └── {simulation_idx} # ex: MUL0006.json_1, MUL0022.json_1
```

우리는 `train_datasets` 폴더에 우리가 실험에서 사용했던 trainset들을 같이 공개한다. 

```
multiwoz_train_dataset: 논문 Figure 4에 기재된 agent train에 사용
multiwoz_train_dataset_528_195: 논문 Appendix D.2 Table 20의 "Uniformly weighted" agent train에 사용
multiwoz_train_dataset_4010101030: 논문 Appendix D.2 Table 20의 "Non-uniformly weighted" agent train에 사용
```

새로운 trainset 구성할 때, 기존 세세 폴더들을 참조해서 똑같은 폴더 구조를 갖도록 구성하여라. 

(2) Agent Training

먼저 `train_fin.py`의 `179-181` line의 arg를 manual하게 입력해야 한다.

```python
...
parser.add_argument("--data_root", type=str, default="train_datasets/<trainset_name>")
parser.add_argument("--model_name", type=str, default=<base_model_repo>")
parser.add_argument("--output_dir", type=str, default=<output_directory>)
...
```

예제로, 아래와 같이 입력하면 된다.
```python
...
parser.add_argument("--data_root", type=str, default="train_datasets/multiwoz_train_dataset_4010101030")
parser.add_argument("--model_name", type=str, default="meta-llama/Llama-3.2-3B-Instruct")
parser.add_argument("--output_dir", type=str, default="./llama-3b-fullepoch_4010101030")
...
```

이후 아래 command에 사용할 GPU number를 `CUDA_VISIBLE_DEVICES` 에 지정하고 실행하여라

```bash
CUDA_VISIBLE_DEVICES={gpu_numbers} accelerate launch --num_processes 2 --main_process_ip 127.0.0.1 --main_process_port 12345 train_fin.py --use_4bit
```

우리는 기본적으로 Q-lora를 사용하고, train 후에는 `./<output_directory`에 lora adapter가 저장된다. 실제 inference를 진행하기 위해선 base model을 quantization하지 않은 상태에서 lora adapter를 merger해야 한다.

## $\tau$-Bench

### Setup

```bash

cd tau_env
conda create -n tau_env python=3.11
conda activate tau_env
pip install -r requirements.txt

```

### Run

MultiWOZ처럼 $\tau$-Bench도 병렬 처리를 통한 실험을 진행한다. 실험을 진행하기 앞서, 아래에 따라 setting이 필요하다.

(1) Number of Simulation, Domain, Models

`run_dialogue_simulation.sh`의 `3-11` line에는 아래와 같은 변수들이 있다.

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

- `domain_list`는 $\tau$-Bench의 domain인 `airline`, `retail`이다.
- `n_trial`는 몇 회 시뮬레이션할 지를 결정한다 (MultiWOZ의 N과 동일함). 우리 논문에선 `n_trial`이 4이다.
- `models` array에는 simulation에 사용할 model을 넣어야 한다.
- 우리 code는 병렬 실행이 지원된다. Domain, trial, model 별로 inference가 병렬적으로 실행된다.

(2) Non-Collaborative Behavior

MultiWOZ와 마찬가지로, tau_env 경로 아래의 5개 yaml file이 존재한다.

```bash
non_coll_emotional_acts.yaml # this is impatience
non_coll_fragment_dumping.yaml # this is incomplete utterenace
non_coll_normal.yaml # this is collaborative
non_coll_tangential.yaml
non_coll_unavailable_service.yaml
```

- 여기서 emotional_acts, fragment_dumping, normal은 우리 paper에서 각각 impatience, incomplete utterance, collaborartive 이다.
- `./non_coll_list ` 폴더 안에 simulation하고자 하는 behavior의 yaml 파일을 복사하여라. 만약 impatience model의 simulation을 진행하고 싶다면, `non_coll_emotional_acts.yaml` file을 non_coll_list 폴더 안에 paste하여라.
- 우리 code는 병렬 실행이 지원된다. `non_coll_list` 안에 여러 yaml들이 있을 경우, 각 behavior mode에서의 inference가 병렬적으로 실행된다.
- YAML file structure는 위의 MultiWOZ의 Run의 (4)번 항목에 기재되어 있다.

**[Warning]**
- 모든 model들과 behavior들 대한 simulation은 parallel하게 돌아간다. API access rate limit이나 컴퓨터 사양 등을 고려하여 우리는 한 번에 최대 두 개 model과 두 개 behavior까지만 병렬 실행하는 것을 권장한다.

(1),(2)까지 마쳤다면 아래 command를 통해 simulation을 진행하라.

```bash
./run_dialogue_simulation.sh
```

(3) 실험 결과 저장

실험 결과는 experiment_result 폴더에 MultiWOZ와 동일한 폴더 구조로 저장된다 (See the Run-(5) on MultiWOZ). 그리고 evaluation score는 score_list폴더에 txt 파일로 저장이 된다. 파일 이름은 아래와 같고 content는 MultiWOZ와 동일하다.

```
# file name
experiment_result_{ours_or_pbus}_{model_name}_{behavior_mode}.txt
```

우리 실험은 goal alignment를 100으로 맞추기 위해 여러 attempt를 통해 regeneration이 진행된다. Regeneration logic `run_dialogue_simulation.sh` 에 작성되어 있다.

### Analysis

For Evaluation 결과에 대한 세부 analysis, 아래 세 step을 따르라.

(1) `run_error_analysis.sh` 파일 내 `7-8` line 에 아래와 같은 변수들이 있다. 분석하고자 하는 model과 behavior에 맞게 변수를 아래 예제와 같이 구성하여라.

```bash
models=("gpt-4.1-mini" "gpt-4.1-nano" "qwen3-235b-a22b" "qwen3-30b-a3b" "llama-3.1-70b-instruct")
yaml_files=("non_coll_emotional_acts.yaml" "non_coll_fragment_dumping.yaml" "non_coll_normal.yaml" "non_coll_tangential.yaml" "non_coll_unavailable_service.yaml")
```

(2) `non_coll_list` 폴더 안에 `yaml_files` 변수에 있는 yaml file 들을 똑같이 넣어두어라. 위의 예제처럼 `yaml_files` 변수를 구성하였다면 `non_coll_list` 안에는 다음과 같은 file이 있어야 한다.

```bash
non_coll_tangential.yaml
non_coll_unavailable_service.yaml
```

(3) 아래 command를 실행하면 된다.

```bash
./run_error_analysis.sh
```

실행 후에 `result_of_error_analysis` 폴더의 txt 파일에서 내용을 확인하면 된다.

추가로, 우리 논문의 appendix에 기재된 apology ratio, tangential complain, API Results hallucination에 대한 analysis는 아래와 같이 실행할 수 있다.

```bash
python additional_analysis.py
```

우리는 논문 experiment results 기재에 사용한 모든 inference results 들은 아래 Google Drive의 zip 파일에 저장되어 있다.
For Tau-Bench, `experiment_result_tau.zip` 파일의 압축을 풀어서 나온 `experiment_result` 폴더로 기존 repo 내의 `experiment_result` 폴더를 대체하면 된다.

https://drive.google.com/drive/u/0/folders/1_UQZlT3fjg38gLqhzxQCMY-AQdWDQtC9


## Extension (ColBench, MINT)

우리는 MultiWOZ와 Tau-Bench를 넘어 ColBench와 MINT로 우리 user simulator를 확장하였다. 이에 대한 source code를 같이 공개한다.
