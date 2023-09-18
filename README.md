# Summary

Agency is a python library that provides an
[Actor model](https://en.wikipedia.org/wiki/Actor_model) framework for creating
agent-integrated systems.

The library provides an easy to use API that enables you to connect intelligent
agents with software systems of all kinds, making it simple to develop the
architecture you need.

Agency's goal is to enable developers to create custom agent-based solutions by
providing a minimal and scalable foundation to both experiment and build upon.
So if you're looking to build a custom agent system of your own, Agency might be
for you.


## Features

### Low-Level API Flexibility
* Straightforward class/method based agent and action definition
* Plug-and-play action discovery at runtime

### Performance and Scalability
* Supports multiprocess and multithreading for concurrency
* AMQP support for networked systems

### Observability and Control
* Action and lifecycle callbacks for observability or other needs
* Access policies and permission callbacks for access control
* Logging with support for `LOGLEVEL` environment variable

### Multi-language Support
* [_Javascript client in progress_](https://github.com/operand/agency/issues/136)

### Multimodal/Multimedia support
* [_Planned_](https://github.com/operand/agency/issues/26)

### Demo application available at [`examples/demo`](./examples/demo/)
* Multiple agent examples for experimentation
  * Two OpenAI agent examples
  * HuggingFace transformers agent example
  * Operating system access
* Includes Gradio UI (_An updated React UI is in progress. See above._)
* Docker configuration for reference and development


# API Overview

In Agency, all entities are represented as instances of the `Agent` class. This
includes all AI-driven agents, traditional software systems, or human users that
may communicate as part of your application.

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

There are three included `Space` implementations to choose from:
* `ThreadSpace` - which distributes and connects agents using
  multithreading, suitable for simple applications and testing.
* `MultiprocessSpace` - which distributes agents using the
  multiprocessing module, for better parallelism.
* `AMQPSpace` - which distributes agents across a network using an AMQP
  server like RabbitMQ.

Finally, here is a simple example of creating a `MultiprocessSpace` and adding two
agents to it.

```python
space = MultiprocessSpace()
space.add(CalculatorAgent, "CalcAgent")
space.add(MyAgent, "MyAgent")
# The agents above can now communicate
```

These are just a few of the features that Agency provides. For more detailed
information please see [the help site](https://createwith.agency).


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

## How does Agency compare to other agent libraries?

Though you could entirely create a simple agent using only the primitives in
Agency (see [`examples/demo/agents/`](./examples/demo/agents/)), it is not
intended to be an all-inclusive toolset like other libraries. For example, it
does not include support for constructing prompts or working with vector
databases, etc. Implementation of agent behavior is left up to you, and you are
free to use other libraries as needed for those purposes.

Agency focuses on the lower level concerns of communication, observation,
scalability, and security. The library strives to provide the basic foundations
of an agent system without imposing additional structure on you.

The goal is to allow you to experiment and discover the right approaches and
technologies that work for you. And once you've found an implementation that
works, you can scale it out to your needs.


## What are some known limitations or issues?

* Despite the 1.x.x version, Agency is still in early development. Like many
  projects in the AI agent space it is somewhat experimental at this time, with
  the goal of finding and providing a minimal yet useful foundation for building
  agent systems.

  Expect changes to the API over time as features are added or changed. The
  library follows semver versioning. Minor version updates may contain breaking
  API changes. Patch versions should not.

* This API does not assume or enforce predefined roles like "user", "system",
  "assistant", etc. This is an intentional decision and is not likely to change.

  Agency is intended to allow potentially large numbers of agents, systems, and
  people to come together. A small predefined set of roles gets in the way of
  representing many things generally. This is a design feature of Agency: that
  all entities are represented similarly and may be interacted with through
  common means.

  The lack of roles may require extra work when integrating with role based
  APIs. See the implementation of
  [`OpenAIFunctionAgent`](./examples/demo/agents/openai_function_agent.py) for
  an example.

* There is currently not much by way of storage support. That is mostly left up
  to you and I'd suggest looking at the many technologies that focus on that.
  The `Agent` class implements a simple `_message_log` array which you can make
  use of or overwrite to back it with longer term storage. More direct support
  for storage APIs will likely be considered in the future.


# Contributing

Please do!

If you're considering a contribution, please check out the [contributing
guide](./CONTRIBUTING.md).

# Planned Work

[See the issues page.](https://github.com/operand/agency/issues)

If you have any suggestions or otherwise, feel free to add an issue or open a
[discussion](https://github.com/operand/agency/discussions).
