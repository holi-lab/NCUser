import json,re,subprocess,random,os,yaml,sys
from prompts import llama_system_multiwoz_prompt
from prompts import input_parameter_dict
from prompts import count_tokens, generate_random_string,price_dict
import shutil 
import warnings
import requests
from openai import OpenAI
from transformers import AutoTokenizer
warnings.filterwarnings('ignore')
from copy import deepcopy
from past.save_to_html import *
from get_experiment_path import get_experiment_path
from goal_align_new import slot_alignment_evaluation
from multiwoz_user import MultiwozUser
from custom_openai_client import *

MAX_REASONING=30

def goal_preprocess_text(dial):
    current_goal = ".\n".join(dial['goal']['message'])+"."
    current_goal = current_goal.replace("<span class='emphasis'>","'").replace("</span>","'")
    
    current_goal = current_goal.replace("'places to go'","places to go").replace("'place to stay'","place to stay").replace("'place to dine'","place to dine")
    
    print(current_goal)
    return current_goal

def goal_preprocess_dict(dial):
    goal_dict = {}
    remove_keys = {"topic","message"}
    for key in dial['goal']:
        if key not in remove_keys and dial['goal'][key]:
            goal_dict[key] = dial['goal'][key]
    return goal_dict

###########################

def vllm_inference(input_text,port_number_list,model_name):
    host = "localhost"
    port_number="800"+str(random.sample(port_number_list,1)[0])
    request_address = f"http://{host}:{port_number}/v1/completions"
    response = requests.post(
        request_address,
        headers={"Content-Type": "application/json"},
        json={
            "model": model_name,
            "prompt": input_text,
            "max_tokens": 1000,
            "temperature": 0.0,
            "top_p": 1.0,
            "top_k": 1
        }
    )
    try:
        output = response.json()['choices'][0]['text']
    except:
        print(response)
        raise ValueError("VLLM Generation Error")
    return output

def gpt_infer_agent(messages,model_name="gpt-4.1-mini"):
    generated_text = openai_client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=1,
        # max_tokens=4096,
    ).choices[0].message.content

    input_tokens = count_tokens(gpt_apply_chat_template(messages), model_name)
    output_tokens = count_tokens(str(generated_text), model_name)
    prices = price_dict[model_name]
    input_cost = input_tokens / 1000 * prices["input_cost_per_1k"]
    output_cost = output_tokens / 1000 * prices["output_cost_per_1k"]
    total_cost = input_cost + output_cost

    file_name = generate_random_string()
    with open(f"price_file/{file_name}.json",'w') as f:
        json.dump({"cost":total_cost},f,indent=4)

    return generated_text

def open_router_infer_agent(messages,model_name):
    response = open_router_client.chat.completions.create(
        model=model_name,  # 원하는 모델 선택
        messages=messages,
    ).choices[0].message.content

    return response

def gpt_apply_chat_template(dial_hist_system_list):
    system_dialogue = ""
    for turn in dial_hist_system_list:
        if turn['role'] == "user":
            system_dialogue+=f"User:{turn['content']}"+"\n\n"
        else:
            system_dialogue+=turn["content"]+"\n\n"
    return system_dialogue
    

