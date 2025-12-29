import os,json

def api_miss_usage(default_path):

    with open("api_documentations/multiwoz_api_documentation.json",'r') as f:
        api_docs_list = json.load(f)

    api_docs_dict = {api_docs['api_name']:api_docs for api_docs in api_docs_list}
    api_name_list = [api_docs['api_name'] for api_docs in api_docs_list]

    api_format_error = 0
    api_hallucination_error = 0
    input_parameter_hallucination_error = 0
    input_parameter_type_error = 0
    
    # API call 중복 카운트를 위한 딕셔너리
    identical_api_calls = {}

    cnt=0
    total_generated_input_param_cnt=0
    n_simulation = 0
    for file in os.listdir(default_path):
        n_simulation+=1
        with open(f"{default_path}/{file}/api_call_log.json",'r') as f:
            api_call_log = json.load(f)

        # 총 생성한 parameter 수 집계
        for api_call in api_call_log:
            try:
                api_call = eval(api_call['call_log'])
            except:
                continue
            if "api_name" not in api_call or "input_parameters" not in api_call:
                continue

            if api_call['api_name'] in  ["show_app_description","show_api_description","show_api_docs"]:
                continue
            total_generated_input_param_cnt +=1

        for api_call in api_call_log:
            cnt+=1
            try:
                api_call = eval(api_call['call_log'])
                if "api_name" not in api_call or "input_parameters" not in api_call:
                    api_format_error+=1
                    continue
            except:
                api_format_error+=1
                continue

            if api_call['api_name'] in  ["show_app_description","show_api_description","show_api_docs"]:
                continue

            if api_call['api_name'] not in api_name_list:
                api_hallucination_error+=1
                continue
            
            # 1
            current_api_docs = api_docs_dict[api_call['api_name']]
            gt_input_parameter_list = [input_parameter['name'] for input_parameter in current_api_docs['parameters']]
            for input_parameter in api_call['input_parameters']:
                if input_parameter not in gt_input_parameter_list:
                    input_parameter_hallucination_error+=1
                    break

            input_parameter_type = {input_param['name']:input_param['type'] for input_param in current_api_docs['parameters']}
            input_parameter_category = {input_param['name']:input_param['constraints'] for input_param in current_api_docs['parameters']}
            for input_parameter in api_call['input_parameters']:
                if input_parameter not in gt_input_parameter_list:
                    break
                if input_parameter_type[input_parameter] == "int":
                    if not isinstance(api_call['input_parameters'][input_parameter],int):
                        input_parameter_type_error+=1
                        break
                if input_parameter_type[input_parameter] == "bool":
                    if not isinstance(api_call['input_parameters'][input_parameter],bool):
                        input_parameter_type_error+=1
                        break

                if isinstance(input_parameter_category[input_parameter],list) and len(input_parameter_category[input_parameter])>0:
                    if api_call['input_parameters'][input_parameter] not in input_parameter_category[input_parameter]:
                        input_parameter_type_error+=1
                        break

    duplicate_call_cnt = 0
    for file in os.listdir(default_path):
        with open(f"{default_path}/{file}/api_call_log.json",'r') as f:
            api_call_log = json.load(f)

        api_call_log_dict_list = []
        for call_log in api_call_log:
            try:
                current_call_log = eval(call_log['call_log'])
                current_call_log['input_parameters'] = dict(sorted(current_call_log['input_parameters'].items()))
                api_call_log_dict_list.append(current_call_log)
            except:
                continue

        call_log_cnt = {}
        for call_log in api_call_log_dict_list:
            if str(call_log) in call_log_cnt:
                call_log_cnt[str(call_log)]+=1
            else:
                call_log_cnt[str(call_log)]=1

        current_duplicated_call_cnt = sum(list(call_log_cnt.values())) - len(list(call_log_cnt.values()))
        duplicate_call_cnt+=current_duplicated_call_cnt

    total_helper_call_cnt = 0
    duplicate_helper_call_cnt = 0
    duplicate_helper_call_cnt_list = []
    for file in os.listdir(default_path):
        with open(f"{default_path}/{file}/api_call_log.json",'r') as f:
            api_call_log = json.load(f)

        api_call_log_dict_list = []
        for call_log in api_call_log:
            try:
                current_call_log = eval(call_log['call_log'])
                current_call_log['input_parameters'] = dict(sorted(current_call_log['input_parameters'].items()))
                if "show" in current_call_log['api_name']:
                    api_call_log_dict_list.append(current_call_log)
            except:
                continue

        call_log_cnt = {}
        for call_log in api_call_log_dict_list:
            if str(call_log) in call_log_cnt:
                call_log_cnt[str(call_log)]+=1
            else:
                call_log_cnt[str(call_log)]=1

        total_helper_call_cnt+=len(api_call_log_dict_list)
        current_duplicated_helper_call_cnt = sum(list(call_log_cnt.values())) - len(list(call_log_cnt.values()))
        duplicate_helper_call_cnt_list.append(current_duplicated_helper_call_cnt)

        duplicate_helper_call_cnt+=current_duplicated_helper_call_cnt

                        
    print(f"Total API call: {cnt}")
    print(f"API format Error: {api_format_error}")
    print(f"API Hallucination Error: {api_hallucination_error}")
    print(f"Input Parameter Hallucination Error: {input_parameter_hallucination_error/n_simulation}")
    print(f"API Utilization Missing: {input_parameter_type_error}")
    print(f"Dulicated API Call: {duplicate_call_cnt}")
    print(f"Dulicated Helper API Call: {duplicate_helper_call_cnt} / (Total: {total_helper_call_cnt})")
    print()
    print(f"Per simulation Total Helper call: {total_helper_call_cnt/len(os.listdir(default_path))}")
    print(f"Per simulation Duplicated Helper call: {duplicate_helper_call_cnt/len(os.listdir(default_path))}")
    print(f"Max duplicated helper call: {max(duplicate_helper_call_cnt_list)}")


