---
title: Creating Spaces
---

# Creating `Space`s

A `Space` is where agents may communicate and interact with each other. Agents
are instantiated within a space when added.

Spaces define the underlying communication transport used for messaging. Agency
currently implements two `Space` types:

- `LocalSpace` - which connects agents within the same application.
- `AMQPSpace` - which connects agents across a network using an AMQP server.


## Using `LocalSpace`

`LocalSpace` is the more basic of the two. It connects agents within the same
python application using interprocess communication (IPC).

Instantiating a `LocalSpace`, like other spaces, is as simple as:

```py
space = LocalSpace()
space.add(Host, "Host")
...
```

The above example would instantiate the `Host` agent within the `LocalSpace`
instance, allowing any other agents added to the space to communicate with it.


## Using `AMQPSpace`

`AMQPSpace` may be used for building applications that allows agent communication
across multiple hosts in a network.

To run an `AMQPSpace` across multiple hosts, you would separate your agents into
multiple applications. Each application would be configured to use the same AMQP
server.

For example, the following would separate the `Host` agent into its own
application:

```python
if __name__ == '__main__':

    # Create a space
    space = AMQPSpace()

    # Add a host agent to the space
    space.add(Host, "Host")

```

And the following would separate the `ChattyAI` agent into its own application:

```python
if __name__ == '__main__':

    # Create a space
    space = AMQPSpace()

    # Add a simple HF based chat agent to the space
    space.add(ChattyAI, "Chatty",
              model="EleutherAI/gpt-neo-125m")

```

Then you can run both applications at the same time, and the agents will be able
to connect and communicate with each other over AMQP. This approach allows you
to scale your agents beyond a single host.

See the [example
application](https://github.com/operand/agency/tree/main/examples/demo/) for a
full working example.


### Configuring AMQP Connectivity

By default, the `AMQPSpace` class will read the following environment variables
and will otherwise use default settings.

```sh
AMQP_HOST
AMQP_PORT
AMQP_USERNAME
AMQP_PASSWORD
AMQP_VHOST
```

You may also customize the options if you provide your own `AMQPOptions` object
when instantiating an `AMQPSpace`. For example:

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

## Instantiating and Destroying `Space`s

`Space` instances manage a number of resources during their lifetime.

To destroy a `Space`, simply call its `destroy` method. This will clean up all
resources used by the space, along with any agents within the space.

`Space`s also support the context manager syntax for convenience. For example:

```python
with LocalSpace() as space:
    space.add(Host, "Host")
    ...
```

This form will automatically clean up Space related resources upon exit of the
with block.