def observation_generator(reasoning,
                          dial_idx,
                          dialogue_stats,
                          process_reward_list,
                          experiment_path):
    action = reasoning.split("Action:")[-1].strip()

    dialogue_stats['n_reasoning']+=1
    if "API call" in action:
        parsed_payload = action.split("call")[-1].strip()

        # experiment_path is now passed as parameter
        with open(f"{experiment_path}/{dial_idx}/api_call_log.json",'r') as f:
            api_call_log = json.load(f)
        api_call_log.append({"call_log":parsed_payload})
        with open(f"{experiment_path}/{dial_idx}/api_call_log.json",'w') as f:
            json.dump(api_call_log,f,indent=4)

        try:
            payload = eval(parsed_payload)  # 위험한 부분이므로 나중에 ast.literal_eval로 바꾸는 게 더 안전함        
        except: ## SyntaxError, NameError,TypeError
            process_reward_list.append(0) # format error
            error_message = str({"success":False,"result":{"message":f"'{parsed_payload}' is not a valid to parse the API call payload. Make sure to follow the 'API call' instruction properly."}})
            return {"observation":f"# Observation: {error_message} ","is_done":False}
        
        ## 여기도 try except 걸어줘야 함. Payload에 api_name, input_parameters 있는지에 따라
        if "api_name" not in payload or "input_parameters" not in payload:
            process_reward_list.append(0)
            error_message = str({"success":False,"result":{"message":f"Payload format is invalid. Please contain 'api_name' and 'input_parameters'"}})
            return {"observation":f"# Observation: {error_message} ","is_done":False}
        
        ## API 없는 거 썼을 때.
        api_name = payload["api_name"]
        if api_name not in input_parameter_dict:
            process_reward_list.append(0)
            error_message = str({"success":False,"result":{"message":f"API {api_name} does not exist. Please check the name properly."}})
            return {"observation":f"# Observation: {error_message} ","is_done":False}
        
        ## 'id': <built-in function id> 이거 생성하면 여기서 걸리더라.
        try:
            input_json = json.dumps(payload["input_parameters"])
        except:
            with open(f"what_is_wrong_on_{dial_idx}.txt",'w') as f:
                f.write(str(payload))
            process_reward_list.append(0)
            error_message = str({"success":False,"result":{"message":f"'{parsed_payload}' is not a valid to parse the API call payload. Make sure to follow the 'API call' instruction properly."}})
            return {"observation":f"# Observation: {error_message} ","is_done":False}

        result = subprocess.run(
            ["python", f"{experiment_path}/{dial_idx}/run_api.py", api_name, input_json, dial_idx, experiment_path],
            capture_output=True,
            text=True
        )

        try:
            is_success = eval(result.stdout.strip().replace("true","True").replace("false","False").replace("null","None"))
        except: ## 여기서는 없는 input parameter 넣어줬을 때 문제가 생김
            with open(f"{experiment_path}/{dial_idx}/error_call.txt",'w') as f:
                f.write(api_name+input_json + "\n\n" + result.stdout.strip())
            process_reward_list.append(0.5)
            error_message = str({"success":False,"result":{"message":"Invalid input parameter detected. Check the API documentation."}})
            return {"observation":f"# Observation: {error_message} ","is_done":False}
        
        call_success = is_success.get('success', False) == True
        dialogue_stats["n_api_call"]+=1

        ## 위에서 명시하지 않았지만, API 자체에서 error를 반환했을 경우엔 reward=0.5
        if call_success:
            process_reward_list.append(1)
            return {"observation":f"Observation: {result.stdout.strip()}","is_done":False}
        else:
            process_reward_list.append(0.5)
            return {"observation":f"Observation: {result.stdout.strip()}","is_done":False}
        
    if "Talk" in action:
        if "Talk(" in action and action[-1] == ")":
            process_reward_list.append(1)
            return {"observation":"Observation: {}","is_done":True}
        else:
            process_reward_list.append(0)
            return {"observation":"Observation: Error message from system: Talk action should be 'Talk(<Your utterence>)'. Please follow it properly.","is_done":False}
    else:
        process_reward_list.append(0)
        return {"observation":"Observation: 'Error message from system: The action you've choosed is not supported for this system.'","is_done":False}

def book_db_init(domain_list,dial_idx,experiment_path):
    # experiment_path is now passed as parameter
    os.mkdir(f"{experiment_path}/{dial_idx}/reservation")
    ## server/reservation 내 book_db 생성
    for domain in domain_list:
        if domain == "attraction":
            continue

        with open(f"{experiment_path}/{dial_idx}/reservation/{domain}_book_db.json",'w') as f:
            json.dump([],f,indent=4)
            
def db_search(db:list,query:dict,is_remove:bool)->list: ## 여러 key constraint가 있는 query가 주어지고, 그 조건에 모두 해당하는 애들만 db에서 걸러줘야 함
    constrained_entity_idx = []
    for idx,entity in enumerate(db):
        
        cnt=0
        for param in query:
            if entity[param] == query[param]:
                cnt+=1
                
        if cnt == len(query): ## 길이가 같으면 조건 다 만족하는 거고, 걔네는 걸러줘야 함. cnt가 len(query)보다 커질 일은 없음
            constrained_entity_idx.append(idx)
        if cnt > len(query):
            raise IndexError("cnt can't be larger than query's slot number.")
        
    ## fail_info 에 기재된 constraint 의 entity가 애초부터 DB에 없는 경우도 많은 듯
    if len(constrained_entity_idx)>0 and is_remove:
        print("Filter happens!")
    
    if is_remove:
        return [entity for entity_idx,entity in enumerate(db) if entity_idx not in set(constrained_entity_idx)]
    else:
        return [entity for entity_idx,entity in enumerate(db) if entity_idx in set(constrained_entity_idx)]
        