import json,os,subprocess
from datetime import datetime
from tqdm import tqdm
from apis import *

def compare_time(time: str, gt_time: str, compare_type: str) -> bool:
    t1 = datetime.strptime(time, "%H:%M") ## pred
    t2 = datetime.strptime(gt_time, "%H:%M") ## gt
    if compare_type == "leaveAt":
        return t1 >= t2
    elif compare_type == "arriveBy":
        return t1 <= t2
    else:
        raise ValueError("compare_type must be leavAt or arriveBy")

def run_api(name,domain,dial_idx):
    if domain == "hotel":
        domain = "accommodation"
    if domain == "train":
        retrieve_slot = "train_schedule_id"
    else:
        retrieve_slot = "name"
        
    api_name = f"{domain}_retrieve"
    parameter_payload = str({retrieve_slot:name})
    dial_idx = dial_idx

    try:
        parameter_payload = eval(parameter_payload.replace("true","True").replace("false","False"))
    except Exception as e:
        print("During Run API -> "+str(e)) 
    result = globals()[api_name](**parameter_payload)
    result_to_return = result['result']
    if len(result_to_return)>0:
        return result_to_return[0]
    else:
        return {}

def grading_booking(default_path,dial_idx):
    with open(f"{default_path}/{dial_idx}/domains.json",'r') as f:
        domains_list = json.load(f)
    with open(f"{default_path}/{dial_idx}/goal_dict.json",'r') as f:
        goal_dict = json.load(f)
    
    filtered_goal = {domain:goal_dict[domain] for domain in domains_list}
    for domain in domains_list:
        for slot in filtered_goal[domain]:
            if "pre_invalid" in filtered_goal[domain][slot]:
                del filtered_goal[domain][slot]['pre_invalid']
            if "invalid" in filtered_goal[domain][slot]:
                del filtered_goal[domain][slot]['invalid']
    
    book_error_case = {"no_book":0,"wrong_book":0,"multi_book":0}

    # For three domain cases
    if "taxi" in domains_list and "restaurant" in domains_list and "accommodation" in domains_list:

        for domain in ['restaurant',"accommodation"]:
            with open(f"{default_path}/{dial_idx}/reservation/{domain}_book_db.json",'r') as f:
                current_book_db = json.load(f)

            ## 예약하는 게 goal에 없는데 예약이 된 상황
            if "book" not in filtered_goal[domain]:
                if len(current_book_db)>0:
                    continue
                elif len(current_book_db)==0:
                    ## 예약에 goal이 없는데 예약을 안했으니 correct임
                    continue
            elif not filtered_goal[domain]['book']:
                if len(current_book_db)>0:
                    continue
                elif len(current_book_db)==0:
                    ## 예약에 goal이 없는데 예약을 안했으니 correct임
                    continue

            ## no_book
            if "book" in filtered_goal[domain]:
                if filtered_goal[domain]['book']:
                    if len(current_book_db)==0:
                        book_error_case['no_book']+=1
                        continue

            ## multi_book
            if len(current_book_db)>1:
                # print(default_path)
                book_error_case['multi_book']+=1
            
            ## GT goal을 해당 domain꺼만 남김
            answer_goal = filtered_goal[domain]

            ## 예약된 entity가 user조건과 만족하는지 비교
            for book_entity in current_book_db:
                # current_book_db = current_book_db[0]

                current_entity_name = book_entity['name']

                try:
                    entity_stats = run_api(current_entity_name,domain,dial_idx)
                except:
                    with open("whatiswrong_on_grading_booking.txt",'w') as f:
                        f.write(f"{current_entity_name}_{domain}_{dial_idx}")
                    book_error_case['wrong_book']+=1
                    continue
                cnt=0

                for slot in answer_goal['info']:
                    if answer_goal['info'][slot] == str(entity_stats[slot]):
                        cnt+=1

                if len(answer_goal['info']) != cnt:
                    if len(answer_goal['info']) <= cnt:
                        raise IndexError("Cnt can't be larger than number of slots of info")
                    elif len(answer_goal['info']) >= cnt:
                        book_error_case['wrong_book']+=1
                        continue

                ## 예약을 알맞는 조건으로 했는지 비교
                for slot in answer_goal['book']:
                    if slot == "invalid" or slot == "pre_invalid":
                        continue
                    if answer_goal['book'][slot] != str(book_entity[slot]):
                        book_error_case['wrong_book']+=1
                        break

        ## 이제 택시 채점
        with open(f"{default_path}/{dial_idx}/reservation/taxi_book_db.json",'r') as f:
            current_book_db = json.load(f)

        if len(current_book_db) == 0:
            book_error_case['no_book']+=1
            return book_error_case

        if len(current_book_db) > 1:
            book_error_case['multi_book']+=1

        for book_entity in current_book_db:
            if "destination" not in book_entity and "departure" not in book_entity:
                book_error_case['wrong_book']+=1
                continue
            
            # destination
            entity_stats = run_api(book_entity["destination"],"restaurant",dial_idx)
            if len(entity_stats)==0:
                book_error_case['wrong_book']+=1
                continue
            else:
                answer_goal = filtered_goal["restaurant"]
                cnt=0
                for slot in answer_goal['info']:
                    if answer_goal['info'][slot] == str(entity_stats[slot]):
                        cnt+=1
                
                pass_ind = False
                if len(answer_goal['info']) != cnt:
                    if len(answer_goal['info']) <= cnt:
                        raise IndexError("Cnt can't be larger than number of slots of info")
                    elif len(answer_goal['info']) >= cnt:
                        book_error_case['wrong_book']+=1
                        pass_ind = True
                        break
                if pass_ind:
                    continue

            # departure
            entity_stats = run_api(book_entity["departure"],"accommodation",dial_idx)
            if len(entity_stats)==0:
                book_error_case['wrong_book']+=1
                continue
            else:
                answer_goal = filtered_goal["accommodation"]
                cnt=0
                for slot in answer_goal['info']:
                    if answer_goal['info'][slot] == str(entity_stats[slot]):
                        cnt+=1
                pass_ind = False
                if len(answer_goal['info']) != cnt:
                    if len(answer_goal['info']) <= cnt:
                        raise IndexError("Cnt can't be larger than number of slots of info")
                    elif len(answer_goal['info']) >= cnt:
                        book_error_case['wrong_book']+=1
                        pass_ind=True
                        # break
                if pass_ind:
                    continue


            # leaveAt or arriveBy
            if "leaveAt" in filtered_goal['taxi']:
                if filtered_goal['taxi']['leaveAt'] != book_entity['leaveAt']:
                    book_error_case['wrong_book']+=1
                    continue
            if "arriveBy" in filtered_goal['taxi']:
                if filtered_goal['taxi']['arriveBy'] != book_entity['arriveBy']:
                    book_error_case['wrong_book']+=1
                    continue
            
        return book_error_case

    for domain in domains_list:
        ## att는 book slot이 없음
        if domain == "attraction":
            continue
        
        ## 예약 DB를 불러옴
        with open(f"{default_path}/{dial_idx}/reservation/{domain}_book_db.json",'r') as f:
            current_book_db = json.load(f)

        ## 예약하는게 goal에 있는데 예약이 아예 안된 상황
        if "book" in filtered_goal[domain]:
            if filtered_goal[domain]['book']:
                if len(current_book_db)==0:
                    book_error_case['no_book']+=1
                    continue     
        
        ## 보통 한 domain에 예약은 한 개만 함 아마(?)
        if len(current_book_db)>1:
            # print(dial_idx)
            book_error_case['multi_book']+=1
          
        
        ## GT goal을 해당 domain꺼만 남김
        answer_goal = filtered_goal[domain]
        
        for book_entity in current_book_db:
            ## 예약된 entity가 user조건과 만족하는지 비교
            
            ## 여기서 taxi, train, 그 외를 다르게 처리해줘야 함
            if domain != "taxi":
                current_entity_name = book_entity['name'] if domain != "train" else book_entity['train_schedule_id']
                entity_stats = run_api(current_entity_name,domain,dial_idx)
                cnt=0
                for slot in answer_goal['info']:
                    ## time 관련 slot의 처리
                    if slot in ["arriveBy","leaveAt"]:
                        if compare_time(time=str(entity_stats[slot]),gt_time=answer_goal['info'][slot],compare_type=slot):
                            cnt+=1

                    ## 그 외 slot 관련 처리.
                    else:
                        if answer_goal['info'][slot] == str(entity_stats[slot]):
                            cnt+=1

                if len(answer_goal['info']) != cnt:
                    if len(answer_goal['info']) <= cnt:
                        raise IndexError("Cnt can't be larger than number of slots of info")
                    elif len(answer_goal['info']) >= cnt:
                        book_error_case['wrong_book']+=1
                        continue

                ## 예약을 알맞는 조건으로 했는지 비교
                pass_ind=False
                for slot in answer_goal['book']:
                    if slot == "invalid" or slot == "pre_invalid":
                        continue
                    if answer_goal['book'][slot] != str(book_entity[slot]):
                        book_error_case['wrong_book']+=1
                        pass_ind=True
                        break
                if pass_ind:
                    continue
            else: ## taxi일 때
                pass_ind=False
                for slot in answer_goal['book']:
                    if slot == "invalid" or slot == "pre_invalid":
                        continue
                    ## time 관련 slot의 처리
                    if slot in ["arriveBy","leaveAt"]:
                        if book_entity[slot]: ## 예약한 instance에 time이 null이 아닐 때때
                            if not compare_time(time=str(book_entity[slot]),gt_time=answer_goal['book'][slot],compare_type=slot):
                                book_error_case['wrong_book']+=1
                                pass_ind=True
                                break
                        else: ## answer의 slot에 있는 건데, 그게 none이면 틀린거지
                            book_error_case['wrong_book']+=1
                            pass_ind=True
                            break

                    ## time 관련 slot 아닌거 처리.
                    else:
                        if answer_goal['book'][slot].lower() != str(book_entity[slot]).lower():
                            book_error_case['wrong_book']+=1
                            pass_ind=True
                            break
                if pass_ind:
                    continue
                
    return book_error_case

