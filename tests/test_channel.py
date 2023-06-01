import unittest


# send basic message -> receive on other side
def test_send_basic_message(space):
  pass


# send unknown action -> error
def test_send_unknown_action(space):
  pass


# send unpermitted action -> permission error
def test_send_unpermitted_action(space):
  pass

# send ask permitted action -> permit -> takes action -> return result
def test_send_ask_permitted_action(space):
  pass


# send ask permitted action -> reject -> return permission error
def test_send_ask_rejected_action(space):
  pass


if __name__ == '__main__':
  unittest.main()
