import json,os,subprocess
from datetime import datetime
from tqdm import tqdm

def compare_time(time: str, gt_time: str, compare_type: str) -> bool:
    # "hh:mm" 형식의 문자열을 datetime 객체로 파싱
    t1 = datetime.strptime(time, "%H:%M") ## pred
    t2 = datetime.strptime(gt_time, "%H:%M") ## gt
    if compare_type == "leaveAt": ## leaveAt 때는 pred가 gt보다 크거나 같으면 true
        return t1 >= t2
    elif compare_type == "arriveBy": ## arriveBy 때는 pred가 gt보다 작거나 같으면 true
        return t1 <= t2
    else:
        raise ValueError("compare_type must be leavAt or arriveBy")

def run_api(name,domain,dial_idx, experiment_path):
    if domain == "hotel":
        domain = "accommodation"
    if domain == "train":
        retrieve_slot = "train_schedule_id"
    else:
        retrieve_slot = "name"
        
    result = subprocess.run(
        ["python", f"{experiment_path}/{dial_idx}/run_api.py", f"{domain}_retrieve", str({retrieve_slot:name}), dial_idx, experiment_path],
        capture_output=True,
        text=True
    )
    print(eval(result.stdout.strip().replace("true","True").replace("false","False").replace("null","None")))
    result_to_return = eval(result.stdout.strip().replace("true","True").replace("false","False").replace("null","None"))['result']
    if len(result_to_return)>0:
        return result_to_return[0]
    else:
        return {}
    # return eval(result.stdout.strip().replace("true","True").replace("false","False").replace("null","None"))['result'][0]

