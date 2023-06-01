from types import MethodType
from everything.channels.channel import ACCESS_PERMITTED, Channel
from everything.things.operator import Operator
import pytest
import time
import unittest
from tests.conftest import space_context


class WebsterChannel(Channel):
  def __init__(self):
    super().__init__(Operator("Webster"))
    self.webchannel_received_messages = []

  def _action__say(self, content):
    print(f"Chatty({self}) received: {self.__current_message__}")
    self.webchannel_received_messages.append(self.__current_message__)
  _action__say.access_policy = ACCESS_PERMITTED


class ChattyChannel(Channel):
  def __init__(self):
    super().__init__(Operator("Chatty"))


@pytest.fixture
def webster_and_chatty():
  webchannel = WebsterChannel()
  chatchannel = ChattyChannel()

  return webchannel, chatchannel


@pytest.mark.focus
def test_send_and_receive(webster_and_chatty):
  """
  Tests sending a basic "say" message from one channel to another and receiving
  a reply."""
  webchannel, chatchannel = webster_and_chatty

  # Set up Chatty's reply
  def chatty_say(self, content):
    print(f"Chatty({self}) received: {self.__current_message__}")
    # Note that we are also testing the default "return" impl which converts a
    # returned value into an incoming "say" action, by returning a string here.
    return 'Hello, Webster!'
  chatchannel._action__say = MethodType(chatty_say, chatchannel)
  chatchannel._action__say.access_policy = ACCESS_PERMITTED

  # The context manager handles setup/teardown of the space
  with space_context([webchannel, chatchannel]):
    # Send the first message
    webchannel._send({
      'action': 'say',
      'from': webchannel.id(),
      'to': chatchannel.id(),
      'thoughts': 'I wonder how Chatty is doing.',
      'args': {
        'content': 'Hello, Chatty!'
      }
    })

    # Wait for a response for up to 3 seconds
    start_time = time.time()
    while time.time() - start_time < 3 and webchannel.received.__len__() == 0:
      time.sleep(0.1)
    assert webchannel.received == [
      'Hello, Webster!'
    ]


def test_send_undefined_action(webster_and_chatty):
  """
  Tests sending an undefined action from one channel to another and receiving
  an appropriate error response."""
  webchannel, chattychannel, webster_received = webster_and_chatty

  # In this test we skip defining a _say action on chatty in order to test the
  # error response

  # Set up Webster's _say to receive the reply
  webster_received = None

  def webster_say(content):
    print(f"Webster received: {content}")
    nonlocal webster_received
    webster_received = content
  webchannel._action__say = webster_say
  webchannel._action__say.access_policy = ACCESS_PERMITTED

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
    while time.time() - start_time < 3 and webster_received is None:
      time.sleep(0.1)
    assert webster_received == 'ERROR: Action "say" is not defined on channel "Chatty.Channel".'


# send unpermitted action -> permission error
def test_send_unpermitted_action(chat_space):
  raise NotImplementedError()

# send ask permitted action -> permit -> takes action -> return result


def test_send_ask_permitted_action(chat_space):
  raise NotImplementedError()


# send ask permitted action -> reject -> return permission error
def test_send_ask_rejected_action(chat_space):
  raise NotImplementedError()


if __name__ == '__main__':
  unittest.main()
