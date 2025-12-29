#!/bin/bash

# Create result directory if it doesn't exist
mkdir -p result_of_error_analysis

# Define models and yaml files explicitly
models=("gpt-4.1-mini" "gpt-4.1-nano" "qwen3-235b-a22b" "qwen3-30b-a3b" "llama-3.1-70b-instruct")
yaml_files=("non_coll_emotional_acts.yaml" "non_coll_fragment_dumping.yaml" "non_coll_normal.yaml" "non_coll_tangential.yaml" "non_coll_unavailable_service.yaml")

# Iterate through all combinations
for model in "${models[@]}"; do
    for yaml_file in "${yaml_files[@]}"; do
        echo "Running analysis for model: $model, yaml_file: $yaml_file"
        
        # Create output filename
        output_file="result_of_error_analysis/${model}_${yaml_file%.yaml}.txt"
        
        # Run success_eval.py and save output to file
        python3 analysis.py "$model" "$yaml_file" > "$output_file" 2>&1
        
        echo "Results saved to: $output_file"
    done
done

echo "All analyses completed!"