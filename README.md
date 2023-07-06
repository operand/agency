# Summary

`agency` defines a common communication and action framework for applications
that integrate AI agents with computing systems or human users.

`agency` allows you to create shared application environments called "spaces"
where you can connect any number of AI, traditional systems, or human users, in
a way where all may equally interact with each other as individual "agents" that
you may perform "actions" on.

`agency` handles the details of the underlying messaging system and allows
discovering and invoking actions across all parties, providing callbacks for
observation and control, and automatically handling things such as reporting
exceptions, enforcing access restrictions, and more.

`agency`'s purpose is to provide an interface through which agents can freely
act given the tools, systems, or users at their disposal, and to provide the
means for observability and control that is necessary for safety.


## Features

* API Flexibility
  * Straightforward method based action definition
  * Supports defining single process applications or networked agent systems
    using AMQP
* Observability and Control
  * before/after action callbacks
  * permission callbacks for access control
* Performance
  * Multithreaded (though python's GIL is a bottleneck for single process apps)
  * AMQP support for multiprocess and networked systems (avoids GIL)
  * _Direct multiprocess support is planned_
* Multimodality
  * _Support for multimedia (image/audio) is planned_
* Full demo available at [`examples/demo`](./examples/demo/)


# API Overview

`agency` is an implementation of the [Actor
model](https://en.wikipedia.org/wiki/Actor_model) intended for integrating AI
agents with traditional computing systems and human users.

In `agency`, all entities are called "agents" and represented as instances of
the `Agent` class. This includes all humans, software, and AI-driven agents that
may communicate as part of your application.

All agents may expose "actions" that other agents can discover and invoke at run
time. An example of an agent implemention could be:

```python
class CalculatorAgent(Agent):
  def _action__add(a, b):
    return a + b
```

This defines an agent with a single action: `"add"`. Other agents will be able
to call this method, by sending a message to an instance of `CalculatorAgent`
and specifying the `"add"` action. This action could invoked from another
agent with:

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
  @access_policy(ACCESS_PERMITTED)
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

  def _request_permision(self, proposed_message: dict)
    # Called before any ACCESS_REQUESTED action is attempted, allowing rejection
```

A `Space` is used to connect agents together. An agent cannot communicate with
others until it is added to a common space. There are two included `Space`
classes to choose from: `NativeSpace` and `AMQPSpace`. Here is an example of
creating a `NativeSpace` and adding two agents to it.

```python
space = NativeSpace()
space.add(CalculatorAgent("CalcAgent"))
space.add(AIAgent("AIAgent"))
```


_For a much more detailed walkthrough please see [the docs](./docs/)._


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

The following is a screenshot of a conversation that showcases all the agents
intelligently interacting and following orders.

Note that my messages are broadcasted in the below conversation, which explains
why all three respond to each message. There is an obvious difference in
quality, of course.

I also demonstrate the results of rejecting an action and directing an agent to
use a different approach.

After I explained my rejection of the `read_file` action (which happened behind
the scenes on the terminal), "FunctionAI" appropriately used the `shell_command`
action with `wc -l Dockerfile`. The Dockerfile indeed had 73 lines.

CompletionAI used that command on the first try. Anecdotally as of this writing,
`CompletionAI` seems to be more accurate, even though it is using the text
completion API vs the function calling feature of the chat API. This may be due
to the implementation or issues arising from the translation into roles
discussed elsewhere.

<p align="center">
  <img src="https://i.ibb.co/nbvLJvg/Screenshot-2023-06-14-at-3-59-01-AM.png"
       alt="Screenshot-2023-06-14-at-3-59-01-AM" border="0" width=500>
</p>


# Hypothetical Examples

The following examples are not implemented, but are presented as additional
ideas for integrations that `agency` could support.

```python
Space([

    # Integrate access to a remote server
    Server("Ubuntu",
        ip="192.168.1.100"),

    # Add a voice assistant interface
    VoiceAssistant("VoiceyAI")

    # Use email to send/receive messages from others
    Email("Dan", address="dan@example.com"),

    # Integrate other ML services, like for images
    DiffusionModel("ImageAI"),

    # Horizontal scaling could be achieved by simply duplicating agents
    # (notice we repeat the last one)
    DiffusionModel("ImageAI"),

    # Existing AI agents may integrate as well
    LangChainAgent("MyLangChainAgent"))

    # Development related tasks like model training may also be accomplished.
    # You would only need to add one new `Agent` that reads a data set and sends
    # it as messages to the `Agent` class used for inference, provided the
    # underlying model is first switched to a training mode. For example:
    DatasetTrainer("DatasetTrainer",
      trainee: "ChattyAIInTraining"
    )
    ChattyAI("ChattyAIInTraining",
      training_mode: True,
      ...
    )

    # Network and share your LMs and Agents with others
    RemoteAgent("AgentHelperDude",
      url: "https://agent.helper.dude:2023",
      ...
    )

    # You get the idea...
    AnySystemOrPersonOrFunctionAtAllThatYouWantToShareChannel(
      "Guest",
      ...
    )

]).create()
```


# FAQ

## How does `agency` compare to agent libraries like LangChain?

Though you could entirely create a simple agent using only the primitives in
`agency` (see [`examples/demo/agents/`](./examples/demo/agents/)), it is not intended to be a
full-fledged agent toolset. It can be thought of as an "agent integration
framework".

Projects like LangChain and others are exploring how to create purpose-built
agents that solve diverse problems using tools.

`agency` is concerned with creating a safe and dynamic _environment_ for these
types of agents to work, where they can freely discover and communicate with the
tools, each other, and any humans available in their environment.

`agency` provides a simple means for defining actions, callbacks, and access
policies that you can use to monitor and ensure safety for the systems you
expose to your agents.

A central part of the design is that humans and other systems can easily
integrate as well, using a simple common format for messages. You can even use
`agency` to set up a basic chat room to use with friends or other systems and
not use AI-driven agents at all!

An additional benefit of its general design is that `agency` may also simplify
some agent development workflows. See the hypothetical examples above.

So, `agency` is a more general framework intended to support agent development
and to ultimately enable agents to safely integrate with anything, in any way
imaginable.

## What are some known limitations or issues?

* It's a new project, so keep that in mind in terms of completeness, but see
  [the issues page](https://github.com/operand/agency/issues) for what is
  currently planned. Core functionality is pretty well tested at the moment.

* This library makes use of threads for each individual agent. Multithreading
  is limited by python's GIL, meaning if you run a CPU bound model other agents
  will have to wait for their "turn". This goes for anything else you might
  define as an "agent", if it is CPU heavy it will block other agents. Note that
  I/O does not block, so networked backends or services will execute in
  parallel.

  Other multiprocessing approaches to avoid the GIL are
  [in development](https://github.com/operand/agency/issues/25).

* This API does NOT assume or enforce predefined roles like "user", "system",
  "assistant", etc. This is an intentional decision and is not likely to change.

  `agency` is intended to allow potentially large numbers of agents, systems,
  and people to come together. A small predefined set of roles gets in the way
  of representing many things uniquely and independently. This is a core feature
  of `agency`: that all things are treated the same and may be interacted with
  through common means.

  The lack of roles introduces some challenges in integrating with role based
  APIs. See the implementation of
  [`OpenAIFunctionAgent`](./agency/agents/openai_function_agent.py) for an
  example.

* There is not much by way of storage support. That is mostly left up to you and
  I'd suggest looking at the many technologies that focus on that. The `Agent`
  class implements a simple `_message_log` array which you can make use of or
  overwrite to back it with longer term storage. More direct support for storage
  APIs may be considered in the future.


# Contributing

Please do!


## Development Installation

```bash
git clone git@github.com:operand/agency.git
cd agency
poetry install
```


## Test Suite

You can run the test suite with:
```bash
poetry run pytest
```

The test suite is currently set up to run on pull requests to the `main` branch.


# Roadmap


## Development Priorities
- **Speed**:
  Performance is always a concern. If it's not performant, it's not practical.
  Currently the limitations of python multi-threading are a bottleneck and a
  priority to address.
- **Access Control and Safety**:
  An effective access control solution for agent-integrated systems is
  fundamental to ensure safety. I believe I've included a sane first step at
  such a pattern, but further development will be a focus of this project.
- **Compatibility and Usability**:
  In general, I believe this is a fair start in defining a set of patterns for
  creating agent systems. I hope to ensure the API is kept small, and compatible
  with a wide variety of use cases.
- **Documentation**:
  I hope to ensure documentation is kept organized, clear, and accurate. This
  readme serves as a start.


## Planned Work

[Please see the issues page.](https://github.com/operand/agency/issues)

If you have any suggestions or otherwise, feel free to add an issue!
