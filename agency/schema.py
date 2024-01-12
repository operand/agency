from typing import Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Model(BaseModel):
    """
    Base for all models. Inherits from pydantic.BaseModel.
    """

    class Config:
        extra = "forbid"
        validate_assignment = True
        populate_by_name = True


class Action(Model):
    """Schema for an action"""

    name: str = Field(
        ...,
        description="The name of the action.")

    args: Optional[Dict] = Field(
        None,
        description="The arguments for the action.")

    def to_markdown(self):
        return self.name


class VarHelp(Model):
    type: str = Field(
        ...,
        description="The type.")

    description: str = Field(
        None,
        description="The description.")


class ActionHelp(Model):
    """Schema for an action help"""

    name: str = Field(
        ...,
        description="The name of the action.")

    description: str = Field(
        None,
        description="The description of the action.")

    args: Optional[Dict[str, VarHelp]] = Field(
        None,
        description="The arguments for the action.")

    returns: Optional[VarHelp] = Field(
        None,
        description="The return values for the action.")


class MessageModel(Model):
    """
    The full message schema used for communication between agents.
    """

    uuid: str = Field(
        default_factory=lambda: str(uuid4()),
        min_length=36,
        max_length=36,
        pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        description="The UUID of the message.")

    parent_uuid: Optional[str] = Field(
        None,
        min_length=36,
        max_length=36,
        pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        description="The UUID of the message that this message responds to.")

    meta: Dict = {}
    """
    An optional dictionary field for storing metadata about the message.
    """

    from_: str = Field(
        ...,
        alias='from',
        description='The id of the sender.')

    to: str = Field(
        ...,
        description='The intended recipient of the message.')

    action: Action = Field(
        ...,
        description='The action to perform')
