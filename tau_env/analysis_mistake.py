import os,json
from tau_bench.envs.airline.tasks_test import TASKS
from tau_bench.envs.retail.tasks_test import TASKS_TEST

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
                current_action = eval(reasoning['content'].split("Action:\n")[-1].strip().replace("""input("Please provide your email address to proceed: ")""","Please provide your email address to proceed: "))
            except:
                continue
            if current_action:
                if "name" in current_action:
                    if current_action['name'] != "respond":
                        action_list.append(current_action)

    return action_list

def compare_input_parameter(dict1, dict2):
    def get_key_structure(obj):
        if isinstance(obj, dict):
            return {key: get_key_structure(value) for key, value in obj.items()}
        else:
            return "value" 
    
    structure1 = get_key_structure(dict1)
    structure2 = get_key_structure(dict2)
    
    return structure1 == structure2

def compare_missing_keys_only(expected_structure, actual_arguments):
    def check_extra_keys(expected_dict, actual_dict):
        if not isinstance(expected_dict, dict) or not isinstance(actual_dict, dict):
            return True 
            
        for actual_key, actual_value in actual_dict.items():
            if actual_key not in expected_dict:
                return False
                
            if isinstance(actual_value, dict) and isinstance(expected_dict[actual_key], dict):
                if not check_extra_keys(expected_dict[actual_key], actual_value):
                    return False
                    
        return True
    
    return check_extra_keys(expected_structure, actual_arguments)

def generate_expected_structure_from_schema(schema):
    if schema['type'] == 'object':
        result = {}
        if 'properties' in schema:
            for key, prop_schema in schema['properties'].items():
                result[key] = generate_expected_structure_from_schema(prop_schema)
        return result
    elif schema['type'] == 'array':
        return []
    elif schema['type'] == 'string':
        return "example_string"
    elif schema['type'] == 'integer':
        return 123
    elif schema['type'] == 'number':
        return 123
    elif schema['type'] == 'boolean':
        return True
    else:
        return None

def check_type_and_enum_violations(schema, actual_data):
    def validate_value(schema_def, value):
        if 'enum' in schema_def:
            if value not in schema_def['enum']:
                return True
                
        schema_type = schema_def.get('type')
        if schema_type == 'string' and not isinstance(value, str):
            return True
        elif schema_type == 'number' and not isinstance(value, (int, float)):
            return True
        elif schema_type == 'integer' and not isinstance(value, int):
            return True
        elif schema_type == 'boolean' and not isinstance(value, bool):
            return True
        elif schema_type == 'array' and not isinstance(value, list):
            return True
            
        if schema_type == 'array' and 'items' in schema_def and isinstance(value, list):
            for item in value:
                if validate_value(schema_def['items'], item):
                    return True
                    
        return False
    
    def check_object(schema_def, data):
        if schema_def.get('type') == 'object' and 'properties' in schema_def:
            for key, prop_schema in schema_def['properties'].items():
                if key in data:
                    if prop_schema.get('type') == 'object':
                        if check_object(prop_schema, data[key]):
                            return True
                    else:
                        if validate_value(prop_schema, data[key]):
                            return True
        return False
    
    return check_object(schema, actual_data)

def normalize_api_call(api_call):
    import json
    
    api_name = api_call['name']
    arguments = api_call['arguments']
    
    normalized_args = json.dumps(arguments, sort_keys=True)
    
    return f"{api_name}:{normalized_args}"

def mistake_analysis(default_path):
    import json

    total_api_call = 0

    api_hallucination_error = 0

    input_parameter_hallucination_error = 0

    input_parameter_type_error = 0

    duplicate_call_cnt = 0

    n_simulation = 0
    for file in os.listdir(default_path):
        n_simulation+=1
        domain,task_idx,n_trial = file.split("_")[0],file.split("_")[1],file.split("_")[2]
        with open(f"{default_path}/{file}/reasoning_trajectory.json",'r') as f:
            reasoning_trajectory = json.load(f)

        if domain == "airline":
            gt_task_list = TASKS
        else:
            gt_task_list = TASKS_TEST

        with open(f"{domain}_api_documentation_list.json",'r') as f:
            api_docs_list = json.load(f)
        all_api_name_list = [api['function']['name'] for api in  api_docs_list]
        api_docs_dict = {api_docs['function']['name']:api_docs for api_docs in api_docs_list}

        gt_task = gt_task_list[int(task_idx)]
        predict_api_call_list = predict_api_call_function(reasoning_trajectory)

        predict_api_name_list = [api_call['name'] for api_call in predict_api_call_list]
        for predict_api_name in predict_api_name_list:
            if predict_api_name not in all_api_name_list:
                api_hallucination_error+=1

        seen_api_calls = set()
        for api_call in predict_api_call_list:
            normalized_call = normalize_api_call(api_call)
            if normalized_call in seen_api_calls:
                duplicate_call_cnt += 1
                import json
            else:
                seen_api_calls.add(normalized_call)

        for predict_api_call in predict_api_call_list:
            total_api_call+=1
            api_name = predict_api_call['name']
            
            if api_name not in api_docs_dict:
                continue
                
            api_doc = api_docs_dict[api_name]
            api_schema = api_doc['function']['parameters']
            
            expected_structure = generate_expected_structure_from_schema(api_schema)
            
            actual_arguments = predict_api_call['arguments']

            if not compare_missing_keys_only(expected_structure,actual_arguments):
                input_parameter_hallucination_error += 1
            else:
                if check_type_and_enum_violations(api_schema, actual_arguments):
                    input_parameter_type_error += 1

    print(f"Total API call: {total_api_call}")
    print(f"Input parameter hallucination error: {input_parameter_hallucination_error/n_simulation}")
    print(f"Input parameter type error: {input_parameter_type_error/n_simulation}")
    print(f"Duplicate call count: {duplicate_call_cnt/n_simulation}")