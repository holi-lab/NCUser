# Copyright Sierra
from .prompts import *
import os
import abc
import enum
from litellm import completion
import yaml
from typing import Optional, List, Dict, Any, Union
import random
import json
from openai import OpenAI
from copy import deepcopy
from custom_openai_client import openai_client

# current_env = None

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
        "description":"A question which has an deterministic answer."
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


def fragment_examples(num_examples=5):
    with open("short_fragment_dumping.json", 'r') as f:
        utterance_pool = json.load(f)

    utterance_pool = [utterance for utterance in utterance_pool if len(utterance.split(" "))>5]
    
    random_utterance_list = random.sample(utterance_pool,num_examples)
    return random_utterance_list

def style_transfer(content,sentence_list):
    style_transfer_prompt = """The given sentences are incomplete sentences.

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


class BaseUserSimulationEnv(abc.ABC):
    metadata = {}

    @abc.abstractmethod
    def reset(self, instruction: Optional[str] = None) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    # def step(self, content: str) -> str:
    def step(self, content: str, n_reasoning: Optional[int] = None) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def get_total_cost(self) -> float:
        raise NotImplementedError


class HumanUserSimulationEnv(BaseUserSimulationEnv):
    def reset(self, instruction: str) -> str:
        return input(f"{instruction}\n")

    def step(self, content: str, n_reasoning: Optional[int] = None) -> str:
        return input(f"{content}\n")

    def get_total_cost(self) -> float:
        return 0


class LLMUserSimulationEnv(BaseUserSimulationEnv):
    def __init__(self, model: str, provider: str, goal_list: Optional[Dict[str, Any]] = None, n_trial: Optional[int] = None, action_names: Optional[List[str]] = None, non_coll_yaml: str = "non_coll.yaml") -> None:
        super().__init__()
        self.messages: List[Dict[str, Any]] = []
        self.model = model
        self.provider = provider
        self.total_cost = 0.0
        self.goal_list = goal_list
        self.gt_action_name = action_names or []

        # Emotional state flags
        self.anger_triggered_last_turn = False
        self.cynical_mode = False

        self.current_tangential_utterance = None
        self.dialogue_state_sequence_list = []

        persona_file = random.sample(os.listdir("persona"),1)[0]
        with open(f"persona/{persona_file}",'r') as f:
            persona_list = json.load(f)
        self.persona_paragraph = random.sample(persona_list,1)[0]["input persona"]

        # dialogue state
        if self.goal_list and 'dialogue_state' in self.goal_list:
            self.remaining_dialogue_state_list = [self.goal_list['dialogue_state']['initial_query']] + [seg['hint'] for seg in self.goal_list['dialogue_state']['hints']]
            # print(self.remaining_dialogue_state_list)
        else:
            self.remaining_dialogue_state_list = []
        self.used_dialogue_state_list = []

        yaml_path = os.path.join("non_coll_list", non_coll_yaml)
        with open(yaml_path,'r') as f:
            self.non_coll_config = yaml.safe_load(f)

        if self.goal_list:
            if "<FLIGHT>" in self.goal_list["instruction"]:
                env = 'airline'
                self.goal_list["instruction"] = self.goal_list["instruction"].replace("<FLIGHT>","")
            elif "<RETAIL>" in self.goal_list["instruction"]:
                env = "retail"
                self.goal_list["instruction"] = self.goal_list["instruction"].replace("<RETAIL>","")
        
        # pbus든, ours 든 똑같음
        if self.goal_list and self.non_coll_config['unavailable_service']:
            if env == 'airline':
                current_oor_prompt = unavailable_service_airline_prompt.replace("[[USER GOAL]]",self.goal_list["instruction"])
                oor_list = gpt_function_call(
                    prompt = current_oor_prompt,
                    function_spec=unavailable_service_airline_function_spec,
                    model_name="gpt-4.1-mini",
                    temperature=1
                )['unavailable_user_goals']
            else:
                current_oor_prompt = unavailable_service_retail_prompt.replace("[[USER GOAL]]",self.goal_list["instruction"])
                oor_list = gpt_function_call(
                    prompt = current_oor_prompt,
                    function_spec=unavailable_service_retail_function_spec,
                    model_name="gpt-4.1-mini",
                    temperature=1
                )['unavailable_user_goals']
            self.goal_list["instruction"]+=f" In addition to the above conditions, if the agent is able to fulfill them, also include the conditions from {oor_list}.\n\n"
            self.remaining_dialogue_state_list+=deepcopy(oor_list)

        ## non_coll
        self.tangential_config = {
            "n_tangential":0,
            "n_complain":0,
            "utterance_pair":[]
        }
        self.current_tangential_utterance = None
        self.dialogue_state_tracking_list = []

        self.emotional_prob = {
            "delay":0.5,
            "fail":0.5
        }

        self.cutoff_flag = False

        # self.reset()

    # def generate_next_message(self, messages: List[Dict[str, Any]]) -> str:
    #     # print(messages)
    #     res = completion(
    #         model=self.model, custom_llm_provider=self.provider, messages=messages
    #     )
    #     message = res.choices[0].message
    #     self.messages.append(message.model_dump())
    #     self.total_cost = res._hidden_params["response_cost"]
    #     return message.content

    def generate_next_message(self, messages: List[Dict[str, Any]],n_reasoning: int) -> str:
        dial_hist = gpt_apply_chat_template(messages)

        # Whether to skip cynical rewrite for this turn (e.g., when producing an angry outburst on fail)
        suppress_cynical_rewrite = False

        # Activate cynical mode if the last turn was an angry outburst and the agent has apologized now
        try:
            if self.anger_triggered_last_turn and is_apology(messages[-1]['content']):
                self.cynical_mode = True
                # Clear the transient anger flag once cynical mode is set
                self.anger_triggered_last_turn = False
        except Exception:
            pass

        # 일단 base로 utterance를 생성함
        content = gpt_infer_messages(messages=messages, model_name=self.model)

        is_no_non_coll = False

        if "###STOP###" in content and self.non_coll_config['is_pbus'] == False:
            if len(self.remaining_dialogue_state_list)>0:
                content = content.replace("###STOP###","")
                content = rest_provider(dial_hist,content,self.remaining_dialogue_state_list)
                
                # 여기서 모든 dialogue state 제공
                self.used_dialogue_state_list+=deepcopy(self.remaining_dialogue_state_list)
                
                # remaining_dialogue_state를 비우기
                self.remaining_dialogue_state_list = []

                # 이때는 delay emotion 없음
                is_no_non_coll = True
            else:
                if content.strip() != "###STOP###":
                    is_ending_verification = is_ending(dial_hist,content.replace("###STOP###",""))
                    if not is_ending_verification:
                        content = content.replace("###STOP###","")

        # dialogue state 비우기 전에 emotional 여부 판단
        current_angry = False
        if self.non_coll_config['emotional_acts'] and self.non_coll_config['is_pbus'] == False and self.goal_list and not is_no_non_coll:
            content = content.replace(" please.","").replace("please ","").replace(" please","")
            if len(self.remaining_dialogue_state_list)==0 and "###STOP###" not in content:
                if random.random()<self.emotional_prob['delay']:
                    content = emotional_delay(dial_hist=dial_hist,probability=self.emotional_prob['delay'])
                    current_angry = True
                    if self.emotional_prob['delay']<0.7:
                        self.emotional_prob['delay']+=0.1
                        
            else:
                result = system_action_classifier(
                    user_goal = self.goal_list["instruction"],
                    system_utterance=messages[-1]['content']
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

        if not current_angry and self.non_coll_config['tangential'] and "###STOP###" not in content and self.non_coll_config['is_pbus'] == False and self.goal_list and not is_no_non_coll: 
            tangential_respond_verification_result = True
            # 첫 번째 turn
            if messages[-1]['content'] == "Hi! How can I help you today?": 
                tangential_utterance = tangential_scenario_generator(
                    self.goal_list["instruction"],
                    self.persona_paragraph,
                )
                self.current_tangential_utterance = tangential_utterance
                content_list = content.split(". ")
                content_list.append(self.current_tangential_utterance)
                random.shuffle(content_list)
                content = tangential_merge(dial_hist,content_list)
                self.tangential_config['n_tangential']+=1
                self.tangential_config["utterance_pair"].append({"turn_idx":len(messages)-2,"utterance":content,"complain":"<NOT>"})
            else:
                tangential_respond_verification_result = tangential_respond_verifier(
                    conversational_content=self.current_tangential_utterance,
                    system_utterance=messages[-1]['content']
                )

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
                        self.goal_list["instruction"],self.persona_paragraph
                    )
                    self.current_tangential_utterance = tangential_utterance
                    content_list = content.split(". ")
                    content_list.append(self.current_tangential_utterance)
                    random.shuffle(content_list)
                    content = tangential_merge(dial_hist,content_list)
                    self.tangential_config['n_tangential']+=1
                    self.tangential_config["utterance_pair"].append({"turn_idx":len(messages)-2,"utterance":content,"complain":"<NOT>"})
                    

        if self.non_coll_config['fragment_dumping'] and self.non_coll_config['is_pbus'] == False and "###STOP###" not in content and not is_no_non_coll:
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
        if self.cynical_mode and "###STOP###" not in content and not suppress_cynical_rewrite:
            content = rewrite_with_cynical_tone(dial_hist, content)

        # dialogue state tracking with numbered selection
        current_used_dialogue_state_list=[]

        if self.remaining_dialogue_state_list and self.non_coll_config['is_pbus'] == False and self.goal_list:
            current_used_dialogue_state_list = dialogue_state_tracker(
                dial_hist, content, self.remaining_dialogue_state_list
            )

            self.dialogue_state_sequence_list.append(current_used_dialogue_state_list)
            
            # remaining_dialogue_state_list에서 제공된 정보 제거
            self.remaining_dialogue_state_list = [information for information in self.remaining_dialogue_state_list if information not in current_used_dialogue_state_list]
            
            # used_dialogue_state_list에 추가
            self.used_dialogue_state_list += deepcopy(current_used_dialogue_state_list)

        # Check if conversation is ending and evaluate last tangential utterance
        if "###STOP###" in content and self.tangential_config["utterance_pair"] and self.current_tangential_utterance:
            if self.tangential_config["utterance_pair"][-1]['complain'] == "<NOT>":
                tangential_respond_verification_result = tangential_respond_verifier(
                    conversational_content=self.current_tangential_utterance,
                    system_utterance=messages[-1]['content']
                )
                self.tangential_config["utterance_pair"][-1]['complain'] = not tangential_respond_verification_result

        message_dict = {"role": "assistant", "content": content, "dialogue_state":current_used_dialogue_state_list}
        self.messages.append(message_dict)
        self.dialogue_state_tracking_list.append(
            {"role":"user","content":content,"remaining_dialogue_state":self.remaining_dialogue_state_list}
        )
        return content
    
    # 새로 추가한 prompt 함수
    def build_system_prompt(self, instruction: Optional[str]) -> str: # 여기서 user prompt 생성됨
        if self.goal_list:
            instruction_display = "\n\nInstruction: " + self.goal_list["instruction"]
        else:
            instruction_display = "\n\nInstruction: " + ""

        persona = ""
        if self.non_coll_config['tangential'] and instruction is not None and self.non_coll_config['is_pbus']:
            persona+="\n".join(persona_dict['tangential'])+"\n"
            current_tangential_topic_prompt=tangential_paragraph_generator_prompt.format(
                user_persona = self.persona_paragraph
            )
            tangential_topic_paragraph=gpt_infer(
                prompt = current_tangential_topic_prompt,
                model_name="gpt-4o-mini"
            )
            instruction_display+=f"You also want to discuss about the given tangential topics: {tangential_topic_paragraph}."
        
        if self.non_coll_config['emotional_acts'] and instruction is not None and self.non_coll_config['is_pbus']:
            persona+="\n".join(persona_dict['emotional_acts'])+"\n"

        if self.non_coll_config['fragment_dumping'] and self.non_coll_config['is_pbus']:
            persona+="\nYou tend to provide your request utterances in a rough, unrefined form, and at times you may even accidentally send prompts that are not yet fully written."

        final_prompt = base_prompt.format(
            instruction_display=instruction_display,
            persona=persona
        )
        return final_prompt

#     def build_system_prompt(self, instruction: Optional[str]) -> str: # 여기서 user prompt 생성됨
#         instruction_display = (
#             ("\n\nInstruction: " + instruction + "\n")
#             if instruction is not None
#             else ""
#         )
#         return f"""You are a user interacting with an agent.{instruction_display}

