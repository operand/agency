import subprocess
import time
import tracemalloc

tracemalloc.start()

import pytest

from agency.spaces.amqp_space import AMQPSpace
from agency.spaces.native_space import NativeSpace

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
def native_space():
    return NativeSpace()


@pytest.fixture
def amqp_space():
    return AMQPSpace(exchange="agency-test")


@pytest.fixture(params=['native_space', 'amqp_space'])
def either_space(request, native_space, amqp_space):
    """
    Used for tests that should be run for both NativeSpace and AMQPSpace.
    """
    space = None
    if request.param == 'native_space':
        space = native_space
    elif request.param == 'amqp_space':
        space = amqp_space

    try:
        yield space
    finally:
        space.remove_all()
