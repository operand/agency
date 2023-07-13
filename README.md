# Summary

`agency` is a python library that provides a communication and action framework
for creating AI agent-integrated applications.

The library provides a low-level means for connecting agents, systems, and human
users by defining actions, callbacks, and access policies that you can use to
connect, monitor, control, and interact with your agents.

`agency` handles the details of the common messaging system and allows
discovering and invoking actions across parties, automatically handling things
such as reporting exceptions, enforcing access restrictions, and more.


## Features

### Low-Level API Flexibility
  * Straightforward class/method based agent and action definition
  * Supports defining single process applications or networked agent systems
  using AMQP

### Observability and Control
  * Before/after action and lifecycle callbacks for observability or other needs
  * Access policies and permission callbacks for access control

### Performance
  * Multithreaded (though python's GIL is a bottleneck for single process apps)
  * AMQP support for multiprocess and networked systems (avoids GIL)
  * [_Python multiprocess support is planned for better scalability on
    single-host systems_](https://github.com/operand/agency/issues/33)

### Multimodal (image/audio) support
  * [_Not yet developed, but is planned_](https://github.com/operand/agency/issues/27)

### Full demo available at [`examples/demo`](./examples/demo/)
  * Two OpenAI agent examples
  * HuggingFace transformers agent example
  * Simple Flask/React web interface included
  * Operating system access for agents
  * Docker configuration for reference and development


# API Overview

`agency` is an implementation of the [Actor
model](https://en.wikipedia.org/wiki/Actor_model) for building AI agent
integrated systems.

In `agency`, all entities are represented as instances of the `Agent` class.
This includes all humans, software, and AI-driven agents that may communicate as
part of your application.

All agents may expose "actions" that other agents can discover and invoke at run
time. An example of a simple agent implemention could be:

```python
class CalculatorAgent(Agent):
  def _action__add(a, b):
    return a + b
```

This defines an agent with a single action: `"add"`. Other agents will be able
to call this method by sending a message to an instance of `CalculatorAgent` and
specifying the `"add"` action.

```python
other_agent._send({
  'to': 'CalcAgent',
  'thoughts': 'Optionally explain here',
  'action': 'add',
  'args': {
    'a': 1,
    'b': 2,
  },
})
```

Actions must also specify an access policy, allowing you to control access for
safety. For example:

```python
  @access_policy(ACCESS_PERMITTED) # This allows the action at any time
  def _action__add(a, b):
    ...
```

You can also define callbacks for various purposes:

```python
class CalculatorAgent(Agent):
  ...
  def _before_action(self, original_message: dict):
    # Called before any action is attempted

  def _after_action(self, original_message: dict, return_value: str, error: str):
    # Called after any action is attempted

  def _after_add(self):
    # Called after the agent is added to the space and may begin communicating

  def _before_remove(self):
    # Called before the agent is removed from the space

  def _request_permission(self, proposed_message: dict) -> bool:
    # Called before an ACCESS_REQUESTED action is attempted for run-time review
```

A `Space` is how you connect your agents together. An agent cannot communicate
with others until it is added to a common `Space`.

There are two included `Space` implementations to choose from:
* `NativeSpace` - which connects agents within the same python process
* `AMQPSpace` - which connects agents across processes and systems using an AMQP
  server like RabbitMQ.

Here is an example of creating a `NativeSpace` and adding two agents to it.

```python
space = NativeSpace()
space.add(CalculatorAgent("CalcAgent"))
space.add(AIAgent("AIAgent"))
# The agents above can now communicate
```

These are just some of the main `agency` features. For more detailed information
please see [the docs directory](./docs/).


# Install

```sh
pip install agency
```
or
```sh
poetry add agency
```


# Running the Demo Application

To run the demo, please follow the directions at
[examples/demo](./examples/demo/). After a short boot time you can visit the
web app at `http://localhost:8080` and you should see a simple chat interface.

The following is a screenshot of the web UI that demonstrates the multiple demo
agents intelligently interacting and following orders.

There are two OpenAI based agents: `"FunctionAI"` and `"CompletionAI"`, named
for the API's they use, and `"Chatty"` a simple chat agent who uses a small
local transformers based model for demonstration.

The screenshot also demonstrates the results of rejecting an action and
directing an agent to use a different approach in real time. After I explained
my rejection of the `read_file` action (which happened behind the scenes on the
terminal), `"FunctionAI"` appropriately used the `shell_command` action with `wc
-l Dockerfile`.

<p align="center">
  <img src="https://i.ibb.co/nbvLJvg/Screenshot-2023-06-14-at-3-59-01-AM.png"
       alt="Screenshot-2023-06-14-at-3-59-01-AM" border="0" width=500>
</p>


# FAQ

## How does `agency` compare to agent libraries like LangChain?

Though you could entirely create a simple agent using only the primitives in
`agency` (see [`examples/demo/agents/`](./examples/demo/agents/)), it is not
intended to be a full-fledged agent toolset like other libraries or tools.

`agency` is an application framework focused on the problems surrounding
agent/tool/human integration, such as communication, observability, and access
control. The library strives to provide a minimal yet practical foundation for
defining and integrating agent-based systems, allowing developers the freedom
to experiment with different agent solutions as they desire.


## What are some known limitations or issues?

* It's a new project, so keep that in mind in terms of
  completeness, but see [the issues
  page](https://github.com/operand/agency/issues) for what is currently planned,
  and the [Roadmap](#roadmap) below for the high level plan.

* This library makes use of threads for each individual agent. Multithreading
  is limited by [python's
  GIL](https://wiki.python.org/moin/GlobalInterpreterLock), meaning that if you
  run a local model or other heavy computation in the same process as other
  agents, they may have to wait for their "turn". Note that I/O does not block,
  so networked backends or services will execute in parallel.
  
  For blocking processes, it's recommended to use the `AMQPSpace` class and run
  heavy computations in isolation to avoid blocking other agents.

* This API does not assume or enforce predefined roles like "user", "system",
  "assistant", etc. This is an intentional decision and is not likely to change.

  `agency` is intended to allow potentially large numbers of agents, systems,
  and people to come together. A small predefined set of roles gets in the way
  of representing many things generally. This is a core feature of `agency`:
  that all entities are treated the same and may be interacted with through
  common means.

  The lack of roles may require extra translation code when integrating with
  role based APIs. See the implementation of
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
allowing changes to be tested manually.


## Test Suite

Ensure you have Docker installed. A small RabbitMQ container will be
automatically created.

You can run the test suite with:

```bash
poetry run pytest
```



# Roadmap

- **Multiprocess Support**:
An additional space type utilizing python multiprocessing, as another
parallelism option for single-host systems.

- **Multimodal Support**:
Image/audio transfer for use with multimodal models or other multimedia
services.

- **Storage Support**
Durable session support will be included. Other forms of storage will be
considered as well though it's not clear yet what that will look like.

- **More Examples**:
More examples of integrations with popular AI libraries and tools such as
Langchain and oobabooga.


## Planned Work

[Please see the issues page.](https://github.com/operand/agency/issues)

If you have any suggestions or otherwise, feel free to add an issue!
