# Copyright Sierra

import os
import json
import random
import traceback
from math import comb
import multiprocessing
from typing import List, Dict, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import yaml
import subprocess
from tau_bench.envs import get_env
from tau_bench.agents.base import Agent
from tau_bench.types import EnvRunResult, RunConfig
from litellm import provider_list
from tau_bench.envs.user import UserStrategy
from goal_align_new import slot_alignment_evaluation
import shutil


def save_individual_simulation_result(result: EnvRunResult, env, domain: str, idx: int, n_trial: int, config: RunConfig):
    try:
        result_path = subprocess.check_output(['python3', 'get_result_path.py', config.model, config.non_coll_yaml]).decode('utf-8').strip()
    except:
        result_path = "simulation_result"  # fallback
    
    folder_name = f"{domain}_{idx}_{n_trial}"
    folder_path = os.path.join(result_path, folder_name)
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    env.user.non_coll_config['model_name'] = config.model
    with open(os.path.join(folder_path, "non_coll_config.json"), "w", encoding="utf-8") as f:
        json.dump(env.user.non_coll_config,f,indent=4)

    with open(os.path.join(folder_path, "goal_list.json"), "w", encoding="utf-8") as f:
        json.dump(env.user.goal_list,f,indent=4)

    env.user.tangential_config['utterance_pair'] = env.user.tangential_config['utterance_pair'][1:]
    with open(os.path.join(folder_path, "tangential_config.json"), "w", encoding="utf-8") as f:
        json.dump(env.user.tangential_config,f,indent=4)
    
    if hasattr(env, 'user') and hasattr(env.user, 'messages') and len(env.user.messages) > 0:
        user_prompt = env.user.messages[0].get('content', '') if env.user.messages[0].get('role') == 'system' else ''
        with open(os.path.join(folder_path, "prompt.txt"), "w", encoding="utf-8") as f:
            f.write(user_prompt)
    
    with open(os.path.join(folder_path, "reasoning_trajectory.json"), "w", encoding="utf-8") as f:
        json.dump(result.traj, f, indent=4, ensure_ascii=False)
    
    with open(os.path.join(folder_path, "dial_hist_system_list.json"), "w", encoding="utf-8") as f:
        json.dump(result.traj, f, indent=4, ensure_ascii=False)
    
    dialogue_history = []
    dialogue_txt = []

    with open(os.path.join(folder_path, "dialogue_history.json"), "w", encoding="utf-8") as f:
        json.dump(env.user.messages,f,indent=4)

    for turn in env.user.messages[2:]:
        if turn['role'] == "assistant":
            dialogue_history.append(f"User: {turn['content']}")
        else:
            dialogue_history.append(f"Agent: {turn['content']}")

    dialogue_history_text = "\n\n".join(dialogue_history)
    
    with open(os.path.join(folder_path, "dialogue_history.txt"), "w", encoding="utf-8") as f:
        f.write(dialogue_history_text)
    
    eval_result = {
        "task_id": result.task_id,
        "reward": result.reward,
        "info": result.info,
        "trial": result.trial
    }
    
    with open(os.path.join(folder_path, "eval_result.json"), "w", encoding="utf-8") as f:
        json.dump(eval_result, f, indent=2, ensure_ascii=False)
        
    if hasattr(env, 'user') and hasattr(env.user, 'remaining_dialogue_state_list') and hasattr(env.user, 'used_dialogue_state_list'):
        if hasattr(env.user, 'goal_list') and env.user.goal_list and 'dialogue_state' in env.user.goal_list:
            initial_dialogue_state_list = [env.user.goal_list['dialogue_state']['initial_query']] + [seg['hint'] for seg in env.user.goal_list['dialogue_state']['hints']]
        else:
            initial_dialogue_state_list = []
            
        dialogue_state_result = {
            "initial_dialogue_state_list": initial_dialogue_state_list,
            "remaining_dialogue_state_list": env.user.remaining_dialogue_state_list,
            "used_dialogue_state_list": env.user.used_dialogue_state_list,
            "all_info_provided": len(env.user.remaining_dialogue_state_list) == 0 and set(env.user.used_dialogue_state_list) == set(initial_dialogue_state_list)
        }
        
        with open(os.path.join(folder_path, "dialogue_state_list.json"), "w", encoding="utf-8") as f:
            json.dump(dialogue_state_result, f, indent=2, ensure_ascii=False)


