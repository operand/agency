from channel import Channel


class IOChannel(Channel):
  """
  Encapsulates prompt/response to stdin/stdout. This allows use directly from
  the invoking terminal
  """
  def send_prompt(self, prompt):
    print(prompt)
    # TODO: handle commands and return as a proper action rather than always a
    # say. could also introduce a syntax (eg. "/read_file ...") and can also
    # allow all actors use it, replacing json
    action_response = {
      "action": "say",
      "args": {
        "content": input(),
      }
    }
    return action_response