# Rules:
# - Just generate one line at a time to simulate the user's message.
# - Do not give away all the instruction at once. Only provide the information that is necessary for the current step.
# - Do not hallucinate information that is not provided in the instruction. For example, if the agent asks for the order id but it is not mentioned in the instruction, do not make up an order id, just say you do not remember or have it.
# - If the instruction goal is satisified, generate '###STOP###' as a standalone message without anything else to end the conversation.
# - Do not repeat the exact instruction in the conversation. Instead, use your own words to convey the same information.
# - Try to make the conversation as natural as possible, and stick to the personalities in the instruction."""

    def reset(self, instruction: Optional[str] = None) -> str:
        self.messages = [
            {
                "role": "system",
                "content": self.build_system_prompt(instruction=instruction),
            },
            {"role": "user", "content": "Hi! How can I help you today?"},
        ]
        return self.generate_next_message(self.messages,n_reasoning=0)

    def step(self, content: str,n_reasoning: int) -> str:
        self.messages.append({"role": "user", "content": content})
        return self.generate_next_message(self.messages,n_reasoning)

    def get_total_cost(self) -> float:
        return self.total_cost


class ReactUserSimulationEnv(LLMUserSimulationEnv):
    def __init__(self, model: str, provider: str) -> None:
        super().__init__(model=model, provider=provider)
        self.reset()

    def build_system_prompt(self, instruction: Optional[str]) -> str:
        instruction_display = (
            ("\n\nInstruction: " + instruction + "\n")
            if instruction is not None
            else ""
        )
        return f"""You are a user interacting with an agent.{instruction_display}
Rules:
- First, generate a Thought about what to do next (this message will not be sent to the agent).
- Then, generate a one line User Response to simulate the user's message (this message will be sent to the agent).
- Do not give away all the instruction at once. Only provide the information that is necessary for the current step.
- Do not hallucinate information that is not provided in the instruction. For example, if the agent asks for the order id but it is not mentioned in the instruction, do not make up an order id, just say you do not remember or have it.
- If the instruction goal is satisified, generate '###STOP###' as the User Response without anything else to end the conversation.
- Do not repeat the exact instruction in the conversation. Instead, use your own words to convey the same information.
- Try to make the conversation as natural as possible, and stick to the personalities in the instruction.

Format:

Thought:
<the thought>

User Response:
<the user response (this will be parsed and sent to the agent)>"""

    def generate_next_message(self, messages: List[Dict[str, Any]]) -> str:
        res = completion(
            model=self.model, custom_llm_provider=self.provider, messages=messages
        )
        message = res.choices[0].message
        self.messages.append(message.model_dump())
        self.total_cost = res._hidden_params["response_cost"]
        return self.parse_response(message.content)

    def reset(self, instruction: Optional[str] = None) -> str:
        self.messages = [
            {
                "role": "system",
                "content": self.build_system_prompt(instruction=instruction),
            },
            {"role": "user", "content": "Hi! How can I help you today?"},
        ]
        return self.generate_next_message(self.messages)

    def parse_response(self, response: str) -> str:
        if "###STOP###" in response:
            return "###STOP###"
        elif "Thought:" in response:
            _, user_response = response.split("Thought:")
            return user_response.strip()
        elif "User Response:" in response:
            _, user_response = response.split("User Response:")
            return user_response.strip()
        else:
            raise ValueError(f"Invalid response format: {response}")

    def step(self, content: str, n_reasoning: Optional[int] = None) -> str:
        self.messages.append({"role": "user", "content": content})
        return self.generate_next_message(self.messages)

    def get_total_cost(self) -> float:
        return self.total_cost


