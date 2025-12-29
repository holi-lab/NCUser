import os,json
from copy import deepcopy
import shutil

with open("run_gpt_infer.sh",'r') as f:
    a = f.read()

config_text_list = a.split("####")[0].split("###")[-1].strip().split("\n")

number_list = []
for sentence in config_text_list:
    number_list.append(int(sentence.split("=")[-1].split("#")[0].strip()))

n_simulation,n_file = number_list[0],number_list[2]

file_list = []
for split_idx in os.listdir("goal_list/split_idx_list"):
    with open(f"goal_list/split_idx_list/{split_idx}",'r') as f:
        current_split_idx_list = json.load(f)
    if n_file == 0:
        file_list+=deepcopy(current_split_idx_list)
    else:
        file_list+=deepcopy(current_split_idx_list[:n_file])

all_simulation_list = []

for file in file_list:
    for n_sim in range(n_simulation):
        all_simulation_list.append(f"{file}_{n_sim}")

error_simulation_idx_list = list(set(all_simulation_list)-set(os.listdir("simulation_result")))

print("Omitted idx:")
print(error_simulation_idx_list)


for split_idx in os.listdir("goal_list/split_idx_list"):
    with open(f"goal_list/split_idx_list/{split_idx}",'r') as f:
        current_split_idx_list = json.load(f)
    for error_simulation_idx in error_simulation_idx_list:
        if error_simulation_idx[:-2] in current_split_idx_list:
            print(split_idx)