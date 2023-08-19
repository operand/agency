import subprocess
import time
import tracemalloc
from agency.agent import RouterProtocol

tracemalloc.start()

from agency.spaces.amqp_space import _AMQPRouter, AMQPOptions, AMQPSpace
from agency.spaces.multiprocess_space import MultiprocessSpace
from agency.spaces.thread_space import ThreadSpace

import pytest

RABBITMQ_OUT = subprocess.DEVNULL  # use subprocess.PIPE for output

@pytest.fixture(scope="session", autouse=True)
def rabbitmq_container():
    """
    Starts and stops a RabbitMQ container for the duration of the test
    session.
    """

    container = subprocess.Popen(
        [
            "docker", "run", "--name", "rabbitmq-test",
            "-p", "5672:5672",
            "-p", "15672:15672",
            "--user", "rabbitmq:rabbitmq",
            "rabbitmq:3-management",
        ],
        start_new_session=True,
        stdout=RABBITMQ_OUT,
        stderr=RABBITMQ_OUT
    )
    try:
        wait_for_rabbitmq()
        yield container
    finally:
        subprocess.run(["docker", "stop", "rabbitmq-test"])
        subprocess.run(["docker", "rm", "rabbitmq-test"])
        container.wait()


def wait_for_rabbitmq():
    print("Waiting for RabbitMQ server to start...")
    retries = 20
    for _ in range(retries):
        try:
            result = subprocess.run([
                "docker", "exec", "rabbitmq-test",
                "rabbitmq-diagnostics", "check_running"
            ],
                stdout=RABBITMQ_OUT,
                stderr=RABBITMQ_OUT,
                check=True,
            )
            if result.returncode == 0:
                print("RabbitMQ server is up and running.")
                return
        except subprocess.CalledProcessError:
            pass
        time.sleep(1)
    raise Exception("RabbitMQ server failed to start.")


@pytest.fixture
def thread_space():
    class TestableThreadSpace(ThreadSpace):
        def send_test_message(self, message: dict):
            """Send a message into the space for testing purposes"""
            self._ThreadSpace__router.route(message)

    try:
        space = TestableThreadSpace()
        yield space
    finally:
        space.remove_all()


@pytest.fixture
def multiprocess_space():
    class TestableMultiprocessSpace(MultiprocessSpace):
        def send_test_message(self, message: dict):
            """Send a message into the space for testing purposes"""
            self._MultiprocessSpace__router.route(message)

    try:
        space = TestableMultiprocessSpace()
        yield space
    finally:
        space.remove_all()


@pytest.fixture
def amqp_space():
    class TestableAMQPSpace(AMQPSpace):
        def __init__(self, amqp_options: AMQPOptions = None, exchange_name: str = "agency"):
            super().__init__(amqp_options, exchange_name)
            self.__test_router: RouterProtocol = _AMQPRouter(
                self._AMQPSpace__kombu_connection_options, exchange_name)

        def send_test_message(self, message: dict):
            """Send a message into the space for testing purposes"""
            self.__test_router.route(message)

    try:
        space = TestableAMQPSpace(exchange_name="agency-test")
        yield space
    finally:
        space.remove_all()


@pytest.fixture(params=['thread_space', 'multiprocess_space', 'amqp_space'])
def any_space(request, thread_space, multiprocess_space, amqp_space):
    """
    Used for testing all space types
    """
    if request.param == 'thread_space':
        return thread_space
    elif request.param == 'multiprocess_space':
        return multiprocess_space
    elif request.param == 'amqp_space':
        return amqp_space