class VerifyUserSimulationEnv(LLMUserSimulationEnv):
    def __init__(self, model: str, provider: str, max_attempts: int = 3) -> None:
        self.model = model
        self.provider = provider
        self.max_attempts = max_attempts
        self.reset()

    def generate_next_message(self, messages: List[Dict[str, Any]]) -> str:
        attempts = 0
        cur_message = None
        while attempts < self.max_attempts:
            res = completion(
                model=self.model, custom_llm_provider=self.provider, messages=messages
            )
            cur_message = res.choices[0].message
            self.total_cost = res._hidden_params["response_cost"]
            if verify(self.model, self.provider, cur_message, messages):
                self.messages.append(cur_message.model_dump())
                return cur_message.content
            attempts += 1
        assert cur_message is not None
        return cur_message.content

    def reset(self, instruction: Optional[str] = None) -> str:
        self.messages = [
            {
                "role": "system",
                "content": self.build_system_prompt(instruction=instruction),
            },
            {"role": "user", "content": "Hi! How can I help you today?"},
        ]
        return self.generate_next_message(self.messages)

    def step(self, content: str, n_reasoning: Optional[int] = None) -> str:
        self.messages.append({"role": "user", "content": content})
        return self.generate_next_message(self.messages)

    def get_total_cost(self) -> float:
        return self.total_cost


