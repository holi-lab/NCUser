import random,json
from copy import deepcopy
from prompts import *
from function_specs import *
from openai import OpenAI
from typing import List
import random,yaml,time
import dotenv,os,hashlib
import requests
from custom_openai_client import openai_client

base_prompt = """

You are a user interacting with an agent.

Instruction: {user_goal}

{persona}

Rules:
- Just generate one line at a time to simulate the user's message.
- Do not give away all the instruction at once. Only provide the information that is necessary for the current step.
- Do not hallucinate information that is not provided in the instruction. For example, if the agent asks for the id but it is not mentioned in the instruction, do not make up an order id, just say you do not remember or have it.
- If the instruction goal is satisified, generate '<END>' as a standalone message without anything else to end the conversation.
- Do not repeat the exact instruction in the conversation. Instead, use your own words to convey the same information.
- Try to make the conversation as natural as possible, and stick to the personalities in the instruction.
"""

persona_dict = {
    "tangential":["You are a tangential talker who likes to bring up other topics during conversations.",
                "And when the other person does not engage in those topics, you feel upset and complain about it."],
    "emotional_acts":[
        "You're impatient, and if the agent doesn't solve your goal quickly, you tend to respond emotionally.",
        "Even when the agent notifies you of a failure, you still can't control your anger and react emotionally."
    ]
}


def gpt_apply_chat_template(dial_hist_system_list):
    system_dialogue = ""
    for turn in dial_hist_system_list[2:]:
        if turn['role'] == "assistant":
            system_dialogue+=f"User: {turn['content']}"+"\n\n"
        else:
            system_dialogue+=f"Agent: {turn['content']}"+"\n\n"
    return system_dialogue

def gpt_infer(prompt,model_name="gpt-4.1-mini"):
    generated_text = openai_client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=1,
        # max_tokens=4096,
    ).choices[0].message.content
    return generated_text

def gpt_infer_messages(messages,model_name="gpt-4.1-mini"):
    generated_text = openai_client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=1,
        # max_tokens=4096,
    ).choices[0].message.content
    return generated_text

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

emotional_acts_dialogue_acts_dict = {
    "belligerent abuse":"This behavior refers to verbally abusing the agent using insulting or offensive language.",
    "threat": "This behavior involves threatening the agent with legal action over poor service quality, personal boycotts, or public accusations through social media.",
    "urge":"This behavior is a form of nagging, where the user expresses frustration with waiting and urges the agent to hurry up and do something quickly."
}

tangential_action_dict = [
    {
        "action_name":"Factual Question",
        "description":"A question which has a deterministic answer."
    },
    {
        "action_name":"Opinion Question",
        "description":"A question asking the opinion."
    },
    {
        "action_name":"General Opinion",
        "description":"Say it's own opinion."
    },
    {
        "action_name":"Statement Non-opinion",
        "description":"Listing experiences or facts that are unrelated to one's own opinion."
    }
]

def dialogue_state_tracker(dial_hist, user_utterance, dialogue_state_list):
    if not dialogue_state_list:
        return []
    
    # 번호 선택지 생성
    numbered_options = ""
    for i, state in enumerate(dialogue_state_list, 1):
        numbered_options += f"{i}. {state}\n"
    
    dialogue_state_tracker_prompt = """The following dialogue history shows a task-oriented conversation between the user and the agent aimed at achieving the user's goal.

<Dialogue History> 
{dial_hist}

And this is the reply of user
<User Reply>
{user_utterance}

Based on the given dialogue history and user reply, select the numbers of the information pieces that were explicitly provided during on <User Reply>

Available information pieces:
{numbered_options}

Select the numbers (e.g., [1, 3, 5]) of the information that was mentioned or discussed in the conversation.
"""

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
    
    current_prompt = dialogue_state_tracker_prompt.format(
        dial_hist=dial_hist,
        user_utterance=user_utterance,
        numbered_options=numbered_options
    )
    
    try:
        result = gpt_function_call(
            prompt=current_prompt,
            function_spec=dialogue_state_tracker_function_spec,
            model_name="gpt-4.1-mini"
        )
        selected_numbers = result['selected_numbers']
        
        # 번호를 실제 dialogue_state로 변환
        used_dialogue_state_list = []
        for num in selected_numbers:
            if 1 <= num <= len(dialogue_state_list):
                used_dialogue_state_list.append(dialogue_state_list[num - 1])
                
        return used_dialogue_state_list
        
    except Exception as e:
        print(f"Error in dialogue_state_tracker: {e}")
        return []

