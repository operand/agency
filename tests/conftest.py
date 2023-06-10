from contextlib import contextmanager
from everything.things.space import Space
import threading
import time


def setup_and_teardown_space():
    """
    Creates a Space and waits for it to fully start before yielding it to the
    test. The Space is torn down after the context is complete.
    """
    space = Space("TestSpace")
    thread = threading.Thread(target=space.run, daemon=True)
    thread.start()

    # wait for the space to fully start
    while not space.running.is_set():
        time.sleep(0.1)

    # Tear down logic is handled by a context manager to ensure it runs after the test
    try:
        yield space
    finally:
        space.stop()
        thread.join()


# Use a context manager to handle setup/teardown
@contextmanager
def space_context():
    yield from setup_and_teardown_space()
