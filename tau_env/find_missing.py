#!/usr/bin/env python3

import os
import sys
import json

def find_missing_simulations(result_path):
    with open("testset_retail_idx.json",'r') as f:
        retail_idx_list = json.load(f)
    # retail_idx_list = [10,12,26,50]

    with open("testset_airline_idx.json",'r') as f:
        airline_idx_list = json.load(f)
    # airline_idx_list = [13,35,36,38]
    trial_list = [0, 1, 2, 3]
    
    if not os.path.exists(result_path):
        print(f"Error: Path {result_path} does not exist", file=sys.stderr)
        return []
    
    simulation_list = os.listdir(result_path)
    missing_list = []
    
    # 각 trial별로 체크
    for trial in trial_list:
        # Retail 체크
        for retail_idx in retail_idx_list:
            current_idx = f"retail_{retail_idx}_{trial}"
            if current_idx not in simulation_list:
                missing_list.append(current_idx)
        
        # Airline 체크  
        for airline_idx in airline_idx_list:
            current_idx = f"airline_{airline_idx}_{trial}"
            if current_idx not in simulation_list:
                missing_list.append(current_idx)
    
    return sorted(missing_list)

def parse_missing_item(missing_item):
    parts = missing_item.split('_')
    if len(parts) != 3:
        return None, None, None
    
    domain = parts[0]
    idx = int(parts[1])
    trial = int(parts[2])
    
    return domain, idx, trial

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 find_missing.py <result_path>", file=sys.stderr)
        sys.exit(1)
    
    result_path = sys.argv[1]
    missing = find_missing_simulations(result_path)
    
    if missing:
        # 각 missing item을 한 줄씩 출력 (shell에서 파싱하기 쉽게)
        for item in missing:
            print(item)
    # 아무것도 출력하지 않으면 missing이 없다는 의미