import json
import textwrap
from datetime import datetime

import openai
from agents.help_methods import HelpMethods
from agents.prompt_methods import PromptMethods

from agency import util
from agency.agent import ACCESS_PERMITTED, Agent, access_policy


class OpenAICompletionAgent(HelpMethods, PromptMethods, Agent):
    """
    An agent which uses OpenAI's completion API for inference
    """

    def __init__(self, id, model, openai_api_key, **args):
        super().__init__(id, **args)
        self.__model = model
        openai.api_key = openai_api_key

    def _prompt_head(self):
        return textwrap.dedent(f"""
        I am "{self.id()}". I am an early prototype of an "agent" system which
        can freely interact with its environment.

        My creator has recently open-sourced my codebase intended to allow
        others to easily create their own AI integrated systems. He is
        demonstrating my abilities so that others can better understand agents
        like myself and how we may integrate with the world.

        My goal is to demonstrate my accurate understanding of the world and my
        ability to communicate with other systems as needed to solve any
        problems at hand.

        In order to communicate, I use a simple terminal application where I can
        interact via JSON formatted messages. I can send messages to discover
        and interact with other systems, AI agents, or humans who may also be
        present.

        %%%%% Terminal App 1.0.0 %%%%%
        """) + \
            self._message_log_to_list()

    def _pre_prompt(self, agent_id, timestamp=util.to_timestamp(datetime.now())):
        return f"\n[{timestamp}] {agent_id}:"

    def _message_line(self, message: dict):
        pre_prompt = self._pre_prompt(message['from'])
        return f"{pre_prompt} {json.dumps(message)}/END"

    @access_policy(ACCESS_PERMITTED)
    def _action__say(self, content: str) -> bool:
        # NOTE that we don't use the content arg here since we construct the
        # prompt from the message log
        full_prompt = self._full_prompt()
        completion = openai.Completion.create(
          model=self.__model,
          prompt=full_prompt,
          temperature=0.1,
          max_tokens=500,
        )
        # parse the output
        action = util.extract_json(completion.choices[0].text, ["/END"])
        self._send(action)