def case_init(dial_idx,goal_dict,domain_list,experiment_path): ## 여기서 DB까지 전부 수정해주기

    # hotel -> accommodation
    domain_list = ["accommodation" if domain == "hotel" else domain for domain in domain_list]

    # 걍 없는거 
    if str(dial_idx) not in os.listdir(experiment_path):
        os.mkdir(f"{experiment_path}/{dial_idx}")
    else:

        # 있는 건데 중간에 에러 난거
        if "grading_result.json" not in os.listdir(f"{experiment_path}/{dial_idx}") or "goal_align_result.json" not in os.listdir(f"{experiment_path}/{dial_idx}"):
            shutil.rmtree(f"{experiment_path}/{dial_idx}")
            os.mkdir(f"{experiment_path}/{dial_idx}")
        else:
            # 없던 거 채울 때
            # return False

            # goal align 안된거 다시 돌리기 위함
            with open(f"{experiment_path}/{dial_idx}/goal_align_result.json",'r') as f:
                goal_align_result = json.load(f)
            
            if goal_align_result['result'] == False:
                shutil.rmtree(f"{experiment_path}/{dial_idx}")
                os.mkdir(f"{experiment_path}/{dial_idx}")
            
            else: # 이미 align 된 거면 다시 돌릴 필요가 없음.
                return False

    ## 각 case 폴더 내에 run_api.py 랑 apis.py 를 복사해줌
    src_file_list = ["run_api.py","apis.py","api_documentations/multiwoz_api_documentation.json"]
    dest_folder = f"{experiment_path}/{dial_idx}"
    for src_file in src_file_list:
        shutil.copy(src_file, dest_folder)
        
    ## DB 폴더를 만들고, domain에 해당하는 DB만 복사해옴
    os.mkdir(f"{experiment_path}/{dial_idx}/db")
    for domain in domain_list:
        src_file = f"server/apis/{domain}_db.json"
        dst_file = f"{experiment_path}/{dial_idx}/db/{domain}_db.json"
        shutil.copy(src_file,dst_file)

    ## domain list 도 저장
    with open(f"{experiment_path}/{dial_idx}/domains.json",'w') as f:
        json.dump(domain_list,f,indent=4)
        
    ## API call log json을 빈 리스트로 초기화
    with open(f"{experiment_path}/{dial_idx}/api_call_log.json",'w') as f:
        json.dump([],f,indent=4)

    ## read docs log json 을 빈 리스트로 초기화
    with open(f"{experiment_path}/{dial_idx}/read_docs_log.json",'w') as f:
        json.dump([],f,indent=4)
    
    ## goal이 바뀔거라서, 여기서 먼저 초기 goal을 저장해줌
    with open(f"{experiment_path}/{dial_idx}/goal_dict.json",'w') as f:
        json.dump(goal_dict,f,indent=4)
    
    ## fail 조건에 따른 db 초기 상태 변경해주기, 덮어써주는 게 있어서 deep copy 필수. 
    goal_dict = deepcopy({domain:goal_dict[domain] for domain in domain_list if domain != "taxi"})
    for domain in goal_dict:
        with open(f"{experiment_path}/{dial_idx}/db/{domain}_db.json",'r') as f:
            current_domain_db = json.load(f)
            
        current_goal = goal_dict[domain]
        for slot in current_goal: ## {'book', 'fail_book', 'fail_info', 'info', 'reqt'}
            if slot == "fail_info": ## fail book 조건에 모두 해당하는 entity들은 제거해주기
                if current_goal['fail_info']: ## fail_info가 비어있으면 DB 굳이 수정할 거 없음
                    query = current_goal["fail_info"]
                    constrained_domain_db = db_search(current_domain_db,query,is_remove=True)
                    with open(f"{experiment_path}/{dial_idx}/db/{domain}_db.json",'w') as f:
                        json.dump(constrained_domain_db,f,indent=4)
            
            # Book에서의 fail을 발생시키기 위함
            if slot == "fail_book":
                if current_goal["fail_book"]: ## fail_book이 비어있으면 굳이 안되는 book 만들 필요 없음
                    query = current_goal['info']
                    info_entity = db_search(current_domain_db,query,is_remove=False) ## info 조건에 맞는 entity(name or id)를 모두 가져옴
                    if domain == "train":
                        info_entity_name_list = [entity['train_schedule_id'] for entity in info_entity]
                        info_entity_id_list = None
                    else:
                        info_entity_name_list = [entity['name'] for entity in info_entity]
                        info_entity_id_list = [entity['id'] for entity in info_entity]
                    
                    ## Book 안되는 조건
                    fail_book_dict = current_goal['book']
                    for slot in current_goal['fail_book']:
                        fail_book_dict[slot] = current_goal['fail_book'][slot]
                    
                    fail_book_list = []
                    for idx,entity_name in enumerate(info_entity_name_list):
                        if domain == "train":
                            fail_book_list.append({"train_schedule_id":entity_name}|fail_book_dict)
                        else:
                            fail_book_list.append({"id":info_entity_id_list[idx],"name":entity_name}|fail_book_dict)
                        
                    ## book 되는 걸 모아놓은게 아니고, book 안되는 예약 조건들을 모아놓은 것임 (용량 issue)
                    with open(f"{experiment_path}/{dial_idx}/db/{domain}_no_book_db.json",'w') as f:
                        json.dump(fail_book_list,f,indent=4)

    return True
        

