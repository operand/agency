from typing import Dict, Optional
from pydantic import BaseModel, Field


class MessageSchema(BaseModel):
    # the sending channel
    from_field: str = Field(..., alias='from')

    # the receiving channel
    # if not specified, the action is sent to all channels _but_ the sender
    to: Optional[str] = Field(None)

    # natural language explanation for the action
    thoughts: str

    # the action name
    action: str

    # the action arguments
    args: Dict
