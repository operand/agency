from everything.channels.channel import ACCESS_REQUESTED, ACCESS_DENIED, ACCESS_PERMITTED, Channel
from everything.things.operator import Operator
import pytest
import time
import unittest
from tests.conftest import space_context


class WebsterChannel(Channel):
  def __init__(self):
    super().__init__(Operator("Webster"))
    self.received_messages = []

  def _action__say(self, content):
    print(f"Chatty({self}) received: {self._current_message}")
    self.received_messages.append(self._current_message)
  _action__say.access_policy = ACCESS_PERMITTED


class ChattyChannel(Channel):
  def __init__(self):
    super().__init__(Operator("Chatty"))


@pytest.fixture
def webster_and_chatty():
  webchannel = WebsterChannel()
  chattychannel = ChattyChannel()
  return webchannel, chattychannel


def wait_for_message(channel):
  start_time = time.time()
  while time.time() - start_time < 1 and channel.received_messages.__len__() == 0:
    time.sleep(0.1)


def test_send_and_receive(webster_and_chatty):
  """
  Tests sending a basic "say" message receiving a "return"ed reply."""
  webchannel, chattychannel = webster_and_chatty

  # We use callable class to dynamically define the _say action for chatty
  class ChattySay():
    def __init__(self, channel) -> None:
      self.channel = channel
      self.access_policy = ACCESS_PERMITTED

    def __call__(self, content):
      print(f"Chatty({self}) received: {self.channel._current_message}")
      return 'Hello, Webster!'

  chattychannel._action__say = ChattySay(chattychannel)

  # The context manager handles setup/teardown of the space
  with space_context([webchannel, chattychannel]):
    # Send the first message from Webster
    webchannel._send({
      'action': 'say',
      'from': webchannel.id(),
      'to': chattychannel.id(),
      'thoughts': '',
      'args': {
        'content': 'Hello, Chatty!'
      }
    })

    wait_for_message(webchannel)

    assert webchannel.received_messages == [{
      'from': 'Chatty.ChattyChannel',
      'to': 'Webster.WebsterChannel',
      'thoughts': 'A value was returned for your action',
      'action': 'say',
      'args': {'content': 'Hello, Webster!'}
    }]


def test_send_undefined_action(webster_and_chatty):
  """
  Tests sending an undefined action and receiving an error response."""
  webchannel, chattychannel = webster_and_chatty

  # In this test we skip defining a _say action on chatty in order to test the
  # error response

  # Use the context manager to handle setup/teardown of the space
  with space_context([webchannel, chattychannel]):
    # Send the first message
    print(f"Webster sending...")
    webchannel._send({
      'action': 'say',
      'from': webchannel.id(),
      'to': chattychannel.id(),
      'thoughts': 'I wonder how Chatty is doing.',
      'args': {
        'content': 'Hello, Chatty!'
      }
    })

    wait_for_message(webchannel)

    # We assert the error message content first with a regex then the rest of the message
    assert webchannel.received_messages[0].pop('args')['content'].startswith(
      "ERROR: \"Chatty.ChattyChannel.say\" not found\nTraceback (most recent call last):")
    assert webchannel.received_messages == [{
      'from': 'Chatty.ChattyChannel',
      'to': 'Webster.WebsterChannel',
      'thoughts': 'An error occurred while committing your action',
      'action': 'say',
    }]


