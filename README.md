# Summary

Agency is a python library that provides a minimal framework for creating
agent-integrated systems.

The library provides an easy to use API that enables you to connect intelligent
agents with software systems and human users, making it simple to integrate,
monitor, and control your agent system.

Agency's design allows you to flexibly experiment and build to your
requirements. Once you've found an architecture that works, you can scale it out
to your needs.


## Features

### Low-Level API Flexibility
* Straightforward class/method based agent and action definition
* Supports defining single process applications or networked agent systems

### Observability and Control
* Action and lifecycle callbacks for observability or other needs
* Access policies and permission callbacks for access control

### Performance and Scalability
* Multithreaded (though python's GIL is a bottleneck for single process apps)
* AMQP support for multiprocess and networked systems (avoids GIL)
* [_Python multiprocess support coming soon_](https://github.com/operand/agency/issues/33)
* [_Decentralized networking support planned_](https://github.com/operand/agency/issues/83)

### Multimodal/Multimedia support
* [_In development_](https://github.com/operand/agency/issues/26)

### Demo application available at [`examples/demo`](./examples/demo/)
* Includes Gradio UI (React UI example also available)
* Multiple agent examples for experimentation
  * Two OpenAI agent examples
  * HuggingFace transformers agent example
  * Operating system access
* Docker configuration for reference and development


# API Overview

Agency is an implementation of the [Actor
model](https://en.wikipedia.org/wiki/Actor_model) for building AI agent
integrated systems.

In Agency, all entities are represented as instances of the `Agent` class. This
includes all human users, software, and AI-driven agents that may communicate as
part of your application.

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
    def before_action(self, original_message: dict):
        """Called before an action is attempted"""

    def after_action(self, original_message: dict, return_value: str, error: str):
        """Called after an action is attempted"""

    def after_add(self):
        """Called after the agent is added to a space and may begin communicating"""

    def before_remove(self):
        """Called before the agent is removed from the space"""
```

A `Space` is how you connect your agents together. An agent cannot communicate
with others until it is added to a common `Space`.

There are two included `Space` implementations to choose from:
* `NativeSpace` - which connects agents within the same python process
* `AMQPSpace` - which connects agents across processes and systems using an AMQP
  server like RabbitMQ.

Finally, here is how to create a `NativeSpace` and add two agents to it.

```python
space = NativeSpace()
space.add(CalculatorAgent("CalcAgent"))
space.add(AIAgent("AIAgent"))
# The agents above can now communicate
```

These are just a few of the features that Agency provides. For more detailed
information please see [the docs directory](./docs/).


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
and a showcase for library features.

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
databases, etc. Implementation of agent behavior is left up to you.

The goal of Agency is to enable others to create custom agent solutions by
providing a minimal, flexible, and scalable foundation that can support a wide
variety of use cases. So if you're looking to build a custom agent system,
Agency might be for you.

## What are some known limitations or issues?

* Agency is still in early development. Like many projects in the AI agent
  space it is somewhat experimental at this time, with the goal of finding and
  providing a minimal yet useful foundation for building agent systems.

  Expect changes to the API over time as features are added or changed. The
  library follows semver versioning starting at 1.x.x. Minor version updates may
  contain breaking API changes. Patch versions should not.

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

## Development Installation

```bash
git clone git@github.com:operand/agency.git
cd agency
poetry install
```

## Developing with the Demo Application

See [the demo directory](./examples/demo/) for instructions on how to run the
demo.

The demo application is written to showcase both native and AMQP spaces and
several agent examples. It can also be used for experimentation and development.

The application is configured to read the agency library source when running,
allowing library changes to be tested manually.

## Test Suite

Ensure you have Docker installed. A small RabbitMQ container will be
automatically created.

You can run the test suite with:

```bash
poetry run pytest
```

## Planned Work

[See the issues page.](https://github.com/operand/agency/issues)

If you have any suggestions or otherwise, please add an issue!