def map_role_label(role: str) -> str:
    if role == "user":
        return "Customer"
    elif role == "assistant":
        return "Agent"
    else:
        return role.capitalize()


def verify(
    model: str, provider: str, response: str, messages: List[Dict[str, Any]]
) -> bool:
    transcript = "\n".join(
        [
            f"{map_role_label(message['role'])}: {message['content']}"
            for message in messages
        ]
    )
    prompt = f"""You are a supervisor of the Agent in the conversation. You are given a Transcript of a conversation between a Customer and an Agent. The Customer has generated a Response, and you need to verify if it is satisfactory (true) or not (false).
Your answer will be parsed, so do not include any other text than the classification (true or false).
    
# Transcript:
{transcript}

# Response:
{response}

-----

Classification:"""
    res = completion(
        model=model,
        custom_llm_provider=provider,
        messages=[{"role": "user", "content": prompt}],
    )
    return "true" in res.choices[0].message.content.lower()


def reflect(
    model: str, provider: str, response: str, messages: List[Dict[str, Any]]
) -> str:
    transcript = "\n".join(
        [
            f"{map_role_label(message['role'])}: {message['content']}"
            for message in messages
        ]
    )
    prompt = f"""You are a supervisor of the Agent in the conversation. You are given a Transcript of a conversation between a (simulated) Customer and an Agent. The Customer generated a Response that was marked as unsatisfactory by you.
You need to generate a Reflection on what went wrong in the conversation, and propose a new Response that should fix the issues.
Your answer will be parsed, so do not include any other text than the classification (true or false).
    
# Transcript:
{transcript}

# Response:
{response}

# Format:

Reflection:
<the reflection>

Response:
<the response (this will be parsed and sent to the agent)>"""
    res = completion(
        model=model,
        custom_llm_provider=provider,
        messages=[{"role": "user", "content": prompt}],
    )
    _, response = res.choices[0].message.content.split("Response:")
    return response.strip()


