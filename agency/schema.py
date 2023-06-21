from pydantic import BaseModel, Field
from typing import Dict, Optional


class ActionSchema(BaseModel):
    """
    Schema for validation when "sending" an action. This format is expected by
    the "_send" method of the Agent class.
    """

    # fully qualified name of the receiving agent.
    # if not specified the action is sent to all agents _but_ the sender
    to: Optional[str] = Field(None)

    # natural language explanation for the action
    thoughts: str

    # the action name
    action: str

    # the action arguments
    args: Dict


class MessageSchema(ActionSchema):
    """
    Schema for validation of a received message. This format is expected by the
    "_receive" method of the Agent class.
    """

    # the sending agent
    from_field: str = Field(..., alias='from')