def test_send_unpermitted_action(webster_and_chatty):
  """
  Tests sending an unpermitted action and receiving an error response."""
  webchannel, chattychannel = webster_and_chatty

  # We use callable class to dynamically define the _say action for chatty
  class ChattySay():
    def __init__(self, channel) -> None:
      self.channel = channel
      self.access_policy = ACCESS_DENIED

    def __call__(self, content):
      print(f"Chatty({self}) received: {self.channel._current_message}")
      # Note that we are also testing the default "return" impl which converts a
      # returned value into an incoming "say" action, by returning a string here.
      return 'Hello, Webster!'

  chattychannel._action__say = ChattySay(chattychannel)

  # Use the context manager to handle setup/teardown of the space
  with space_context([webchannel, chattychannel]):
    # Send the first message
    print(f"Webster sending...")
    webchannel._send({
      'action': 'say',
      'from': webchannel.id(),
      'to': chattychannel.id(),
      'thoughts': 'I wonder how Chatty is doing.',
      'args': {
        'content': 'Hello, Chatty!'
      }
    })

    wait_for_message(webchannel)

    # We assert the error message content first with a regex then the rest of the message
    assert webchannel.received_messages[0].pop('args')['content'].startswith(
      "ERROR: \"Chatty.ChattyChannel.say\" not permitted\nTraceback (most recent call last):")
    assert webchannel.received_messages == [{
      'from': 'Chatty.ChattyChannel',
      'to': 'Webster.WebsterChannel',
      'thoughts': 'An error occurred while committing your action',
      'action': 'say',
    }]


def test_send_request_permitted_action(webster_and_chatty):
  """
  Tests sending an action, granting permission, and returning response"""
  webchannel, chattychannel = webster_and_chatty

  # We use callable classes to dynamically define _action__say and
  # _request_permission
  class ChattySay():
    def __init__(self, channel) -> None:
      self.channel = channel
      self.access_policy = ACCESS_REQUESTED

    def __call__(self, content):
      print(f"Chatty({self}) received: {self.channel._current_message}")
      return '42'

  chattychannel._action__say = ChattySay(chattychannel)

  class ChattyAsk():
    def __call__(self, proposed_message):
      print(
        f"Chatty({self}) received permission request for: {proposed_message}")
      return True

  chattychannel._request_permission = ChattyAsk()

  # Use the context manager to handle setup/teardown of the space
  with space_context([webchannel, chattychannel]):
    # Send the first message
    print(f"Webster sending...")
    webchannel._send({
      'action': 'say',
      'from': webchannel.id(),
      'to': chattychannel.id(),
      'thoughts': 'hmmmm',
      'args': {
        'content': 'Chatty, what is the answer to life, the universe, and everything?'
      }
    })

    wait_for_message(webchannel)

    assert webchannel.received_messages == [{
      'from': 'Chatty.ChattyChannel',
      'to': 'Webster.WebsterChannel',
      'thoughts': 'A value was returned for your action',
      'action': 'say',
      'args': {
        'content': '42'
      }
    }]


# send action -> reject -> return permission error
def test_send_request_rejected_action(webster_and_chatty):
  """
  Tests sending an action, rejecting permission, and returning error"""
  webchannel, chattychannel = webster_and_chatty

  # We use callable classes to dynamically define _action__say and
  # _request_permission
  class ChattySay():
    def __init__(self, channel) -> None:
      self.channel = channel
      self.access_policy = ACCESS_REQUESTED

    def __call__(self, content):
      print(f"Chatty({self}) received: {self.channel._current_message}")
      return '42'

  chattychannel._action__say = ChattySay(chattychannel)

  class ChattyAsk():
    def __call__(self, proposed_message):
      print(
        f"Chatty({self}) received permission request for: {proposed_message}")
      return False

  chattychannel._request_permission = ChattyAsk()

  # Use the context manager to handle setup/teardown of the space
  with space_context([webchannel, chattychannel]):
    # Send the first message
    print(f"Webster sending...")
    webchannel._send({
      'action': 'say',
      'from': webchannel.id(),
      'to': chattychannel.id(),
      'thoughts': 'hmmmm',
      'args': {
        'content': 'Chatty, what is the answer to life, the universe, and everything?'
      }
    })

    wait_for_message(webchannel)

    # We assert the error message content first with a regex then the rest of the message
    assert webchannel.received_messages[0].pop('args')['content'].startswith(
      "ERROR: \"Chatty.ChattyChannel.say\" not permitted\nTraceback (most recent call last):")
    assert webchannel.received_messages == [{
      'from': 'Chatty.ChattyChannel',
      'to': 'Webster.WebsterChannel',
      'thoughts': 'An error occurred while committing your action',
      'action': 'say',
    }]


if __name__ == '__main__':
  unittest.main()
