#!/usr/bin/env python3

import os
import sys
import yaml

def get_result_path(model_name=None, yaml_file=None):
    if model_name is None:
        print("Error: model_name is required", file=sys.stderr)
        sys.exit(1)
    
    if yaml_file is None:
        print("Error: yaml_file is required", file=sys.stderr)
        sys.exit(1)
    
    # model_name에서 '/' 뒤의 부분만 사용 (파일 경로용)
    if '/' in model_name:
        model_name = model_name.split('/')[-1]
    
    # YAML에서 behavior 감지
    yaml_path = os.path.join('non_coll_list', yaml_file)
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)
    
    behavior_keys = ['unavailable_service', 'tangential', 'emotional_acts', 'fragment_dumping']
    behavior_list = []
    for key in behavior_keys:
        if config.get(key, False):
            behavior_list.append(key)

    if not behavior_list:
        behavior = "normal"
    else:
        behavior = "+".join(behavior_list)
    
    # 경로 생성
    experiment_name = "experiment_result"
    # experiment_name = "experiment_result_with_human"
    if not config['is_pbus']:
        result_path = f"{experiment_name}/ours/{model_name}/{behavior}"
    else:
        result_path = f"{experiment_name}/pbus/{model_name}/{behavior}"
    
    # 디렉토리가 없으면 생성
    if not os.path.exists(result_path):
        os.makedirs(result_path)
    
    return result_path

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 get_result_path.py <model_name> <yaml_file>", file=sys.stderr)
        sys.exit(1)
    
    model_name = sys.argv[1]
    yaml_file = sys.argv[2]
    print(get_result_path(model_name, yaml_file))