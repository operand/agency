import time
import unittest
import pytest


# send message -> receive reply
@pytest.mark.focus
def test_send_basic_message(chat_space):
  # Set up Chatty's reply by implementing a mock _say method
  chatty = chat_space.channels[1]
  def chatty_say(content):
    print(f"Chatty received: {content}")
    return 'Hello, Webster!'
  chatty._action__say = chatty_say

  # Set up Webster's _say to receive the reply
  webster = chat_space.channels[0]
  webster_received = None
  def webster_say(content):
    print(f"Webster received: {content}")
    nonlocal webster_received
    webster_received = content
  webster._action__say = webster_say

  # Send the first message
  print(f"Webster sending...")
  webster._send({
    'action': 'say',
    'from': webster.id(),
    'to': chatty.id(),
    'args': {
      'content': 'Hello, Chatty!'
    }
  })

  time.sleep(3) # really not crazy about this

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
