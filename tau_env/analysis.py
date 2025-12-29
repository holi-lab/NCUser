import json, os
from statistics import mean
import subprocess
from analysis_error import error_analysis
from analysis_mistake import mistake_analysis

def evaluate_from_simulation_result_per_domain(model_name,behavior,simulation_result_dir):
    
    for domain in ["airline","retail"]:
        result_list = []
        for folder_name in os.listdir(simulation_result_dir):
            if domain not in folder_name:
                continue
            folder_path = os.path.join(simulation_result_dir, folder_name)
            eval_result_path = os.path.join(folder_path, "eval_result.json")
            with open(eval_result_path, 'r', encoding='utf-8') as f:
                eval_result = json.load(f)
                result_list.append(eval_result)

        trial_dict = {}
        for result in result_list:
            trial_num = result['trial']
            if trial_num not in trial_dict:
                trial_dict[trial_num] = []
            trial_dict[trial_num].append(result['reward'])
        
        # 각 trial별 success rate 계산 (0~100%)
        score_list = []
        for trial in sorted(trial_dict.keys()):  # trial 순서대로 정렬
            success_rate = mean(trial_dict[trial]) * 100
            score_list.append(success_rate)

        print(f"{domain} score: {mean(score_list)} {score_list}")

def evaluate_from_simulation_result(simulation_result_dir):
    if not os.path.exists(simulation_result_dir):
        print(f"Error: {simulation_result_dir} directory does not exist")
        return []
    
    # normal behavior가 아닌 경우, normal behavior 결과도 로드해서 교집합 구하기

    result_list = []
    for folder_name in sorted(os.listdir(simulation_result_dir)):

        folder_path = os.path.join(simulation_result_dir, folder_name)
        # print(folder_name)
        if os.path.isdir(folder_path):
            eval_result_path = os.path.join(folder_path, "eval_result.json")
            # 조건을 만족하는 경우 eval_result 로드
            with open(eval_result_path, 'r', encoding='utf-8') as f:
                eval_result = json.load(f)

            if "traceback" not in eval_result['info']:
                result_list.append(eval_result)
            else:
                if "AssertionError" in eval_result['info']['traceback']:
                    result_list.append(eval_result)
                else:
                    print(folder_name)

                        
    print(f"total_graded_cnt: {len(result_list)}")
    if not result_list:
        # print("No valid eval_result.json files found")
        return []
    
    # trial별로 그룹핑
    trial_dict = {}
    for result in result_list:
        trial_num = result['trial']
        if trial_num not in trial_dict:
            trial_dict[trial_num] = []
        trial_dict[trial_num].append(result['reward'])
    
    # 각 trial별 success rate 계산 (0~100%)
    score_list = []
    for trial in sorted(trial_dict.keys()):  # trial 순서대로 정렬
        success_rate = mean(trial_dict[trial]) * 100
        score_list.append(success_rate)
    
    return score_list

def average_turn_length(simulation_result_dir):
    file_list = os.listdir(simulation_result_dir)
    total_turn = 0
    total_turn_length_list = []
    for file in file_list:
        with open(f"{simulation_result_dir}/{file}/dialogue_history.json",'r') as f:
            dial_hist_list = json.load(f)
        total_turn+=(len(dial_hist_list)-2)
        total_turn_length_list.append(len(dial_hist_list)-2)
    print(f"Max turn: {max(total_turn_length_list)}")
    print(f"Average turn: {total_turn/len(file_list)}")

def average_reasoning_length(simulation_result_dir):
    file_list = os.listdir(simulation_result_dir)
    total_turn = 0
    total_turn_length_list = []
    for file in file_list:
        with open(f"{simulation_result_dir}/{file}/reasoning_trajectory.json",'r') as f:
            reasoning_trajectory = json.load(f)
        reasoning_trajectory = [reasoning for reasoning in reasoning_trajectory if reasoning['role'] == "assistant"]
        total_turn+=len(reasoning_trajectory)
    print(f"Average Reasoning: {total_turn/len(file_list)}")

def slot_alignment(simulation_result_dir):
    file_list = os.listdir(simulation_result_dir)
    trial_dict = {}
    false_list = []
    for file in file_list:
        with open(f"{simulation_result_dir}/{file}/goal_align_result.json",'r') as f:
            goal_align_result = json.load(f)
        # print(goal_align_result)

        with open(f"{simulation_result_dir}/{file}/reasoning_trajectory.json",'r') as f:
            reasoning_trajectory = json.load(f)

        if len(reasoning_trajectory)==0:
            continue

        if not goal_align_result['result']:
            false_list.append(file)

        if file[-1] not in trial_dict:
            trial_dict[file[-1]] = [goal_align_result['result']]
        else:
            trial_dict[file[-1]].append(goal_align_result['result'])

    score_list = []
    for trial in trial_dict:
        score_list.append(mean(trial_dict[trial])*100)
    # print(false_list)
    return score_list

def remaining_dialogue_state(simulation_path):
    file_list = os.listdir(simulation_path)
    cnt=0
    for file in file_list:
        with open(f"{simulation_path}/{file}/dialogue_state_list.json",'r') as f:
            dialogue_state_list = json.load(f)
        if len(dialogue_state_list['remaining_dialogue_state_list'])>0:
            print(file)
            cnt+=1
    print(f"Remaining dialogue state simulation: {cnt}")

# 실행
if __name__ == "__main__":
    import sys
    
    # 명령행 인자 확인
    if len(sys.argv) < 3:
        print("Usage: python3 success_eval.py <model_name> <yaml_file>", file=sys.stderr)
        sys.exit(1)
    model_name = sys.argv[1]
    yaml_file = sys.argv[2]
    
    # get_result_path.py에서 simulation_path 받아오기
    try:
        simulation_path = subprocess.check_output(['python3', 'get_result_path.py', model_name, yaml_file]).decode('utf-8').strip()
    except:
        simulation_path = "simulation_result"  # fallback
    print(f"Result of {simulation_path}")
    # print("===================================")
    
    # Success rate 계산
    success_score_list = evaluate_from_simulation_result(
        simulation_result_dir=simulation_path
    )
    
    # Pass rate 계산 (현재는 success rate와 동일하게 처리)
    pass_score_list = success_score_list.copy()
    
    # Goal alignment 계산
    goal_align_list = slot_alignment(simulation_result_dir=simulation_path)
    
    if success_score_list:
        print(f"success_rate_mean: {mean(success_score_list):.3f}")
        print(f"success_rate_values: {success_score_list}")
    if pass_score_list:
        print(f"pass_rate_mean: {mean(pass_score_list):.3f}")
        print(f"pass_rate_values: {pass_score_list}")
    if goal_align_list:
        print(f"goal_align_mean: {mean(goal_align_list):.3f}")
        print(f"goal_align_values: {goal_align_list}")

    average_reasoning_length(simulation_result_dir=simulation_path)
    print("Error Analysis:")
    error_analysis(simulation_path)
    print("------------------")
    print("Mistake Analysis")
    mistake_analysis(simulation_path)