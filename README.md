# Summary

Agency is a python library that provides an [Actor
model](https://en.wikipedia.org/wiki/Actor_model) framework for creating
agent-integrated systems.

The library provides an easy to use API that enables you to connect agents with
traditional software systems in a flexible and scalable way, allowing you to
develop any architecture you need.

Agency's goal is to enable developers to create custom agent-based applications
by providing a minimal foundation to both experiment and build upon. So if
you're looking to build a custom agent system of your own, Agency might be for
you.

## Features

### Easy to use API
* Straightforward class/method based agent and action definition
* [Up to date documentation](https://createwith.agency) and [examples](./examples/demo/) for reference

### Performance and Scalability
* Supports multiprocessing and multithreading for concurrency
* AMQP support for networked agent systems

### Observability and Control
* Action and lifecycle callbacks
* Access policies and permission callbacks
* Detailed logging

### Demo application available at [`examples/demo`](./examples/demo/)
* Multiple agent examples for experimentation
  * Two OpenAI agent examples
  * HuggingFace transformers agent example
  * Operating system access
* Includes Gradio UI
* Docker configuration for reference and development


# API Overview

In Agency, all entities are represented as instances of the `Agent` class. This
includes all AI-driven agents, software interfaces, or human users that may
communicate as part of your application.

All agents may expose "actions" that other agents can discover and invoke at run
time. An example of a simple agent could be:

```python
class CalculatorAgent(Agent):
    @action
    def add(a, b):
        return a + b
```

This defines an agent with a single action: `add`. Other agents will be able
to call this method by sending a message to an instance of `CalculatorAgent` and
specifying the `add` action. For example:

```python
other_agent.send({
    'to': 'CalcAgent',
    'action': {
        'name': 'add',
        'args': {
            'a': 1,
            'b': 2,
        }
    },
})
```

Actions may specify an access policy, allowing you to control access for safety.

```python
@action(access_policy=ACCESS_PERMITTED) # This allows the action at any time
def add(a, b):
    ...

@action(access_policy=ACCESS_REQUESTED) # This requires review before the action
def add(a, b):
    ...
```

Agents may also define callbacks for various purposes:

```python
class CalculatorAgent(Agent):
    ...
    def before_action(self, message: dict):
        """Called before an action is attempted"""

    def after_action(self, message: dict, return_value: str, error: str):
        """Called after an action is attempted"""

    def after_add(self):
        """Called after the agent is added to a space and may begin communicating"""

    def before_remove(self):
        """Called before the agent is removed from the space"""
```

A `Space` is how you connect your agents together. An agent cannot communicate
with others until it is added to a common `Space`.

There are two included `Space` implementations to choose from:
* `LocalSpace` - which connects agents within the same application.
* `AMQPSpace` - which connects agents across a network using an AMQP
  server like RabbitMQ.

Finally, here is a simple example of creating a `LocalSpace` and adding two
agents to it.

```python
space = LocalSpace()
space.add(CalculatorAgent, "CalcAgent")
space.add(MyAgent, "MyAgent")
# The agents above can now communicate
```

These are just the basic features that Agency provides. For more information
please see [the help site](https://createwith.agency).


# Install

```sh
pip install agency
```
or
```sh
poetry add agency
```


# The Demo Application

The demo application is maintained as an experimental development environment
and a showcase for library features. It includes multiple agent examples which
may communicate with eachother and supports a "slash" syntax for invoking
actions as an agent yourself.

To run the demo, please follow the directions at
[examples/demo](./examples/demo/).

The following is a screenshot of the Gradio UI that demonstrates the example
`OpenAIFunctionAgent` following orders and interacting with the `Host` agent.

<p align="center">
  <img src="https://i.ibb.co/h29m5S4/Screenshot-2023-07-26-at-4-53-05-PM.png"
      alt="Screenshot-2023-07-26-at-4-53-05-PM" border="0">
</p>


# FAQ

## How does Agency compare to other agent frameworks?

Though you could entirely create a simple agent using only the primitives in
Agency (see [`examples/demo/agents/`](./examples/demo/agents/)), it is not
intended to be an all-inclusive LLM-oriented toolset like other libraries. For
example, it does not include support for constructing prompts or working with
vector databases. Implementation of agent behavior is left entirely up to you,
and you are free to use other libraries as needed for those purposes.

Agency focuses on the concerns of communication, observation,
and scalability. The library strives to provide the operating
foundations of an agent system without imposing additional structure on you.

The goal is to allow you to experiment and discover the right approaches and
technologies that work for your application. And once you've found an
implementation that works, you can scale it out to your needs.


# Contributing

Please do!

If you're considering a contribution, please check out the [contributing
guide](./CONTRIBUTING.md).

# Planned Work

[See the issues page.](https://github.com/operand/agency/issues)

If you have any suggestions or otherwise, feel free to add an issue or open a
[discussion](https://github.com/operand/agency/discussions).
