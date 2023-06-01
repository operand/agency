import time
import unittest
import pytest


# send message -> receive reply
@pytest.mark.focus
def test_send_basic_message(chat_space):
  # Here we set up Chatty's reply to a basic message by implementing a mock _say
  # method on the channel
  chatty = chat_space.channels[1]
  def chatty_say(content):
    return 'Hello, Webster!'
  chatty._action__say = chatty_say

  # Here we set up Webster's message to Chatty and an
  webster = chat_space.channels[0]
  websters_received = None
  def webster_say(content):
    nonlocal websters_received
    websters_received = content
  webster._action__say = webster_say

  # and send the message to Chatty
  webster._send({
    'action': 'say',
    'from': webster.id(),
    'to': chatty.id(),
    'args': {
      'content': 'Hello, Chatty!'
    }
  })

  time.sleep(1) # not crazy about this

  assert websters_received == 'Hello, Webster!'


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