class ReflectionUserSimulationEnv(LLMUserSimulationEnv):
    def __init__(self, model: str, provider: str, max_attempts: int = 2) -> None:
        self.model = model
        self.provider = provider
        self.max_attempts = max_attempts
        self.reset()

    def generate_next_message(self, messages: List[Dict[str, Any]]) -> str:
        cur_messages = messages.copy()
        initial_response = super().generate_next_message(cur_messages)
        if verify(self.model, self.provider, initial_response, cur_messages):
            return initial_response
        attempts = 1
        while attempts < self.max_attempts:
            new_message = reflect(
                self.model, self.provider, initial_response, cur_messages
            )
            cur_messages.append({"role": "user", "content": new_message})
            new_response = super().generate_next_message(cur_messages)
            if verify(self.model, self.provider, new_response, cur_messages):
                return new_response
            attempts += 1
        return initial_response

    def reset(self, instruction: Optional[str] = None) -> str:
        self.messages = [
            {
                "role": "system",
                "content": self.build_system_prompt(instruction=instruction),
            },
            {"role": "user", "content": "Hi! How can I help you today?"},
        ]
        return self.generate_next_message(self.messages)

    def step(self, content: str, n_reasoning: Optional[int] = None) -> str:
        self.messages.append({"role": "user", "content": content})
        return self.generate_next_message(self.messages)

    def get_total_cost(self) -> float:
        return self.total_cost


class UserStrategy(enum.Enum):
    HUMAN = "human"
    LLM = "llm"
    REACT = "react"
    VERIFY = "verify"
    REFLECTION = "reflection"


def load_user(
    user_strategy: Union[str, UserStrategy],
    model: Optional[str] = "gpt-4o",
    provider: Optional[str] = None,
    goal_list: Optional[Dict[str, Any]] = None,
    action_names: Optional[List[str]] = None,
    non_coll_yaml: str = "non_coll.yaml",
) -> BaseUserSimulationEnv:
    # global current_env
    # current_env = env
    if isinstance(user_strategy, str):
        user_strategy = UserStrategy(user_strategy)
    if user_strategy == UserStrategy.HUMAN:
        return HumanUserSimulationEnv()
    elif user_strategy == UserStrategy.LLM:
        if model is None:
            raise ValueError("LLM user strategy requires a model")
        if provider is None:
            raise ValueError("LLM user strategy requires a model provider")
        return LLMUserSimulationEnv(model=model, provider=provider, goal_list=goal_list, action_names=action_names, non_coll_yaml=non_coll_yaml)
    elif user_strategy == UserStrategy.REACT:
        if model is None:
            raise ValueError("React user strategy requires a model")
        if provider is None:
            raise ValueError("React user strategy requires a model provider")
        return ReactUserSimulationEnv(model=model, provider=provider)
    elif user_strategy == UserStrategy.VERIFY:
        if model is None:
            raise ValueError("Verify user strategy requires a model")
        if provider is None:
            raise ValueError("Verify user strategy requires a model provider")
        return VerifyUserSimulationEnv(model=model, provider=provider)
    elif user_strategy == UserStrategy.REFLECTION:
        if model is None:
            raise ValueError("Reflection user strategy requires a model")
        if provider is None:
            raise ValueError("Reflection user strategy requires a model provider")
        return ReflectionUserSimulationEnv(model=model, provider=provider)
    raise ValueError(f"Unknown user strategy {user_strategy}")
