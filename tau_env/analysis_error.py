# 아마 gt
from tau_bench.envs.airline.tasks_test import TASKS
from tau_bench.envs.retail.tasks_test import TASKS_TEST
import json,os
from statistics import mean
from copy import deepcopy
from collections import Counter

def gt_api_call_function(task):
    action_list = []
    for action in task.actions:
        current_action = {"name":action.name,"arguments":action.kwargs}
        action_list.append(current_action)
    return action_list

def predict_api_call_function(reasoning_trajectory):
    action_list = []
    for reasoning in reasoning_trajectory:
        if reasoning['role'] == "assistant":
            try:
                # print("Before eval")
                current_action = eval(reasoning['content'].split("Action:\n")[-1].strip().replace("""input("Please provide your email address to proceed: ")""","Please provide your email address to proceed: "))
                # print("After eval")
            except:
                continue
            if current_action:
                if "name" in current_action:
                    if current_action['name'] != "respond":
                        action_list.append(current_action)

    return action_list

def error_analysis(simulation_path):
    # 이름 api docs 에 다 있는 것 검증함
    write_api_list = [
        "cancel_pending_order",
        "exchange_delivered_order_items",
        "modify_pending_order_address",
        "modify_pending_order_items",
        "modify_pending_order_payment",
        "modify_user_address",
        "return_delivered_order_items",
        "book_reservation",
        "cancel_reservation",
        "send_certificate",
        "update_reservation_baggages",
        "update_reservation_flights",
        "update_reservation_passengers"
    ]

    # dialgue state 모두 제공 x인 경우
    file_list = os.listdir(simulation_path)
    cnt=0

    error_category = {
        "parse_error":0,
        "no_gt_api":0,
        "gt_api_parameter_error":0,
        "invalid_write_api":0,
        "total_duplicated_api":0
    }

    for file in file_list:
        domain,task_idx,n_trial = file.split("_")[0],file.split("_")[1],file.split("_")[2]
        with open(f"{simulation_path}/{file}/dialogue_state_list.json",'r') as f:
            dialogue_state_list = json.load(f)
        with open(f"{simulation_path}/{file}/reasoning_trajectory.json",'r') as f:
            resoning_trajectory = json.load(f)
        with open(f"{simulation_path}/{file}/eval_result.json",'r') as f:
            eval_result = json.load(f)

        if len(dialogue_state_list['remaining_dialogue_state_list'])>0:
            if "error" not in eval_result["info"]:
                if resoning_trajectory[-1]['content'] != "API output: Transfer successful":
                    cnt+=1

    wrong_file_idx_list = []
    for file in file_list:
        with open(f"{simulation_path}/{file}/eval_result.json",'r') as f:
            eval_result = json.load(f)
        if eval_result['reward'] == 0:
            wrong_file_idx_list.append(file)

    all_error_cnt = len(wrong_file_idx_list)
    # print("---------------------------------")

    # 중간에 에러나서 틀린 경우
    parse_error_list = []
    for file in wrong_file_idx_list:
        domain,task_idx,n_trial = file.split("_")[0],file.split("_")[1],file.split("_")[2]
        with open(f"{simulation_path}/{file}/eval_result.json",'r') as f:
            eval_result = json.load(f)
        if "error" in eval_result["info"]:
            parse_error_list.append(file)

    wrong_file_idx_list = [file_idx for file_idx in wrong_file_idx_list if file_idx not in parse_error_list]
    print(f"Parse Error: {len(parse_error_list)}")
    error_category["parse_error"]+=len(parse_error_list)

    human_transfer_error_list = []
    for file in wrong_file_idx_list:
        domain,task_idx,n_trial = file.split("_")[0],file.split("_")[1],file.split("_")[2]
        with open(f"{simulation_path}/{file}/eval_result.json",'r') as f:
            eval_result = json.load(f)

        with open(f"{simulation_path}/{file}/reasoning_trajectory.json",'r') as f:
            resoning_trajectory = json.load(f)

        if len(resoning_trajectory)>0 and eval_result['reward'] == 0 and resoning_trajectory[-1]['content'] == "API output: Transfer successful":
            human_transfer_error_list.append(file)

    wrong_file_idx_list = [file_idx for file_idx in wrong_file_idx_list if file_idx not in human_transfer_error_list]
    no_gt_api_error_list = []

    for file in wrong_file_idx_list:
        domain,task_idx,n_trial = file.split("_")[0],file.split("_")[1],file.split("_")[2]
        if domain == "airline":
            gt_task_list = TASKS
        else:
            gt_task_list = TASKS_TEST

        with open(f"{domain}_api_documentation_list.json",'r') as f:
            api_docs_list = json.load(f)

        with open(f"{simulation_path}/{file}/reasoning_trajectory.json",'r') as f:
            resoning_trajectory = json.load(f)
        
        gt_task = gt_task_list[int(task_idx)]
        gt_api_call_list = gt_api_call_function(gt_task)
        gt_api_call_list = [api_call for api_call in gt_api_call_list if api_call['name'] in write_api_list]

        predict_api_call_list = predict_api_call_function(resoning_trajectory)

        gt_api_name_list = [api_call['name'] for api_call in gt_api_call_list]
        predict_api_name_list = [api_call['name'] for api_call in predict_api_call_list]

        # 종류가 다 있어야 하고, call횟수가 다 맞아야 함
        gt_api_name_counter = dict(Counter(gt_api_name_list))
        predict_api_name_counter = dict(Counter(predict_api_name_list))
        correct_cnt = 0
        for api_name in gt_api_name_counter:
            if api_name in predict_api_name_counter:
                if predict_api_name_counter[api_name] == gt_api_name_counter[api_name]:
                    correct_cnt+=1

        if correct_cnt>0:
            if correct_cnt != len(gt_api_name_counter):
                no_gt_api_error_list.append(file)
        else:  
            if len(gt_api_name_list)>0: # 진짜 맞은게 없어서 0
                no_gt_api_error_list.append(file)
            else: # gt api가 빈 경우가 있음. 이럴 땐, write api call만 안했으면 됨
                None
                # for predict_api_name in predict_api_name_list:
                #     if predict_api_name in write_api_list:
                #         no_gt_api_error_list.append(file)
                #         break        

    print(f"No GT API Error: {len(no_gt_api_error_list)}")
    print(f"Ratio: {len(set(no_gt_api_error_list))/len(wrong_file_idx_list)}")
    print()
    error_category["no_gt_api"]+=len(no_gt_api_error_list)

    # predict의 call 중, gt에 이름이 있는 건데, parameter가 잘못된 경우

    api_parameter_error_list = []

    for idx,file in enumerate(wrong_file_idx_list):
        domain,task_idx,n_trial = file.split("_")[0],file.split("_")[1],file.split("_")[2]
        if domain == "airline":
            gt_task_list = TASKS
        else:
            gt_task_list = TASKS_TEST

        with open(f"{domain}_api_documentation_list.json",'r') as f:
            api_docs_list = json.load(f)

        with open(f"{simulation_path}/{file}/reasoning_trajectory.json",'r') as f:
            resoning_trajectory = json.load(f)

        gt_task = gt_task_list[int(task_idx)]
        gt_api_call_list = gt_api_call_function(gt_task)
        gt_api_call_list = [api_call for api_call in gt_api_call_list if api_call['name'] in write_api_list]
        predict_api_call_list = predict_api_call_function(resoning_trajectory)


        total_cnt=0
        correct_cnt=0
        for predict_api_call in predict_api_call_list:
            current_gt_api_call_list = [
                api_call for api_call in gt_api_call_list if api_call['name'] == predict_api_call['name']
            ]
            
            # predict call이 gt에 있긴 있는 경우만 포함시켜야함.
            if len(current_gt_api_call_list)==0:
                continue
            
            total_cnt+=1
            ind=False
            for gt_api_call in current_gt_api_call_list:
                if "kwargs" in gt_api_call:
                    gt_api_call['arguments'] = deepcopy(gt_api_call['kwargs'])
                    del gt_api_call['kwargs']
                if gt_api_call == predict_api_call:
                    correct_cnt+=1
                    break
        if total_cnt != correct_cnt:
            api_parameter_error_list.append(file)

    print(f"GT and predict parameter error: {len(api_parameter_error_list)}")
    print(f"Ratio: {len(set(api_parameter_error_list))/len(wrong_file_idx_list)}")
    print()
    error_category['gt_api_parameter_error']+=len(api_parameter_error_list)

    invalid_write_api_error_list = []

    for idx,file in enumerate(wrong_file_idx_list):
        domain,task_idx,n_trial = file.split("_")[0],file.split("_")[1],file.split("_")[2]
        if domain == "airline":
            gt_task_list = TASKS
        else:
            gt_task_list = TASKS_TEST

        with open(f"{domain}_api_documentation_list.json",'r') as f:
            api_docs_list = json.load(f)

        with open(f"{simulation_path}/{file}/reasoning_trajectory.json",'r') as f:
            resoning_trajectory = json.load(f)

        gt_task = gt_task_list[int(task_idx)]
        gt_api_call_list = gt_api_call_function(gt_task)
        gt_api_call_list = [api_call for api_call in gt_api_call_list if api_call['name'] in write_api_list]
        predict_api_call_list = predict_api_call_function(resoning_trajectory)

        gt_api_name_list = [api_call['name'] for api_call in gt_api_call_list]
        predict_api_name_list = [api_call['name'] for api_call in predict_api_call_list]

        for predict_api_name in predict_api_name_list:
            if predict_api_name not in gt_api_name_list and predict_api_name in write_api_list:
                invalid_write_api_error_list.append(file)
                break

    print(f"Invalid write api error: {len(invalid_write_api_error_list)}")
    print(f"Ratio: {len(set(invalid_write_api_error_list))/len(wrong_file_idx_list)}")
    print()
    error_category['invalid_write_api']+=len(invalid_write_api_error_list)

    # duplicate
    duplicate_api_error_list = []
    total_duplicate_calls = 0
    
    # for idx,file in enumerate(wrong_file_idx_list):
    for idx,file in enumerate(file_list):
        # print(file)
        domain,task_idx,n_trial = file.split("_")[0],file.split("_")[1],file.split("_")[2]
        if domain == "airline":
            gt_task_list = TASKS
        else:
            gt_task_list = TASKS_TEST

        with open(f"{domain}_api_documentation_list.json",'r') as f:
            api_docs_list = json.load(f)

        with open(f"{simulation_path}/{file}/reasoning_trajectory.json",'r') as f:
            resoning_trajectory = json.load(f)
    

        predict_api_call_list = predict_api_call_function(resoning_trajectory)
        
        # 중복된 API call 체크 (같은 API 이름 + 같은 arguments)
        from collections import defaultdict
        api_call_count = defaultdict(int)
        duplicate_calls = []
        
        # 각 API call의 발생 횟수 세기
        for api_call in predict_api_call_list:
            api_signature = (api_call['name'], str(sorted(api_call['arguments'].items())))
            api_call_count[api_signature] += 1
        
        # 2회 이상 호출된 API들 찾기
        file_duplicate_count = 0
        for api_signature, count in api_call_count.items():
            if count > 1:
                duplicate_calls.append((api_signature, count))
                file_duplicate_count += (count - 1)  # 중복 횟수는 (전체 호출 - 1)
        
        if duplicate_calls:
            duplicate_api_error_list.append(file)
            total_duplicate_calls += file_duplicate_count

    error_123_list = list(set(no_gt_api_error_list+api_parameter_error_list+invalid_write_api_error_list+duplicate_api_error_list))
    remaining_list = [file for file in wrong_file_idx_list if file not in error_123_list]

    total_misbehavior_cnt = 0
    print()
    for category in error_category:
        if category == "total_duplicated_api":
            continue
        print(f'{category}: {error_category[category]}')
        total_misbehavior_cnt+=error_category[category]
    print("-------------------------------------")
    print(f"Total Error: {all_error_cnt}")
    print(f"Total misbehavior cnt: {total_misbehavior_cnt}")
    print(f"Misbehavior per simulation: {total_misbehavior_cnt/len(wrong_file_idx_list)}")
    print("-------------------------------------")
    print(f"Total duplicate API calls: {total_duplicate_calls}")