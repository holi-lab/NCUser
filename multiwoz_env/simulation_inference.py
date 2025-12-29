import json,random,os,sys
import warnings
from eval import grading
warnings.filterwarnings('ignore')
import traceback
from tqdm import tqdm
from utils_multiwoz import simulation_multiwoz

def evaluation(dial_idx,goal_collection, model_name=None,yaml_file=None):
    return grading(dial_idx,goal_collection, model_name,yaml_file)

def run_simulation(model_name, # 경로용
                   model_name_init, # API 호출용
                   completion_idx,
                   goal_collection,
                   port_number_list,
                   simulation_domain,
                   yaml_file="non_coll.yaml"): ## 각종 ids와 mask, 그리고 reward를 0.0, 1.0의 float로 return

    test_task_id = goal_collection['dial_idx']
    is_valid_simulation = simulation_multiwoz(None,model_name_init, goal_collection, completion_idx,port_number_list, model_name, yaml_file)

    if simulation_domain == "multiwoz" and is_valid_simulation:
        eval_result = evaluation(f"{test_task_id}_{completion_idx}", goal_collection['goal_dict'], model_name,yaml_file)
        from get_experiment_path import get_experiment_path
        experiment_path = get_experiment_path(model_name,yaml_file)
        with open(f"{experiment_path}/{test_task_id}_{completion_idx}/grading_result.json",'w') as f:
            json.dump(eval_result,f,indent=4)

if __name__ == "__main__":
    simulation_number = sys.argv[1]
    file_number = sys.argv[2]
    n_file = sys.argv[3]
    model_name = sys.argv[4]  # model name passed as command line argument
    model_name_init = sys.argv[5]
    yaml_file = sys.argv[6] if len(sys.argv) > 6 else "non_coll.yaml"  # yaml file name
    is_vllm = int(sys.argv[7])
    is_train = int(sys.argv[8])

    if is_vllm:
        # Parse gpu_list from run_multi_server.sh
        with open('./run_multi_server.sh', 'r') as f:
            content = f.read()
        
        # Find the line with gpu_list declaration
        import re
        match = re.search(r'gpu_list=\(([^)]+)\)', content)
        if match:
            gpu_list_str = match.group(1)
            # Extract numbers from the string and convert to list of integers
            port_number_list = [int(x.strip()) for x in gpu_list_str.split() if x.strip().isdigit()]
        else:
            raise ValueError("Insert the GPU number properly on run_multi_server.sh")
    else:
        port_number_list = None


    if is_train:
        with open(f"goal_list/split_idx_list_train/split_idx_{file_number}.json",'r') as f:
            idx_list = json.load(f)
    else:
        # for single domain test
        # with open(f"goal_list/split_idx_list_single/split_idx_{file_number}.json",'r') as f:
        #     idx_list = json.load(f)

        with open(f"goal_list/split_idx_list_test/split_idx_{file_number}.json",'r') as f:
            idx_list = json.load(f)

    goal_list = []

    if int(n_file) == 0:
        offset = len(idx_list)
    else:
        offset = int(n_file)

    for idx in idx_list[:offset]:
        if is_train:
            with open(f"goal_list/train_goal_list/{idx}", 'r') as f:
                goal_collection = json.load(f)
        else:
            with open(f"goal_list/multiwoz_test_goal_list/{idx}", 'r') as f:
                goal_collection = json.load(f)


        goal_list.append(goal_collection)

    error_goal_list = []
    for goal_collection in tqdm(goal_list):
        simulation_domain = "multiwoz"
        try:
            print(f"---{goal_collection['dial_idx']}_{str(int(simulation_number))}---")
            run_simulation(model_name, 
                model_name_init,
                int(simulation_number), 
                goal_collection, 
                port_number_list,
                simulation_domain,
                yaml_file
            )
        except Exception as e:
            error_filename = f"error_on_{goal_collection['dial_idx']}_{simulation_number}.txt"
            with open(error_filename, 'w') as err_file:
                traceback.print_exc(file=err_file)
            print(f"Error processing {goal_collection['dial_idx']}: {e}")
            continue