def grading_booking(dial_idx, experiment_path):
    with open(f"{experiment_path}/{str(dial_idx)}/domains.json",'r') as f:
        domains_list = json.load(f)
    with open(f"{experiment_path}/{str(dial_idx)}/goal_dict.json",'r') as f:
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
    
    ### Booking checking, 일단 모든 domain 별로 다 맞았다고 초기화 (attraction은 어차피 book이 없음)
    correct_dict = {domain:True for domain in domains_list if domain != "attraction"}

    # 도메인 세개 있는 건 예외 case로 따로 채점함
    if "taxi" in domains_list and "restaurant" in domains_list and "accommodation" in domains_list:

        # 여기서 restaurant, accommodation 먼저 채점.
        for domain in ['restaurant',"accommodation"]:
            ## 예약 DB를 불러옴
            with open(f"{experiment_path}/{str(dial_idx)}/reservation/{domain}_book_db.json",'r') as f:
                current_book_db = json.load(f)

            ## 보통 한 domain에 예약은 한 개만 함 아마(?)
            if len(current_book_db)>1:
                correct_dict[domain] = False
                continue

            ## 예약하는 게 goal에 없는데 예약이 된 상황
            if "book" not in filtered_goal[domain]:
                if len(current_book_db)>0:
                    correct_dict[domain] = False
                    continue
                elif len(current_book_db)==0:
                    ## 예약에 goal이 없는데 예약을 안했으니 correct임
                    continue
            elif not filtered_goal[domain]['book']:
                if len(current_book_db)>0:
                    correct_dict[domain] = False
                    continue
                elif len(current_book_db)==0:
                    ## 예약에 goal이 없는데 예약을 안했으니 correct임
                    continue

            ## 예약하는게 goal에 있는데 예약이 아예 안된 상황
            if "book" in filtered_goal[domain]:
                if filtered_goal[domain]['book']:
                    if len(current_book_db)==0:
                        correct_dict[domain] = False
                        continue
            
            ## GT goal을 해당 domain꺼만 남김
            answer_goal = filtered_goal[domain]

            ## 예약된 entity가 user조건과 만족하는지 비교
            current_book_db = current_book_db[0]

            current_entity_name = current_book_db['name']

            try:
                entity_stats = run_api(current_entity_name,domain,dial_idx, experiment_path)
            except:
                with open("whatiswrong_on_grading_booking.txt",'w') as f:
                    f.write(f"{current_entity_name}_{domain}_{dial_idx}")
                correct_dict[domain]=False
            cnt=0

            for slot in answer_goal['info']:
                if answer_goal['info'][slot] == str(entity_stats[slot]):
                    cnt+=1

            if len(answer_goal['info']) != cnt:
                if len(answer_goal['info']) <= cnt:
                    raise IndexError("Cnt can't be larger than number of slots of info")
                elif len(answer_goal['info']) >= cnt:
                    correct_dict[domain]=False

            ## 예약을 알맞는 조건으로 했는지 비교
            for slot in answer_goal['book']:
                if slot == "invalid" or slot == "pre_invalid":
                    continue
                if answer_goal['book'][slot] != str(current_book_db[slot]):
                    correct_dict[domain]=False
                    break

        # 하나라도 틀렸으면 taxi는 채점할 필요도 없음.
        if correct_dict['accommodation'] == False or correct_dict['restaurant'] == False:
            correct_dict["taxi"]=False
            return correct_dict

        ## 이제 택시 채점
        with open(f"{experiment_path}/{str(dial_idx)}/reservation/taxi_book_db.json",'r') as f:
            current_book_db = json.load(f)

        if len(current_book_db) != 1:
            correct_dict["taxi"]=False
            return correct_dict

        current_book_db = current_book_db[0]

        if "destination" not in current_book_db and "departure" not in current_book_db:
            correct_dict['taxi'] = False
        
        # destination
        entity_stats = run_api(current_book_db["destination"],"restaurant",dial_idx, experiment_path)
        if len(entity_stats)==0:
            correct_dict["taxi"]=False
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
                    correct_dict["taxi"]=False

        # departure
        entity_stats = run_api(current_book_db["departure"],"accommodation",dial_idx, experiment_path)
        if len(entity_stats)==0:
            correct_dict["taxi"]=False
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
                    correct_dict["taxi"]=False

        # leaveAt or arriveBy
        if "leaveAt" in filtered_goal['taxi']:
            if filtered_goal['taxi']['leaveAt'] != current_book_db['leaveAt']:
                correct_dict["taxi"]=False
        if "arriveBy" in filtered_goal['taxi']:
            if filtered_goal['taxi']['arriveBy'] != current_book_db['arriveBy']:
                correct_dict["taxi"]=False
        
        correct_dict = {("accommodation" if key == "hotel" else key):value for key,value in correct_dict.items()}
        return correct_dict


    for domain in domains_list:
        ## att는 book slot이 없음
        if domain == "attraction":
            continue
        
        ## 예약 DB를 불러옴
        with open(f"{experiment_path}/{str(dial_idx)}/reservation/{domain}_book_db.json",'r') as f:
            current_book_db = json.load(f)
        
        ## 보통 한 domain에 예약은 한 개만 함 아마(?)
        if len(current_book_db)>1:
            correct_dict[domain] = False
            continue        
        
        ## 예약하는 게 goal에 없는데 예약이 된 상황
        if "book" not in filtered_goal[domain]:
            if len(current_book_db)>0:
                correct_dict[domain] = False
                continue
            elif len(current_book_db)==0:
                ## 예약에 goal이 없는데 예약을 안했으니 correct임
                continue
        elif not filtered_goal[domain]['book']:
            if len(current_book_db)>0:
                correct_dict[domain] = False
                continue
            elif len(current_book_db)==0:
                ## 예약에 goal이 없는데 예약을 안했으니 correct임
                continue
        
        ## 예약하는게 goal에 있는데 예약이 아예 안된 상황
        if "book" in filtered_goal[domain]:
            if filtered_goal[domain]['book']:
                if len(current_book_db)==0:
                    correct_dict[domain] = False
                    continue       
        
        ## GT goal을 해당 domain꺼만 남김
        answer_goal = filtered_goal[domain]
        
        ## 예약된 entity가 user조건과 만족하는지 비교
        current_book_db = current_book_db[0]
        
        ## 여기서 taxi, train, 그 외를 다르게 처리해줘야 함
        if domain != "taxi":
            # print(correct_dict)
            current_entity_name = current_book_db['name'] if domain != "train" else current_book_db['train_schedule_id']
            try:
                # print(current_entity_name)
                entity_stats = run_api(current_entity_name,domain,dial_idx, experiment_path)
            except:
                with open("whatiswrong_on_grading_booking.txt",'w') as f:
                    f.write(f"{current_entity_name}_{domain}_{dial_idx}")
                correct_dict[domain]=False
            cnt=0
            print(entity_stats)
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
                    correct_dict[domain]=False

            ## 예약을 알맞는 조건으로 했는지 비교
            for slot in answer_goal['book']:
                if slot == "invalid" or slot == "pre_invalid":
                    continue
                if answer_goal['book'][slot] != str(current_book_db[slot]):
                    correct_dict[domain]=False
                    break
        else: ## taxi일 때
            for slot in answer_goal['book']:
                if slot == "invalid" or slot == "pre_invalid":
                    continue
                ## time 관련 slot의 처리
                if slot in ["arriveBy","leaveAt"]:
                    if current_book_db[slot]: ## 예약한 instance에 time이 null이 아닐 때때
                        if not compare_time(time=str(current_book_db[slot]),gt_time=answer_goal['book'][slot],compare_type=slot):
                            correct_dict[domain]=False
                            break
                    else: ## answer의 slot에 있는 건데, 그게 none이면 틀린거지
                        correct_dict[domain]=False
                        break

                ## time 관련 slot 아닌거 처리.
                else:
                    if answer_goal['book'][slot].lower() != str(current_book_db[slot]).lower():
                        correct_dict[domain]=False
                        break
                
    correct_dict = {("accommodation" if key == "hotel" else key):value for key,value in correct_dict.items()}
    return correct_dict

