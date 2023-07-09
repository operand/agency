import inspect
import re
import threading
from typing import List

from colorama import Fore, Style

from agency.schema import ActionSchema, MessageSchema

# access keys
ACCESS = "access"
ACCESS_PERMITTED = "permitted"
ACCESS_DENIED = "denied"
ACCESS_REQUESTED = "requested"


def access_policy(level):
    def decorator(func):
        func.access_policy = level
        return func
    return decorator


class Agent():
    """
    An Actor that may represent an AI agent, computing system, or human user
    """

    ACTION_METHOD_PREFIX = "_action__"

    def __init__(self, id: str) -> None:
        if len(id) < 1 or len(id) > 255:
            raise ValueError("id must be between 1 and 255 characters")
        if re.match(r"^amq\.", id):
            raise ValueError("id cannot start with \"amq.\"")
        self.__id: str = id
        # threading state
        self._thread_started = threading.Event()
        self._thread_stopping = threading.Event()
        self._thread_stopped = threading.Event()
        # set by Space when added
        self._space = None
        # a basic approach to storing messages
        self._message_log: List[MessageSchema] = []
        self.__cached__help = None

    def id(self) -> str:
        """
        Returns the id of this agent. The id is a string that identifies this
        agent within the space. ID's are not necessarily unique. If two agents
        have the same id they will both receive messages sent to that id.
        """
        return self.__id

    def _send(self, action: dict):
        """
        Sends (out) an action
        """
        self._space._route(sender=self, action=action)

    def _receive(self, message: dict):
        """
        Receives and processes an incoming message
        """
        message = MessageSchema(**message).dict(by_alias=True)  # validate
        try:
            # Record message and commit action
            self._message_log.append(message)
            self.__commit(message)
        except Exception as e:
            # Here we handle exceptions that occur while committing an
            # action, including PermissionError's from access denial, by
            # reporting the error back to the sender.
            self._send({
                "to": message['from'],
                "thoughts": "An error occurred",
                "action": "error",
                "args": {
                    "original_message": message,
                    "error": f"{e}",
                },
            })

    def __commit(self, message: dict):
        """
        Invokes action if permitted otherwise raises PermissionError
        """
        # Check if the action method exists
        action_method = None
        try:
            action_method = getattr(
              self, f"{self.ACTION_METHOD_PREFIX}{message['action']}")
        except AttributeError as e:
            # the action was not found
            if message['to'] == self.id():
                # if it was point to point, raise an error
                raise AttributeError(
                    f"\"{message['action']}\" action not found on \"{self.id()}\"")
            else:
                # broadcasts will not raise an error
                return

        self._before_action(message)

        return_value = None
        error = None
        try:

            # Check if the action is permitted
            if self.__permitted(message):

                # Invoke the action method
                # (set _current_message so that it can be used by the action)
                self._current_message = message
                return_value = action_method(**message['args'])
                self._current_message = None

                # An immediate data structure response (return value) if any, from an
                # action method is sent back to the sender as a "return" action. This is
                # useful for actions that simply need to return a value to the sender.
                if return_value is not None:
                    self._send({
                      "to": message['from'],
                      "thoughts": "A value was returned for your action",
                      "action": "return",
                      "args": {
                        "original_message": message,
                        "return_value": return_value,
                      },
                    })
            else:
                raise PermissionError(
                  f"\"{self.id()}.{message['action']}\" not permitted")
        except Exception as e:
            error = e  # save the error for _after_action
            raise Exception(e)
        finally:
            self._after_action(message, return_value, error)

    def __permitted(self, message: dict) -> bool:
        """
        Checks whether the action represented by the message is allowed
        """
        policy = getattr(
          self, f"{self.ACTION_METHOD_PREFIX}{message['action']}").access_policy
        if policy == ACCESS_PERMITTED:
            return True
        elif policy == ACCESS_DENIED:
            return False
        elif policy == ACCESS_REQUESTED:
            return self._request_permission(message)
        else:
            raise Exception(
              f"Invalid access policy for method: {message['action']}, got '{policy}'")

    def _help(self, action_name: str = None) -> list:
        """
        Returns an array of all action methods on this class that match
        'action_name'. If no action_name is passed, returns all actions.
        [
          {
            "to": "<agent_id>",
            "thoughts": "<docstring_of_action_method>",
            "action": "<action_method_name>",
            "args": {
              "arg_name": "<arg_type>",
              ...
            }
          },
          ...
        ]
        """
        if self.__cached__help is None:
            def get_arguments(method):
                sig = inspect.signature(method)
                return {
                  k: v.annotation.__name__
                  if v.annotation != inspect.Parameter.empty else ""
                  for k, v in sig.parameters.items()
                  if v.default == inspect.Parameter.empty
                }

            def get_docstring(method):
                return re.sub(r'\s+', ' ', method.__doc__).strip() if method.__doc__ else ""

            methods = {
              name: getattr(self, name)
              for name in dir(self)
              if name.startswith(self.ACTION_METHOD_PREFIX)
              and callable(getattr(self, name))
            }
            self.__cached__help = [
              {
                'to': self.id(),  # fully qualified agent id to send the action
                'action': name.replace(self.ACTION_METHOD_PREFIX, ''),
                'thoughts': get_docstring(method),
                'args': get_arguments(method),
              }
              for name, method in methods.items()
              if method.access_policy != ACCESS_DENIED \
                and re.search(r'^_action__(help|return|error)$', name) is None
            ]
        if action_name:
            return self.__cached__help[action_name]
        else:
            return self.__cached__help

    # Override any of the following methods as needed to implement your agent

    @access_policy(ACCESS_PERMITTED)
    def _action__help(self, action_name: str = None) -> list:
        """
        Returns list of actions on this agent matching action_name, or all if none
        is passed.
        """
        return self._help(action_name)

    @access_policy(ACCESS_PERMITTED)
    def _action__return(self, original_message: dict, return_value: str):
        """
        Implement this action to handle returned data from a prior action. By
        default this action simply replaces it with an incoming "say".
        """
        print(f"{Fore.YELLOW}WARNING: Data was returned from an action. Implement _action__return to handle it.{Style.RESET_ALL}")

    @access_policy(ACCESS_PERMITTED)
    def _action__error(self, original_message: dict, error: str):
        """
        Implement this action to handle errors from an action.
        """
        print(f"{Fore.YELLOW}WARNING: An error occurred in an action. Implement _action__error to handle it.{Style.RESET_ALL}")

    def _before_action(self, message: dict):
        """
        Called before every action. Override and use this method for logging or
        other situations where you may want to pass through all actions.
        """

    def _after_action(self, original_message: dict, return_value: str, error: str):
        """
        Called after every action. Override and use this method for logging or other
        situations where you may want to pass through all actions.
        """

    def _request_permission(self, proposed_message: dict) -> bool:
        """
        Implement this method to receive a proposed action message and present it to
        the agent for review. Return true or false to indicate whether access
        should be permitted.
        """
        raise NotImplementedError(
            "You must implement _request_permission to use ACCESS_REQUESTED")

    def _after_add(self):
        """
        Called after the agent is added to a space. Override this method to
        perform any additional setup.
        """

    def _before_remove(self):
        """
        Called before the agent is removed from a space. Override this method to
        perform any cleanup.
        """