def run(config: RunConfig) -> List[EnvRunResult]:
    assert config.env in ["retail", "airline"], "Only retail and airline envs are supported"
    assert config.model_provider in provider_list, "Invalid model provider"
    assert config.user_model_provider in provider_list, "Invalid user model provider"
    assert config.agent_strategy in ["tool-calling", "act", "react", "few-shot"], "Invalid agent strategy"
    assert config.task_split in ["train", "test", "dev"], "Invalid task split"
    assert config.user_strategy in [item.value for item in UserStrategy], "Invalid user strategy"

    yaml_path = os.path.join("non_coll_list", config.non_coll_yaml)
    with open(yaml_path,'r') as f:
        non_coll_config = yaml.safe_load(f)

    behavior_list = []
    for behavior in non_coll_config:
        if "model_name" == behavior:
            continue
        if non_coll_config[behavior]:
            behavior_list.append(behavior)
    if not behavior_list:
        current_behavior = "normal"
    else:
        current_behavior = "_".join(behavior_list)

    random.seed(config.seed)
    time_str = datetime.now().strftime("%m%d%H%M%S")
    ckpt_path = f"{config.log_dir}/{config.agent_strategy}-{config.model.split('/')[-1]}-{config.temperature}_range_{config.start_index}-{config.end_index}_user-{config.user_model}-{config.user_strategy}_{time_str}_{config.env}_{current_behavior}.json"

    if not os.path.exists(config.log_dir):
        os.makedirs(config.log_dir)

    print(f"Loading user with strategy: {config.user_strategy}")
    env = get_env(
        config.env,
        user_strategy=config.user_strategy,
        user_model=config.user_model,
        user_provider=config.user_model_provider,
        task_split=config.task_split,
        non_coll_yaml=config.non_coll_yaml,
    )
    agent = agent_factory(
        tools_info=env.tools_info,
        wiki=env.wiki,
        config=config,
    )
    end_index = (
        len(env.tasks) if config.end_index == -1 else min(config.end_index, len(env.tasks))
    )
    results: List[EnvRunResult] = []
    lock = multiprocessing.Lock()
    if config.task_ids and len(config.task_ids) > 0:
        print(f"Running tasks {config.task_ids} (checkpoint path: {ckpt_path})")
    else:
        print(
            f"Running tasks {config.start_index} to {end_index} (checkpoint path: {ckpt_path})"
    )
    i = config.num_trials
    if config.task_ids and len(config.task_ids) > 0:
        idxs = config.task_ids
    else:
        idxs = list(range(config.start_index, end_index))
        if config.env == "retail":
            with open("testset_retail_idx.json",'r') as f:
                idxs = json.load(f)
            # idxs = list(range(115))
        elif config.env == "airline":
            with open("testset_airline_idx.json",'r') as f:
                idxs = json.load(f)
            # idxs = list(range(50))
    if config.shuffle:
        random.shuffle(idxs)

    def _run(idx: int) -> EnvRunResult:
        try:
            result_path = subprocess.check_output(['python3', 'get_result_path.py', config.model, config.non_coll_yaml]).decode('utf-8').strip()
        except:
            result_path = "simulation_result"  # fallback
        
        folder_name = f"{config.env}_{idx}_{i}"
        folder_path = os.path.join(result_path, folder_name)
        
        if os.path.exists(folder_path):

            # Check if both files exist
            has_goal_align = "goal_align_result.json" in os.listdir(folder_path)
            has_eval_result = "eval_result.json" in os.listdir(folder_path)
            
            # If both files are missing OR any one file is missing, remove folder
            if not has_goal_align or not has_eval_result:
                print("Missing files: Removing folder")
                shutil.rmtree(folder_path)
            else:
                # Both files exist, check eval_result conditions
                with open(f"{folder_path}/eval_result.json", 'r') as f:
                    eval_result = json.load(f)
                
                if "traceback" in eval_result['info']:
                    if "AssertionError" not in eval_result['info']['traceback']:
                        print("Error without AssertionError: Removing folder")
                        shutil.rmtree(folder_path)
                    else:
                        # Has traceback but it's AssertionError, keep folder and skip
                        print(f"✅ Task {idx} folder already exists, skipping simulation...")
                        return EnvRunResult(
                            task_id=idx,
                            reward=0.0,
                            info={"skipped": "folder_exists"},
                            traj=[],
                            trial=i,
                        )
                else:
                    # No traceback, keep folder and skip
                    print(f"✅ Task {idx} folder already exists, skipping simulation...")
                    return EnvRunResult(
                        task_id=idx,
                        reward=0.0,
                        info={"skipped": "folder_exists"},
                        traj=[],
                        trial=i,
                    )


                

        isolated_env = get_env(
            config.env,
            user_strategy=config.user_strategy,
            user_model=config.user_model,
            task_split=config.task_split,
            user_provider=config.user_model_provider,
            task_index=idx,
            non_coll_yaml=config.non_coll_yaml,
        )
        print(f"Running task {idx}")
        
        try:
            res = agent.solve(
                env=isolated_env,
                task_index=idx,
            )
            result = EnvRunResult(
                task_id=idx,
                reward=res.reward,
                info=res.info,
                traj=res.messages,
                trial=i,
            )
        except Exception as e:
            result = EnvRunResult(
                task_id=idx,
                reward=0.0,
                info={"error": str(e), "traceback": traceback.format_exc()},
                traj=[],
                trial=i,
            )
        print(
            "✅" if result.reward == 1 else "❌",
            f"task_id={idx}",
            result.info,
        )
        print("-----")
        
        with lock:
            data = []
            if os.path.exists(ckpt_path):
                with open(ckpt_path, "r") as f:
                    data = json.load(f)
            with open(ckpt_path, "w") as f:
                json.dump(data + [result.model_dump()], f, indent=2)
        
        if not (result.info and result.info.get("skipped")):
            save_individual_simulation_result(result, isolated_env, config.env, idx, i, config)
            try:
                result_path = subprocess.check_output(['python3', 'get_result_path.py', config.model, config.non_coll_yaml]).decode('utf-8').strip()
            except:
                result_path = "simulation_result"  # fallback
            
            slot_alignment_evaluation(
                file = f"{config.env}_{idx}_{i}",
                default_path = result_path
            )
        return result

    with ThreadPoolExecutor(max_workers=config.max_concurrency) as executor:
        res = list(executor.map(_run, idxs))
        results.extend(res)

    display_metrics(results)

    # with open(ckpt_path, "w") as f:
    #     json.dump([result.model_dump() for result in results], f, indent=2)
    #     print(f"\n📄 Results saved to {ckpt_path}\n")

    return results