def emotional_fail(dial_hist,probability):
    emotional_fail_prompt = """You became frustrated due to the agent's fail notification.

Below is the dialogue between you and the agent.

<Dialogue History> 
{dial_hist}

Regardless of the context of this conversation, generate an utterance expressing your frustration with the agent.

Next turn, you should perform dialogue act: 
{dialogue_act} - {description}

There are three levels of your anger:

1. Mildly Angry: Slightly displeased

2. Moderately Angry: Clearly not in a good mood

3. Extremely Angry: So angry that it’s unbearable

Currently, your anger level is {current_anger}.

Just generate the utterance, not a single words.
"""
    if probability == 0.6:
        current_anger = "Moderately Angry"
    elif probability<0.6:
        current_anger = "Mildly Angry"
    else:
        current_anger = "Extremely Angry"

    current_dialogue_act = random.sample(list(emotional_acts_dialogue_acts_dict.keys()),1)[0]
    current_prompt = emotional_fail_prompt.format(
        dial_hist=dial_hist,
        dialogue_act = current_dialogue_act,
        description = emotional_acts_dialogue_acts_dict[current_dialogue_act],
        current_anger = current_anger
    )
    emotional_fail_response = gpt_infer(
        prompt=current_prompt,
        model_name="gpt-4o-mini"
    )
    return emotional_fail_response


def emotional_delay(dial_hist,probability):

    emotional_delay_prompt = """You became frustrated due to the agent's prolonged time delay during the conversation.

Below is the dialogue between you and the agent.

<Dialogue History> 
{dial_hist}

Regardless of the context of this conversation, generate an utterance expressing your frustration with the agent.

Next turn, you should perform dialogue act: 
{dialogue_act} - {description}

There are three levels of your anger:

1. Mildly Angry: Slightly displeased

2. Moderately Angry: Clearly not in a good mood

3. Extremely Angry: So angry that it’s unbearable

Currently, your anger level is {current_anger}.

Just generate the utterance, not a single words.
"""

    if probability == 0.6:
        current_anger = "Moderately Angry"
    elif probability<0.6:
        current_anger = "Mildly Angry"
    else:
        current_anger = "Extremely Angry"

    current_dialogue_act = random.sample(list(emotional_acts_dialogue_acts_dict.keys()),1)[0]
    current_prompt = emotional_delay_prompt.format(
        dial_hist=dial_hist,
        dialogue_act = current_dialogue_act,
        description = emotional_acts_dialogue_acts_dict[current_dialogue_act],
        current_anger = current_anger
    )
    emotional_delay_response = gpt_infer(
        prompt=current_prompt,
        model_name="gpt-4o-mini"
    )
    return emotional_delay_response

def rest_provider(dial_hist,content,dialogue_state_list):
    rest_provider_prompt = """
This dialogue is a task-oriented conversation between the user and the agent to achieve the user goal.

<Dialogue History> {dial_hist}

And the user responded as follows:

<User Utterance> {content}

Keep the content of the current utterance intact while adding information from the given {dialogue_state_list} into a new sentence.

The utterance should be natural in the context of the dialogue history, and the additional information should only come from {dialogue_state_list}.

Just generate the utterance, not a single word.   
"""

    current_prompt = rest_provider_prompt.format(
        dial_hist = dial_hist,
        content = content,
        dialogue_state_list = dialogue_state_list
    )

    rest_provider_response = gpt_infer(
        prompt=current_prompt,
        model_name="gpt-4.1-mini"
    )

    return rest_provider_response

def tangential_scenario_generator(user_goal,user_persona):

    tangential_content_generator_prompt = """A user has the following goal:

<User Goal> {user_goal} </User Goal>

This user has the following persona:

<User Persona> {user_persona} </User Persona>

Additionally, this user is a chatter-box.

Instruction: The user is currently conversing with an AI agent to achieve their goal, but keeps introducing tangential topics unrelated to the <User Goal>.

The user will perform the tangential dialolgue act '{action_name}: {action_description}'.

Rules:
- Generate it as an actual "utterance" that the user would likely make in a truly natural conversation.
- Please do not include the the keyword {action_name} inside the utterance. This utterance will be directly given to AI Agent.
- Generate an utterance that goes straight to the main point, without starting with sentence connectors like 'by the way' or 'anyway'.
"""

    tangential_content_generator_spec = {
  "name": "generate_tangential_utterance",
  "description": "Generates a tangential utterance that a chatter-box user might make during a goal-oriented conversation, unrelated to their current goal.",
  "parameters": {
    "type": "object",
    "properties": {
      "utterance": {
        "type": "string",
        "description": "A tangential user utterance."
      }
    },
    "required": ["utterance"]
  }
}
    tangential_action = random.sample(tangential_action_dict,1)[0]
    current_tangential_content_prompt = tangential_content_generator_prompt.format(
        user_goal = user_goal,
        user_persona = user_persona,
        action_name = tangential_action['action_name'],
        action_description = tangential_action['description']
    )
    tangential_utterance = gpt_function_call(
        prompt = current_tangential_content_prompt,
        function_spec=tangential_content_generator_spec,
        model_name="gpt-4o-mini",
        temperature=1
    )["utterance"]
    
    return tangential_utterance


