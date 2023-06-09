class Operator():
  """
  Represents an external Actor that communicates through a Channel An Operator
  is intended to be a stateful object, allowing access to the message log and
  other information about the Operator.
  """

  def __init__(self, name: str) -> None:
    self.name = name

    # A basic approach to storing messages
    self._message_log = []

  def id(self) -> str:
    return self.name
