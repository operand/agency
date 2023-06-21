from abc import abstractmethod
from agency.schema import ActionSchema, MessageSchema
import inspect
import queue
import re
import threading


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


ACTION_METHOD_PREFIX = "_action__"


class Agent():
    """
    An Actor that may represent a human, AI, or other system.
    """

    def __init__(self, id: str) -> None:
        self.__id = id
        self.__message_queue = queue.Queue()
        self.__cached__get_action_help = None
        # threading related
        self.__thread = None
        self.running = threading.Event()
        self.stopping = threading.Event()
        # set by parent Space when added
        self.space = None
        # A basic approach to storing messages
        self._message_log = []

    def id(self, fully_qualified=True) -> str:
        """
        Returns the fully qualified id of this agent
        """
        if fully_qualified:
            _id = self.__id
            if self.space is not None:
                _id = f"{self.__id}.{self.space.id()}"
            return _id
        else:
            return self.__id

    def run(self):
        """Starts the agent in a thread"""
        if not self.running.is_set():
            self.__thread = threading.Thread(target=self.__process)
            self.__thread.start()
            self.running.set()

    def stop(self):
        """Stops the agents thread"""
        self.stopping.set()
        self.__thread.join()

    def _send(self, action: ActionSchema):
        """
        Validates and sends (out) an action
        """
        # define message, validate, and route it
        message = MessageSchema(**{
          **action,
          "from": self.id(),
        }).dict(by_alias=True)
        # Record message and route it
        self._message_log.append(message)
        self.space._route(message)

    def _receive(self, message: MessageSchema):
        """
        Validates and enqueues an incoming action to be processed
        """
        message = MessageSchema(**message).dict(by_alias=True)
        # Record message and place on queue
        self._message_log.append(message)
        self.__message_queue.put(message)

    def __process(self) -> str:
        """
        Continually processes queued messages/actions
        """
        while not self.stopping.is_set():
            try:
                message = self.__message_queue.get(timeout=0.01)
                try:
                    self.__commit_action(message)
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
            except queue.Empty:
                continue

    def __commit_action(self, message: MessageSchema):
        """
        Invokes action if permitted otherwise raises PermissionError
        """
        # Check if the action exists
        action_method = None
        try:
            action_method = getattr(
              self, f"{ACTION_METHOD_PREFIX}{message['action']}")
        except AttributeError as e:
            # the action was not found
            if message['to'] == self.id():
                # if it was point to point, raise an error
                raise AttributeError(
                    f"\"{message['action']}\" action not found on \"{self.id()}\"")
            else:
                # broadcasts will not raise an error
                return

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
            # If an error occurs, we reraise it to be handled by the process loop
            error = e
            raise Exception(e)
        finally:
            # Always call _after_action
            self._after_action(message, return_value, error)

    def __permitted(self, message) -> bool:
        """
        Checks whether the action represented by the message is allowed
        """
        policy = getattr(
          self, f"{ACTION_METHOD_PREFIX}{message['action']}").access_policy
        if policy == ACCESS_PERMITTED:
            return True
        elif policy == ACCESS_DENIED:
            return False
        elif policy == ACCESS_REQUESTED:
            return self._request_permission(message)
        else:
            raise Exception(
              f"Invalid access policy for method: {message['action']}, got '{policy}'")

    def _get_help(self, action_name: str = None) -> list:
        """
        Returns an array of all action methods on this class that match
        'action_name'. If no action_name is passed, returns all actions.
        [
          {
            "space.agent": "<space_name>.<agent_name>",
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
        if self.__cached__get_action_help is None:
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
              if name.startswith(ACTION_METHOD_PREFIX)
              and callable(getattr(self, name))
            }
            self.__cached__get_action_help = [
              {
                'to': self.id(),  # fully qualified agent id to send the action
                'action': name.replace(ACTION_METHOD_PREFIX, ''),
                'thoughts': get_docstring(method),
                'args': get_arguments(method),
              }
              for name, method in methods.items()
              if method.access_policy != ACCESS_DENIED \
                and re.search(r'^_action__(help|return|error)$', name) is None
            ]
        if action_name:
            return self.__cached__get_action_help[action_name]
        else:
            return self.__cached__get_action_help

    def _action_exists(self, action_name: str):
        """
        Returns true if the action exists on this agent
        """
        return hasattr(self, f"{ACTION_METHOD_PREFIX}{action_name}")

    # Override any of the following methods as needed to implement your agent

    @access_policy(ACCESS_PERMITTED)
    def _action__help(self, action_name: str = None) -> list:
        """
        Returns list of actions on this agent matching action_name, or all if none
        is passed.
        """
        return self._get_help(action_name)

    @access_policy(ACCESS_PERMITTED)
    def _action__return(self, original_message: MessageSchema, return_value: str):
        """
        Implement this action to handle returned data from a prior action. By
        default this action simply replaces it with an incoming "say".
        """
        print("WARNING: Data was returned from an action. Implement _action__return to handle it.")
        pass

    @access_policy(ACCESS_PERMITTED)
    def _action__error(self, original_message: MessageSchema, error: str):
        """
        Implement this action to handle errors from an action.
        """
        print("WARNING: An error occurred in an action. Implement _action__error to handle it.")
        pass

    def _after_action(self, original_message: MessageSchema, return_value: str, error: str):
        """
        Called after every action. Override and use this method for logging or other
        situations where you may want to pass through all actions.

        Note that this is only called if the action was actually attempted, meaning
        BOTH the action exists AND is permitted.
        """
        pass

    @abstractmethod
    def _request_permission(self, proposed_message: MessageSchema) -> bool:
        """
        Implement this method to receive a proposed action message and present it to
        the agent for review. Return true or false to indicate whether access
        should be permitted.
        """
        raise NotImplementedError()
