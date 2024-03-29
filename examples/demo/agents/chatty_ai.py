import os
import textwrap

from agents.mixins.prompt_methods import PromptMethods
from transformers import AutoModelForCausalLM, AutoTokenizer

from agency.agent import Agent, action

os.environ['TOKENIZERS_PARALLELISM'] = 'true'


class ChattyAI(PromptMethods, Agent):
    """
    Encapsulates a simple chatting AI backed by a language model.
    Uses the transformers library as a backend provider.
    """

    def __init__(self, id: str, **kwargs):
        super().__init__(id)
        # initialize transformers model
        self.tokenizer = AutoTokenizer.from_pretrained(kwargs['model'])
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(kwargs['model'])

    def _prompt_head(self) -> str:
        return textwrap.dedent(f"""
        Below is a conversation between "ChattyAI", an awesome AI that follows
        instructions and a human who they serve.
        """) + \
            self._message_log_to_list(self._message_log)

    def _message_line(self, message: dict, indent: int = None) -> str:
        pre_prompt = self._pre_prompt(message['from'].split('.')[0])
        # Here we format what a previous message looks like in the prompt
        # For "say" actions, we just present the content as a line of text
        if message['action']['name'] == 'say':
            return f"\n{pre_prompt} {message['action']['args']['content']}"
        else:
            return ""

    def _pre_prompt(self, agent_id: str, timestamp=None) -> str:
        return f"\n### {agent_id.split('.')[0]}: "

    @action
    def say(self, content: str):
        """
        Use this action to say something to Chatty
        """
        full_prompt = self._full_prompt()
        input_ids = self.tokenizer.encode(full_prompt, return_tensors="pt")
        output = self.model.generate(
          input_ids,
          attention_mask=input_ids.new_ones(input_ids.shape),
          do_sample=True,
          max_new_tokens=50,
        )
        new_tokens = output[0][input_ids.shape[1]:]
        response_text = self.tokenizer.decode(
          new_tokens,
          skip_special_tokens=True,
        )
        response_content = response_text.split('\n###')[0]
        self.send({
          "to": self.current_message['from'],
          "action": {
            "name": "say",
            "args": {
                "content": response_content,
            }
          }
        })
