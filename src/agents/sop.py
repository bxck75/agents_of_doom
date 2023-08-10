# coding=utf-8
# Copyright 2023  The AIWaves Inc. team.

#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""standard operation procedure of an LLM Autonomous agent"""
import json
from component import *


class SOP:
    """
    input:the json of the sop
    output: a sop graph
    """

    def __init__(self, json_path):
        with open(json_path) as f:
            sop = json.load(f)
        self.sop = sop
        self.root = None
        self.temperature = sop["temperature"] if "temperature" in sop else 0.3
        self.active_mode = sop["active_mode"] if "active_mode" in sop else False
        self.log_path = sop["log_path"] if "log_path" in sop else "logs"

        self.shared_memory = {}
        self.nodes = self.init_nodes(sop)
        self.init_relation(sop)
        
        self.controller_dict = {}

    def init_nodes(self, sop):
        # node_sop: a list of the node
        node_sop = sop["nodes"]
        nodes_dict = {}
        for node in node_sop.values():
            
            # str
            name = node["name"]
            
            # true or false
            is_interactive = node["is_interactive"]
            
            """
            agent_states:
            {
                role1:{
                    component1:{
                        component_key: component_value
                        component_key2:componnt_value 
                    }
                }
            }
            """
            agent_states = self.init_states(node["agent_states"])
            
            # config ["style","rule",......]
            config = node["config"]
            
            # contrller  {judge_system_prompt:,judge_last_prompt: ,call_system_prompt: , call_last_prompt}
            self.controller_dict[name] = node["controller"]
            
            now_node = Node(name=name,
                            is_interactive=is_interactive,
                            config=config,
                            agent_states=agent_states)
            nodes_dict[name] = now_node
            
            if "root" in node.keys() and node["root"]:
                self.root = now_node
        return nodes_dict

    def init_states(self, agent_states_dict: dict):
        agent_states = {}
        for key, value in agent_states_dict.items():
            component_dict = {}
            for component, component_args in value.items():
                if component:
                    
                    # "role" "style"
                    if component == "style":
                        component_dict["style"] = StyleComponent(
                            component_args)
                        
                        # "task"
                    elif component == "task":
                        component_dict["task"] = TaskComponent(component_args)
                        
                        # "rule"
                    elif component == "rule":
                        component_dict["rule"] = RuleComponent(component_args)
                        
                        # "demonstration"
                    elif component == "demonstration":
                        component_dict[
                            "demonstration"] = DemonstrationComponent(
                                component_args)
                            
                    # "output"
                    elif component == "output":
                        component_dict["output"] = OutputComponent(
                            component_args)
                        
                     # "demonstrations"   
                    elif component == "cot":
                        component_dict["cot"] = CoTComponent(component_args)

                    #=================================================================================#

                    elif component == "Top_Category_ShoppingComponent":
                        component_dict[
                            "Top_Category_Shopping"] = Top_Category_ShoppingComponent(
                            )
                            
                    elif component == "User_Intent_ShoppingComponent":
                        component_dict[
                            "User_Intent_ShoppingComponent"] = User_Intent_ShoppingComponent(
                            )
                            
                            
                    elif component == "RecomComponent":
                        component_dict["RecomComponent"] = RecomComponent()
                        
                    # "output"
                    elif component == "StaticComponent":
                        component_dict["StaticComponent"] = StaticComponent(
                            component_dict)
                        
                    # "top_k"  "type" "knowledge_base" "system_prompt" "last_prompt"                        
                    elif component == "KnowledgeBaseComponent":
                        component_dict["tool"] = KnowledgeBaseComponent(
                            component_args)
                        
                    elif component == "MatchComponent":
                        component_dict["MatchComponent"] = MatchComponent()
                        
                    elif component == "SearchComponent":
                        component_dict["SearchComponent"] = SearchComponent()
                        
                    # "short_memory_extract_words"  "long_memory_extract_words" "system_prompt" "last_prompt" 
                    elif component == "ExtractComponent":
                        component_dict["ExtractComponent"] = ExtractComponent(
                            component_args)

            agent_states[key] = component_dict
        return agent_states
    

    def init_relation(self, sop):
        relation = sop["relation"]
        for key, value in relation.items():
            for keyword, next_node in value.items():
                self.nodes[key].next_nodes[keyword] = self.nodes[next_node]


class Node():

    def __init__(self,
                 name: str = None,
                 agent_states: dict = None,
                 is_interactive=False,
                 config: list = None,
                 transition_rule: str = None):

        self.next_nodes = {}
        self.agent_states = agent_states
        self.is_interactive = is_interactive
        self.name = name
        self.config = config
        self.transition_rule = transition_rule

    def get_state(self, role, args_dict):
        system_prompt, last_prompt = self.compile(role, args_dict)
        current_role_state = f"目前的角色为：{role}，它的system_prompt为{system_prompt},last_prompt为{last_prompt}"
        return current_role_state

    def compile(self, role, args_dict: dict):
        components = self.agent_states[role]
        system_prompt = ""
        last_prompt = ""
        res_dict = {}
        for component_name in self.config:
            component = components[component_name]
            if isinstance(component, OutputComponent):
                last_prompt = last_prompt + "\n" + component.get_prompt(
                    args_dict)
            elif isinstance(component, PromptComponent):
                system_prompt = system_prompt + "\n" + component.get_prompt(
                    args_dict)
            elif isinstance(component, ToolComponent):
                response = component.func(args_dict)
                args_dict.update(response)
                res_dict.update(response)
        return system_prompt, last_prompt, res_dict
