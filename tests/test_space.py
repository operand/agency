from tests.conftest import space_context
import time
import unittest


def test_create_destroy():
    """
    Tests basic creation and destruction of a Space without Operators.
    """
    with space_context():
        # Just wait for 1 second here and let the context handle the rest
        time.sleep(1)


if __name__ == '__main__':
    unittest.main()
