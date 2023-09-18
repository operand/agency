import os
import subprocess
import time
import tracemalloc

import pytest
from agency.space import Space

from agency.spaces.amqp_space import AMQPOptions, AMQPSpace
from agency.spaces.local_space import LocalSpace

tracemalloc.start()


RABBITMQ_OUT = subprocess.DEVNULL  # DEVNULL for no output, PIPE for output
SKIP_AMQP = os.environ.get("SKIP_AMQP")


@pytest.fixture(scope="session", autouse=True)
def rabbitmq_container():
    """
    Starts and stops a RabbitMQ container for the duration of the test
    session.
    """
    if SKIP_AMQP:
        yield None
        return

    container = subprocess.Popen(
        [
            "docker", "run",
            "--name", "rabbitmq-test",
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
        time.sleep(0.5)
    raise Exception("RabbitMQ server failed to start.")


@pytest.fixture
def local_space() -> LocalSpace:
    with LocalSpace() as space:
        yield space


@pytest.fixture
def amqp_space() -> AMQPSpace:
    with AMQPSpace(exchange_name="agency-test") as space:
        yield space


@pytest.fixture(params=['local_space', 'amqp_space'])
def any_space(request) -> Space:
    """
    Used for testing all space types
    """
    if request.param == 'amqp_space' and SKIP_AMQP:
        pytest.skip(f"SKIP_AMQP={SKIP_AMQP}")

    return request.getfixturevalue(request.param)
