from everything.channels.channel import ACCESS_PERMITTED, Channel
from everything.things.operator import Operator
import pytest
import time
import unittest
from tests.conftest import space_context


# send message -> receive reply
@pytest.mark.focus
def test_send_basic_message():
  webster = Operator("Webster")
  webchannel = Channel(webster)
  chatty = Operator("Chatty")
  chattychannel = Channel(chatty)

  # Set up Chatty's reply by implementing a mock _say method
  def chatty_say(content):
    print(f"Chatty received: {content}")
    return 'Hello, Webster!'
  chattychannel._action__say = chatty_say
  chattychannel._action__say.access_policy = ACCESS_PERMITTED


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
    assert webster_received == 'Hello, Webster!'


# send unknown action -> error
def test_send_unknown_action(chat_space):
  raise NotImplementedError()


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
