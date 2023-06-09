from everything.things.operator import ACCESS_REQUESTED, ACCESS_DENIED, ACCESS_PERMITTED
from everything.things.operator import Operator
from everything.things.space import Space
from tests.conftest import space_context
import time
import unittest


class Webserver(Space):
  def __init__(self):
    # super().__init__(Operator("Webster"))
    self.received_messages = []

  def _action__say(self, content):
    print(f"Chatty({self}) received: {self._current_message}")
    self.received_messages.append(self._current_message)
  _action__say.access_policy = ACCESS_PERMITTED


class Chatty(Operator):
  def __init__(self):
    super().__init__(id="Chatty")


def wait_for_message(operator):
  start_time = time.time()
  while time.time() - start_time < 1 and operator.received_messages.__len__() == 0:
    time.sleep(0.1)


def test_send_and_receive():
  """
  Tests sending a basic "say" message receiving a "return"ed reply"""
  webserver = Webserver()
  chatty = Chatty()

  # We use callable class to dynamically define the _say action for chatty
  class ChattySay():
    def __init__(self, operator) -> None:
      self.operator = operator
      self.access_policy = ACCESS_PERMITTED

    def __call__(self, content):
      print(f"Chatty({self}) received: {self.operator._current_message}")
      return 'Hello, Webster!'

  chatty._action__say = ChattySay(chatty)

  # The context manager handles setup/teardown of the space
  with space_context([webserver, chatty]):
    # Send the first message from Webster
    webserver._send({
      'action': 'say',
      'to': chatty.id(),
      'thoughts': '',
      'args': {
        'content': 'Hello, Chatty!'
      }
    })

    wait_for_message(webserver)

    assert webserver.received_messages == [{
      'from': 'Chatty',
      'to': 'Webster.Webserver',
      'thoughts': 'A value was returned for your action',
      'action': 'say',
      'args': {'content': 'Hello, Webster!'}
    }]


def test_send_undefined_action():
  """
  Tests sending an undefined action and receiving an error response."""
  server = Webserver()
  chatty = Chatty()

  # In this test we skip defining a _say action on chatty in order to test the
  # error response

  # Use the context manager to handle setup/teardown of the space
  with space_context([server, chatty]):
    # Send the first message
    print(f"Webster sending...")
    server._send({
      'action': 'say',
      'to': chatty.id(),
      'thoughts': 'I wonder how Chatty is doing.',
      'args': {
        'content': 'Hello, Chatty!'
      }
    })

    wait_for_message(server)

    # We assert the error message content first with a regex then the rest of the message
    assert server.received_messages == [{
      'from': 'Chatty.Chatty',
      'to': 'Webster.Webserver',
      'thoughts': 'An error occurred',
      'action': 'say',
      'args': {'content': 'ERROR: \"say\" not found'}
    }]


def test_send_unpermitted_action():
  """
  Tests sending an unpermitted action and receiving an error response."""
  webserver = Webserver()
  chatty = Chatty()

  # We use callable class to dynamically define the _say action for chatty
  class ChattySay():
    def __init__(self, operator) -> None:
      self.operator = operator
      self.access_policy = ACCESS_DENIED

    def __call__(self, content):
      print(f"Chatty({self}) received: {self.operator._current_message}")
      # Note that we are also testing the default "return" impl which converts a
      # returned value into an incoming "say" action, by returning a string here.
      return 'Hello, Webster!'

  chatty._action__say = ChattySay(chatty)

  # Use the context manager to handle setup/teardown of the space
  with space_context([webserver, chatty]):
    # Send the first message
    print(f"Webster sending...")
    webserver._send({
      'action': 'say',
      'to': chatty.id(),
      'thoughts': 'I wonder how Chatty is doing.',
      'args': {
        'content': 'Hello, Chatty!'
      }
    })

    wait_for_message(webserver)

    # We assert the error message content first with a regex then the rest of the message
    assert webserver.received_messages == [{
      'from': 'Chatty',
      'to': 'Webster.Webserver',
      'thoughts': 'An error occurred',
      'action': 'say',
      'args': {'content': 'ERROR: \"Chatty.say\" not permitted'}
    }]


def test_send_request_permitted_action():
  """
  Tests sending an action, granting permission, and returning response"""
  webserver = Webserver()
  chatty = Chatty()

  # We use callable classes to dynamically define _action__say and
  # _request_permission
  class ChattySay():
    def __init__(self, operator) -> None:
      self.operator = operator
      self.access_policy = ACCESS_REQUESTED

    def __call__(self, content):
      print(f"Chatty({self}) received: {self.operator._current_message}")
      return '42'

  chatty._action__say = ChattySay(chatty)

  class ChattyAsk():
    def __call__(self, proposed_message):
      print(
        f"Chatty({self}) received permission request for: {proposed_message}")
      return True

  chatty._request_permission = ChattyAsk()

  # Use the context manager to handle setup/teardown of the space
  with space_context([webserver, chatty]):
    # Send the first message
    print(f"Webster sending...")
    webserver._send({
      'action': 'say',
      'to': chatty.id(),
      'thoughts': 'hmmmm',
      'args': {
        'content': 'Chatty, what is the answer to life, the universe, and everything?'
      }
    })

    wait_for_message(webserver)

    assert webserver.received_messages == [{
      'from': 'Chatty',
      'to': 'Webster.Webserver',
      'thoughts': 'A value was returned for your action',
      'action': 'say',
      'args': {
        'content': '42'
      }
    }]


# send action -> reject -> return permission error
def test_send_request_rejected_action():
  """
  Tests sending an action, rejecting permission, and returning error"""
  webserver = Webserver()
  chatty = Chatty()

  # We use callable classes to dynamically define _action__say and
  # _request_permission
  class ChattySay():
    def __init__(self, operator) -> None:
      self.operator = operator
      self.access_policy = ACCESS_REQUESTED

    def __call__(self, content):
      print(f"Chatty({self}) received: {self.operator._current_message}")
      return '42'

  chatty._action__say = ChattySay(chatty)

  class ChattyAsk():
    def __call__(self, proposed_message):
      print(
        f"Chatty({self}) received permission request for: {proposed_message}")
      return False

  chatty._request_permission = ChattyAsk()

  # Use the context manager to handle setup/teardown of the space
  with space_context([webserver, chatty]):
    # Send the first message
    print(f"Webster sending...")
    webserver._send({
      'action': 'say',
      'to': chatty.id(),
      'thoughts': 'hmmmm',
      'args': {
        'content': 'Chatty, what is the answer to life, the universe, and everything?'
      }
    })

    wait_for_message(webserver)

    # We assert the error message content first with a regex then the rest of the message
    assert webserver.received_messages == [{
      'from': 'Chatty',
      'to': 'Webster.Webserver',
      'thoughts': 'An error occurred',
      'action': 'say',
      'args': {
        'content': 'ERROR: \"Chatty.say\" not permitted'
      }
    }]


if __name__ == '__main__':
  unittest.main()