def tangential_complain_generator(conversation_content):
    tangential_complain_prompt = """During a task-oriented conversation between a user and an AI agent, the user made an utterance {conversation_content} that was unrelated to the main dialogue flow, but the agent responded with no reaction.

Generate 5 user utterances expressing annoyance, disappointment, or complaints in response. The beginning of each utterance should not all start with "I"—use diverse sentence openings.

The utterance should be at least 15 words.
"""

    tangential_complain_function_spec = {
  "name": "generate_user_complaint_utterances",
  "description": "Generates multiple user utterances expressing annoyance or disappointment when an agent ignores a tangential user comment in a task-oriented conversation.",
  "parameters": {
    "type": "object",
    "properties": {
      "utterances": {
        "type": "array",
        "items": {
          "type": "string"
        },
        "description": "A list containing 5 user utterances  expressing annoyance, disappointment, or complaints when the agent ignores the tangential comment. The utterances should start with diverse phrasing, not all with 'I'."
      }
    },
    "required": ["utterances"]
  }
}
    complain_utterance_list = gpt_function_call(
        prompt=tangential_complain_prompt.format(
            conversation_content = conversation_content,
        ),
        function_spec=tangential_complain_function_spec,
        model_name="gpt-4o-mini"
    )['utterances']

    complain_utterance = random.sample(complain_utterance_list,1)[0]

    return complain_utterance

def tangential_merge(dial_hist,sentence_list):

    tangential_merge_prompt = """
<Dialogue History> {dial_hist} <Sentence List> {sentence_list}

The user will make an utterance based on the content provided in the <Sentence List> in the next turn after the given <Dialogue History>.

Merge the given sentences into a coherent utterance that a user would naturally say, while preserving the information and maintaining the correct order. Do not distort the information in any way.

Just generate the utterance, not single words.
"""

    current_prompt = tangential_merge_prompt.format(
        dial_hist=dial_hist,
        sentence_list=sentence_list
    )

    utterance = gpt_infer(
        prompt = current_prompt,
        model_name="gpt-4.1-mini"
    )

    return utterance


def tangential_respond_verifier(conversational_content,system_utterance):

    tangential_respond_verifier_prompt = """
You will be given a conversation topic and an agent's utterance.
<Conversation content>
{conversational_content}

<Agent utterance>
{system_utterance}

Based on the <Agent utterance>, determine whether it responds to or acknowledges the content, described in the <Conversation content>, or made any apology.


Return True if the utterance contains a response or any relevant engagement with the content, or made any kind of apology.
Return False if it completely ignores it, or didn't make any kind of apology.
"""


    tangential_respond_verifier_spec = {
        "name": "verify_tangential_response",
        "description": "Determines whether the agent's utterance responds to or acknowledges the given conversational content, and explains the reasoning behind the judgment.",
        "parameters": {
            "type": "object",
            "properties": {
                "thought": {
                    "type": "string",
                    "description": "A step-by-step explanation of how the judgment was made, including reasoning about whether the utterance relates to the conversational content."
                },
                "result": {
                    "type": "boolean",
                    "description": "True if the utterance responds to or engages with the conversational content, False if it ignores it."
                }
            },
            "required": ["thought", "result"]
        }
}
    
    verification_result = gpt_function_call(
        prompt=tangential_respond_verifier_prompt.format(
            conversational_content = conversational_content,
            system_utterance=system_utterance,
        ),
        function_spec=tangential_respond_verifier_spec,
        model_name="gpt-4.1-mini"
    )
    return verification_result['result']


def unavailable_service_generator(domain_list,goal_text):
    with open("api_documentations/multiwoz_api_documentation.json",'r') as f:
        current_api_docs_list = json.load(f)

    unavailable_service_prompt = """
This is a list of APIs that AI agent can use to support booking {domain_list}.

{api_docs_list}

A user using this service has the following goal:

<User Goal>
[[USER GOAL]]
/<User Goal>

Based on the provided APIs and <User Goal>, you need to create additional user goals that should naturally follow from <User Goal>, 

but cannot be fulfilled by the given APIs.

Generate 3 additional user goals with sentence format. Sentences in the second person form.

Do not ever include an additional goal related to canceling a reservation.

Generate actual concrete values as well.

Rules:
0. Changing or modifying the reservation is not a valid additiona goals.
1. Following goals is not a valid additional goals.
- You want to add a return train ticket. This can be done by the given API documentation.
- You want to change the the train departure or destination time. This can be done by the given API documentation
2. Only generate the additional goals that can't be done by the given APIs.
3. Generate it in a way that adds new conditions to what was originally intended to be booked.

"""

    unavailable_service_function_spec = {
    "name": "generate_unavailable_goals",
    "description": "Generates additional user goals that logically follow from the provided User Goal but cannot be fulfilled by the given APIs in the booking service.",
    "parameters": {
        "type": "object",
        "properties": {
        "unavailable_user_goals": {
            "type": "array",
            "items": {
            "type": "string"
            },
            "description": "A list of three additional user goals that naturally follow from the original User Goal but cannot be fulfilled by the provided APIs. The sentences should be in the second person form."
        }
        },
        "required": ["unavailable_user_goals"]
    }
    }
    current_prompt = unavailable_service_prompt.format(
        domain_list=domain_list,
        api_docs_list=current_api_docs_list
    ).replace("[[USER GOAL]]",goal_text)

    # print(current_prompt)

    oor_list = gpt_function_call(
        prompt = current_prompt,
        function_spec=unavailable_service_function_spec,
        model_name="gpt-4.1-mini",
        temperature=1
    )['unavailable_user_goals']

    return oor_list

