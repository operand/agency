# Summary

Experiment using MQTT ([RabbitMQ MQTT Plugin](https://www.rabbitmq.com/mqtt.html)) for message delivery.

## Running the RabbitMQ、OpenAIFunctionAgent and webapp

1.  Ensure you have [Docker](https://www.docker.com/)(built-in docker-compose) installed on your system.

2.  Start the RabbitMQ service(enable MQTT and web MQTT plugin).

        docker-compose up -d
        # docker-compose stop
        # docker-compose start
        # docker-compose ls

3.  Install dependencies

        poetry install

4.  set environment variables:

        export OPENAI_API_KEY="sk-"
        export WEB_APP_PORT=8080

5.  Start the application.

        poetry run python main.py

6.  Visit [http://localhost:8080](http://localhost:8080) and try it out!

## Running the MicroPython Agent

Put the files in [micropython](./micropython/) directory into the board(The board needs to support wifi, ESP32 is recommended).

I recommend using [Thonny](https://thonny.org/) to program the board.

### Screenshots and Videos

![](http://storage.codelab.club/agency-mqtt-micropython.png)

- [video: MicroPython Demo](http://storage.codelab.club/agency-mqtt-fan-light.mp4)

## Snap! Agent

[Snap!](https://snap.berkeley.edu/) is a broadly inviting programming language for kids and adults that's also a platform for serious study of computer science.

Snap! is a live programming environment with powerful **liveness**. 

It has a built-in **MQTT** library, which is very suitable for interactively building agents, which is very helpful for early experiments.

![](http://storage.codelab.club/agency-mqtt-snap.png)

- [video: Snap! Demo](http://storage.codelab.club/agency-mqtt-snap.mp4)