def simulation_multiwoz(client,
               model_name,
               goal_collection,
               completion_idx,
               port_number_list=None,
               model_name_for_path=None,
               yaml_file="non_coll.yaml"):
    
    dial_idx = f"{goal_collection['dial_idx']}_{completion_idx}"  ## MUL0533.json_0
    
    # Calculate experiment path for this simulation
    experiment_path = get_experiment_path(model_name_for_path,yaml_file)
    domains = goal_collection['domains'] ## ["hotel",'restaurant']

    ## goal 및 shuffle goal 의 text, dict 생성
    goal = [f"Book the {'accommodation' if domain == 'hotel' else domain}" for domain in domains]
    goal = " ".join(goal)

    goal_dict = goal_collection['goal_dict'] ## {"hotel":{}, "taxi":{} ...}
    
    ## case_id로 폴더 만들고, DB 복사해오고, DB를 goal에 따른 situation에 맞게 수정해줌
    is_simulation = case_init(dial_idx,goal_dict,domains,experiment_path)
    if not is_simulation:
        return False
    book_db_init(domains,dial_idx,experiment_path)

    with open(f"{experiment_path}/{str(dial_idx)}/model_name.json",'w') as f:
        json.dump({"model_name":model_name},f,indent=4)
    
    dial_hist_user = ""
    dial_hist_system_list = [{"role":"system","content":llama_system_multiwoz_prompt}]

    # model_name 변수는 repo/model_id 형태임
    if port_number_list:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
    else:
        tokenizer = None
    
    # initialize process reward list
    process_reward_list = []
    dialogue_stats = {"n_reasoning":0,"n_turn":0,"n_api_call":0,"n_retriever_call":0,"n_read_docs":0}

    user_simulator = MultiwozUser(dial_idx,goal_collection, experiment_path, yaml_file)
    
    n_total_reasoning = 0
    agent_response_list = []
    # for turn_idx in range(MAX_TURN): # max turn
    turn_idx = 0
    while n_total_reasoning<MAX_REASONING:
        if turn_idx%2==0: ## user turn
            response = user_simulator.generate(
                system_utterance=None if turn_idx==0 else system_utt_for_user,
            )

            dial_hist_user+=response+"\n"
            dial_hist_system_list.append({"role":"user","content":response.replace("# You:","")})
            if tokenizer:
                with open(f"{experiment_path}/{str(dial_idx)}/dial_hist_system.txt",'w') as f:
                    f.write(tokenizer.apply_chat_template(dial_hist_system_list,tokenize=False, add_generation_prompt=False))
            else:
                with open(f"{experiment_path}/{str(dial_idx)}/dial_hist_system.txt",'w') as f:
                    f.write(gpt_apply_chat_template(dial_hist_system_list))
            dialogue_stats['n_turn']+=1
            with open(f"{experiment_path}/{str(dial_idx)}/dial_hist_user.txt",'w') as f:
                f.write(dial_hist_user)
            if "END" in response:
                break
            turn_idx+=1
        else: ## agent turn
            is_done=False
            while not is_done and n_total_reasoning<MAX_REASONING:
                if client is not None: ## training mode
                    while True:
                        try:
                            response = client.generate(
                                prompts=[tokenizer.apply_chat_template(
                                    dial_hist_system_list,
                                    tokenize=False,
                                    add_generation_prompt=True,
                                )],
                            )
                            response = tokenizer.decode(response["completion_ids"][0], skip_special_tokens=True)
                            break
                        except:
                            continue
                else: ## inference mode
                    if tokenizer: ## vllm infer 일 때
                        current_x=tokenizer.apply_chat_template(dial_hist_system_list,tokenize=False, add_generation_prompt=True)
                        response = vllm_inference(current_x,port_number_list,model_name)
                    else: ## gpt infer 일 때
                        if "gpt" in model_name and "/" not in model_name:
                            response = gpt_infer_agent(dial_hist_system_list,model_name=model_name)
                        else:
                            response = open_router_infer_agent(dial_hist_system_list,model_name=model_name)

                # agent response 후처리
                if "Thought: " in response and "- Thought: " not in response:
                    response = response.replace("Thought: ","- Thought: ")
                
                if "Action: " in response and "Action: " not in response:
                    response = response.replace("Action: ","Action: ")
                
                agent_response_list.append(response)
                dial_hist_system_list.append({"role":"assistant","content":response})
                current_observation = observation_generator(response,
                                                            dial_idx,
                                                            dialogue_stats,
                                                            process_reward_list,
                                                            experiment_path)
                is_done,observation_message = current_observation['is_done'],current_observation['observation']

                dial_hist_system_list.append(
                    {"role":"system","content":observation_message}
                )

                if tokenizer:
                    with open(f"{experiment_path}/{str(dial_idx)}/dial_hist_system.txt",'w') as f:
                        f.write(tokenizer.apply_chat_template(dial_hist_system_list,tokenize=False, add_generation_prompt=False))
                else:
                    with open(f"{experiment_path}/{str(dial_idx)}/dial_hist_system.txt",'w') as f:
                        f.write(gpt_apply_chat_template(dial_hist_system_list))

                n_total_reasoning+=1
            turn_idx+=1
            system_utt_for_user = "# System: "+response.split("Talk(")[-1].replace(")","").strip()

            
            ## user dialogue history concatenation
            dial_hist_user+=system_utt_for_user+"\n"
            
            # dialogue statistics update
            dialogue_stats['n_turn']+=1

    ## simulation 이 끝나고 dialogue_statistics 저장
    with open(f"{experiment_path}/{str(dial_idx)}/dialogue_stats.json",'w') as f:
        json.dump(dialogue_stats,f,indent=4)

    with open(f"{experiment_path}/{str(dial_idx)}/agent_response_list.json",'w') as f:
        json.dump(agent_response_list,f,indent=4)

    dialogue_state_result = {
        "initial_dialogue_state_list":user_simulator.dialogue_state_list,
        "remaining_dialogue_state_list":user_simulator.remaining_dialogue_state_list,
        "used_dialogue_state_list":user_simulator.used_dialogue_state_list
    }
        
    with open(f"{experiment_path}/{str(dial_idx)}/dialogue_state_list.json",'w') as f:
        json.dump(dialogue_state_result,f,indent=4)

    with open(f"{experiment_path}/{str(dial_idx)}/tangential_config.json",'w') as f:
        json.dump(user_simulator.tangential_config,f,indent=4)

    with open(f"{experiment_path}/{str(dial_idx)}/dial_hist_system_list.json",'w') as f:
        json.dump(dial_hist_system_list,f,indent=4)

    with open(f"{experiment_path}/{str(dial_idx)}/tangential_respond_result_list.json",'w') as f:
        json.dump(user_simulator.tangential_respond_result_list,f,indent=4)

    # evaluate goal align
    slot_alignment_evaluation(
        file = str(dial_idx),
        default_path = experiment_path
    )

    return True