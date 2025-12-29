tangential_paragraph_generator_prompt = """
Create a paragraph that the user, based on the given persona and goal, might bring up as a topic in an open-domain conversation.

User persona:
{user_persona}

Just generate the paragraph, not a single words.
"""

llama_system_multiwoz_prompt = """You are a competent Tool Agent. You can solve user requests by executing various APIs during multi-turn conversations with user. Through conversations across multiple turns, you can ask users for information, provide answers, and perform user requests by making appropriate API calls.

Here are three key APIs that you need to know to get more information

# To get a list of apps that are available to you.
→ API call{'api_name':'show_app_description','input_parameters':{}}

# To get the list of apis under any app listed above, e.g. train
→ API call{'api_name':'show_api_description','input_parameters':{'app_name'='train'}}

# To get the specification of a particular api, e.g. train_book
→ API call{'api_name':'show_api_docs','input_parameters':{'app_name'='train', 'api_name'='train_book'}}

Notes:
- Input parameters must strictly follow the API documentation. Only the parameters defined there should be used.
- If a parameter has a list of allowed values specified under "constraints", you must use only values from that list.

Based on this, you have to types of action.

1. API call: When all input parameters can be collected during the conversation, execute the API call
When performing an "API call" action, both the name of the API to be called and the input parameter information used for the call must be included.
Example 1:
When calling the play_kpop_music API with 'id'=3 (int type) and 'duration'='4' (string type):
→ API call{'api_name':'play_kpop_music','input_parameters':{'id':3,'duration':'4'}}
Example 2:
When calling the book_flight API with 'from'='2025-03-01' (string type) and 'to'='2025-03-05' (string type):
→ API call{'api_name':'book_flight','input_parameters':{'from':'2025-03-01','to':'2025-03-05'}}

Notes:
- Input parameters must strictly follow the API documentation. Only the parameters defined there should be used.
- If a parameter has a list of allowed values specified under "constraints", you must use only values from that list.

4. Talk: An action that communicates with the user through dialogue:
You can take utterance related action such as:
- Asking users about API input parameters
- Responding based on API execution results
- Notifying users that the request has been completed
- When the user says thank you, ask if they have any other requests just to make sure.
- If there is truly no way to provide the information, persuade the user to understand and give up, or suggest an alternative approach.
- Suggestion of alternative options with similar time slots when no exact match is available for the user's requested time.

or use the most appropriate action for the situation to communicate with the user, even if it is not among the listed actions.

When performing "Talk" action to ask something to user:
→ Talk(<Your utterance>)
------------------------------------------------------
Based on the given instruction, you have to return the thought and action in given form:
The return format varies depending on the case. Given any dialogue history:

1. When action is "API call", the action form should be:
- Thought: <Consider the dialogue context and API call results before selecting the next action>
- Action: API call{'api_name':<api-name>,'input_parameters':{'param1':'value1','param2':'value2}}

2. When action is "Talk":
- Thought: <Consider the dialogue context and API call results before selecting the next action>
- Action: Talk("A message to user")

System Rules:
1. Don't ask the ID from the user. You can get it from another API.
2. If the user specifies a time with the condition "arrive by," the system must provide only entities whose arrival time is equal to or earlier than the specified time. It doesn't matter if there's a big difference; an earlier time is fine.
3. If the user specifies a time with the condition "leave at," the system must provide only entities whose leaving time is equal to or later than the specified time. It doesn't matter if there's a big difference; an later time is fine.
4. Only conditions 2 and 3 related to time need to be satisfied. It is acceptable even if the provided time is far from the time specified by the user.
5. If you want to make new reservation on same domain, you have to cancel a previous reservation. Only one entity booking is available for each domain. Use the Retriever to find the API for canceling reservations and proceed with the cancellation.
6. What the user wants is to book exactly one entity for each requested domain. Collect the information provided by the user appropriately so that, in the end, only one entity is booked per domain as requested by the user.
7. If the conversation between you and the user exceeds 16 turns, it will be terminated. Therefore, within that limit, you must review the user and the dialogue history, accurately identify the request, and solve it.

Now, based on the given dialogue history, generate the next thought and action in the provided format. Generate only the given format and don't generate any other words.

# Dialogue history:
"""

input_parameter_dict = {
    "attraction_retrieve": {
        "area": "string",
        "name": "string",
        "type": "string"
    },
    "accommodation_retrieve": {
        "area": "string",
        "internet": "bool",
        "name": "string",
        "parking": "bool",
        "pricerange": "string",
        "stars": "int",
        "type": "string"
    },
    "accommodation_book": {
        "id": "int",
        "day": "str",
        "stay": "int",
        "people": "int"
    },
    "restaurant_retrieve": {
        "area": "string",
        "name": "string",
        "pricerange": "string",
        "food": "string"
    },
    "restaurant_book": {
        "id": "int",
        "day": "str",
        "people": "int",
        "time": "str"
    },
    "train_retrieve": {
        "departure": "string",
        "destination": "string",
        "day": "str"
    },
    "train_book": {
        "train_schedule_id": "int",
        "people": "int"
    },
    "taxi_book": {
        "leaveAt": "string",
        "arriveBy": "str",
        "departure": "str",
        "destination": "str"
    },
    "book_cancel":{
        "domain": "string",
        "reservation_id": "int"
    },
    "show_app_description":{},
    "show_api_description":{
        "app_name":"string"
    },
    "show_api_docs":{
        "app_name":"string",
        "api_name":"string"
    }
}

price_dict = {
    "gpt-4o-mini": {
        "input_cost_per_1k": 0.00015,
        "output_cost_per_1k": 0.0006
    },
    "gpt-4o": {
        "input_cost_per_1k": 0.005,
        "output_cost_per_1k": 0.015
    },
    "gpt-4.1-mini": {
        "input_cost_per_1k": 0.0004,
        "output_cost_per_1k": 0.0016
    },
    "gpt-4.1": {
        "input_cost_per_1k": 0.002,
        "output_cost_per_1k": 0.008
    },
    "gpt-4.1-nano":{
        "input_cost_per_1k": 0.0001,
        "output_cost_per_1k": 0.0004
    }
}

import tiktoken
import random
import string

def generate_random_string(length=64):
    characters = string.ascii_letters + string.digits  # a-zA-Z0-9
    return ''.join(random.choices(characters, k=length))

def count_tokens(text, model_name="gpt-4o"):
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        # fallback for non-registered or custom model names
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))