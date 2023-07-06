# Summary

`agency` defines a common communication and action framework for creating
AI agent integrated applications.

`agency` provides a simple means for connecting systems and defining actions,
callbacks, and access policies that you can use to monitor and ensure safety for
the systems you expose to your agents.


`agency` allows you to create shared application environments called "spaces"
where you can connect any number of AI, traditional systems, or human users, in
a way where all may equally interact with each other as individual "agents" that
you may perform "actions" on.


`agency` handles the details of the underlying messaging system and allows
discovering and invoking actions across all parties, providing callbacks for
observation and control, and automatically handling things such as reporting
exceptions, enforcing access restrictions, and more.


`agency`'s purpose is to provide an interface through which agents can freely
act given the tools, systems, or users in their environment, and to provide the
means for observability and control that is necessary for safety.


An additional benefit of its general design is that `agency` may also simplify
some agent development workflows. See the hypothetical examples above.


## Features

* Low-Level API Flexibility
  * Straightforward method based action definition
  * Supports defining single process applications or networked agent systems
    using AMQP
* Observability and Control
  * before/after action callbacks
  * access policies and permission callbacks for access control
* Performance
  * Multithreaded (although python's GIL is a bottleneck for single process apps)
  * AMQP support for multiprocess and networked systems (avoids GIL)
  * _Python multiprocess support is planned_
* _Multimodal support (image/audio) planned_
* Full demo available at [`examples/demo`](./examples/demo/)


# API Overview

`agency` is an implementation of the [Actor
model](https://en.wikipedia.org/wiki/Actor_model) for building AI agent
integrated systems.

In `agency`, all entities represented as instances of the `Agent` class. This
includes all humans, software, and AI-driven agents that may communicate as part
of your application.

All agents may expose "actions" that other agents can discover and invoke at run
time. An example of a simple agent implemention could be:

```python
class CalculatorAgent(Agent):
  def _action__add(a, b):
    return a + b
```

This defines an agent with a single action: `"add"`. Other agents will be able
to call this method by sending a message to an instance of `CalculatorAgent` and
specifying the `"add"` action. This action could be invoked from another agent
with:

```python
other_agent._send({
  'to': 'CalcAgent',
  'action': 'add',
  'args': {
    'a': 1,
    'b': 2,
  },
  'thoughts': 'Optionally explain here',
})
```

Actions must also specify an access policy, allowing you to control access for
safety. For example:

```python
  @access_policy(ACCESS_PERMITTED) # This allows the action at any time
  def _action__add(a, b):
    ...
```

You can also define before/after and permission callbacks for various purposes:

```python
class CalculatorAgent(Agent):
  ...
  def _before_action(self, original_message: dict):
    # Called before any action is attempted

  def _after_action(self, original_message: dict, return_value: str, error: str):
    # Called after any action is attempted

  def _request_permission(self, proposed_message: dict)
    # Called before any ACCESS_REQUESTED action is attempted, allowing rejection
```

A `Space` is how you connect your agents together. An agent cannot communicate
with others until it is added to a common space. There are two included `Space`
implementations to choose from: `NativeSpace` and `AMQPSpace`.

Here is an example of creating a `NativeSpace` and adding two agents to it.

```python
space = NativeSpace()
space.add(CalculatorAgent("CalcAgent"))
space.add(AIAgent("AIAgent"))
# The agents above can now communicate
```

These are just some the main `agency` features. For more detailed information
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
[examples/demo](./examples/demo/).

After a short boot time you can visit the web app at `http://localhost:8080` and
you should see a simple chat interface.

The following is a screenshot of a conversation that demonstrates multiple
agents intelligently interacting and following orders. There are two OpenAI
based agents: `"FunctionAI"` and `"CompletionAI"`, named for the API's they use,
and `"Chatty"` a simple chat agent who uses a small local transformers based
model for demonstration.

I also demonstrate the results of rejecting an action and directing an agent to
use a different approach. After I explained my rejection of the `read_file`
action (which happened behind the scenes on the terminal), `"FunctionAI"`
appropriately used the `shell_command` action with `wc -l Dockerfile`. The
Dockerfile indeed had 73 lines.

<p align="center">
  <img src="https://i.ibb.co/nbvLJvg/Screenshot-2023-06-14-at-3-59-01-AM.png"
       alt="Screenshot-2023-06-14-at-3-59-01-AM" border="0" width=500>
</p>


# FAQ

## How does `agency` compare to agent libraries like LangChain?

Though you could entirely create a simple agent using only the primitives in
`agency` (see [`examples/demo/agents/`](./examples/demo/agents/)), it is not
intended to be a full-fledged agent toolset.

Projects like LangChain and others are exploring how to create purpose-built
agents that solve diverse problems using tools.

`agency` is focused on the problems surrounding agent integration, and can be
thought of as an application framework for creating agent integrated systems.

So more likely you would use LangChain or other libraries for defining agent
behavior, and rely on `agency` to provide the connective fabric for bringing
custom agent applications together in a way where you can observe, control and
ensure safety.

So, `agency` is a more general framework intended to support agent development
and to ultimately enable agents to freely act and safely integrate with
anything.

## What are some known limitations or issues?

* It's a new project, so keep that in mind in terms of completeness, but see
  [the issues page](https://github.com/operand/agency/issues) for what is
  currently planned, and the Roadmap just below for the high level plan.

* This library makes use of threads for each individual agent. Multithreading
  is limited by [python's
  GIL](https://wiki.python.org/moin/GlobalInterpreterLock), meaning that if you
  run a local model in the same process as other agents, they may have to wait
  for their "turn". This goes for anything else you might define as an "agent".
  Note that I/O does not block, so networked backends or services will execute
  in parallel. For blocking processes, it's recommended to use the `AMQPSpace`
  class and run blocking agents in isolation to avoid blocking other agents.

* This API does NOT assume or enforce predefined roles like "user", "system",
  "assistant", etc. This is an intentional decision and is not likely to change.

  `agency` is intended to allow potentially large numbers of agents, systems,
  and people to come together. A small predefined set of roles gets in the way
  of representing many things generally. This is a core feature of `agency`:
  that all things are treated the same and may be interacted with through common
  means.

  The lack of roles introduces some extra work in integrating with role based
  APIs. See the implementation of
  [`OpenAIFunctionAgent`](./examples/demo/agents/openai_function_agent.py) for
  an example.

* There is not much by way of storage support. That is mostly left up to you and
  I'd suggest looking at the many technologies that focus on that. The `Agent`
  class implements a simple `_message_log` array which you can make use of or
  overwrite to back it with longer term storage. More direct support for storage
  APIs will likely be considered in the future.


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

The demo application is written to showcase both native and AMQP spaces, and it
can also be used for experimentation and development.

The application is configured to read the agency library source when running
allowing changes to be tested manually.


## Test Suite

You can run the test suite with:
```bash
poetry run pytest
```


# Roadmap

- Multiprocess Support
- Multimodal Support


## Planned Work

[Please see the issues page.](https://github.com/operand/agency/issues)

If you have any suggestions or otherwise, feel free to add an issue!