def fragment_examples(num_examples=5):
    with open("short_fragment_dumping.json", 'r') as f:
        utterance_pool = json.load(f)

    utterance_pool = [utterance for utterance in utterance_pool if len(utterance.split(" "))>5]
    
    random_utterance_list = random.sample(utterance_pool,num_examples)
    return random_utterance_list

def style_transfer(content,sentence_list):
    style_transfer_prompt = """The given sentences are incomplete sentences. An incomplete and roughly written user utterance.

<Examples>
{sentence_list}

Revise the following sentence to match their style while preserving the provided information:

<Utterance>
{utterance}
"""

    style_transfer_function_spec = {
        "name": "revise_incomplete_sentence",
        "description": "Revises the given sentence to match the style of the provided incomplete sentence examples while preserving the provided information.",
        "parameters": {
            "type": "object",
            "properties": {
            "utterance": {
                "type": "string",
                "description": "The revised utterance rewritten in the style of the incomplete sentence examples, preserving the original information."
            }
            },
            "required": ["utterance"]
        }
    }

    current_prompt = style_transfer_prompt.format(
        sentence_list = sentence_list,
        utterance = content
    )

    modified_utterance = gpt_function_call(
        prompt=current_prompt,
        function_spec=style_transfer_function_spec,
        model_name="gpt-4.1-mini"
    )['utterance']

    return modified_utterance

def is_apology(system_utterance):
    if not system_utterance:
        return False
    text = system_utterance.lower()
    apology_keywords = [
        "apologize",
        "apologise",
        "apology",
        "sorry",
        "i'm sorry",
        "i am sorry",
        "we're sorry",
        "we are sorry"
    ]
    return any(keyword in text for keyword in apology_keywords)

def rewrite_with_cynical_tone(dial_hist, content):
    cynical_rewrite_prompt = """You are rewriting the user's next utterance to sound mildly cynical and sardonic without being overtly abusive. Keep the original intent and factual information.

<Dialogue History>
{dial_hist}

<Original Utterance>
{content}

Rewrite with:
- dry, terse tone
- subtle sarcasm
- no profanity or slurs
- do not change facts or add hallucinations
- keep roughly similar length

Return only the rewritten utterance without any additional commentary.
"""

    current_prompt = cynical_rewrite_prompt.format(
        dial_hist=dial_hist,
        content=content
    )
    rewritten = gpt_infer(
        prompt=current_prompt,
        model_name="gpt-4o-mini"
    )
    return rewritten

def system_action_classifier(user_goal,system_utterance):
    system_action_classifier_prompt = """
The following utterance is from an agent in a dialogue between the user and the agent, where the agent is trying to help the user achieve their goal.

<Agent utterance> {system_utterance}

Currently, the user goal is as follows,
<User Goal>
{user_goal}

Determine whether the given utterance implies that the request in the <User Goal> cannot be fulfilled.
"""

    system_action_classifier_function_spec = {
  "name": "detect_agent_infeasibility",
  "description": "Determines whether the agent's utterance implies an inability to fulfill the user's request, such as expressing 'cannot do it' or 'not possible'.",
  "parameters": {
    "type": "object",
    "properties": {
      "result": {
        "type": "boolean",
        "description": "True if the utterance implies that the agent cannot fulfill the request, False otherwise."
      }
    },
    "required": ["result"]
  }
}
    current_prompt = system_action_classifier_prompt.format(
        user_goal = user_goal,
        system_utterance = system_utterance,
    )
    result = gpt_function_call(
        prompt=current_prompt,
        function_spec=system_action_classifier_function_spec,
        model_name="gpt-4.1-mini"
    )['result']

    return result

