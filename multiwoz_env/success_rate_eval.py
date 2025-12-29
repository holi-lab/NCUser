import json
import shutil,os
import numpy as np
import sys
from statistics import mean
from collections import Counter
from analysis_error import api_miss_usage,misbehavior_category
from get_experiment_path import get_experiment_path

def print_price():
    total_price = 0
    for file in os.listdir("price_file"):
        with open(f"price_file/{file}",'r') as f:
            current_file = json.load(f)
        total_price+=current_file['cost']

    print(f"Total price: ${total_price}")

# Get model name and yaml file from command line arguments
if len(sys.argv) < 2:
    print("Usage: python success_rate_eval.py <model_name> [yaml_file]")
    sys.exit(1)

model_name = sys.argv[1]
yaml_file = sys.argv[2] if len(sys.argv) > 2 else "non_coll.yaml"
foldername = get_experiment_path(model_name, yaml_file)

print_price()
print(f"Result of {foldername}")

# print(len(os.listdir(foldername)))

n_simulation_list = list(set([int(idx[-1:]) for idx in os.listdir(foldername)]))
n_simulation_list=sorted(n_simulation_list)
unique_idx_list = list(set([idx[:-2] for idx in os.listdir(foldername)]))

print(f"Number of Simulation: {len(n_simulation_list)}")

test_idx_list = [idx.split("_")[0] for idx in os.listdir(foldername)]
print("---------------",len(test_idx_list),"---------------")

n_turn = 0
n_turn_list = []

n_reasoning = 0
n_reasoning_list = []

wrong_cnt = 0

if len([idx for idx in test_idx_list if ".json" in idx])>0:
    print("<Result of MultiWOZ>")
    multiwoz_simulation_result_list = {
            "success_rate":[],
            "pass_rate":[],
            "goal_align":[]
        }
    total_graded_cnt = 0
    for n_simulation in n_simulation_list:
        result_list = []
        idx_list = []
        domains = []
        for idx in os.listdir(foldername):
            if ".json" not in idx or int(idx[-1]) != n_simulation: # multiwoz
                continue
            
            try:
                with open(f"{foldername}/{idx}/grading_result.json",'r') as f:
                    result = json.load(f)
            except:
                # print(idx)
                shutil.rmtree(f"{foldername}/{idx}")
                continue

            with open(f"{foldername}/{idx}/domains.json",'r') as f:
                current_domain_list = json.load(f)

            domains+=current_domain_list

            result_list.append(result)
            idx_list.append(idx)

        total_graded_cnt+=len(result_list)

        domains = set(domains)
        total_correct_cnt=0
        cnt = 0
        domain_cnt = {("accommodation" if domain=="hotel" else domain):{"correct":0,"cnt":0} for domain in domains}
        multiwoz_pass_rate = 0
        multiwoz_n_goal_align = 0
        for idx,result in zip(idx_list,result_list):
            true_or_false = []
            for domain in result:
                true_or_false.append(result[domain]["book"])
                if result[domain]["book"]:
                    domain_cnt[domain]['correct']+=1
                domain_cnt[domain]['cnt']+=1
            if all(true_or_false):
                total_correct_cnt+=1
                with open(f"{foldername}/{idx}/pass_or_fail.txt",'w') as f:
                    f.write("PASS")
            else:
                
                with open(f"{foldername}/{idx}/domains.json",'r') as f:
                    tmp_domain_list = json.load(f)
                # if "accommodation" in tmp_domain_list:
                #     print(idx)
                # print((len(true_or_false) - sum(true_or_false)))
                wrong_cnt+=(len(true_or_false) - sum(true_or_false))
                with open(f"{foldername}/{idx}/pass_or_fail.txt",'w') as f:
                    f.write("FAIL")

            with open(f"{foldername}/{idx}/dialogue_stats.json",'r') as f:
                current_n_turn = json.load(f)

            n_turn+=current_n_turn['n_turn']
            n_turn_list.append(current_n_turn['n_turn'])

            n_reasoning+=current_n_turn['n_reasoning']

            with open(f"{foldername}/{idx}/goal_align_result.json",'r') as f:
                goal_align_result = json.load(f)
            if goal_align_result['result']:
                multiwoz_n_goal_align+=1
            # else:
            #     print(idx)

            multiwoz_pass_rate+=sum(true_or_false)/len(true_or_false)

        multiwoz_simulation_result_list["success_rate"].append(total_correct_cnt/len(result_list)*100)
        multiwoz_simulation_result_list["pass_rate"].append(multiwoz_pass_rate/len(result_list)*100)
        multiwoz_simulation_result_list['goal_align'].append(multiwoz_n_goal_align/len(result_list)*100)
    for metric in ["success_rate", "pass_rate","goal_align"]:
        values = multiwoz_simulation_result_list[metric]
        mean_val = np.mean(values)
        std_val = np.std(values)
        print(f"{metric}_values: {values}")
        print(f"{metric}_mean: {mean_val:.3f}")
        print(f"{metric}_std: {std_val:.3f}")
        print()

print(f"total_graded_cnt: {total_graded_cnt}")
print(f"Average Turn: {n_turn/len(test_idx_list)}")
print(f"Average Reasoning: {n_reasoning/len(test_idx_list)}")
print(f"Max turn: {max(n_turn_list)}")
print("===============Misbehavior Category===============")
# print(f"Total wrong: {wrong_cnt}")
misbehavior_category(foldername)


print("===============API call Error Analysis===============")
api_miss_usage(foldername)