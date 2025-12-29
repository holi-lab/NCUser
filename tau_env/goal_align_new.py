from openai import OpenAI
from custom_openai_client import openai_client
import os
import json
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import threading

def gpt_infer(prompt,model_name="gpt-4.1-mini"):
    generated_text = openai_client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=1,
        # max_tokens=4096,
    ).choices[0].message.content
    return generated_text

def gpt_function_call(prompt,
                        function_spec,
                        model_name="gpt-4o-mini"):
    generated_text = openai_client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        functions=[function_spec],
        function_call={"name": function_spec['name']},
        temperature=0,
        # max_tokens=4096,
    )
    arguments = generated_text.choices[0].message.function_call.arguments
    return json.loads(arguments)

# Define the function that will process each file in parallel
def slot_alignment_evaluation(file, default_path):

    dialogue_state_tracker_function_spec = {
        "name": "track_dialogue_state_numbers",
        "description": "Evaluates the dialogue history, user's reply and selects numbers corresponding to information that was explicitly provided on user's reply.",
        "parameters": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "An explanation of which numbers were selected and why they were determined to be part of the conversation."
                },
                "selected_numbers": {
                    "type": "array",
                    "items": {
                        "type": "integer",
                        "minimum": 1
                    },
                    "description": "A list of numbers corresponding to information pieces that were explicitly provided in user's reply."
                }
            },
            "required": ["reasoning", "selected_numbers"]
        }
    }

    slot_prompt = """
You are an expert at extracting the information representations from user dialogue.  

Here are the information list strings:

<Information List>
{dialogue_state_list}

<Dialogue History>
{dial_hist}

<User Utterance>
{user_utterance}

Your task:  
For **each user utterance in the dialogue below**, output the cumulative set of information strings the user has explicitly mentioned, confirmed, or agreed to up to and including that turn.  
After the <dialogue history>, select which information from the <Information List> is included in the <User utterance> and return the number of the information.
Select the numbers (e.g., [1, 3, 5]) of the information that was mentioned or discussed in the conversation.

RULES 
1. A slot may be mentioned either by the user or by the system and subsequently accepted by the user. 
2. Dialogue information ONLY include what user decided BEFORE the dialogue. 
"""

    with open(f"{default_path}/{file}/dialogue_history.txt", 'r') as f:
        dial_hist = f.read()

    with open(f"{default_path}/{file}/dialogue_state_list.json", 'r') as f:
        dialogue_state_list = json.load(f)['initial_dialogue_state_list']

    dial_hist = dial_hist.replace("User: ", "# User: ").replace("Agent: ","# Agent:")
    dial_hist = dial_hist.replace("user: ","# user: ").replace("assistant: ","# assistant: ")
    dial_hist_list = dial_hist.split("# ")[1:]

    cum_dial_hist = ""
    cumulative_dialogue_slot_list = []
    for uttreance_idx, utterance in enumerate(dial_hist_list):
        if uttreance_idx % 2 == 0:  # user turn
            numbered_options = ""
            for i, state in enumerate(dialogue_state_list, 1):
                numbered_options += f"{i}. {state}\n"

            current_prompt = slot_prompt.format(
                dialogue_state_list=numbered_options,
                dial_hist=cum_dial_hist if cum_dial_hist else "The conversation has not started yet, and the <User Utterance> is the first utterance of the dialogue.",
                user_utterance=utterance
            )
            current_dialogue_state_idx_list = gpt_function_call(
                prompt=current_prompt,
                function_spec=dialogue_state_tracker_function_spec,
                model_name="gpt-4o-mini"
            )['selected_numbers']

            for num in current_dialogue_state_idx_list:
                if 1 <= num <= len(dialogue_state_list):
                    cumulative_dialogue_slot_list.append(dialogue_state_list[num - 1])
            dialogue_state_list = [
                dialogue_state for dialogue_state in dialogue_state_list if dialogue_state not in cumulative_dialogue_slot_list
            ]
            if len(dialogue_state_list) == 0:
                break
            cum_dial_hist += utterance
        else:
            cum_dial_hist += utterance

    if len(dialogue_state_list) > 0:
        result = False
    else:
        result = True

    final_result = {
        "dial_idx": file,
        "dial_hist": dial_hist,
        "result": result,
        "dialogue_state":dialogue_state_list
    }

    with open(f"{default_path}/{file}/goal_align_result.json", 'w') as f:
        json.dump(final_result, f, indent=4)

# Main function that initializes the thread pool and processes the files in parallel
def process_all_files(default_path, dialogue_state_tracker_function_spec, slot_prompt):
    result_list = []
    
    # List all files in the directory
    files = os.listdir(default_path)
    
    # Use ThreadPoolExecutor to parallelize the file processing
    with ThreadPoolExecutor(max_workers=20) as executor:  # Set max_workers based on your machine's capability
        futures = []
        
        # Submit tasks to the thread pool
        for file in tqdm(files):
            futures.append(executor.submit(slot_alignment_evaluation, file, default_path))
        
        # Wait for all tasks to complete
        for future in futures:
            future.result()  # This will block until the future is done

# Set the default path and function specifications
default_path = "experiment_result/ours/gpt-4.1-mini/emotional_acts"
# default_path = "e"
dialogue_state_tracker_function_spec = {
    "name": "track_dialogue_state_numbers",
    "description": "Evaluates the dialogue history, user's reply and selects numbers corresponding to information that was explicitly provided on user's reply.",
    "parameters": {
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "An explanation of which numbers were selected and why they were determined to be part of the conversation."
            },
            "selected_numbers": {
                "type": "array",
                "items": {
                    "type": "integer",
                    "minimum": 1
                },
                "description": "A list of numbers corresponding to information pieces that were explicitly provided in user's reply."
            }
        },
        "required": ["reasoning", "selected_numbers"]
    }
}

slot_prompt = """
You are an expert at extracting the information representations from user dialogue.  

Here are the information list strings:

<Information List>
{dialogue_state_list}

<Dialogue History>
{dial_hist}

<User Utterance>
{user_utterance}

Your task:  
For **each user utterance in the dialogue below**, output the cumulative set of information strings the user has explicitly mentioned, confirmed, or agreed to up to and including that turn.  
After the <dialogue history>, select which information from the <Information List> is included in the <User utterance> and return the number of the information.
Select the numbers (e.g., [1, 3, 5]) of the information that was mentioned or discussed in the conversation.

RULES 
1. The slot must be mentioned by the user prior to the system. 
2. Dialogue information ONLY include what user decided BEFORE the dialogue. 
"""

# Run the parallelized processing
# process_all_files(default_path, dialogue_state_tracker_function_spec, slot_prompt)
