
# An Operator is not much more than a name right now. Eventually this could be
# associated with a unique person or entity that can be communicated with.

class Operator():
  """
  Represents an external Actor that communicates through a Channel
  """

  def __init__(self, name: str) -> None:
    self.name = name

  def id(self) -> str:
    return self.name
