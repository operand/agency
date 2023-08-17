# Using AMQPSpace

To use AMQP for multi-process or networked communication, you can simply swap
the `AMQPSpace` class for the `NativeSpace` class.

Then to take advantage of parallelism, you would also separate your agents into
multiple processes configured to use the same AMQP server.

For example, the following would separate the `Host` agent into its own
application:

```python
if __name__ == '__main__':

    # Create a space
    space = AMQPSpace()

    # Add a host agent to the space
    space.add(Host("Host"))

    # keep alive
    while True:
        time.sleep(1)
```

And the following would separate the `ChattyAI` agent into its own application:

```python
if __name__ == '__main__':

    # Create a space
    space = AMQPSpace()

    # Add a simple HF based chat agent to the space
    space.add(
        ChattyAI("Chatty",
                 model="EleutherAI/gpt-neo-125m"))

    # keep alive
    while True:
        time.sleep(1)
```

Make sure to reuse the same AMQP server and configuration for both applications.

Then you can run both applications at the same time, and the agents will be able
to connect and communicate with each other over AMQP. This approach allows you
to scale your agents across multiple processes or hosts, and avoids the
multithreading limitations of python's GIL.

See the [example application](https://github.com/operand/agency/tree/main/examples/demo/) for a full working example.


## Configuring AMQP Connectivity

By default, the `AMQPSpace` class will read the following environment variables
and will otherwise use default settings.

```sh
AMQP_HOST
AMQP_PORT
AMQP_USERNAME
AMQP_PASSWORD
AMQP_VHOST
```

You may also customize the full list of options if you provide your own
`AMQPOptions` object when instantiating an `AMQPSpace`. For example:

```python
space = AMQPSpace(
    amqp_options=AMQPOptions(
        hostname="localhost",
        port=5672,
        username="guest",
        password="guest",
        virtual_host="/",
        use_ssl=True,
        heartbeat=60))
```
