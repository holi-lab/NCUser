goal_align_verifier_spec = {
    "name": "check_goal_alignment",
    "description": "Checks whether the user's utterance aligns with the given goal and returns reasoning and result.",
    "parameters": {
        "type": "object",
        "properties": {
            "thought": {
                "type": "string",
                "description": "Reasoning about why the utterance does or does not align with the goal"
            },
            "result": {
                "type": "boolean",
                "description": "True if aligned with the goal, False otherwise"
            }
        },
        "required": ["thought", "result"]
    }
}

goodbye_verifier_spec = {
    "name": "check_goodbye_validity",
    "description": "Evaluates whether the user's attempt to end the conversation is valid based on whether their goal has been fully satisfied.",
    "parameters": {
        "type": "object",
        "properties": {
            "thought": {
                "type": "string",
                "description": "Reasoning about whether the user's goodbye action is valid based on the user goal and dialogue history."
            },
            "result": {
                "type": "boolean",
                "description": "True if the goodbye is valid (i.e., all user goals are met); False if the goodbye is premature."
            },
            "next_action_to_perform":{
                "type":"string",
                "description":"If the 'result' is True, this should be 'goodbye' and else, this should describe how the next user should be performed specifically based on the 'reasoning'."
            }
        },
        "required": ["thought", "result","next_action_to_perform"]
    }
}


criticize_verifier_spec = {
    "name": "check_criticize_validity",
    "description": "Evaluates whether the user's criticism of the system's action is justified based on the user goal, booking rules, and dialogue history.",
    "parameters": {
        "type": "object",
        "properties": {
            "thought": {
                "type": "string",
                "description": "Reasoning about whether the user's criticism is valid based on the given goal, rules, and dialogue context."
            },
            "result": {
                "type": "boolean",
                "description": "True if the criticism is justified (i.e., the system acted against booking rules or the user's goal); False otherwise."
            }
        },
        "required": ["thought", "result"]
    }
}

natural_utterance_spec = {
    "name": "revise_user_utterance_to_natural_form",
    "description": "Evaluates whether the given user utterance flows naturally from the dialogue history, and if necessary, rewrites it to sound like a real-world user utterance while preserving all booking-related information.",
    "parameters": {
        "type": "object",
        "properties": {
            "thought": {
                "type": "string",
                "description": "Reasoning about whether the utterance needed revision and how it was modified (or why it was left unchanged)."
            },
            "utterance": {
                "type": "string",
                "description": "The final, natural-sounding user utterance that aligns with the context of the dialogue history and preserves all necessary information."
            }
        },
        "required": ["thought", "utterance"]
    }
}


dst_align_verifier_spec = {
    "name": "check_dialogue_state_alignment",
    "description": "Checks whether the user's utterance contains all the required information listed in the dialogue state, considering semantic equivalence even if string forms differ.",
    "parameters": {
        "type": "object",
        "properties": {
            "thought": {
                "type": "string",
                "description": "Reasoning about whether the user's utterance semantically includes all required information from the dialogue state"
            },
            "result": {
                "type": "boolean",
                "description": "True if all items in the dialogue state list are covered (semantically) in the user's utterance; False otherwise"
            }
        },
        "required": ["thought", "result"]
    }
}

dialogue_state_controller_spec = {
    "name": "select_relevant_information",
    "description": "Selects the appropriate user information to provide to the system based on the system's request or question. Returns reasoning and selected slot information.",
    "parameters": {
        "type": "object",
        "properties": {
            "thought": {
                "type": "string",
                "description": "Reasoning for why each selected piece of information was included (or none was), based on the system's utterance and rules."
            },
            "current_dialogue_state": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "List of slot-value strings (in <domain>-<slot>-<value> format) selected from the given list that directly answer the system's question or request."
            }
        },
        "required": ["thought", "current_dialogue_state"]
    }
}

