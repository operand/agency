from pydantic import BaseModel, Field
from typing import Dict, Optional


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
    """Schema for a message"""

    class Config:
        extra = "forbid"
        validate_assignment = True

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


def validate_message(message: Message) -> Message:
    """
    Validate and return a message

    Args:
        message: The message

    Returns:
        The validated message

    Raises:
        ValueError: If the message is invalid
    """
    try:
        return Message(**message).dict(by_alias=True, exclude_unset=True)
    except TypeError as e:
        raise ValueError(str(e))