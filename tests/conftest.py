import threading
from unittest.mock import AsyncMock, create_autospec
from everything.channels.channel import Channel
from everything.things.operator import Operator
from everything.things.space import Space
import pytest


@pytest.fixture
def space():
    mock_channel = create_autospec(Channel)
    mock_channel._process.return_value = AsyncMock()
    space = Space([
        mock_channel(Operator("test")),
    ])
    thread = threading.Thread(target=space.create, daemon=True)
    thread.start()

    yield space

    space.destroy()
    thread.join()
    assert not space.running  # Assert that the loop has stopped