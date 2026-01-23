#!/bin/bash

domain_list=("airline" "retail")
# trial_list=(0 1 2 3)
n_trial=3
models=(
    # "gpt-4.1-mini"
    "gpt-4.1-nano"
    # "qwen/qwen3-235b-a22b"
    # "qwen/qwen3-30b-a3b"
    # "meta-llama/llama-3.1-70b-instruct"
)

get_result_path() {
    python3 get_result_path.py "$1" "$2"
}

# non_coll_list 폴더에서 yaml 파일들 가져오기
non_coll_yamls=($(ls non_coll_list/*.yaml | xargs -n 1 basename))


# 모델별, yaml별로 이중 루프 실행
for model_name in "${models[@]}"; do
    for yaml_file in "${non_coll_yamls[@]}"; do
        echo "Starting experiments for model: ${model_name}, yaml: ${yaml_file}"
        
        # 결과 디렉토리 생성 (get_result_path.py에서 자동으로 생성됨)
        result_dir=$(get_result_path "${model_name}" "${yaml_file}")
        echo "Using result directory: $result_dir"

        # domain 반복
        for idx in "${!domain_list[@]}"; do
            domain="${domain_list[$idx]}"
            session_name="s_${model_name//\//_}_${yaml_file%.yaml}_${idx}"
            
            echo "Starting sessions for domain: ${domain} with model: ${model_name}, yaml: ${yaml_file}"
            
            # num-trials 반복
            # for trial in "${trial_list[@]}"; do
            for ((trial=0; trial<n_trial; trial++)); do
                trial_session_name="${session_name}_trial${trial}"
                echo "Starting session ${trial_session_name} for trial ${trial}"

                tmux new-session -d -s "${trial_session_name}" \
                    "export MODEL_NAME='${model_name}'; python run.py --num-trials ${trial} --agent-strategy react --env ${domain} --model ${model_name} --model-provider openai --user-model gpt-4.1-mini --user-model-provider openai --user-strategy llm --max-concurrency 60 --non-coll-yaml ${yaml_file}"
            done
        done
    done
done

# tmux 세션 완료 대기 함수
wait_for_tmux_sessions() {
    local pattern="${1:-s_}"  # 기본값은 "s_", 인자로 다른 패턴도 받을 수 있음
    echo "Waiting for tmux sessions with pattern '$pattern' to complete..."
    
    while true; do
        # 현재 실행 중인 tmux 세션 개수 확인
        if tmux list-sessions 2>/dev/null >/dev/null; then
            session_count=$(tmux list-sessions 2>/dev/null | grep "$pattern" | wc -l 2>/dev/null || echo "0")
        else
            session_count=0
        fi
        
        # 숫자만 추출하고 공백/줄바꿈 제거
        session_count=$(echo "$session_count" | tr -d '\n\r' | grep -o '[0-9]*' | head -1)
        
        # 빈 문자열이면 0으로 설정
        if [ -z "$session_count" ]; then
            session_count=0
        fi
        
        if [ "$session_count" -eq 0 ]; then
            echo "All tmux sessions with pattern '$pattern' completed!"
            break
        else
            echo "Still running sessions with pattern '$pattern': $session_count"
            # 현재 실행 중인 세션들 보여주기
            tmux list-sessions 2>/dev/null | grep "$pattern" | cut -d':' -f1 | head -5 | while read session; do
                echo "  - $session"
            done
            sleep 10
        fi
    done
}

# 누락된 시뮬레이션 찾고 실행하는 함수
run_missing_simulations() {
    local model_name="$1"
    local result_path="$2"
    local yaml_file="$3"
    
    echo "Checking for missing simulations for model: $model_name"
    
    # 누락된 시뮬레이션을 배열로 가져오기
    mapfile -t missing_array < <(python3 find_missing.py "$result_path" "$n_trial")
    
    if [ ${#missing_array[@]} -eq 0 ]; then
        echo "No missing simulations found for $model_name"
        return
    fi
    
    echo "Found ${#missing_array[@]} missing simulations for $model_name:"
    printf '%s\n' "${missing_array[@]}"
    
    # 배열을 for 루프로 처리 (run_miss_infer.sh 스타일)
    for missing_item in "${missing_array[@]}"; do
        if [ -n "$missing_item" ]; then
            # missing_item 파싱 (예: retail_0_1 -> domain=retail, idx=0, trial=1)
            IFS='_' read -r domain idx trial <<< "$missing_item"
            
            if [ -n "$domain" ] && [ -n "$idx" ] && [ -n "$trial" ]; then
                session_name="missing_${model_name//\//_}_${yaml_file%.yaml}_${domain}_${idx}_${trial}"
                echo "Running missing simulation: $session_name"
                
                # yaml_file은 현재 for 루프의 변수를 그대로 사용
                
                tmux new-session -d -s "$session_name" \
                    "export MODEL_NAME='${model_name}'; python run.py --num-trials ${trial} --agent-strategy react --env ${domain} --model ${model_name} --model-provider openai --user-model gpt-4.1-mini --user-model-provider openai --user-strategy llm --max-concurrency 1 --task-ids ${idx} --non-coll-yaml ${yaml_file}"
            fi
        fi
    done
}

# goal_align_result.json에서 result=false인 시뮬레이션과 eval_result.json 에러 조건인 시뮬레이션 찾고 실행하는 함수
run_failed_goal_align_simulations() {
    local model_name="$1"
    local result_path="$2"
    local yaml_file="$3"
    
    echo "Checking for failed goal alignment and eval result simulations for model: $model_name"
    
    failed_count=0
    if [ -d "$result_path" ]; then
        for folder in "$result_path"/*; do
            if [ -d "$folder" ]; then
                goal_align_file="$folder/goal_align_result.json"
                eval_result_file="$folder/eval_result.json"
                should_rerun=false
                
                # goal_align_result.json 체크
                if [ -f "$goal_align_file" ]; then
                    result=$(python3 -c "import json; print(json.load(open('$goal_align_file')).get('result', False))" 2>/dev/null || echo "False")
                    if [ "$result" = "False" ]; then
                        should_rerun=true
                        echo "Found failed goal alignment in: $(basename "$folder")"
                    fi
                fi
                
                # eval_result.json 체크
                if [ -f "$eval_result_file" ]; then
                    has_error=$(python3 -c "
import json
try:
    with open('$eval_result_file', 'r') as f:
        eval_result = json.load(f)
    if 'traceback' in eval_result.get('info', {}):
        if 'AssertionError' not in eval_result['info']['traceback']:
            print('True')
        else:
            print('False')
    else:
        print('False')
except:
    print('False')
" 2>/dev/null || echo "False")
                    if [ "$has_error" = "True" ]; then
                        should_rerun=true
                        echo "Found error without AssertionError in: $(basename "$folder")"
                    fi
                else
                    # eval_result.json이 없으면 재실행
                    should_rerun=true
                    echo "Missing eval_result.json in: $(basename "$folder")"
                fi
                
                if [ "$should_rerun" = true ]; then
                    folder_name=$(basename "$folder")
                    IFS='_' read -r domain idx trial <<< "$folder_name"
                    
                    if [ -n "$domain" ] && [ -n "$idx" ] && [ -n "$trial" ]; then
                        session_name="retry_${model_name//\//_}_${yaml_file%.yaml}_${domain}_${idx}_${trial}"
                        echo "Re-running simulation: $session_name"
                        
                        # 폴더 삭제 후 재실행
                        rm -rf "$folder"
                        
                        tmux new-session -d -s "$session_name" \
                            "export MODEL_NAME='${model_name}'; python run.py --num-trials ${trial} --agent-strategy react --env ${domain} --model ${model_name} --model-provider openai --user-model gpt-4.1-mini --user-model-provider openai --user-strategy llm --max-concurrency 1 --task-ids ${idx} --non-coll-yaml ${yaml_file}"
                        
                        failed_count=$((failed_count + 1))
                    fi
                fi
            fi
        done
    fi
    
    echo "Found $failed_count simulations to retry for $model_name"
    return $failed_count
}

echo "All initial sessions started. Use 'tmux list-sessions' to see running sessions."

# 모든 tmux 세션이 완료될 때까지 대기
wait_for_tmux_sessions

# goal_align_result.json이 누락된 시뮬레이션 찾고 실행하는 함수
run_missing_goal_align_files() {
    local model_name="$1"
    local result_path="$2"
    local yaml_file="$3"
    
    echo "Checking for missing goal_align_result.json files for model: $model_name"
    
    missing_count=0
    if [ -d "$result_path" ]; then
        for folder in "$result_path"/*; do
            if [ -d "$folder" ]; then
                goal_align_file="$folder/goal_align_result.json"
                if [ ! -f "$goal_align_file" ]; then
                    folder_name=$(basename "$folder")
                    IFS='_' read -r domain idx trial <<< "$folder_name"
                    
                    if [ -n "$domain" ] && [ -n "$idx" ] && [ -n "$trial" ]; then
                        session_name="missing_goal_${model_name//\//_}_${yaml_file%.yaml}_${domain}_${idx}_${trial}"
                        echo "Re-running simulation with missing goal_align_result.json: $session_name"
                        
                        # 폴더 삭제 후 재실행
                        rm -rf "$folder"
                        
                        tmux new-session -d -s "$session_name" \
                            "export MODEL_NAME='${model_name}'; python run.py --num-trials ${trial} --agent-strategy react --env ${domain} --model ${model_name} --model-provider openai --user-model gpt-4.1-mini --user-model-provider openai --user-strategy llm --max-concurrency 1 --task-ids ${idx} --non-coll-yaml ${yaml_file}"
                        
                        missing_count=$((missing_count + 1))
                    fi
                fi
            fi
        done
    fi
    
    echo "Found $missing_count missing goal_align_result.json files for $model_name"
    return $missing_count
}

# -----------------------------------------------------------

# goal_align_result.json 누락 파일 처리 루프 (최대 10번 반복)
echo "Starting missing goal_align_result.json file detection and re-execution..."
for goal_align_round in {1..10}; do
    echo "=== Missing goal_align_result.json detection round $goal_align_round/10 ==="
    
    # 모든 모델의 누락된 goal_align_result.json 파일 개수 계산
    total_missing_goal_align=0
    for model_name in "${models[@]}"; do
        for yaml_file in "${non_coll_yamls[@]}"; do
            result_path=$(get_result_path "${model_name}" "${yaml_file}")
            run_missing_goal_align_files "$model_name" "$result_path" "$yaml_file"
            missing_count=$?
            total_missing_goal_align=$((total_missing_goal_align + missing_count))
        done
    done
    
    if [ $total_missing_goal_align -eq 0 ]; then
        echo "No missing goal_align_result.json files found in round $goal_align_round. All files present!"
        break
    fi
    
    echo "Found $total_missing_goal_align missing goal_align_result.json files in round $goal_align_round"
    
    # 누락된 goal_align_result.json 파일 재생성 세션들이 완료될 때까지 대기
    echo "Waiting for missing goal_align_result.json sessions in round $goal_align_round to complete..."
    wait_for_tmux_sessions "missing_goal_"
    
    echo "Round $goal_align_round completed."
    
    # 마지막 라운드가 아니면 잠시 대기
    if [ $goal_align_round -lt 10 ]; then
        echo "Waiting 5 seconds before next round..."
        sleep 5
    fi
done

echo "Missing goal_align_result.json file detection completed."

# 메인 반복 루프 - goal_align_result가 모두 true가 될 때까지 반복 (최대 10번)
max_attempts=10
main_round=1
while [ $main_round -le $max_attempts ]; do
    echo "=== Main simulation cycle $main_round/$max_attempts ==="
    
    echo "Starting missing simulation detection and execution..."

    # 최대 5번 반복하여 누락된 시뮬레이션 검사 및 실행
    for round in {1..5}; do
        echo "=== Missing simulation detection round $round/10 ==="
        
        # 모든 모델의 누락된 시뮬레이션 개수 계산
        total_missing=0
        for model_name in "${models[@]}"; do
            for yaml_file in "${non_coll_yamls[@]}"; do
                result_path=$(get_result_path "${model_name}" "${yaml_file}")
                mapfile -t missing_array < <(python3 find_missing.py "$result_path" "$n_trial")
                total_missing=$((total_missing + ${#missing_array[@]}))
            done
        done
        
        if [ $total_missing -eq 0 ]; then
            echo "No missing simulations found in round $round. All simulations completed!"
            break
        fi
        
        echo "Found $total_missing missing simulations in round $round"
        
        # 각 모델별, yaml별로 누락된 시뮬레이션 찾고 실행
        for model_name in "${models[@]}"; do
            for yaml_file in "${non_coll_yamls[@]}"; do
                result_path=$(get_result_path "${model_name}" "${yaml_file}")
                run_missing_simulations "$model_name" "$result_path" "$yaml_file"
            done
        done
        
        # 누락된 시뮬레이션 세션들이 완료될 때까지 대기
        echo "Waiting for missing simulation sessions in round $round to complete..."
        wait_for_tmux_sessions "missing_"
        
        echo "Round $round completed."
        
        # 마지막 라운드가 아니면 잠시 대기
        if [ $round -lt 5 ]; then
            echo "Waiting 5 seconds before next round..."
            sleep 5
        fi
    done

    echo "Missing simulation detection completed. Now checking goal alignment..."
    
    # 현재 사이클 결과를 success_eval.py로 평가하고 저장
    echo "Running success evaluation and saving results for main cycle $main_round..."
    for model_name in "${models[@]}"; do
        for yaml_file in "${non_coll_yamls[@]}"; do
            result_path=$(get_result_path "${model_name}" "${yaml_file}")
            
            # score_list 디렉토리 생성
            mkdir -p score_list
            
            # 파일명 생성: 전체 경로에서 /를 _로 대체하고 yaml 정보도 포함
            filename=$(echo "$result_path" | sed 's/\//_/g')
            yaml_name=$(echo "$yaml_file" | sed 's/non_coll_//g' | sed 's/.yaml//g')
            output_file="score_list/${filename}_${yaml_name}.txt"
            
            # 기존 파일이 있으면 구분자 추가
            if [ -f "$output_file" ]; then
                echo -e "\n" >> "$output_file"
            fi
            
            # Attempt 번호 추가
            echo "Attempt $main_round" >> "$output_file"
            
            # success_eval.py 실행하고 결과 캡처
            python3 success_eval.py "$model_name" "$yaml_file" 2>/dev/null | grep -E "(success_rate_mean|success_rate_values|pass_rate_mean|pass_rate_values|goal_align_mean|goal_align_values|total_graded_cnt|Error Analysis:)" | sed 's/^/  /' >> "$output_file"
            
            echo "Results for cycle $main_round saved to $output_file"
        done
    done
    
    # goal_align_result가 false인 시뮬레이션들 재실행
    total_failed=0
    for model_name in "${models[@]}"; do
        for yaml_file in "${non_coll_yamls[@]}"; do
            result_path=$(get_result_path "${model_name}" "${yaml_file}")
            run_failed_goal_align_simulations "$model_name" "$result_path" "$yaml_file"
            failed_count=$?
            total_failed=$((total_failed + failed_count))
        done
    done
    
    if [ $total_failed -eq 0 ]; then
        echo "All goal alignment results are true. Simulation cycle complete!"
        break
    else
        echo "Found $total_failed failed goal alignment simulations. Re-running cycle..."
        
        # 최대 시도 횟수에 도달했는지 확인
        if [ $main_round -eq $max_attempts ]; then
            echo "Maximum attempts ($max_attempts) reached. Stopping simulation cycles."
            break
        fi
        
        # 재시도 세션들이 완료될 때까지 대기
        echo "Waiting for retry sessions to complete..."
        wait_for_tmux_sessions "retry_"
        
        main_round=$((main_round + 1))
        echo "Main cycle $main_round starting..."
    fi
done

if [ $total_failed -eq 0 ]; then
    echo "All simulations completed with successful goal alignment!"
else
    echo "Simulation cycles completed. Some goal alignments may still be false after $max_attempts attempts."
fi