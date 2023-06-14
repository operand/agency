from datetime import datetime
from agency import util
from agency.agent import ACCESS_PERMITTED, access_policy
from agency.agent import Agent
from agency.agents.prompt_methods import PromptMethods
import json
import openai
import textwrap


class DemoAgent(Agent, PromptMethods):

    def __init__(self, id, model, openai_api_key, **kwargs):
        super().__init__(id, **kwargs)
        self.__model = model
        openai.api_key = openai_api_key

    def _prompt_head(self):
        return textwrap.dedent(f"""
        You are "Demo". You are a prototype of an "agent" system which can
        freely interact with its environment.

        Your creator has recently open-sourced your codebase intended to allow
        others to easily create their own AI integrated systems. He is
        demonstrating your abilities so that others can better understand agents
        like yourself and how you may integrate with the world.

        Your goal is to demonstrate your accurate understanding of the world and
        your ability to communicate with other systems as needed to solve any
        problems at hand.

        In order to communicate, you use a simple terminal application where
        your can interact via JSON formatted messages. You can send messages to
        discover and interact with other systems, AI agents, or humans who may
        also be present.

        The following is your current session on the terminal application.
        Respond with a JSON formatted message to continue the conversation.

        %%%%% Terminal App 1.0.0 %%%%%
        (Use the "help" action to see available commands")
        """) + \
            self._message_line({
                "from": self.id(),
                "to": None,
                "thoughts": "I should see what commands are available.",
                "action": "help",
                "args": {},
            }, indent=2) + \
            self._pre_prompt(agent_id=self.space.id()) + \
            json.dumps(self.space._get_help__sync()) + \
            self._message_log_to_list()

    def _pre_prompt(self, agent_id, timestamp=util.to_timestamp(datetime.now())):
        return f"\n[{timestamp}] {agent_id}:"

    def _message_line(self, message, indent=None):
        pre_prompt = self._pre_prompt(message['from'])
        return f"{pre_prompt} {json.dumps(message)}/END"

    @access_policy(ACCESS_PERMITTED)
    def _action__say(self, content: str) -> bool:
        full_prompt = self._full_prompt()
        completion = openai.ChatCompletion.create(
          model=self.__model,
          messages=[{ "role": "user", "content": full_prompt }],
          functions=[
              {

              }
              for 
          ]
          # temperature=0.1,
          # max_tokens=500,
        )
        # parse the output
        action = util.extract_json(completion.choices[0].text, ["/END"])
        self._send(action)
