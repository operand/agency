# `everything`

A fast and minimal foundation for unifying human, AI, and other computing
systems, in python


## What is `everything`?

`everything` is an implementation of the [Actor
model](https://en.wikipedia.org/wiki/Actor_model) that defines a common
communication and action framework for integrating AI agents, humans, and
traditional computing systems.

Conceptually, `everything` establishes a shared environment called a "space"
where any number of humans, artificial, or computing systems may equally address
each other as individual "operators" that you may perform "actions" on.

`everything` handles the details of the common messaging protocol and allows
discovering and invoking actions across all parties, automatically handling
things such as reporting exceptions, enforcing access restrictions, and more.

By defining custom `Operator` subclasses, the API allows integration of entities
as varied as:
- voice assistants
- UI driven applications
- terminal environments
- web applications
- software APIs
- people
- ...
- anything


# Install
> **WARNING:**\
Running `everything` may result in exposing your computer to access by any
connected `Operator` including AI agents. Please understand the risks before
using this software and do not configure it for OS access otherwise.\
\
If you want to enable OS access, to allow for file I/O for example, I HIGHLY
RECOMMEND using a Docker container to prevent direct access to your host,
allowing you to limit the resources and directories it may access.

Please note that `everything` is still under active development and is **not yet
at a stable release**, though it is very close. I expect to have a first stable
API within the next few days. There's not a lot more to do except for shoring up
what's there with tests etc, but that may reveal some API changes.

As I don't consider it fully stable yet, I haven't published this as a pip
package, so for now just:
```
git clone git@github.com:operand/everything.git
pip install ./everything
```


# API Overview

In `everything`, all entities are represented as instances of the base class
`Operator`. This includes all humans, software, or AI agents.

`Operator` can be thought of as a base class similar to "Object" in many
object-oriented languages. All `Operator` subclasses may expose "actions" which
can be invoked by others, by simply defining methods on the class.

A `Space` is itself a subclass of `Operator` and is used to group multiple
`Operator`'s together and facilitate the communication among them. It can be
thought of as both a collection of `Operator`'s and "router" of their
communication. An `Operator` cannot communicate with others until it is first
added to a `Space`.

Since `Space`'s are `Operator`'s themselves, they may be nested, allowing for
namespacing and hierarchical organization of the `Operator`'s in your
application.

So to summarize, the two classes of `Operator` and `Space` together create a
simple API for defining and integrating complex multimodal applications that mix
AI, human, and traditional computing systems.

Let's walk through a thorough example to see how this all works in practice.


## Walkthrough

_Please note that the example classes used in this walkthrough are implemented
for you to explore and try out, but should be considered "proof of concept"
quality only._

Let's start by instantiating our demo space.

```python
demo_space = Space("DemoSpace")
```

Spaces, like all `Operator`'s, must be given an `id`. So the line above
instantiates a single space called `"DemoSpace"` that we can now add
`Operator`'s to.

Now, let's add our first `Operator` to the space, a simple transformers backed
chatbot class named `ChattyLM`. You can browse the source code for this class
[here](./everything/operators/chattylm.py).

```python
demo_space.add(
    ChattyLM(
        "Chatty",
        model="EleutherAI/gpt-neo-125m"))
```

The line above adds a new `ChattyLM` instance to the space, with the `id`
`"Chatty"`. It also passes the `model` argument to the constructor, which is
used to initialize the HuggingFace `transformers` language model.

At this point "Chatty" now has a fully qualified `id` of `"Chatty.DemoSpace"`.
This is because `ChattyLM` is a member of the `DemoSpace` space. As you can see,
spaces establish a namespace for their members which as we'll see later is used
to address them.


It exposes a single action called `"say"` which takes a string as an argument.
This action is how other operators may chat with it.

When `ChattyLM` receives a `"say"` action, it will generate a response using its
prompt format with the language model, and return the result to the sender.


### Adding the WebApp

A single chatting AI wouldn't be useful without someone to chat with it, so now
let's add a human into the space so that they can chat with "Chatty".

To do this, we'll use the `WebApp` class, which is subclass of `Space`.

Why is `WebApp` a subclass of `Space`? This is an arbitrary choice, up to the
developer, but in this example, we use it to show how you can use a `Space` to
group together multiple `Operator`'s and expose them under a single namespace.

Since a web application likely has multiple users, we can use this approach to
group them together under a single space, which itself connects to the root
space.

This allows for namespacing when addressing users of the web application.




## Host
## DemoAgent











# Hypothetical Examples
The following are not implemented, but are examples of other things that could
be implemented, to give you an idea of what else is possible.

```python
Space([

    # Allow access to a remote server
    Server("Ubuntu",
        ip="192.168.1.100"),

    # Add a voice assistant interface to Dan
    VoiceAssistant("Dan")

    # "Dan" could also communicate via email
    Email("Dan"),

    # Perhaps "ChattyAI" also uses multiple channels, like one for images
    ImageIO("ChattyAI"),

    # Horizontal scaling of LM backends could be achieved by duplicating channels
    # (notice we repeat the last one)
    ImageIO("ChattyAI"),

    # Existing AI agent frameworks may integrate as well
    LangChainAgentChannel(
      Operator("MyLangChainAgent"),
      ...
    )

    # Model training is also benefited. You would only need to add one new
    # channel that reads a data set and sends it as messages to the channel
    # class used for inference, provided the underlying LM is first switched to a
    # training mode.
    # For example:
    LMTrainerChannel(
      Operator("LMTrainer"),
      trainee: "ChattyAIInTraining",
      ...
    )
    ChattyLMChannel(
      Operator("ChattyAIInTraining"),
      training_mode: True,
      ...
    )

    # Network with friends and share your LMs and Agents
    RemoteAgentChannel(
      Operator("AgentHelperDude"),
      url: "https://agent.helper.dude:2023",
      ...
    )

    # You get the idea...
    AnySystemOrPersonOrFunctionAtAllThatYouWantToShareChannel(
      Operator("Guest"),
      ...
  )
]).create()
```


## Discovering and Invoking Actions

After loading the above, all the `Operator`'s are in the same `Space`, and can
interact via messages we also call `Action`s.

Each `Operator`, may send a `help` message to discover which other operators,
channels, and actions are available in the space, and what arguments they take.

The `WebChannel` which hosts a simple chat UI, supports a "slash" syntax
summarized here:
```python
/actionname arg1:val1 arg2:val2 arg3:
```
_(Note that an empty argument value is considered true.)_

So a person using the chat UI can discover the available actions in their space
with:
```python
/help
```
And that will return a data structure listing the actions.

---

Agents may be presented with the same help information, either as part of their
prompt or they may act directly by invoking the `/help` action themselves.

Note that agents, like any other "operator" do not need to use the same 
"slash" syntax described above for calling actions. An agent may, for example,
be designed to communicate entirely in JSON.

So just to illustrate, the equivalent of an agent's `/help` command in JSON could be:
```json
{
  "from": "AgentChannel",
  "thoughts": "I need to find what actions are available",
  "action": "help",
  "args": {}
}
```

This approach allows both human users _and_ AI agents or any other system to
dynamically discover and call on each other!


# Going Deeper

What makes `everything` work flexibly is largely thanks to the `Channel` class
and its responsibility in translating from the shared messaging format to any
"view" required for a given operator.

Given that a `Channel` receives a stream of messages, it is free to use previous
messages to provide context, or not.

For example, in this simple conversation using the `WebChannel` and
`ChattyLMChannel` above, "Dan" might see the following conversation on his web page
as:
```
(Dan): Chatty, what's the meaning of life?
(ChattyAI): As an AI language model I ...
(Dan): Woah, that's deep
```

The important thing to note is that the `WebChannel` only needed to format
and forward each _individual_ message to Dan's web UI. A single ajax or
websocket based request would only need to carry something like:
```
{
  sender: "ChattyAI",
  receiver: "Dan",
  action: {
    "name": "say",
    "args":{"content": "As an AI language model I ..." }}
}
```

The UI itself will maintain the previous context for "Dan" (as will his own
memory hopefully), so the prior context for the message does not need to be sent
every time (though it could be, allowing for "hydration" of the web UI if
needed).

These details, regarding _how_ to present through the web application are
entirely hidden in the `WebChannel` class.

---

Now compare the perspective of a language model behind `ChattyLMChannel`. Language
models must be provided with the _full_ context to process on every continuation
request.

So the language model, instead of receiving a single message at a time like the
web UI, must be presented with some previous context formatted appropriately,
and ending with Dan's last message as a prompt for the model continuation.

Following the example above, after Dan's last message, `ChattyLMChannel` will
format and send something like the following to the underlying LM:
```
Below is a conversation between "ChattyAI", an awesome AI that follows
instructions and a human who they serve.

### Human:
Chatty, what's the meaning of life?

### ChattyAI:
As an AI language model I ...

### Human:
Woah, that's deep

### ChattyAI:
```

Here you see that the entire context for the LM to process is provided with
_each_ request, thanks to logic in `ChattyLMChannel`. As the context size limit
is reached, `ChattyLMChannel` could summarize as needed to represent earlier
events.

Also, note how each participant may see an entirely different view of the messages passed.

An AI agent (full example to come), may see conversations with only structured
messages that follow a format, whereas a human in that same conversation may
only need to be presented with the "thoughts" field, as things are happening...

The combined ability of restoring context from prior messages and translating
to/from a common message schema is fundamental to the flexibility that
the `Channel` class provides.

This leaves the developer to only need to define the actions, their policies,
and the minimum translation logic to interface with any new system, ignoring the
details of how messages are carried and translated between systems, as long as
they can translate to/from the
[common message schema](./things/schema.py).


## Access Control

Access Control is essential for safety when exposing systems to independently
working intelligent agents.

I've included a simple but I believe sensible first step towards access control
that requires _you_ as the developer of a channel to indicate what form of
access control you associate with each action on the channel. The access policy
can currently be one of three values:

- `permitted` - which permits any operator in the space to use that action at
any time
- `denied` - which prevents use
- `requested` - which will prompt the receiving operator for permission when
access is attempted. Access will await approval or denial. If denied, the sender
is notified of the denial and reason.

This is just a start, and further development of the access control mechanics is
a priority.


# FAQ

## How does `everything` compare to agent libraries like LangChain?

Though you could entirely create a simple agent using only the primitives in
`everything` (see [`DemoAgent`](./everything/operators/demo_agent.py)), it is
not intended to be a full-fledged agent toolset. It can be thought of as more of
an "agent integration framework".

Projects like LangChain, AutoGPT and many others are exploring how to create
purpose-built agents that solve diverse problems using tools.

`everything` is concerned with creating a safe and dynamic _environment_ for
these types of agents to work, where they can freely discover and communicate
with the tools, each other, and any humans available in their environment.

`everything` provides a simple means for defining actions, callbacks, and
access policies that you can use to monitor and ensure safety for the systems
you expose to your agents.

A central part of the design is that humans and other systems can easily
integrate as well, using a simple common format for messages. You can even use
`everything` to set up a basic chat room to use with friends or other systems
and not use agents at all!

An additional benefit of its general design is that `everything` may also
simplify some agent development workflows. See the example below.

So, `everything` is a simple but more general framework intended to support
agent development and to ultimately enable agents to safely integrate with
anything, in any way imaginable.


# Contributing

Please feel free to open PRs!

If you have questions, suggestions, or problems, please open an
[issue](https://github.com/operand/everything/issues).

## Development Installation

Stable development dependencies are maintained in `requirements-dev.in`. You can
install the development dependencies with:
```bash
pip install -r requirements-dev.txt
```

To add a dependency, add it to the `requirements.in` file and run:
```bash
pip-compile requirements-dev.in
```

## Test Suite

You can run the test suite with:
```bash
pytest
```

The test suite is currently set up to run on pull requests to the `main` branch.


# Roadmap

My goal is to maintain a minimal, natural, and practical API for bringing human,
artificial, and other computing systems together, with the following priorities.


## Priorities
- **Speed**:
  Performance is always a concern. If it's not performant, it's not practical.
- **Access Control and Safety**:
  Designing an effective access control solution for AI integrated systems is a
  fundamental problem to solve in order to ensure safety. I believe I've
  included a sane first attempt at such a pattern, but further exploration will
  be a focus of this project.
- **Compatibility and Usability**:
  In general, I believe this is a fair start in defining a set of patterns for
  creating AI integrated systems. I intend to continually improve the API,
  protocol, and other aspects of its design as needed based on feedback from
  real world use. [So please let me know!](https://github.com/operand/everything/issues)
- **Stability**
  A strong testing and versioning stance will be taken ASAP
- **Documentation**:
  I hope to ensure documentation is kept small, accurate and up to date. This
  readme serves as a start.


## Planned Work
- Add examples
  - Agent using JSON actions and discovery
  - simple function channel
  - web i/o
    - image
    - audio
    - video
  - model training example
  - multimodal model example
- Add message broker/networking support (rabbitmq)
- Add integration with [mlc-llm](https://github.com/mlc-ai/mlc-llm)
- Add integration with [gorilla](https://github.com/ShishirPatil/gorilla)
- Add integration with LangChain
- Consider storage API
- Consider prior work on distributed access control
- Consider cross-compilation to C or other languages
- Add a docker file to encourage using it
- [_feel free to make suggestions_](https://github.com/operand/everything/issues)


<p align="center">
  <img src="https://i.ibb.co/p1Y41QX/logo-3.png" alt="logo-3" border="0" width=128>
</p>
