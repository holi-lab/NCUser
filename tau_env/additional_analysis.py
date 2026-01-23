import os
import json
from statistics import mean

default_path_list =[
    "experiment_result/ours/gpt-4.1-mini/tangential",
    "experiment_result/ours/gpt-4.1-nano/tangential",
    "experiment_result/ours/qwen3-30b-a3b/tangential",
    "experiment_result/ours/qwen3-235b-a22b/tangential",
    "experiment_result/ours/llama-3.1-70b-instruct/tangential",
]

print("--------Tangential Complaints Analysis--------")
# 데이터 수집
model_names = []
complain_averages = []

for default_path in default_path_list:
    model_name = default_path.split("/")[-2]
    total_tangential_complain = 0
    file_count = 0
    
    try:
        for file in os.listdir(default_path):
            with open(f"{default_path}/{file}/tangential_config.json",'r') as f:
                tangential_config = json.load(f)
            total_tangential_complain += tangential_config["n_complain"]
            file_count += 1

        
        if file_count > 0:
            # print(file_count)
            avg_complain = total_tangential_complain / file_count
            model_names.append(model_name)
            complain_averages.append(avg_complain)
            print(f"{model_name}: {avg_complain:.3f}")
    except FileNotFoundError:
        print(f"Path not found: {default_path}")
        continue

print("--------------------------------")
print()
print("--------API Results Hallucination per dialogue simulation--------")

model_name_list = ["gpt-4.1-mini","gpt-4.1-nano","qwen3-235b-a22b","qwen3-30b-a3b","llama-3.1-70b-instruct"]
behavior_list = ["normal","tangential","unavailable_service","fragment_dumping","emotional_acts"]

for model_name in model_name_list:
    for behavior in behavior_list:
        default_path = f"experiment_result/ours/{model_name}/{behavior}"
        model_name = default_path.split('/')[-2]
        behavior_name = default_path.split('/')[-1]

        n_obs_hall = 0
        for file in os.listdir(default_path):
            with open(f"{default_path}/{file}/reasoning_trajectory.json", 'r') as f:
                reasoning_trajectory = json.load(f)

            reasoning_trajectory_agent = [
                reasoning for reasoning in reasoning_trajectory if reasoning['role'] == "assistant"
            ]
            for response in reasoning_trajectory_agent:
                n_obs_hall+=response['content'].count("API output:")

        print(model_name,behavior_name)
        print(n_obs_hall/len(os.listdir(default_path)))
    print()
print("--------------------------------")
print()
print("--------Apology Ratio Analysis--------")

def is_apology(system_utterance):
    if not system_utterance:
        return False
    text = system_utterance.lower()
    apology_keywords = [
        "apologize",
        "apologise",
        "apology",
        "sorry",
        "i'm sorry",
        "i am sorry",
        "we're sorry",
        "we are sorry"
    ]
    return any(keyword in text for keyword in apology_keywords)

default_path_list =[
    f"experiment_result/ours/{model_name}/emotional_acts"
    for model_name in ["gpt-4.1-mini","gpt-4.1-nano","qwen3-235b-a22b","qwen3-30b-a3b","llama-3.1-70b-instruct"]
]

for default_path in default_path_list:
    average_apology_list = []
    for file in os.listdir(default_path):
        with open(f"{default_path}/{file}/dialogue_history.json",'r') as f:
            dial_hist_system_list = json.load(f)
        total_agent_turn=0
        is_apology_reply = 0
        for idx,turn in enumerate(dial_hist_system_list):
            if idx+1 == len(dial_hist_system_list):
                continue
            if turn['role'] == "user":
                total_agent_turn+=1
                if is_apology(turn['content']):
                    is_apology_reply+=1
        if total_agent_turn>0:
            average_apology_list.append(is_apology_reply/total_agent_turn)
        else:
            print(file)
        
    print(default_path.split("/")[-2],mean(average_apology_list))