import subprocess
import pytest
import time

# Starts and stops a RabbitMQ container for the duration of the test session.


@pytest.fixture(scope="session", autouse=True)
def rabbitmq_container():
    container = subprocess.Popen([
        "docker", "run", "--name", "rabbitmq-test",
        "-p", "5672:5672",
        "-p", "15672:15672",
        "--user", "rabbitmq:rabbitmq",
        "rabbitmq:3-management",
    ], start_new_session=True)
    wait_for_rabbitmq()
    yield container
    subprocess.run(["docker", "stop", "rabbitmq-test"])
    subprocess.run(["docker", "rm", "rabbitmq-test"])


def wait_for_rabbitmq():
    print("Waiting for RabbitMQ server to start...")
    retries = 20
    for _ in range(retries):
        try:
            result = subprocess.run([
                    "docker", "exec", "rabbitmq-test",
                    "rabbitmq-diagnostics", "check_running"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            if result.returncode == 0:
                print("RabbitMQ server is up and running.")
                return
        except subprocess.CalledProcessError:
            pass
        time.sleep(1)
    raise Exception("RabbitMQ server failed to start.")