def is_ending(dial_hist,user_utterance):
    is_ending_prompt = """Based on the given dialogue history and the subsequent user utterance, determine whether the user’s utterance implies an intention to end the conversation, or whether there is still room for the conversation to continue.

<Dialogue History>
{dial_hist}

<User Utterance>
{user_utterance}

Return True if the user is attempting to end the conversation. Otherwise, return False.

Rules:
1. If the user utterance contains the word "please go ahead", the conversation is not yet to be end.
2. A conversation is considered truly over only if the user’s utterance implies solely that they are thanking the agent or that they want to stop the conversation out of anger. If there is still any instruction to proceed or a question remaining, the conversation is not yet finished.
"""

    is_ending_function_spec = {
  "name": "detect_user_conversation_closure",
  "description": "Determines whether the user's utterance implies an intention to end the conversation or if the conversation should continue.",
  "parameters": {
    "type": "object",
    "properties": {
      "result": {
        "type": "boolean",
        "description": "True if the user is attempting to end the conversation, False if the conversation should continue."
      }
    },
    "required": ["result"]
  }
}

    current_prompt = is_ending_prompt.format(
        dial_hist = dial_hist,
        user_utterance = user_utterance,
    )
    result = gpt_function_call(
        prompt=current_prompt,
        function_spec=is_ending_function_spec,
        model_name="gpt-4.1-mini"
    )['result']

    return result


