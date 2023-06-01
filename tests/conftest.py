import threading
from unittest.mock import AsyncMock, create_autospec
from everything.channels.channel import Channel
from everything.channels.web_channel import WebChannel
from everything.things.operator import Operator
from everything.things.space import Space
import pytest


@pytest.fixture
def empty_space():
  space = Space()
  thread = threading.Thread(target=space.create, daemon=True)
  thread.start()

  yield space

  space.destroy()
  thread.join()
  # Assert that the loop (should have) stopped
  assert space.should_stop.is_set()


@pytest.fixture
def chat_space():
  mock_webchannel = create_autospec(WebChannel)
  mock_webchannel._process.return_value = AsyncMock()
  mock_chattychannel = create_autospec(WebChannel)
  mock_chattychannel._process.return_value = AsyncMock()
  space = Space([
    mock_webchannel(Operator("Webster")),
    mock_chattychannel(Operator("Chatty")),
  ])
  thread = threading.Thread(target=space.create, daemon=True)
  thread.start()

  yield space

  space.destroy()
  thread.join()
  # Assert that the loop (should have) stopped
  assert space.should_stop.is_set()