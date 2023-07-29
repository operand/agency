from pydantic import BaseModel, Field
from typing import Dict, Optional


class Action(BaseModel):
    """
    Schema for an action
    """

    name: str = Field(
        ...,
        description="The name of the action."
    )

    args: Dict = Field(
        ...,
        description="The arguments for the action."
    )


class Message(BaseModel):
    """
    Schema for a message
    """

    id: Optional[str] = Field(
        None,
        description="An optional id referenced as `original_message_id` in `response` or `error` messages."
    )

    meta: Optional[Dict] = Field(
        None,
        description="An optional dictionary field for storing metadata about the message."
    )

    to: str = Field(
        ...,
        description="The intended recipient of the message. If set to `*`, the message is broadcast."
    )

    from_: str = Field(
        ...,
        alias='from',
        description="The id of the sender."
    )

    action: Action
