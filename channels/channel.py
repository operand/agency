from abc import abstractmethod
from array import array
import inspect
import re
import traceback
from things.schema import MessageSchema
import things.util as util
import queue


# access keys
ACCESS = "access"
ACCESS_ALWAYS = "always"
ACCESS_NEVER = "never"
ACCESS_ASK = "ask"


def access_policy(level):
  def decorator(func):
    func.access_policy = level
    return func
  return decorator


ACTION_METHOD_PREFIX = "_action__"


class Channel():
  """
  An action based interface to an Operator
  """

  def __init__(self, operator, **kwargs) -> None:
    self.operator = operator
    self.kwargs = kwargs
    self.__message_queue = queue.Queue()
    self.__cached__get_action_help = None

    # A basic approach to storing messages
    self._message_log = []

  def id(self) -> str:
    return f"{self.operator.id()}.{self.__class__.__name__}"

  def _send(self, action):
    """
    Validates and sends an action"""
    self._message_log.append(MessageSchema(**{
      **action,
    }).dict(by_alias=True))
    self.space._route(action)

  def _receive(self, action: dict):
    """
    Validates and enqueues an action to be processed by this channel
    """
    message = MessageSchema(**{
      **action,
    }).dict(by_alias=True)

    self._message_log.append(message)
    self.__message_queue.put(message)

  async def _process(self) -> str:
    """
    Called periodically to process queued messages/actions
    """
    while not self.__message_queue.empty():
      message = self.__message_queue.get()
      util.debug(f"*({self}) processing:", message)
      try:
        try:
          self.__commit_action(message)
        except PermissionError as e:
          # prompt operator for permission and requeue message or raise new
          # permission error
          if self._ask_permission(message):
            self.__message_queue.put(message)
          else:
            raise PermissionError(
              f"Access denied by '{self.operator}' for: {message}")
      except Exception as e:
        try:
          # Here we handle errors that occur while handling an action, including
          # access denial, by reporting the error back to the sender.
          self._send({
            "from": self.id(),
            "to": message['from'],
            "thoughts": "An error occurred while processing your action",
            "action": "error",
            "args": {
              "original_message": message,
              "error": f"ERROR: {e}: {traceback.format_exc()}",
            },
          })
        except Exception as e:
          # an error happened while handling an error, just exit. this is bad
          print(f"ERROR: {e}: {traceback.format_exc()}")
          exit(1)

  def __commit_action(self, message: dict) -> dict:
    """
    Invokes action if permitted, otherwise raises PermissionError
    """

    # Check if the action exists
    action_method = None
    try:
      action_method = getattr(
        self, f"{ACTION_METHOD_PREFIX}{message['action']}")
    except AttributeError as e:
      raise AttributeError(f"Action '{message['action']}' not found")

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
        #
        # Note that you are still free to send messages to channels from within
        # an action method, and you can also reply to the sender later on
        # however you choose, even using the "return" action directly.
        if return_value is not None:
          self._send({
            "from": self.id(),
            "to": message['from'],
            "thoughts": "A value was returned for your action",
            "action": "return",
            "args": {
              "original_message": message,
              "return_value": return_value,
            },
          })
      else:
        raise PermissionError(f"Access denied for {message['action']}")
    except Exception as e:
      # If an error occurs, we reraise it to be handled by the process loop
      error = e
      raise e
    finally:
      # Always call __action__after__
      self._after_action___(message, return_value, error)

  def _get_help(self, action_name=None) -> array:
    """
    Returns an array of all action methods on this class that match
    'action_name'. If no action_name is passed, returns all actions.
    [
      {
        "channel": <channel_name>,
        "action": <action_name>,
        "thoughts": <docstring of method>,
        "args": {
          "arg_name": "arg_type",
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
          k: str(v.annotation) if v.annotation != inspect.Parameter.empty else ""
          for k, v in sig.parameters.items()
          if v.default == inspect.Parameter.empty
        }

      def get_docstring(method):
        return re.sub(r'\s+', ' ', method.__doc__).strip() if method.__doc__ else ""

      methods = {
        name: getattr(self, name)
        for name in dir(self)
        if name.startswith(ACTION_METHOD_PREFIX) and callable(getattr(self, name))
      }
      self.__cached__get_action_help = [
        {
          'to': self.id(), # the channel that the action is on
          'action': name.replace(ACTION_METHOD_PREFIX, ''),
          'thoughts': get_docstring(method),
          'args': get_arguments(method),
        }
        for name, method in methods.items()
      ]
    if action_name:
      return self.__cached__get_action_help[action_name]
    else:
      return self.__cached__get_action_help

  def __permitted(self, message) -> bool:
    """
    Checks whether the action represented by the message is allowed
    """
    policy = getattr(
      self, f"{ACTION_METHOD_PREFIX}{message['action']}").access_policy
    if policy == ACCESS_ALWAYS:
      return True
    elif policy == ACCESS_NEVER:
      return False
    elif policy == ACCESS_ASK:
      return self._ask_permission(message)
    else:
      raise Exception(
        f"Invalid access policy for method: {message['action']}, got '{policy}'")

  @access_policy(ACCESS_ALWAYS)
  def _action__help(self, action_name=None) -> array:
    """
    Returns list of actions on this channel matching action_name, or all if none
    is passed.
    """
    return self._get_help(action_name)

  @access_policy(ACCESS_ALWAYS)
  def _action__return(self, original_message, return_value):
    """
    Overwrite this action to handle returned data from a prior action
    By default, this action simply sends a "say" action as a reply
    """
    self._send({
      "from": original_message['to'],
      "to": self.id(),
      "thoughts": "A value was returned for your action",
      "action": "say",
      "args": {
        "content": return_value.__str__(), # cast as string
      },
    })

  # Override the following methods as needed to implement your channel

  @abstractmethod
  def _ask_permission(self, proposed_message: dict) -> bool:
    """
    Implement this method to receive a proposed action message and present it to
    the operator of the channel for review. Return true or false to indicate
    whether access should be permitted.
    """
    raise NotImplementedError

  @abstractmethod
  @access_policy(ACCESS_ALWAYS)
  def _action__error(self, original_message, error_message: dict):
    """
    Define this action to handle errors from an action
    """
    # TODO: handle errors during errors to stop infinite loops
    raise NotImplementedError

  def _after_action___(self, original_message, return_value, error):
    """
    Called after every action. Override and use this method for logging or other
    situations where you may want to pass through all actions.

    Note that this is ONLY called if the action was actually attempted, meaning
    BOTH the action exists _and_ is permitted.
    """
    pass