def grading(dial_idx,goal_collection, model_name=None,yaml_file = None):
    """
    taxi - inform은 항상 true 임
    attraction - book은 항상 true
    book은 시작이 True 임, Inform은 시작이 false이고고
    """
    # Calculate experiment path
    from get_experiment_path import get_experiment_path
    experiment_path = get_experiment_path(model_name,yaml_file)
    ## hotel -> accommodation
    if "hotel" in goal_collection:
        goal_collection["accommodation"] = goal_collection["hotel"]
        del goal_collection["hotel"]

    ## 일단 총괄 채점
    book_grade = grading_booking(dial_idx, experiment_path) ## book은 default가 true임임
    final_grade = {domain:{"book":""} for domain in book_grade}
    for domain in final_grade:
        final_grade[domain]['book'] = book_grade[domain]
    
    ## 후처리: 각 goal에 info나 book이 없는 경우도 있으므로, 이것도 따로 소거해주기
    for domain in final_grade:
        current_domain_goal_dict = goal_collection[domain]
        
        # 뭐가 됫든 false로 찍혔으면 뭔가 잘못을 한거임
        if 'book' in final_grade[domain] and final_grade[domain]['book'] == False:
            continue
        if "book" in current_domain_goal_dict:
            if current_domain_goal_dict['book']:
                None
            else:
                final_grade[domain].pop("book", None)
        else:
            final_grade[domain].pop("book", None)
    return final_grade

goal_collection = {
    "taxi": {},
    "police": {},
    "hospital": {},
    "attraction": {},
    "train": {},
    "message": [
        "You are looking for a <span class='emphasis'>place to stay</span>. The hotel should have <span class='emphasis'>a star of 4</span> and should be in the type of <span class='emphasis'>guesthouse</span>",
        "The hotel should be in the <span class='emphasis'>south</span> and should <span class='emphasis'>include free wifi</span>",
        "Once you find the <span class='emphasis'>hotel</span> you want to book it for <span class='emphasis'>8 people</span> and <span class='emphasis'>3 nights</span> starting from <span class='emphasis'>friday</span>",
        "Make sure you get the <span class='emphasis'>reference number</span>"
    ],
    "restaurant": {},
    "accommodation": {
        "info": {
            "internet": "yes",
            "type": "guesthouse",
            "stars": "4",
            "area": "south"
        },
        "fail_info": {},
        "book": {
            "stay": "3",
            "day": "friday",
            "invalid": False,
            "people": "8"
        },
        "fail_book": {}
    }
}

if __name__ == "__main__":
    print(run_api("rosa's bed and breakfast","accommodation","SNG0782.json_0"))