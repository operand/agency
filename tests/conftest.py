from contextlib import contextmanager
from everything.things.space import Space
import threading
import time


def setup_and_teardown_space(operators):
    """
    Creates a Space and waits for it to fully start before yielding it to the
    test. The Space is torn down after the context is complete.
    """
    space = Space("TestSpace", operators)
    thread = threading.Thread(target=space.create, daemon=True)
    thread.start()

    # wait for the space to fully start
    while not space.running.is_set():
        time.sleep(0.1)

    # Tear down logic is handled by a context manager to ensure it runs after the test
    try:
        yield space
    finally:
        space.destroy()
        thread.join()


# Use a context manager instead of a fixture to handle setup/teardown
@contextmanager
def space_context(operators):
    yield from setup_and_teardown_space(operators)
