import asyncio
import inspect
import re
import traceback
from asyncio import Queue
from contextvars import ContextVar
from typing import Any, Callable, Dict, List

from app.logger import log
from app.agency.schema import Action, ActionHelp, MessageModel
from app.util import generate_help


# Special action names
_RESPONSE_ACTION_NAME = "__response__"
_ERROR_ACTION_NAME = "__error__"


def action(*args, **kwargs):
    """
    Declares instance methods as actions making them accessible to other agents.

    Keyword arguments:
        name: The name of the action. Defaults to the name of the method.
        help: The help object. Defaults to a generated object.
    """
    def decorator(method):
        action_name = kwargs.get("name", method.__name__)
        if action_name in [_RESPONSE_ACTION_NAME, _ERROR_ACTION_NAME]:
            raise ValueError(f"action name '{action_name}' is reserved")
        method.__action_help__ = generate_help(action_name, method)
        return method

    if len(args) == 1 and callable(args[0]) and not kwargs:
        return decorator(args[0])  # The decorator was used without parentheses
    else:
        return decorator  # The decorator was used with parentheses


class ActionError(Exception):
    """Raised from the request() method if the action responds with an error"""


class Agent():
    """
    An Actor that may be an AI agent, software tool, or human user.
    """

    def __init__(self, id: str):
        """
        Initializes an Agent.

        This constructor is not meant to be called directly. It is invoked by
        the Space class when adding an agent.

        Subclasses should call super().__init__() in their constructor.

        Args:
            id: The id of the agent
        """
        if len(id) < 1 or len(id) > 255:
            raise ValueError("id must be between 1 and 255 characters")
        if re.match(r"^amq\.", id):
            raise ValueError("id cannot start with \"amq.\"")
        self.id: str = id
        # --- private properties set by Space/Processor ---
        self._outbound_queue: Queue[MessageModel] = None
        self._is_processing: bool = False
        # --- private properties ---
        self._history: List[MessageModel] = []
        self._history_lock: asyncio.Lock = asyncio.Lock()
        self.__current_message: ContextVar[MessageModel] = ContextVar(
            "current_message", default=None)
        self._all_help: Dict[str, List[ActionHelp]] = {}
        """
        Holds all help objects for all agents in the space.

        agent_id -> action_name -> ActionHelp
        """

    async def send(self, message: MessageModel) -> str:
        """
        Sends (out) a message from this agent.

        Args:
            message: The message

        Returns:
            The UUID of the sent message

        Raises:
            ValueError: If the message is invalid
        """
        if message.from_ != self.id:  # enforce 'from' field
            raise ValueError(
                f"'from' field value '{message.from_}' does not match this agent's id.")
        async with self._history_lock:
            log("info", f"{self.id}: sending", message)
            self._history.append(message)
            await self._outbound_queue.put(message)
        return message.uuid

    async def respond_with(self, value):
        """
        Sends a response with the given value.

        Parameters:
            value (any): The value to be sent in the response message.
        """
        await self.send(
            MessageModel(
                parent_uuid=self.current_message().uuid,
                from_=self.id,
                to=self.current_message().from_,
                action=Action(
                    name=_RESPONSE_ACTION_NAME,
                    args={'value': value})
                ))

    async def raise_with(self, error: Exception):
        """
        Sends an error response.

        Args:
            error (Exception): The error to send.
        """
        await self.send(
            MessageModel(
                parent_uuid=self.current_message().uuid,
                from_=self.id,
                to=self.current_message().from_,
                action=Action(
                    name=_ERROR_ACTION_NAME,
                    args={'error': f'{error.__class__.__name__}: {error}'})
                ))

    async def _receive(self, message: MessageModel):
        """
        Receives and handles an incoming message.

        Args:
            message: The incoming message
        """
        try:
            log("debug", f"{self.id}: received message", message.uuid)

            # Record the message before handling
            async with self._history_lock:
                self._history.append(message)

            # Spawn a task to process the message. This means that messages are
            # processed concurrently and may be completed out of order.
            asyncio.create_task(self.__process(message))
        except Exception:
            log("error",
                f"{self.id}: raised exception while receiving", message)
            traceback.print_exc()

    async def __process(self, message: MessageModel):
        """
        Top level task for processing an incoming message.
        """
        try:
            self.__current_message.set(message)
            await self.__commit(message)
        except Exception as e:
            # Handle errors that occur while committing an action by reporting
            # back to the sender.
            log("warning",
                f"{self.id}: raised exception while processing", message)
            traceback.print_exc()
            await self.raise_with(e)

    async def __commit(self, message: MessageModel):
        """
        Invokes the message's intended action.

        Args:
            message: The incoming message
        """
        # Spawn task to handle the action
        try:
            asyncio.create_task(self.__handle_action(message.action))
        except Exception as e:
            log("warning",
                f"{self.id}: raised exception while handling", message)
            traceback.print_exc()
            await self.raise_with(e)

    async def __handle_action(self, action: Action):
        """
        Top level task for processing an action.

        Args:
            action_call: The action
        """
        try:
            # handle special response actions
            if action.name == _RESPONSE_ACTION_NAME:
                await self.handle_action_value(action.args['value'])
            elif action.name == _ERROR_ACTION_NAME:
                await self.handle_action_error(action.args['error'])

            # handle all other actions
            elif action.name in [help.name for help in self._help()]:
                action_method = self._action_methods()[action.name]

                await self.before_action()

                return_value = None
                error = None
                try:
                    log("debug", f"{self.id}: invoking '{action_method.__name__}'...")
                    return_value = await action_method(**action.args)
                except Exception as e:
                    error = e
                    raise
                finally:
                    await self.after_action(return_value, error)
                return return_value

            else:
                raise AttributeError(
                    f"\"{action.name}\" not found on \"{self.id}\"")
        except Exception as e:
            log("error",
                f"{self.id}: raised exception while handling action", action)
            traceback.print_exc()
            await self.raise_with(e)

    def _action_methods(self) -> Dict[str, Callable]:
        """
        Maps action names to their methods.
        """
        instance_methods = inspect.getmembers(self, inspect.ismethod)
        action_methods = {
            method.__action_help__.name: method
            for method_name, method in instance_methods
            if hasattr(method, "__action_help__")
        }
        return action_methods

    def _find_message(self, uuid: str) -> MessageModel | None:
        """
        Returns a message from the log with the given UUID.

        Args:
            uuid: The UUID of the message to find

        Returns:
            The message or None
        """
        for message in self._history:
            if message.uuid == uuid:
                return message

    def current_message(self) -> MessageModel:
        """
        Returns the full incoming message which invoked the current action.

        This method may be called within an action or action related callback to
        retrieve the current message, for example to determine the sender or
        inspect other details.

        Returns:
            The current message
        """
        return self.__current_message.get()

    def parent_message(self, message: MessageModel = None) -> MessageModel | None:
        """
        Returns the message that the given message is responding to, if any.

        This method may be used within the handle_action_value and
        handle_action_error callbacks.

        Args:
            message: The message to get the parent message of. Defaults to the
            current message.

        Returns:
            The parent message or None
        """
        if message is None:
            message = self.current_message()
        parent_uuid = message.parent_uuid
        if parent_uuid is not None:
            return self._find_message(parent_uuid)

    async def handle_action_value(self, value: Any):
        """
        Receives a return value from a previous action.

        This method receives return values from actions invoked by the send()
        method. It is not called when using the request() method, which returns
        the value directly.

        To inspect the full response carrying this value, use
        current_message(). To inspect the message which generated the value,
        use parent_message().

        Args:
            value: The return value
        """
        if not hasattr(self, "_issued_handle_action_value_warning"):
            self._issued_handle_action_value_warning = True
            log("warning",
                f"A value was returned from an action. Implement {self.__class__.__name__}.handle_action_value() to handle it.")

    async def handle_action_error(self, error: ActionError):
        """
        Receives an error from a previous action.

        This method receives errors from actions invoked by the send() method.
        It is not called when using the request() method, which raises an error
        directly.

        To inspect the full response carrying this error, use
        current_message(). To inspect the message which caused the error, use
        parent_message().

        Args:
            error: The error
        """
        if not hasattr(self, "_issued_handle_action_error_warning"):
            self._issued_handle_action_error_warning = True
            log("warning",
                f"An error was raised from an action. Implement {self.__class__.__name__}.handle_action_error() to handle it.")

    async def after_add(self):
        """
        Called after the agent is added to a space, but before it begins
        processing incoming messages.

        The agent may send messages during this callback using the send()
        method, but may not use the request() method since it relies on
        processing incoming messages.
        """

    async def before_remove(self):
        """
        Called before the agent is removed from a space, after it has finished
        processing incoming messages.

        The agent may send final messages during this callback using the send()
        method, but may not use the request() method since it relies on
        processing incoming messages.
        """

    async def before_action(self):
        """
        Called before every action is invoked.

        This method will only be called if the action exists. Use
        self.current_message() to inspect the current message. If an exception
        is thrown by this method, it will cause the action to not be invoked.
        """

    async def after_action(self, return_value: Any, error: str):
        """
        Called after every action, whether or not an error occurred.

        Use self.current_message() to inspect the current message.

        Args:
            return_value: The return value from the action
            error: The error from the action if any
        """

    def _help(self, action_name: str = None) -> List[ActionHelp]:
        special_actions = [_RESPONSE_ACTION_NAME, _ERROR_ACTION_NAME]
        help_list = [
            method.__action_help__
            for method in self._action_methods().values()
            if action_name is None  # meaning we want all
            and method.__action_help__.name not in special_actions
            or method.__action_help__.name == action_name
        ]
        return help_list

    @action
    async def help(self, action_name: str = None) -> List[ActionHelp]:
        """
        Returns a list of actions on this agent.

        If action_name is passed, returns a list with only that action.
        If no action_name is passed, returns all actions on this agent.

        Args:
            action_name: (Optional) The name of an action to request help for

        Returns:
            A list of actions
        """
        await self.respond_with(self._help(action_name=action_name))
