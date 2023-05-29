# `everything`

A fast and minimal foundation for combining human, AI, and other computing
systems, in python


## How does `everything` work?

`everything` is an implementation of the
[Actor pattern](https://en.wikipedia.org/wiki/Actor_model) with an additional
abstraction of a "channel" sitting in front of each actor, serving as an
interface to them.

`everything` establishes a sort of chat-room called a "space" where any
number of humans, artificial, or other computing systems may equally address
each other as individual "operators" that you may perform "actions" on.

`everything` handles the details of the common messaging system and allows
discovering and invoking actions across all parties, automatically handling
things such as reporting exceptions, enforcing access restrictions, and more.

By defining just a single `Channel` subclass, the API may accommodate systems
as varied as:
- voice assistants
- UI driven applications
- terminal environments
- software APIs
- people
- ...
- anything


## How does `everything` compare to agent libraries like LangChain?

`everything` is not an agent toolset and does not intend to be. It can be
thought of as an "integration" framework, intended for use with agents.

Projects like LangChain, AutoGPT, the HF agent API, and others are exploring
how to create purpose built agents that solve diverse problems using tools.

`everything` is concerned with creating a safe and dynamic _environment_ for
these types of agents to work, where they can _discover_ and use the tools
available in their given environment.

`everything` provides a simple means for defining actions _and_ defining
access policies on those actions that you can use to ensure safety for the
systems you expose to your agents.

A central part of the design, is that humans and other systems can easily
integrate as well, using a simple common format for messages. You can even use
`everything` to set up a basic chat room to interface with other systems and
not use agents at all!

So, `everything` is very much a compliment to agent libraries and is intended
to enable agents to safely integrate with _any_ system imaginable.


# Install

I haven't published this as a pip package yet, so for now just:
```
git clone git@github.com:operand/everything.git
pip install ./everything
```

> **WARNING:**\
Running `everything` may result in exposing your computer to access by any
connected `Operator` including AI agents. Please understand the risks before
using this software and do not configure it for OS access otherwise.\
\
If you want to enable OS access, to allow for file I/O for example, I HIGHLY
RECOMMEND using a Docker container to prevent direct access to your host,
allowing you to limit the resources and directories it may access.


# Example Use

In the following example, please note that the first two channel classes
`WebChannel` and `ChattyLMChannel` are minimally implemented for you to try out.
The rest are hypothetical but example implementations may follow.

```python
# We simply pass an array of `Channel`s to the `Space` initializer.
# Each Channel has a single named Operator, representing a user or outside system.
Space([

  # We'll start with two typical Channels. (These are implemented)
  # Each channel may take whatever configuration makes sense for it.

  # A chat-like web UI driven by a human
  WebChannel(
    Operator("Dan"),
    port: 8080,
  ),

  # A language model backend
  ChattyLMChannel(
    Operator("ChattyAI"), 
    model="chattylm/123b"
  ),


  # One could easily add many more. (the following are NOT implemented)

  # Allow access to an OS for file i/o etc.
  OSChannel(
    Operator("Ubuntu"), 
    ...
  ),

  # Add a concurrent channel to "Dan" for speech in/out, like an Alexa
  VoiceAssistantChannel(
    Operator("Dan"), 
    ...
  )

  # "Dan" may also communicate via email through another channel
  EmailChannel(
    Operator("Dan"), 
    ...
  )

  # Perhaps "ChattyAI" also uses multiple channels, like one for images
  ImageIOChannel(
    Operator("ChattyAI"),
    ...
  )

  # Horizontal scaling of LM backends could be achieved by duplicating channels
  # (notice we repeat the last one)
  ImageIOChannel(
    Operator("ChattyAI"),
    ...
  )

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

  # Network with friends and share your LM's and Agents for fun and profit
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
_Note that an empty argument value is considered true._

So, for a person using the chat UI, they can discover the available actions in
their space with:
```python
/help
```
And that will return a (currently crude) data structure listing the actions.

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


## Going Deeper

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
`everything` provides.

This leaves the developer to only need to define the minimum translation and
"re-hydration" logic to interface with any new system, and ignore the details of
how messages are carried and translated between systems, as long as they can
translate to/from the [common message schema](./things/schema.py).


## Access Control

Access Control is essential for safety when exposing systems to independently
working intelligent agents.

I've included a simple but I believe sensible first step towards access control
that requires _you_ as the developer of a channel to indicate what form of
access control you associate with each action on the channel. The access policy
can currently be one of three values:

- `always` - which permits any operator in the space to use that action at any time
- `never` - which prevents use
- `ask` - which will prompt the receiving operator for permission when access is
attempted. Access will await your approval or denial. If denied, the sender is
notified of the denial and reason.

This is just a start, and further development of the access control mechanics is
a priority.


```python
# TODO write an example
```


# Contributing

Feel free to open PRs or issues!


# Roadmap

My goal is to maintain a minimal, natural, and practical API for bringing human,
artificial, and other computing systems together, with the following priorities.


## Priorities:
- **Speed**:
  Performance is always a concern. If it's not performant, it's not practical.
  There is a clear opportunity to use established messaging/queueing solutions
  so that will be at least one direction for R&D.
- **Access Control and Safety**:
  Designing a safe and effective access policy solution within a
  "multi-operator" system is a fundamental problem to solve in order to ensure
  safety for AI interactions. I believe I've included a sane first attempt at
  such a pattern, but further exploration will be a focus of this project.
- **Interoperability**:
  Especially as it pertains to the common messaging protocol.  Again, I think
  what I have is a good start. This may also be simplified once
  messaging/queuing solutions are reviewed. There is enormous potential to
  establish a common protocol for agents to collaborate online. That's
  essentially what this project is attempting.
- **Flexibility**:
  The examples show how flexible the API is already. I intend to keep
  questioning the design to identify the lowest common denominator that will
  work with whatever use cases arise.
- **Stability**
  A strong testing and versioning stance will be taken ASAP
- **Documentation**:
  I hope to ensure documentation is kept small, accurate and up to date. This
  readme serves as a start.


## Planned work:
- Add examples
  - Agent using JSON actions and discovery
  - simple function channel
  - web i/o
    - image
    - audio
    - video
  - model training example
  - multimodal model example
- Consider queuing/storage API
- Consider prior work on distributed access control
- Consider cross compiling to support multiple languages
- Add a docker file to encourage using it
- [_feel free to make suggestions_](https://github.com/operand/everything/issues)