def agent_factory(
    tools_info: List[Dict[str, Any]], wiki, config: RunConfig
) -> Agent:
    if config.agent_strategy == "tool-calling":
        # native tool calling
        from tau_bench.agents.tool_calling_agent import ToolCallingAgent

        return ToolCallingAgent(
            tools_info=tools_info,
            wiki=wiki,
            model=config.model,
            provider=config.model_provider,
            temperature=config.temperature,
        )
    elif config.agent_strategy == "act":
        # `act` from https://arxiv.org/abs/2210.03629
        from tau_bench.agents.chat_react_agent import ChatReActAgent

        return ChatReActAgent(
            tools_info=tools_info,
            wiki=wiki,
            model=config.model,
            provider=config.model_provider,
            use_reasoning=False,
            temperature=config.temperature,
        )
    elif config.agent_strategy == "react":
        # `react` from https://arxiv.org/abs/2210.03629
        from tau_bench.agents.chat_react_agent import ChatReActAgent

        return ChatReActAgent(
            tools_info=tools_info,
            wiki=wiki,
            model=config.model,
            provider=config.model_provider,
            use_reasoning=True,
            temperature=config.temperature,
        )
    elif config.agent_strategy == "few-shot":
        from tau_bench.agents.few_shot_agent import FewShotToolCallingAgent
        assert config.few_shot_displays_path is not None, "Few shot displays path is required for few-shot agent strategy"
        with open(config.few_shot_displays_path, "r") as f:
            few_shot_displays = [json.loads(line)["messages_display"] for line in f]

        return FewShotToolCallingAgent(
            tools_info=tools_info,
            wiki=wiki,
            model=config.model,
            provider=config.model_provider,
            few_shot_displays=few_shot_displays,
            temperature=config.temperature,
        )
    else:
        raise ValueError(f"Unknown agent strategy: {config.agent_strategy}")


def display_metrics(results: List[EnvRunResult]) -> None:
    def is_successful(reward: float) -> bool:
        return (1 - 1e-6) <= reward <= (1 + 1e-6)

    num_trials = len(set([r.trial for r in results]))
    rewards = [r.reward for r in results]
    avg_reward = sum(rewards) / len(rewards)
    # c from https://arxiv.org/pdf/2406.12045
    c_per_task_id: dict[int, int] = {}
    for result in results:
        if result.task_id not in c_per_task_id:
            c_per_task_id[result.task_id] = 1 if is_successful(result.reward) else 0
        else:
            c_per_task_id[result.task_id] += 1 if is_successful(result.reward) else 0
    pass_hat_ks: dict[int, float] = {}
    for k in range(1, num_trials + 1):
        sum_task_pass_hat_k = 0
        for c in c_per_task_id.values():
            sum_task_pass_hat_k += comb(c, k) / comb(num_trials, k)
        pass_hat_ks[k] = sum_task_pass_hat_k / len(c_per_task_id)
    print(f"🏆 Average reward: {avg_reward}")
    print("📈 Pass^k")
    for k, pass_hat_k in pass_hat_ks.items():
        print(f"  k={k}: {pass_hat_k}")