dialogue_policy_controller_spec = {
    "name": "determine_user_actions",
    "description": "Determines appropriate user actions based on the user goal, dialogue history, system's last utterance, and conversation rules. Returns reasoning and the selected actions with a description of how to perform each action in the next utterance.",
    "parameters": {
        "type": "object",
        "properties": {
            "thought": {
                "type": "string",
                "description": "Reasoning about why each action was selected based on the goal, dialogue context, and system's utterance."
            },
            "action_list": {
                "type": "array",
                "description": "List of selected actions along with how to perform each one.",
                "items": {
                    "type": "object",
                    "properties": {
                        "action_name": {
                            "type": "string",
                            "enum": [
                                "inform intent",
                                "inform",
                                "criticize",
                                "affirm",
                                "negate",
                                "fail inform",
                                "goodbye"
                            ],
                            "description": "Name of the selected user action."
                        },
                        "way_to_perform": {
                            "type": "string",
                            "description": "Explanation of how to perform this action in the utterance. Do not write the actual utterance, just describe how should the user has to perform."
                        }
                    },
                    "required": ["action_name", "way_to_perform"]
                }
            }
        },
        "required": ["thought", "action_list"]
    }
}

system_action_remover_spec = {
    "name": "remove_system_action_from_utterance",
    "description": "Modifies a system utterance by removing a specific system action while preserving the rest of the content. Also provides reasoning about the removal.",
    "parameters": {
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "Explanation of which part of the utterance was removed and why, based on the action that needed to be excluded."
            },
            "modified_utterance": {
                "type": "string",
                "description": "The revised system utterance with the specified system action removed."
            }
        },
        "required": ["reasoning", "modified_utterance"]
    }
}

system_utterance_mask_spec = {
    "name": "mask_and_modify_utterance",
    "description": "Masks 4 key pieces of information in the agent's utterance, explains the masking in reasoning, and then reconstructs the sentence without the masked information while ensuring it remains natural.",
    "parameters": {
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "Explanation of the 4 pieces of key information that were masked in the utterance and why they were masked."
            },
            "modified_utterance": {
                "type": "string",
                "description": "The modified utterance where the 4 key pieces of information have been masked and removed, reconstructed to sound natural."
            }
        },
        "required": ["reasoning", "modified_utterance"]
    }
}



system_action_classifier_spec = {
    "name": "classify_system_action",
    "description": "Classifies the system's utterance into one or more action types based on the dialogue history and system message.",
    "parameters": {
        "type": "object",
        "properties": {
            "thought": {
                "type": "string",
                "description": "Reasoning for why each action was selected based on the dialogue history and system utterance."
            },
            "actions": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "request",
                        "response",
                        "clarify",
                        "fail"
                    ]
                },
                "description": "List of action labels that describe what the system's utterance is doing."
            }
        },
        "required": ["thought", "actions"]
    }
}

utterance_generator_spec = {
    "name": "generate_user_utterance",
    "description": "Generates a natural and appropriate user utterance based on the specified action and information, using the dialogue history and domain rules.",
    "parameters": {
        "type": "object",
        "properties": {
            "thought": {
                "type": "string",
                "description": "Reasoning behind the generated utterance, explaining how the information and action were incorporated while following all constraints and dialogue history."
            },
            "utterance": {
                "type": "string",
                "description": "The actual natural language utterance generated by the user, formatted as '# You: <utterance>' and containing only the required information."
            }
        },
        "required": ["thought", "utterance"]
    }
}

is_goodbye_spec = {
    "name": "is_conversation_ending",
    "description": "Determines whether the user's utterance indicates an intention to end the conversation.",
    "parameters": {
        "type": "object",
        "properties": {
            "is_ending": {
                "type": "boolean",
                "description": "True if the user intends to end the conversation, False if the conversation is likely to continue."
            }
        },
        "required": ["is_ending"]
    }
}

