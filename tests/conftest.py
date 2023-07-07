import subprocess
from tracemalloc import start
import pytest
import time

# Starts and stops a RabbitMQ container for the duration of the test session.


@pytest.fixture(scope="session", autouse=True)
def rabbitmq_container():
    subprocess.run(["docker", "rm", "rabbitmq-test"])
    container = subprocess.Popen([
        "docker", "run", "--name", "rabbitmq-test",
        "-p", "5672:5672",
        "-p", "15672:15672",
        "--user", "rabbitmq:rabbitmq",
        # "-e", "RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS=\"-rabbit log_levels [{debug}]\""
        "rabbitmq:3-management"
    ], start_new_session=True)
    wait_for_rabbitmq()
    yield container
    subprocess.run(["docker", "stop", "rabbitmq-test"])


def wait_for_rabbitmq():
    print("Waiting for RabbitMQ server to start...")
    retries = 10
    for _ in range(retries):
        try:
            result = subprocess.run(["docker", "exec", "rabbitmq-test", "rabbitmq-diagnostics", "ping"],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if result.returncode == 0:
                print("RabbitMQ server is up and running.")
                return
        except subprocess.CalledProcessError:
            pass
        time.sleep(10)
    raise Exception("RabbitMQ server failed to start.")
