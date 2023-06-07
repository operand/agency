from abc import abstractmethod
import inspect
import re
import traceback
from everything.things.operator import Operator
from everything.things.schema import ActionSchema, MessageSchema
import everything.things.util as util
import queue


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


class Channel():
  """
  An action based interface to an Operator
  """

  def __init__(self, operator: Operator, **kwargs) -> None:
    self.operator = operator
    self.kwargs = kwargs
    self.__message_queue = queue.Queue()
    self.__cached__get_action_help = None

    # A basic approach to storing messages
    self._message_log = []

  def id(self) -> str:
    return f"{self.operator.id()}.{self.__class__.__name__}"

  def _send(self, action: ActionSchema):
    """
    Validates and sends (out) an action
    """
    # define message, validate, and route it
    message = MessageSchema(**{
      "from": self.id(),
      **action,
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

  async def _process(self) -> str:
    """
    Called periodically to process queued messages/actions
    """
    while not self.__message_queue.empty():
      message = self.__message_queue.get()
      util.debug(f"[{self.id()}] processing:", message)
      try:
        try:
          self.__commit_action(message)
        except PermissionError as e:
          # prompt for permission and requeue or raise new permission error
          if self._request_permission(message):
            self.__message_queue.put(message)
          else:
            raise PermissionError(
              f"Access denied by '{self.operator.id()}' for: {message}")
      except Exception as e:
        # Here we handle errors that occur while handling an action including
        # access denial, by reporting the error back to the sender. If an error
        # occurs here, indicating that basic _send() functionality is broken,
        # the application will exit.
        util.debug(f"*[{self.id()}] error processing: {e}", traceback.format_exc())
        self._send({
          "to": message['from'],
          "thoughts": "An error occurred",
          "action": "error",
          "args": {
            "original_message": message,
            "error": f"{e}",
          },
        })

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
      raise AttributeError(
        f"\"{message['action']}\" not found")

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
      # Always call __action__after__
      self._after_action___(message, return_value, error)

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
        "operator.channel": "<operator_name>.<channel_name>",
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
          'to': self.id(),  # the channel that the action is on
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
    Returns true if the action exists on this channel
    """
    return hasattr(self, f"{ACTION_METHOD_PREFIX}{action_name}")

  # Override any of the following methods as needed to implement your channel

  @access_policy(ACCESS_PERMITTED)
  def _action__help(self, action_name: str = None) -> list:
    """
    Returns list of actions on this channel matching action_name, or all if none
    is passed.
    """
    return self._get_help(action_name)

  @access_policy(ACCESS_PERMITTED)
  def _action__return(self, original_message: MessageSchema, return_value: str):
    """
    Overwrite this action to handle returned data from a prior action. By
    default this action simply replaces it with an incoming "say".
    """
    self._receive({
      "from": original_message['to'],
      "to": self.id(),
      "thoughts": "A value was returned for your action",
      "action": "say",
      "args": {
        "content": return_value.__str__(),
      },
    })

  @access_policy(ACCESS_PERMITTED)
  def _action__error(self, original_message: MessageSchema, error: str):
    """
    Overwrite this action to handle errors from an action. By default this
    action simply converts it to an incoming "say".
    """
    # TODO: handle errors during errors to stop infinite loops
    self._receive({
      "from": original_message['to'],
      "to": self.id(),
      "thoughts": "An error occurred",
      "action": "say",
      "args": {
        "content": f"ERROR: {error}",
      },
    })

  def _after_action___(self, original_message: MessageSchema, return_value: str, error: str):
    """
    Called after every action. Override and use this method for logging or other
    situations where you may want to pass through all actions.

    Note that this is ONLY called if the action was actually attempted, meaning
    BOTH the action exists AND is permitted.
    """
    pass

  @abstractmethod
  def _request_permission(self, proposed_message: MessageSchema) -> bool:
    """
    Implement this method to receive a proposed action message and present it to
    the operator of the channel for review. Return true or false to indicate
    whether access should be permitted.
    """
    raise NotImplementedError()
