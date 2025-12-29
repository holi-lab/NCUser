#!/usr/bin/env python3
import yaml
import os
import sys

def get_experiment_path(model_name=None, yaml_file=None):
    """
    Get the experiment path based on model name and behavior from yaml file
    Returns: experiment_result/ours/{model_name}/{behavior}
    
    Args:
        model_name: Model name to use. If None, tries to get from command line args.
        yaml_file: YAML file name to use. If None, tries to get from command line args.
    """
    # Get model name from parameter or command line
    if model_name is None:
        if len(sys.argv) > 1:
            model_name = sys.argv[1]
        else:
            raise ValueError("Model name must be provided either as parameter or command line argument")
    
    # Get yaml file from parameter or command line
    if yaml_file is None:
        if len(sys.argv) > 2:
            yaml_file = sys.argv[2]
        else:
            yaml_file = "non_coll.yaml"  # default
    
    # Load config from the specified yaml file
    if yaml_file.startswith("non_coll_list/"):
        yaml_path = yaml_file
    else:
        yaml_path = f"non_coll_list/{yaml_file}"
    
    with open(yaml_path, 'r') as f:
        non_coll_config = yaml.safe_load(f)
    
    # Get behavior string
    behaviors = []
    for behavior in non_coll_config:
        if behavior in ['is_pbus']:
            continue
        if non_coll_config[behavior]:
            behaviors.append(behavior)
    
    # If no behaviors are enabled, use "normal"
    if not behaviors:
        behavior_str = "normal"
    else:
        # Create abbreviated behavior string
        behavior_mapping = {
            'unavailable_service': 'unavailable_service',
            'tangential': 'tangential', 
            'emotional_acts': 'emotional_acts',
            'fragment_dumping': 'fragment_dumping'
        }
        
        abbreviated_behaviors = []
        for behavior in behaviors:
            if behavior in behavior_mapping:
                abbreviated_behaviors.append(behavior_mapping[behavior])
            else:
                abbreviated_behaviors.append(behavior)
        
        behavior_str = '+'.join(abbreviated_behaviors)
    
    # Convert model name to safe directory name (replace / with _)
    if "/" in model_name:
        model_dir_name = model_name.split('/')[-1]
    else:
        model_dir_name = model_name
    
    # Create experiment path (absolute path)

    # for test dataset
    experiment_name = "experiment_result"
    
    current_dir = os.getcwd()
    if non_coll_config['is_pbus']:
        experiment_path = os.path.join(current_dir, f"{experiment_name}/pbus/{model_dir_name}/{behavior_str}")
    else:
        experiment_path = os.path.join(current_dir, f"{experiment_name}/ours/{model_dir_name}/{behavior_str}")
    
    # Ensure the directory exists
    os.makedirs(experiment_path, exist_ok=True)
    
    return experiment_path

if __name__ == "__main__":
    if len(sys.argv) > 1:
        model_name = sys.argv[1]
        yaml_file = sys.argv[2] if len(sys.argv) > 2 else None
        print(get_experiment_path(model_name, yaml_file))
    else:
        print("Usage: python get_experiment_path.py <model_name> [yaml_file]")
        sys.exit(1)