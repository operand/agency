import time
import unittest
from everything.channels.web_channel import WebChannel
import pytest
from tests.conftest import create_mock_channel, space_context


# send message -> receive reply
@pytest.mark.focus
def test_send_basic_message():
  mock_webchannel = create_mock_channel(WebChannel, "Webster")
  mock_chattychannel = create_mock_channel(WebChannel, "Chatty")

  # Set up Chatty's reply by implementing a mock _say method
  def chatty_say(content):
    print(f"Chatty received: {content}")
    return 'Hello, Webster!'
  mock_chattychannel._action__say = chatty_say

  # Set up Webster's _say to receive the reply
  webster_received = None
  def webster_say(content):
    print(f"Webster received: {content}")
    nonlocal webster_received
    webster_received = content
  mock_webchannel._action__say = webster_say

  # Use the context manager to handle setup/teardown of the space
  with space_context([mock_webchannel, mock_chattychannel]) as chat_space:
    # Send the first message
    print(f"Webster sending...")
    mock_webchannel._send({
      'action': 'say',
      'from': mock_webchannel.id(),
      'to': mock_chattychannel.id(),
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