def grading_booking_specified(default_path,dial_idx):
    with open(f"{default_path}/{dial_idx}/domains.json",'r') as f:
        domains_list = json.load(f)
    with open(f"{default_path}/{dial_idx}/goal_dict.json",'r') as f:
        goal_dict = json.load(f)
    
    ## raw goal에서 현재 dial_idx에 해당하는 domain만 가져옴
    filtered_goal = {domain:goal_dict[domain] for domain in domains_list}
    # ["pre_invalid","invalid"] slot 제거
    for domain in domains_list:
        for slot in filtered_goal[domain]:
            if "pre_invalid" in filtered_goal[domain][slot]:
                del filtered_goal[domain][slot]['pre_invalid']
            if "invalid" in filtered_goal[domain][slot]:
                del filtered_goal[domain][slot]['invalid']
    
    # correct_dict = {domain:True for domain in domains_list if domain != "attraction"}
    book_error_case = {"no_book":0,"wrong_book":0,"multi_book":0}

    # 도메인 세개 있는 건 예외 case로 따로 채점함
    if "taxi" in domains_list and "restaurant" in domains_list and "accommodation" in domains_list:

        # 여기서 restaurant, accommodation 먼저 채점.
        for domain in ['restaurant',"accommodation"]:
            domain_has_wrong_book = False
            
            ## 예약 DB를 불러옴
            with open(f"{default_path}/{dial_idx}/reservation/{domain}_book_db.json",'r') as f:
                current_book_db = json.load(f)

            ## 예약하는 게 goal에 없는데 예약이 된 상황
            if "book" not in filtered_goal[domain]:
                if len(current_book_db)>0:
                    continue
                elif len(current_book_db)==0:
                    ## 예약에 goal이 없는데 예약을 안했으니 correct임
                    continue
            elif not filtered_goal[domain]['book']:
                if len(current_book_db)>0:
                    continue
                elif len(current_book_db)==0:
                    ## 예약에 goal이 없는데 예약을 안했으니 correct임
                    continue

            ## no_book
            if "book" in filtered_goal[domain]:
                if filtered_goal[domain]['book']:
                    if len(current_book_db)==0:
                        book_error_case['no_book']+=1
                        continue

            ## multi_book
            if len(current_book_db)>1:
                # print(default_path)
                book_error_case['multi_book']+=1
            
            ## GT goal을 해당 domain꺼만 남김
            answer_goal = filtered_goal[domain]

            ## 예약된 entity가 user조건과 만족하는지 비교
            for book_entity in current_book_db:
                current_entity_name = book_entity['name']

                try:
                    entity_stats = run_api(current_entity_name,domain,dial_idx)
                except:
                    with open("whatiswrong_on_grading_booking.txt",'w') as f:
                        f.write(f"{current_entity_name}_{domain}_{dial_idx}")
                    domain_has_wrong_book = True
                    continue
                cnt=0

                for slot in answer_goal['info']:
                    if answer_goal['info'][slot] == str(entity_stats[slot]):
                        cnt+=1

                if len(answer_goal['info']) != cnt:
                    if len(answer_goal['info']) <= cnt:
                        raise IndexError("Cnt can't be larger than number of slots of info")
                    elif len(answer_goal['info']) >= cnt:
                        domain_has_wrong_book = True
                        continue

                ## 예약을 알맞는 조건으로 했는지 비교
                for slot in answer_goal['book']:
                    if slot == "invalid" or slot == "pre_invalid":
                        continue
                    if answer_goal['book'][slot] != str(book_entity[slot]):
                        domain_has_wrong_book = True
                        break
            
            # 도메인별로 한 번만 카운트
            if domain_has_wrong_book:
                book_error_case['wrong_book']+=1

        ## 이제 택시 채점
        taxi_has_wrong_book = False
        with open(f"{default_path}/{dial_idx}/reservation/taxi_book_db.json",'r') as f:
            current_book_db = json.load(f)

        if len(current_book_db) == 0:
            book_error_case['no_book']+=1
            return book_error_case

        if len(current_book_db) > 1:
            book_error_case['multi_book']+=1

        for book_entity in current_book_db:
            if "destination" not in book_entity and "departure" not in book_entity:
                taxi_has_wrong_book = True
                break
            
            # destination
            entity_stats = run_api(book_entity["destination"],"restaurant",dial_idx)
            if len(entity_stats)==0:
                taxi_has_wrong_book = True
                break
            else:
                answer_goal = filtered_goal["restaurant"]
                cnt=0
                for slot in answer_goal['info']:
                    if answer_goal['info'][slot] == str(entity_stats[slot]):
                        cnt+=1
                
                if len(answer_goal['info']) != cnt:
                    if len(answer_goal['info']) <= cnt:
                        raise IndexError("Cnt can't be larger than number of slots of info")
                    elif len(answer_goal['info']) >= cnt:
                        taxi_has_wrong_book = True
                        break

            # departure
            entity_stats = run_api(book_entity["departure"],"accommodation",dial_idx)
            if len(entity_stats)==0:
                taxi_has_wrong_book = True
                break
            else:
                answer_goal = filtered_goal["accommodation"]
                cnt=0
                for slot in answer_goal['info']:
                    if answer_goal['info'][slot] == str(entity_stats[slot]):
                        cnt+=1
                if len(answer_goal['info']) != cnt:
                    if len(answer_goal['info']) <= cnt:
                        raise IndexError("Cnt can't be larger than number of slots of info")
                    elif len(answer_goal['info']) >= cnt:
                        taxi_has_wrong_book = True
                        break

            # leaveAt or arriveBy
            if "leaveAt" in filtered_goal['taxi']:
                if filtered_goal['taxi']['leaveAt'] != book_entity['leaveAt']:
                    taxi_has_wrong_book = True
                    continue
            if "arriveBy" in filtered_goal['taxi']:
                if filtered_goal['taxi']['arriveBy'] != book_entity['arriveBy']:
                    taxi_has_wrong_book = True
                    continue
        
        # 택시 도메인별로 한 번만 카운트
        if taxi_has_wrong_book:
            book_error_case['wrong_book']+=1
            
        return book_error_case

    for domain in domains_list:
        ## att는 book slot이 없음
        if domain == "attraction":
            continue
        
        domain_has_wrong_book = False
        
        ## 예약 DB를 불러옴
        with open(f"{default_path}/{dial_idx}/reservation/{domain}_book_db.json",'r') as f:
            current_book_db = json.load(f)

        ## 예약하는게 goal에 있는데 예약이 아예 안된 상황
        if "book" in filtered_goal[domain]:
            if filtered_goal[domain]['book']:
                if len(current_book_db)==0:
                    book_error_case['no_book']+=1
                    continue     
        
        ## 보통 한 domain에 예약은 한 개만 함 아마(?)
        if len(current_book_db)>1:
            # print(dial_idx)
            book_error_case['multi_book']+=1
          
        
        ## GT goal을 해당 domain꺼만 남김
        answer_goal = filtered_goal[domain]
        
        for book_entity in current_book_db:
            ## 예약된 entity가 user조건과 만족하는지 비교
            
            ## 여기서 taxi, train, 그 외를 다르게 처리해줘야 함
            if domain != "taxi":
                current_entity_name = book_entity['name'] if domain != "train" else book_entity['train_schedule_id']
                entity_stats = run_api(current_entity_name,domain,dial_idx)
                cnt=0
                for slot in answer_goal['info']:
                    ## time 관련 slot의 처리
                    if slot in ["arriveBy","leaveAt"]:
                        if compare_time(time=str(entity_stats[slot]),gt_time=answer_goal['info'][slot],compare_type=slot):
                            cnt+=1

                    ## 그 외 slot 관련 처리.
                    else:
                        if answer_goal['info'][slot] == str(entity_stats[slot]):
                            cnt+=1

                if len(answer_goal['info']) != cnt:
                    if len(answer_goal['info']) <= cnt:
                        raise IndexError("Cnt can't be larger than number of slots of info")
                    elif len(answer_goal['info']) >= cnt:
                        domain_has_wrong_book = True
                        break

                ## 예약을 알맞는 조건으로 했는지 비교
                for slot in answer_goal['book']:
                    if slot == "invalid" or slot == "pre_invalid":
                        continue
                    if answer_goal['book'][slot] != str(book_entity[slot]):
                        domain_has_wrong_book = True
                        break
                if domain_has_wrong_book:
                    break
            else: ## taxi일 때
                for slot in answer_goal['book']:
                    if slot == "invalid" or slot == "pre_invalid":
                        continue
                    ## time 관련 slot의 처리
                    if slot in ["arriveBy","leaveAt"]:
                        if book_entity[slot]: ## 예약한 instance에 time이 null이 아닐 때때
                            if not compare_time(time=str(book_entity[slot]),gt_time=answer_goal['book'][slot],compare_type=slot):
                                domain_has_wrong_book = True
                                break
                        else: ## answer의 slot에 있는 건데, 그게 none이면 틀린거지
                            domain_has_wrong_book = True
                            break

                    ## time 관련 slot 아닌거 처리.
                    else:
                        if answer_goal['book'][slot].lower() != str(book_entity[slot]).lower():
                            domain_has_wrong_book = True
                            break
                if domain_has_wrong_book:
                    break
        
        # 도메인별로 한 번만 카운트
        if domain_has_wrong_book:
            book_error_case['wrong_book']+=1
                
    return book_error_case



def misbehavior_category(default_path):
    book_error_case_list = []
    task_cnt = 0
    wrong_cnt = 0
    for file in os.listdir(f"{default_path}"):
        task_cnt+=1
        
        try:
            with open(f"{default_path}/{file}/pass_or_fail.txt",'r') as f:
                pass_or_fail = f.read()
        except:
            continue
        if pass_or_fail == "PASS":
            continue
        wrong_cnt+=1

        book_error_case_list.append(grading_booking_specified(default_path,file))
    all_keys = book_error_case_list[0].keys()
    total_counts = {k: sum(d[k] for d in book_error_case_list) for k in all_keys}
    print(f"Total wrong cnt: {sum(total_counts.values())}")
    print(total_counts)