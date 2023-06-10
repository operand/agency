from datetime import datetime
from everything.things import util
from everything.things.operator import ACCESS_PERMITTED, access_policy
from everything.things.operator import Operator
from everything.operators.prompt_methods import PromptMethods
import json
import openai
import textwrap


class DemoAgent(Operator, PromptMethods):

    def __init__(self, id, model, openai_api_key, **kwargs):
        super().__init__(id, **kwargs)
        self.__model = model
        openai.api_key = openai_api_key

    def _prompt_head(self):
        return textwrap.dedent(f"""
        I am "Demo". I am an AI system under development by my human creator,
        Dan. I am an early prototype of an "agent" system which can freely
        interact with its environment.

        Dan has recently open-sourced a portion of my codebase intended to allow
        others to easily create their own AI integrated systems. He is recording
        a video demonstration of my capabilities to share with others.

        Our goal is to demonstrate the possibilities of artificial intelligence
        integration so that our audience can better understand agents like
        myself and our capabilities.

        My goal is to demonstrate my accurate understanding of the world and my
        ability to communicate with other systems as needed to solve any
        problems at hand.

        To enable me to communicate, Dan created a simple terminal application
        where we can correspond via JSON formatted messages. I can use it to
        discover and interact with other systems, other AI agents, or Dan.

        It is {util.to_timestamp(datetime.now())}. I am ready to begin with our
        demonstration.


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
            self._pre_prompt(operator_id=self._space.id()) + \
            json.dumps(self._space._get_help__sync()) + \
            self._message_log_to_list()

    def _pre_prompt(self, operator_id, timestamp=util.to_timestamp(datetime.now())):
        return f"\n[{timestamp}] {operator_id}:"

    def _message_line(self, message, indent=None):
        pre_prompt = self._pre_prompt(message['from'])
        return f"{pre_prompt} {json.dumps(message)}/END"

    @access_policy(ACCESS_PERMITTED)
    def _action__say(self, content: str) -> bool:
        full_prompt = self._full_prompt()
        util.debug(f"*openai prompt:", full_prompt)
        completion = openai.Completion.create(
          model=self.__model,
          prompt=full_prompt,
          temperature=0.1,
          max_tokens=500,
        )
        util.debug(f"openai completion response:", completion)
        # parse the output
        action = util.extract_json(completion.choices[0].text, ["/END"])
        self._send(action)