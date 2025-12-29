#!/bin/bash

N=4 # Number of Simulation (In our paper, we use N=4)
M=40 # FIX Value. Do not modify
O=1 # if O == 0, use all 89 test scenarios. elif 1 or 2, use the subset from 89 test scenarios

is_vllm=0 # if 0, no vllm. Else, use vllm.

is_train_mode=0 # if 0, use testset. Else, use trainset.

get_experiment_path() {
    local model_name="$1"
    local yaml_file="$2"
    python3 get_experiment_path.py "$model_name" "$yaml_file"
}

models=(
    # "gpt-4.1-mini"
    "gpt-4.1-nano"
    # "qwen/qwen3-235b-a22b"
    # "qwen/qwen3-30b-a3b"
    # "meta-llama/llama-3.1-70b-instruct"

    # "holi-lab/llama-3.2-3b-multiwoz-finetuned"
    # "holi-lab/qwen-2.5-3b-multiwoz-finetuned"
    # "holi-lab/qwen-2.5-7b-multiwoz-finetuned"

    # "holi-lab/qwen-2.5-3b-528_195"
    # "holi-lab/qwen-2.5-3b-4010101030"
)

# YAML files array
yaml_files=()
for file in non_coll_list/*.yaml; do
    yaml_files+=($(basename "$file"))
done


# Remove old error files
rm -f error*.txt

# Function to process a single model with yaml config
process_model() {
    local model_name="$1"
    local yaml_file="$2"
    echo "Starting experiments for model: ${model_name} with config: ${yaml_file}"
    
    # Get experiment directory for this model
    experiment_dir=$(get_experiment_path "$model_name" "$yaml_file")
    echo "Using experiment directory: $experiment_dir"
    
    # Create unique temp file for this model and yaml
    yaml_name="${yaml_file%.yaml}"  # Remove .yaml extension
    temp_file="temp_eval_output_${experiment_dir//\//_}_${yaml_name}.txt"
    
    # Run simulations for this model
    for ((n=0; n<N; n++)); do
        for ((m=0; m<M; m++)); do
            session_name="sim_${model_name//\//_}_${yaml_name}_${n}_${m}"
            # Extract model name (part after the last '/')
            model_name_short="${model_name##*/}"
            tmux new-session -d -s "$session_name" "python simulation_inference.py ${n} ${m} ${O} '${model_name_short}' '${model_name}' '${yaml_file}' ${is_vllm} ${is_train_mode}"
        done
    done
    
    echo "All tmux sessions started for model: ${model_name}"
    echo "Use 'tmux list-sessions' to see running sessions."
    
    # # Initialize retry counter for this model
    ######################GOALAIGN###########################3
    retry_count=0
    max_retries=5
    
    while [ $retry_count -lt $max_retries ]; do
        echo "Attempt $((retry_count + 1)) for model: ${model_name} with config: ${yaml_file}"
        
        # Wait for all sessions for this model to complete
        echo "Waiting for ${model_name} (${yaml_file}) simulations to complete..."
        while true; do
            if tmux list-sessions 2>/dev/null >/dev/null; then
                session_count=$(tmux list-sessions 2>/dev/null | grep "sim_${model_name//\//_}_${yaml_name}_" | wc -l 2>/dev/null || echo "0")
            else
                session_count=0
            fi
            
            session_count=$(echo "$session_count" | tr -d '\n\r' | grep -o '[0-9]*' | head -1)
            if [ -z "$session_count" ]; then
                session_count=0
            fi
            
            if [ "$session_count" -eq 0 ]; then
                echo "All simulations completed for model: ${model_name} (${yaml_file})!"
                break
            else
                echo "Still running sessions for ${model_name} (${yaml_file}): $session_count"
                sleep 10
            fi
        done
        
        # Run success_rate_eval.py for this model
        echo "Running evaluation for model: ${model_name}"
        python success_rate_eval.py "$model_name" "$yaml_file" > "$temp_file"
        
        # Extract mean values and individual values
        success_rate_mean=$(grep "success_rate_mean:" "$temp_file" | awk '{print $2}')
        success_rate_values=$(grep "success_rate_values:" "$temp_file" | cut -d':' -f2 | sed 's/^ //')
        
        pass_rate_mean=$(grep "pass_rate_mean:" "$temp_file" | awk '{print $2}')
        pass_rate_values=$(grep "pass_rate_values:" "$temp_file" | cut -d':' -f2 | sed 's/^ //')
        
        goal_align_mean=$(grep "goal_align_mean:" "$temp_file" | awk '{print $2}')
        goal_align_values=$(grep "goal_align_values:" "$temp_file" | cut -d':' -f2 | sed 's/^ //')
        
        total_graded_cnt=$(grep "total_graded_cnt:" "$temp_file" | awk '{print $2}')
        
        # Create score_list directory if it doesn't exist
        mkdir -p score_list
        
        # Create filename by replacing / with _
        filename="score_list/${experiment_dir//\//_}.txt"
        
        # Append results to file
        if [ $retry_count -eq 0 ]; then
            # First attempt - check if file exists
            if [ -f "$filename" ]; then
                # File exists, append with separator
                echo -e "\n\nAttempt $((retry_count + 1)):" >> "$filename"
            else
                # File doesn't exist, create new file
                echo "Attempt $((retry_count + 1)):" > "$filename"
            fi
        else
            # Subsequent attempts - append with separator
            echo -e "\n\nAttempt $((retry_count + 1)):" >> "$filename"
        fi
        echo "success_rate_mean: $success_rate_mean" >> "$filename"
        echo "success_rate_values: $success_rate_values" >> "$filename"
        echo "pass_rate_mean: $pass_rate_mean" >> "$filename"
        echo "pass_rate_values: $pass_rate_values" >> "$filename"
        echo "goal_align_mean: $goal_align_mean" >> "$filename"
        echo "goal_align_values: $goal_align_values" >> "$filename"
        echo "total_graded_cnt: $total_graded_cnt" >> "$filename"
        
        # Check if goal_align is 100 (or very close)
        goal_align_int=$(echo "$goal_align_mean" | cut -d '.' -f1)
        if [ "$goal_align_int" -eq 100 ]; then
            echo "Goal align reached 100 for model: ${model_name} (${yaml_file}). Moving to next combination."
            break
        else
            echo "Goal align is $goal_align_mean, retrying model: ${model_name} (${yaml_file})"
            retry_count=$((retry_count + 1))
            
            if [ $retry_count -lt $max_retries ]; then
                # Re-run simulations for this model
                echo "Re-running simulations for model: ${model_name} (${yaml_file}) (attempt $((retry_count + 1)))"
                for ((n=0; n<N; n++)); do
                    for ((m=0; m<M; m++)); do
                        session_name="sim_${model_name//\//_}_${yaml_name}_${n}_${m}"
                        model_name_short="${model_name##*/}"
                        tmux new-session -d -s "$session_name" "python simulation_inference.py ${n} ${m} ${O} '${model_name_short}' '${model_name}' '${yaml_file}' ${is_vllm} ${is_train_mode}"
                    done
                done
            fi
        fi
    done
    
    
    if [ $retry_count -eq $max_retries ]; then
        echo "Maximum retries reached for model: ${model_name} (${yaml_file})"
    fi
    
    # Clean up temp file
    rm -f "$temp_file"
    
    echo "Completed processing for model: ${model_name} with config: ${yaml_file}"
    ######################GOALAIGN###########################3
}

# Run all models and yaml combinations in parallel
for model_name in "${models[@]}"; do
    for yaml_file in "${yaml_files[@]}"; do
        process_model "$model_name" "$yaml_file" &
    done
done

# Wait for all background processes to complete
echo "Waiting for all model-yaml combinations to complete..."
wait

echo "All simulations completed for all models!"