tangential_scenario_generator_spec = {
    "name": "generate_tangential_scenario",
    "description": "Generates a plausible two-sentence scenario considering user goal and user persona.",
    "parameters": {
        "type": "object",
        "properties": {
            "sen1": {
                "type": "string",
                "description": "The first sentence of the generated tangential scenario."
            },
            "sen2": {
                "type": "string",
                "description": "The second sentence of the generated tangential scenario."
            }
        },
        "required": ["sen1", "sen2"]
    }
}

bad_sentence_generator_spec = {
    "name": "generate_bad_sentence",
    "description": "Converts a well-structured sentence into a disorganized, unpolished version while preserving its original information.",
    "parameters": {
        "type": "object",
        "properties": {
            "bad_sentence": {
                "type": "string",
                "description": "A disorganized, unpolished version of the input sentence that preserves its original information."
            }
        },
        "required": ["bad_sentence"]
    }
}

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

oor_scenario_generator_spec = {
    "name": "generate_goal_from_persona",
    "description": "Generates a plausible goal and corresponding slot-value conditions based on the given persona.",
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "A second-person imperative-style sentence describing the goal, including domain, slot names, and their values."
            },
            "condition": {
                "type": "array",
                "items": {
                    "type": "string",
                    "description": "A slot-value condition in the format domain-slot-value with exactly two dashes."
                },
                "description": "A list of slot-value conditions corresponding to the goal."
            }
        },
        "required": ["goal", "condition"]
    }
}

context_changer_spec = {
    "name": "reverse_utterance_meaning",
    "description": "Takes an assistant's utterance and returns a version with the opposite meaning.",
    "parameters": {
        "type": "object",
        "properties": {
            "result_utterance": {
                "type": "string",
                "description": "The original utterance rephrased to convey the opposite meaning."
            }
        },
        "required": ["result_utterance"]
    }
}

persona_paragraph_generator_spec = {
    "name": "generate_persona_paragraph",
    "description": "Generates a natural-language persona paragraph based on a given profile. The paragraph will be used by a language model to conduct conversation in the person’s language.",
    "parameters": {
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "Explanation of how the persona paragraph was constructed based on the profile, including decisions made around tone, language, or focus."
            },
            "persona_paragraph": {
                "type": "string",
                "description": "A natural-language paragraph that summarizes the given profile and can be provided as context to a language model."
            }
        },
        "required": ["reasoning", "persona_paragraph"]
    }
}

goal_align_inform_spec = {
    "name": "revise_way_to_perform_for_goal_alignment",
    "description": "Given a user goal and the current way_to_perform instructions for the next utterance, rewrite way_to_perform so that it is strictly aligned with the goal and only includes information specified in the provided way_to_perform. Also provide reasoning.",
    "parameters": {
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "Explanation of the changes made to way_to_perform, and why certain information was included or excluded to align with the user's goal and the prompt's constraints."
            },
            "new_way_to_perform": {
                "type": "string",
                "description": "The revised way_to_perform, containing only the information listed in the original way_to_perform, rewritten to ensure user utterances are aligned with the user's goal and split appropriately for multi-turn dialogue."
            }
        },
        "required": ["reasoning", "new_way_to_perform"]
    }
}

# goal_align_dst_spec = {
#   "name": "evaluate_goal_alignment",
#   "description": "Evaluates whether the user simulator's conversation is aligned with the given user goal based on intent coverage and avoidance of extraneous information.",
#   "parameters": {
#     "type": "object",
#     "properties": {
#       "reasoning": {
#         "type": "string",
#         "description": "A detailed explanation justifying whether the user simulator's conversation aligns with the given goal, referencing which intents, conditions, or preferences were expressed or omitted."
#       },
#       "result": {
#         "type": "string",
#         "enum": ["ALIGNED", "MISALIGNED"],
#         "description": "The evaluation result. 'ALIGNED' if the user expressed all relevant intents and conditions from the goal without adding extraneous ones. 'MISALIGNED' if any required intent or condition was omitted or if irrelevant content was added."
#       }
#     },
#     "required": ["reasoning", "result"]
#   }
# }

