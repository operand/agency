from everything.channels.channel import ACCESS_DENIED, ACCESS_PERMITTED, Channel
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


def test_send_and_receive(webster_and_chatty):
  """
  Tests sending a basic "say" message from one channel to another and receiving
  a reply."""
  webchannel, chattychannel = webster_and_chatty

  # We use callable class to dynamically define the _say action for chatty
  class ChattySay():
    def __init__(self, channel) -> None:
      self.channel = channel
      self.access_policy = ACCESS_PERMITTED

    def __call__(self, content):
      print(f"Chatty({self}) received: {self.channel._current_message}")
      # Note that we are also testing the default "return" impl which converts a
      # returned value into an incoming "say" action, by returning a string here.
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

    # Wait for a response for up to 3 seconds
    start_time = time.time()
    while time.time() - start_time < 3 and webchannel.received_messages.__len__() == 0:
      time.sleep(0.1)

    assert webchannel.received_messages == [{
      'from': 'Chatty.ChattyChannel',
      'to': 'Webster.WebsterChannel',
      'thoughts': 'A value was returned for your action',
      'action': 'say',
      'args': {'content': 'Hello, Webster!'}
    }]


def test_send_undefined_action(webster_and_chatty):
  """
  Tests sending an undefined action from one channel to another and receiving
  an appropriate error response."""
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

    # Wait for a response for up to 3 seconds
    start_time = time.time()
    while time.time() - start_time < 3 and webchannel.received_messages.__len__() == 0:
      time.sleep(0.1)

    # Assert one field at a time so we can do a regex on args.content
    assert webchannel.received_messages[0]['from'] == 'Chatty.ChattyChannel'
    assert webchannel.received_messages[0]['to'] == 'Webster.WebsterChannel'
    assert webchannel.received_messages[0]['thoughts'] == 'An error occurred while committing your action'
    assert webchannel.received_messages[0]['action'] == 'say'
    assert webchannel.received_messages[0]['args']['content'].startswith(
      'ERROR: Action "Chatty.ChattyChannel.say" not found')


# send unpermitted action -> permission error
def test_send_unpermitted_action(webster_and_chatty):
  """
  Tests sending an unpermitted action from one channel to another and receiving
  an appropriate error response."""
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

    # Wait for a response for up to 3 seconds
    start_time = time.time()
    while time.time() - start_time < 3 and webchannel.received_messages.__len__() == 0:
      time.sleep(0.1)

    # assert one field at a time so we can do a regex on args.content
    assert webchannel.received_messages[0]['from'] == 'Chatty.ChattyChannel'
    assert webchannel.received_messages[0]['to'] == 'Webster.WebsterChannel'
    assert webchannel.received_messages[0]['thoughts'] == 'An error occurred while committing your action'
    assert webchannel.received_messages[0]['action'] == 'say'
    assert webchannel.received_messages[0]['args']['content'].startswith(
      'ERROR: Action "Chatty.ChattyChannel.say" not permitted')


# send ask permitted action -> permit -> takes action -> return result
def test_send_ask_permitted_action(chat_space):
  raise NotImplementedError()


# send ask permitted action -> reject -> return permission error
def test_send_ask_rejected_action(chat_space):
  raise NotImplementedError()


if __name__ == '__main__':
  unittest.main()
