from contextlib import contextmanager
import threading
import time
from everything.things.space import Space


def setup_and_teardown_space(channels):
  space = Space(channels)
  thread = threading.Thread(target=space.create, daemon=True)
  thread.start()

  # wait for the space to fully start
  while not space.created.is_set():
    time.sleep(0.1)

  # Tear down logic is handled by a context manager to ensure it runs after the test
  try:
    yield space
  finally:
    space.destroy()
    thread.join()


# Use a context manager instead of a fixture to handle setup/teardown
@contextmanager
def space_context(channels):
  yield from setup_and_teardown_space(channels)