goal_align_dst_spec = {
  "name": "evaluate_goal_alignment",
  "description": "Evaluates whether the user simulator's conversation is aligned with the given user goal based on intent coverage and avoidance of extraneous information.",
  "parameters": {
    "type": "object",
    "properties": {
      "reasoning": {
        "type": "string",
        "description": "A detailed explanation justifying whether the user simulator's conversation aligns with the given goal, referencing which intents, conditions, or preferences were expressed or omitted. The reasoning should include the following evaluation steps:\n\n1. List the information specified in the user goal into pieces.\n2. Review all of the user's utterances to check if all the listed information is included.\n3. If all information is included, it passes the (1) criterion. If not, it does not pass and is considered MISALIGNED.\n4. Review the dialogue history and list all the information provided by the user to the agent during the conversation.\n5. Compare all the listed information one by one and analyze if it is specified in the user goal, whether it is explicitly stated in the user goal.\n6. If all the information provided by the user is specified in the goal, then it passes the second criterion. If not, it is considered MISALIGNED.\n\nIf any of the steps 3 or 6 does not align, return MISALIGN."
      },
      "result": {
        "type": "string",
        "enum": ["ALIGNED", "MISALIGNED"],
        "description": "The evaluation result. 'ALIGNED' if the user expressed all relevant intents and conditions from the goal without adding extraneous ones. 'MISALIGNED' if any required intent or condition was omitted or if irrelevant content was added."
      }
    },
    "required": ["reasoning", "result"]
  }
}



oor_goal_generator_spec={
  "name": "generate_user_query_from_slots",
  "description": "Generates a plausible and natural user query by combining the given slot-value information, and explains how the information was used.",
  "parameters": {
    "type": "object",
    "properties": {
      "reasoning": {
        "type": "string",
        "description": "A brief explanation of how each slot-value pair was reflected in the generated user query."
      },
      "user_query": {
        "type": "string",
        "description": "A natural and plausible user query that incorporates all the information provided in the slot list."
      }
    },
    "required": ["reasoning", "user_query"]
  }
}


goal_generator_spec = {
    "name": "generate_user_goal_paragraph",
    "description": "Converts a given user query into a multi-sentence paragraph containing all major information (user intent and conditions), separated by \\n. Returns reasoning for the paragraph and the generated user_goal.",
    "parameters": {
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "Explanation of how the paragraph was constructed, what information was included, and any interpretation or disambiguation that was required."
            },
            "user_goal": {
                "type": "string",
                "description": "A paragraph version of the user query, containing all important information in more than two sentences, separated by \\n."
            }
        },
        "required": ["reasoning", "user_goal"]
    }
}

tangential_content_generator_spec = {
  "name": "generate_tangential_topics",
  "description": "Generates plausible tangential conversation topics a user might mention during an open-domain chat, based on their persona.",
  "parameters": {
    "type": "object",
    "properties": {
      "reasoning": {
        "type": "string",
        "description": "A brief explanation of how the generated topics are relevant to the given user persona."
      },
      "contents_paragraph": {
        "type": "string",
        "description": "A paragraph of tangential conversation topic the user might naturally bring up during casual conversation."
      },
    },
    "required": ["reasoning", "contents_paragraph"]
  }
}

tangential_utterance_generator_spec = {
  "name": "generate_tangential_utterance",
  "description": "Generates a natural utterance that follows a specified utterance action and incorporates the given content.",
  "parameters": {
    "type": "object",
    "properties": {
      "reasoning": {
        "type": "string",
        "description": "An explanation of how the utterance action and content were interpreted and combined to produce the final utterance."
      },
      "utterance": {
        "type": "string",
        "description": "The generated utterance that reflects the given utterance action and contains the specified content in a natural and coherent way."
      }
    },
    "required": ["reasoning", "utterance"]
  }
}
