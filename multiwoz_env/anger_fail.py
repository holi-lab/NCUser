import random,json
from copy import deepcopy
from prompts import *
from function_specs import *
from openai import OpenAI
from typing import List
import random,yaml,time
import dotenv,os,hashlib
from pbus_prompts import *
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from custom_openai_client import *

def gpt_function_call(prompt,
                        function_spec,
                        model_name="gpt-4.1-mini",
                        temperature=0):
    generated_text = openai_client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        functions=[function_spec],
        function_call={"name": function_spec['name']},
        temperature=temperature,
        # max_tokens=4096,
    )
    arguments = generated_text.choices[0].message.function_call.arguments
    return json.loads(arguments)

anger_fail_prompt = """
The given dialogue is between a user and a tool agent.

{dial_hist}

Your task is to count how many turns in the conversation contain anger expressed by the user and how many turns contain failure notifications by the agent.

Rules
1. A turn is defined as a single utterance starting with # You: for the user and # System: for the tool agent. You must count anger and failure notifications across all turns. Even if anger or failure notification appears multiple times within the same turn, it is counted as 1.
2. An agent’s turn consisting only of an apology does not count as a failure notification. A turn counts as a failure notification only if it explicitly conveys that a problem occurred or that the agent cannot proceed.
"""

anger_fail_function_spec = {
  "name": "count_anger_and_failure",
  "description": "Counts how many user turns contain anger and how many agent turns contain failure notifications in the given dialogue history.",
  "parameters": {
    "type": "object",
    "properties": {
      "reasoning": {
        "type": "string",
        "description": "An explanation of how anger turns and failure notification turns were identified and counted according to the given rules."
      },
      "anger_count": {
        "type": "integer",
        "description": "The number of user turns (# You:) that express anger."
      },
      "failure_notify_count": {
        "type": "integer",
        "description": "The number of agent turns (# System:) that contain a failure notification (excluding turns with apology only)."
      }
    },
    "required": ["reasoning", "anger_count", "failure_notify_count"]
  }
}

def process_file(file_info):
    model, file = file_info
    if "anger_fail.json" not in os.listdir(f"experiment_result/ours/{model}/normal/{file}"):
        with open(f"experiment_result/ours/{model}/normal/{file}/dial_hist_user.txt",'r') as f:
            dial_hist = f.read()

        current_prompt = anger_fail_prompt.format(dial_hist=dial_hist)

        result = gpt_function_call(
            prompt=current_prompt,
            function_spec=anger_fail_function_spec
        )

        with open(f"experiment_result/ours/{model}/normal/{file}/anger_fail.json",'w') as f:
            json.dump(result,f,indent=4)

model_name = ["gpt-4.1-mini","gpt-4.1-nano","llama-3.1-70b-instruct","qwen3-30b-a3b","qwen3-235b-a22b"]
concurrency = 20

file_list = []
for model in model_name:
    for file in os.listdir(f"experiment_result/ours/{model}/normal"):
        file_list.append((model, file))

with ThreadPoolExecutor(max_workers=concurrency) as executor:
    futures = [executor.submit(process_file, file_info) for file_info in file_list]
    for future in tqdm(as_completed(futures), total=len(file_list), desc="processing"):
        try:
            future.result()
        except Exception as e:
            print(f"Error: {e}")