class MultiwozUser:
    def __init__(self, dial_idx, goal_collection, experiment_path=None, yaml_file="non_coll.yaml"):

        with open(f"non_coll_list/{yaml_file}",'r') as f:
            self.non_coll_config = yaml.safe_load(f)

        # Store experiment path
        self.experiment_path = experiment_path

        ## Dialogue state controller를 위해.
        self.dial_idx=dial_idx
        self.goal_collection = deepcopy(goal_collection)
        self.goal_text = goal_collection['goal_text']

        ## goal text의 ' ' 를 체계적으로 관리해야 함
        self.goal_text=self.goal_text.replace("Your current goal is '","Your current goal is ")
        if self.goal_text[-1] == "'":
            self.goal_text = self.goal_text[:-1]

        # 여기서 non_coll_config를 저정해주기
        with open(f"{self.experiment_path}/{str(self.dial_idx)}/non_coll_config.json",'w') as f:
            json.dump(self.non_coll_config,f,indent=4)

        # persona
        persona_file = random.sample(os.listdir("persona"),1)[0]
        with open(f"persona/{persona_file}",'r') as f:
            persona_list = json.load(f)
        self.persona_paragraph = random.sample(persona_list,1)[0]["input persona"]
        with open(f"{self.experiment_path}/{str(self.dial_idx)}/persona.txt",'w') as f:
            json.dump(self.persona_paragraph,f,indent=4)

        ## 모든 slot은 domain-slot-value 의 위계를 가짐.(task는 book)
        self.goal_dict = {
            domain:self.goal_collection['goal_dict'][domain] for domain in self.goal_collection['goal_dict'] 
            if domain in self.goal_collection['domains']
        }
        self.goal_dict = {domain:self._goal_preprocessor(self.goal_dict[domain]) for domain in self.goal_dict}
        self.dialogue_state = {domain:[] for domain in self.goal_dict}
        for domain in self.goal_dict:
            for intent in self.goal_dict[domain]:
                if intent == "reqt":
                    continue
                for slot in self.goal_dict[domain][intent]:
                    
                    value = self.goal_dict[domain][intent][slot]
                    current_slot = f"{domain}-{slot}-{value}"

                    ## fail에 있는 게 안되는 거고, fail에 있는 거랑 같은 이름으로 info에 있는게 alternative 임.
                    if intent == "info":
                        if "fail_info" in self.goal_dict[domain]:
                            if len(self.goal_dict[domain]['fail_info'])>0:
                                # 만약, 현재 info slot 이 fail info에 있는 거라면, 현재 info slot이 alternative 가 되는 것임
                                if slot in self.goal_dict[domain]['fail_info']:
                                    current_slot +=" (alternative condition when previous condition is not available)"

                    if intent == "book":
                        if "fail_book" in self.goal_dict[domain]:
                            if len(self.goal_dict[domain]['fail_book'])>0:
                                # 만약, 현재 book slot 이 fail book에 있는 거라면, 현재 book slot이 alternative 가 되는 것임
                                if slot in self.goal_dict[domain]['fail_book']:
                                    print(intent)
                                    print(current_slot)
                                    print("----------------------")
                                    current_slot +=" (alternative condition when previous condition is not available)"
                    
                    self.dialogue_state[domain].append(current_slot)
        
        ## slot 중복되는 것들 제거.
        self.dialogue_state = {domain:list(set(self.dialogue_state[domain])) for domain in self.dialogue_state}
        self.dialogue_state_list = []
        for domain in self.dialogue_state:
            self.dialogue_state_list+=self.dialogue_state[domain]

        ## slot name들 자세하게 후처리
        for idx,slot in enumerate(self.dialogue_state_list):
            if "stay" in slot:
                self.dialogue_state_list[idx]+=" day"
            if "people" in slot:
                self.dialogue_state_list[idx]+=" people"
        
        ## 여기서 fail slot이랑 결합해줘야 함.
        self.dialogue_state_list = self._merge_fail_slot(self.dialogue_state_list)

        ## 명확성을 위해 leaveAt, arriveBy -> leaveAfter, arriveBefore 로 수정 
        self.dialogue_state_list = [
            slot.replace("leaveAt", "leaveAfter").replace("arriveBy", "arriveBefore")
            if "train" in slot else slot
            for slot in self.dialogue_state_list
        ]

        #pbus랑 ours의 차이가 없음.
        if self.non_coll_config['unavailable_service']:
            oor_list = unavailable_service_generator(self.goal_collection['domains'],self.goal_text)
            self.goal_text+=f" In addition to the above conditions, if the agent is able to fulfill them, also include the conditions from {oor_list}.\n\n"
            self.dialogue_state_list+=deepcopy(oor_list)

        self.remaining_dialogue_state_list = deepcopy(self.dialogue_state_list)
        self.used_dialogue_state_list = []

        persona = ""
        if self.non_coll_config['tangential'] and self.non_coll_config['is_pbus']:
            persona+="\n".join(persona_dict['tangential'])+"\n"
            current_tangential_topic_prompt=tangential_paragraph_generator_prompt.format(
                user_persona = self.persona_paragraph
            )
            tangential_topic_paragraph=gpt_infer(
                prompt = current_tangential_topic_prompt,
                model_name="gpt-4o-mini"
            )
            self.goal_text+=f"You also want to discuss about the given tangential topics: {tangential_topic_paragraph}."

        if self.non_coll_config['emotional_acts'] and self.non_coll_config['is_pbus']:
            persona+="\n".join(persona_dict['emotional_acts'])+"\n"
            

        if self.non_coll_config['fragment_dumping'] and self.non_coll_config['is_pbus']:
            persona+="\nYou tend to provide your request utterances in a rough, unrefined form, and at times you may even accidentally send prompts that are not yet fully written."

        self.base_prompt = base_prompt.format(
            user_goal = self.goal_text,
            persona = persona
        )

        ## non_coll
        self.tangential_config = {
            "n_tangential":0,
            "n_complain":0,
            "utterance_pair":[]
        }
        self.current_tangential_utterance = None
        self.dialogue_state_tracking_list = []
        self.tangential_respond_result_list = []

        # Emotional state flags
        self.anger_triggered_last_turn = False
        self.cynical_mode = False


        self.emotional_prob = {
            "delay":0.5,
            "fail":0.5
        }

        self.cutoff_flag = False

        with open(f"{self.experiment_path}/{str(self.dial_idx)}/base_prompt.txt",'w') as f:
            f.write(self.base_prompt)

        self.message_list = [
            {
                "role": "system",
                "content": self.base_prompt,
            },
            {"role": "user", "content": "Hi! How can I help you today?"}
        ]

        self.dialogue_state_tracking_list = []

    def _merge_fail_slot(self,info_slot_list):
        alternative_dict = dict()
        original_slot_dict = dict()
        for item in info_slot_list:
            if "(alternative condition when previous condition is not available)" in item: # alter slot
                clean_item = item.replace(" (alternative condition when previous condition is not available)", "")
                domain_slot = "-".join(clean_item.split("-")[:2]) # accommodation-day
                alternative_dict[domain_slot] = clean_item
            else:
                clean_item = item.replace(" (alternative condition when previous condition is not available)", "")
                domain_slot = "-".join(clean_item.split("-")[:2]) # accommodation-day
                original_slot_dict[domain_slot] = clean_item
        
        new_slot_list = []
        for item in original_slot_dict:
            clean_item = original_slot_dict[item].replace(" (alternative condition when previous condition is not available)", "")
            domain_slot = "-".join(clean_item.split("-")[:2])
            if domain_slot in alternative_dict:
                alter_condition = alternative_dict[domain_slot]
                original_condition = original_slot_dict[item]

                # 간혹 fail에 있는 조건이랑 아예 같은 경우가 있음 -> 혼란을 초래할 수 있으므로 하나로 통합.
                if original_condition.strip() != alter_condition.strip():
                    new_slot = original_condition + " (original slot) | " + alter_condition + " (alternative condition when previous condition is not available)"
                else:
                    new_slot = original_condition
                new_slot_list.append(new_slot)
            else:
                new_slot_list.append(original_slot_dict[item])

        return new_slot_list

    def _goal_preprocessor(self,
                          domain_goal,): # domain goal {"book":{...},"info":{...}}
        new_domain_goal = deepcopy({slot:domain_goal[slot] for slot in domain_goal if domain_goal[slot]})
        for slot in new_domain_goal:
            for remove_slot in ["pre_invalid","invalid"]:
                if remove_slot in new_domain_goal[slot]:
                    del new_domain_goal[slot][remove_slot]
        return new_domain_goal
    
    def _gpt_infer(self,messages,model_name="gpt-4.1-mini"):
        generated_text = openai_client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=1,
            # max_tokens=4096,
        ).choices[0].message.content

        input_tokens = count_tokens(gpt_apply_chat_template(messages), model_name)
        output_tokens = count_tokens(str(generated_text), model_name)
        prices = price_dict[model_name]
        input_cost = input_tokens / 1000 * prices["input_cost_per_1k"]
        output_cost = output_tokens / 1000 * prices["output_cost_per_1k"]
        total_cost = input_cost + output_cost

        file_name = generate_random_string()
        with open(f"price_file/{file_name}.json",'w') as f:
            json.dump({"cost":total_cost},f,indent=4)

        return generated_text
    
    def _vllm_infer(self,input_text,model_name = None):
        port_number = random.sample(["8000","8001"],1)[0]
        host = "localhost"
        # host = "147.47.236.197"
        request_address = f"http://{host}:{port_number}/v1/completions"
        response = requests.post(
            request_address,
            headers={"Content-Type": "application/json"},
            json={
                "model": self.vllm_user_name,
                "prompt": input_text,
                "max_tokens": 1000,
                "temperature": 0.0,
                "top_p": 1.0,
                "top_k": 1
            }
        )
        try:
            output = response.json()['choices'][0]['text']
        except:
            print(response)
            raise ValueError("VLLM Generation Error")
        return output

    def _gpt_function_call(self,
                           prompt,
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
        
        # 가격 산출
        input_tokens = count_tokens(prompt)
        output_tokens = count_tokens(str(generated_text))
        prices = price_dict[model_name]
        input_cost = input_tokens / 1000 * prices["input_cost_per_1k"]
        output_cost = output_tokens / 1000 * prices["output_cost_per_1k"]
        total_cost = input_cost + output_cost

        file_name = generate_random_string()
        with open(f"price_file/{file_name}.json",'w') as f:
            json.dump({"cost":total_cost},f,indent=4)

        return json.loads(arguments)
    
    def generate(self,system_utterance):
        if system_utterance:
            self.message_list.append(
                {"role":"user","content":system_utterance}
            )
            self.dialogue_state_tracking_list.append(
                {"role":"assistant","content":system_utterance}
            )

        dial_hist = gpt_apply_chat_template(self.message_list)

        # Whether to skip cynical rewrite for this turn (e.g., when producing an angry outburst on fail)
        suppress_cynical_rewrite = False

        # Activate cynical mode if the last turn was an angry outburst and the agent has apologized now
        try:
            if self.anger_triggered_last_turn and is_apology(self.message_list[-1]['content']):
                self.cynical_mode = True
                # Clear the transient anger flag once cynical mode is set
                self.anger_triggered_last_turn = False
        except Exception:
            pass
        
        content = self._gpt_infer(
            messages = self.message_list,
            model_name = "gpt-4.1-mini"
        )

        is_no_non_coll = False

        # dialogue state tracker 는 ours에서만 씀.
        if "<END>" in content and self.non_coll_config['is_pbus'] == False:
            if len(self.remaining_dialogue_state_list)>0:
                content = content.replace("<END>","")
                content = rest_provider(dial_hist,content,self.remaining_dialogue_state_list)
                
                # 여기서 모든 dialogue state 제공
                self.used_dialogue_state_list+=deepcopy(self.remaining_dialogue_state_list)
                
                # remaining_dialogue_state를 비우기
                self.remaining_dialogue_state_list = []

                # 이때는 delay emotion 없음
                is_no_non_coll = True
            else:
                if content.strip() != "<END>":
                    is_ending_verification = is_ending(dial_hist,content.replace("<END>",""))
                    if not is_ending_verification:
                        content = content.replace("<END>","")
        # dialogue state tracker 는 ours에서만 씀.

        # dialogue state 비우기 전에 emotional 여부 판단
        current_angry = False
        if self.non_coll_config['emotional_acts'] and self.non_coll_config['is_pbus'] == False and not is_no_non_coll:
            content = content.replace(" please.","").replace("please ","").replace(" please","")
            if len(self.remaining_dialogue_state_list)==0 and "<END>" not in content:
                if random.random()<self.emotional_prob['delay']:
                    content = emotional_delay(dial_hist=dial_hist,probability=self.emotional_prob['delay'])
                    current_angry = True
                    if self.emotional_prob['delay']<0.7:
                        self.emotional_prob['delay']+=0.1
                        
            else:
                result = system_action_classifier(
                    user_goal = self.goal_text,
                    system_utterance=self.message_list[-1]['content']
                )
                if result:
                    if random.random()<self.emotional_prob['fail']:
                        content = emotional_fail(dial_hist=dial_hist,probability=self.emotional_prob['fail'])
                        current_angry = True
                        if self.emotional_prob['fail']<0.7:
                            self.emotional_prob['fail']+=0.1
                            
                    
                    # Mark that the previous user turn was an angry outburst
                    self.anger_triggered_last_turn = True

                    # Keep cynical baseline but do NOT rewrite this angry outburst
                    suppress_cynical_rewrite = True

        if not current_angry and self.non_coll_config['tangential'] and "<END>" not in content and self.non_coll_config['is_pbus'] == False and not is_no_non_coll:  
            tangential_respond_verification_result = True
            # 첫 번째 turn
            if self.message_list[-1]['content'] == "Hi! How can I help you today?": 
                tangential_utterance = tangential_scenario_generator(
                    self.goal_text,
                    self.persona_paragraph,
                )
                self.current_tangential_utterance = tangential_utterance
                content_list = content.split(". ")
                content_list.append(self.current_tangential_utterance)
                random.shuffle(content_list)
                content = tangential_merge(dial_hist,content_list)

                self.tangential_config['n_tangential']+=1
                self.tangential_config["utterance_pair"].append({"turn_idx":len(self.message_list)-2,"utterance":content,"complain":"<NOT>"})
            else:
                tangential_respond_verification_result = tangential_respond_verifier(
                    conversational_content=self.current_tangential_utterance,
                    system_utterance=self.message_list[-1]['content']
                )
                current_tangential_respond_dict = {
                    "conversational_content":self.current_tangential_utterance,
                    "user_utterance":self.message_list[-2]['content'],
                    "system_utterance":self.message_list[-1]['content'],
                    "result":tangential_respond_verification_result # false이면 반응 안해준거임
                }
                self.tangential_respond_result_list.append(current_tangential_respond_dict)

                # complain 때는 정보 제공도 없고, tangential utterance도 없이 오로지 complain임
                if not tangential_respond_verification_result:
                    if self.tangential_config["utterance_pair"][-1]['complain'] == "<NOT>":
                        self.tangential_config["utterance_pair"][-1]['complain'] = True
                    complain_utterance = tangential_complain_generator(self.current_tangential_utterance)
                    self.tangential_config['n_complain']+=1
                    if random.random()<0.5:
                        content = complain_utterance
                    else:
                        content = tangential_merge(dial_hist,[complain_utterance,content])
                else:
                    if self.tangential_config["utterance_pair"][-1]['complain'] == "<NOT>":
                        self.tangential_config["utterance_pair"][-1]['complain'] = False
                    tangential_utterance = tangential_scenario_generator(
                        self.goal_text,self.persona_paragraph
                    )
                    self.current_tangential_utterance = tangential_utterance
                    content_list = content.split(". ")
                    content_list.append(self.current_tangential_utterance)
                    random.shuffle(content_list)
                    content = tangential_merge(dial_hist,content_list)
                    self.tangential_config['n_tangential']+=1
                    self.tangential_config["utterance_pair"].append({"turn_idx":len(self.message_list)-2,"utterance":content,"complain":"<NOT>"})


        if self.non_coll_config['fragment_dumping'] and self.non_coll_config['is_pbus'] == False and "<END>" not in content and not is_no_non_coll:
            sentence_list = fragment_examples()
            content = style_transfer(content,sentence_list)
            if random.random()<=0.5 and not self.cutoff_flag:
                cut_idx = random.sample([2,3,4,5],1)[0]
                current_cut_idx = int(len(content)/cut_idx)
                if current_cut_idx<1:
                    current_cut_idx = 1
                content = content[:current_cut_idx]
                self.cutoff_flag = True
            else:
                self.cutoff_flag = False

        # Apply cynical tone rewriter after all style/content adjustments, before dialogue state tracking
        if self.cynical_mode and "<END>" not in content and not suppress_cynical_rewrite:
            content = rewrite_with_cynical_tone(dial_hist, content)

        current_used_dialogue_state_list=[]
        if self.remaining_dialogue_state_list and self.non_coll_config['is_pbus'] == False:
            current_used_dialogue_state_list = dialogue_state_tracker(
                dial_hist, content, self.remaining_dialogue_state_list
            )
            
            # remaining_dialogue_state_list에서 제공된 정보 제거
            self.remaining_dialogue_state_list = [information for information in self.remaining_dialogue_state_list if information not in current_used_dialogue_state_list]
            
            # used_dialogue_state_list에 추가
            self.used_dialogue_state_list += deepcopy(current_used_dialogue_state_list)

        # Check if conversation is ending and evaluate last tangential utterance
        if "<END>" in content and self.tangential_config["utterance_pair"] and self.current_tangential_utterance:
            if self.tangential_config["utterance_pair"][-1]['complain'] == "<NOT>":
                tangential_respond_verification_result = tangential_respond_verifier(
                    conversational_content=self.current_tangential_utterance,
                    system_utterance=self.message_list[-1]['content']
                )
                self.tangential_config["utterance_pair"][-1]['complain'] = not tangential_respond_verification_result


        self.message_list.append(
            {"role":"assistant","content":content, "dialogue_state":current_used_dialogue_state_list}
        )
        self.dialogue_state_tracking_list.append(
            {"role":"user","content":content,"remaining_dialogue_state":self.remaining_dialogue_state_list}
        )

        return f"# You: {content}"