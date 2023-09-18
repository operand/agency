from typing import Dict, Optional

from pydantic import BaseModel, Field


class Meta(BaseModel):
    """A dictionary field for storing metadata about the message"""

    class Config:
        extra = "allow"
        validate_assignment = True

    id: str = Field(
        ...,
        description="The id of the message."
    )

    parent_id: Optional[str] = Field(
        None,
        description="The id of the previous message that generated this message."
    )


class Action(BaseModel):
    """Schema for an action"""

    class Config:
        extra = "forbid"
        validate_assignment = True

    name: str = Field(
        ...,
        description="The name of the action."
    )

    args: Optional[Dict] = Field(
        None,
        description="The arguments for the action."
    )


class Message(BaseModel):
    """The full message schema used for communication"""

    class Config:
        extra = "forbid"
        validate_assignment = True

    meta: Meta

    from_: str = Field(
        ...,
        alias="from",
        description="The id of the sender."
    )

    to: str = Field(
        ...,
        description="The intended recipient of the message. If set to `*`, the message is broadcast."
    )

    action: Action
