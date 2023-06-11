# `everything`

A fast and minimal foundation for unifying human, AI, and other computing
systems, in python


## What is `everything`?

`everything` defines a common communication and action framework for integrating
AI agents, humans, and traditional computing systems.

`everything` allows you to establish shared environments called "spaces" where
any number of humans, artificial, or other computing systems may equally address
each other as individual "operators" that you may perform "actions" on.

`everything` handles the details of the common messaging protocol and allows
discovering and invoking actions across all parties, automatically handling
things such as reporting exceptions, enforcing access restrictions, and more.

The API equally accommodates integration of systems as varied as:

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
RECOMMEND running your project within a Docker container to prevent direct
access to your host, allowing you to limit the resources and directories that
may be accessed.

```sh
pip install everything
```


# API Overview

`everything` is an implementation of the [Actor
model](https://en.wikipedia.org/wiki/Actor_model) intended for use in systems
that may equally mix AI, humans, and traditional computing systems.

In `everything`, all entities are represented as instances of the class
`Operator`. This includes all humans, software, or AI agents.

The `Operator` class can be thought of as a base class similar to "Object" in
many object-oriented languages. All `Operator`'s may expose "actions" which can
be invoked by other `Operator`'s, by simply defining instance methods on the
class.

A `Space` is itself a subclass of `Operator` and is used to group multiple
`Operator`'s together and facilitate communication among them.

A `Space` can be thought of as both a collection of `Operator`'s and a "router"
for their communication. An `Operator` cannot communicate with others until it
is first added to a `Space`.

Since `Space`'s are `Operator`'s themselves, they may be nested, allowing for
namespacing and hierarchical organization of the `Operator`'s in your
application.

To summarize, the two classes of `Operator` and `Space` together create a simple
API for defining and integrating complex multimodal applications that mix AI,
human, and traditional computing systems.

Let's walk through a thorough example to see how this works in practice.


# Walkthrough

_Please note that the example classes used in this walkthrough are implemented
for you to explore and try out, but should be considered "proof of concept"
quality only._


## Creating a `Space`

Let's start by instantiating a demo space.

```python
demo_space = Space("DemoSpace")
```

Spaces, like all `Operator`'s, must be given an `id`. So the line above
instantiates a single space called `"DemoSpace"` that we can now add
`Operator`'s to.


## Adding an `Operator` to a `Space`

Now, let's add our first `Operator` to the space, a simple transformers library
backed chatbot class named `ChattyAI`. You can browse the source code for
`ChattyAI` [here](./everything/operators/chattyai.py).

```python
demo_space.add(
    ChattyAI("Chatty", model="EleutherAI/gpt-neo-125m"))
```

The line above adds a new `ChattyAI` instance to the space, with the `id` of
`"Chatty"`. It also passes the `model` argument to the constructor, which is
used to initialize the HuggingFace transformers language model.

At this point "Chatty" has a fully qualified `id` of `"Chatty.DemoSpace"`.  This
is because `ChattyAI` is a member of the `DemoSpace` space.

In this way, spaces establish a namespace for their members which can later be
used to address them.


## Defining Actions

Looking at `ChattyAI`'s source code, you'll see that it is a subclass of
`Operator`, and that it exposes a single action called `"say"`.

The `"say"` action is defined as a method on the `ChattyAI` class, using
the following signature:

```python
def _action__say(self, content: str):
    """Use this action to say something to Chatty"""
    ...
```

The prefix `_action__` is used to indicate that this is an action that can be
invoked by other `Operator`'s. The suffix `say` is the name of the action.

This `"say"` action takes a single string argument `content`. This action is
intended to allow other operators to chat with Chatty, as expressed in its
docstring.

When `ChattyAI` receives a `"say"` action, it will generate a response using its
prompt format with the language model, and return the result to the sender.


## Invoking Actions

At the end of the `ChattyAI` `"say"` implementation, we see the first instance
of `everything`'s messaging protocol. `ChattyAI` returns a response to the
sender by calling:

```python
self._send({
    "to": self._current_message['from'],
    "thoughts": "",
    "action": "say",
    "args": {
      "content": response_content,
    }
})
```

This is a very simple implementation, but it demonstrates the basic idea of how
to invoke an "action" on another `Operator`.

When an `Operator` receives a message, it invokes the action specified in the
`action` field of the message, passing the `args` to the action as keyword
arguments.

So here we see that `ChattyAI` is invoking the `"say"` action on the sender of
the message, passing the response as the `content` argument.


## The Common Message Schema

In the example above, we also see the format that is used when sending actions.

In describing the messaging format, there are two terms that are used similarly:
"action" and "message".

Simply put, an "action" is the format you use when sending, as seen in the
`_send()` call above. You do not specify your own `id` in the `from` field,
because the `Space` will automatically add it for you when routing.

A "message" then, is simply an "action" with the addition of the sender's `id`
in the `from` field.

Continuing the example above, the original sender would recieve a response
message from `ChattyAI` that would look something like:

```python
{
    "from": "Chatty.DemoSpace",
    "to": "Sender.DemoSpace",
    "thoughts": "Whatever Chatty was thinking",
    "action": "say",
    "args": {
      "content": "Whatever Chatty said",
    }
}
```

This is an example of the full common message schema that is used for all
messages sent between `Operator`'s in `everything`.

This format is intended to be simple and extensible enough to support any use
case while remaining human readable.

So when the sending `Operator` receives the above response, it in turn invokes
their own `"say"` action, for them to process as they choose.

Note that the `"thoughts"` field is broken out as a distinct argument for
providing a natural language explanation to accompany any action.

For more details on the common message schema see
[schema.py](./everything/things/schema.py).


## Access Control

You may have noticed the `access_policy` decorator used on the `"say"` action in
`ChattyAI`:

```python
@access_policy(ACCESS_PERMITTED)
def _action__say(self, content: str):
    """Use this action to say something to Chatty"""
    ...
```

This is an example of an access control policy. Access control policies are used
to control what actions can be invoked by other `Operator`'s.

The access policy can currently be one of three values:

- `ACCESS_PERMITTED` - which permits any operator to use that action at
any time
- `ACCESS_DENIED` - which prevents use
- `ACCESS_REQUESTED` - which will prompt the receiving operator for permission
when access is attempted. Access will await approval or denial. If denied, the
sender is notified of the denial.

If `ACCESS_REQUESTED` is used, the receiving operator will be prompted at run
time to approve the action.

To implement a method for an operator to approve/disapprove access, you must
implement the `_request_permission` method with the following signature:

```python
def _request_permission(self, proposed_message: MessageSchema) -> bool:
    ...
```

This method is called when an operator attempts to invoke an action that has
been marked as `ACCESS_REQUESTED`. Your method should inspect the
`proposed_message` and return a boolean indicating whether or not to permit the
action.

You can use this approach to protect against dangerous actions being taken. For
example if you allow terminal access, you may want to review commands before
they are invoked.

This implementation of access control is just a start, and further development
of the mechanics is a priority for this project.


## Adding Human Users With the `WebApp` Class

A single chatting AI wouldn't be useful without someone to chat with, so now
let's add humans into the space so that they can chat with "Chatty". To do
this, we'll use the `WebApp` class, which is subclass of `Space`.

Why is `WebApp` a subclass of `Space` and not `Operator`?

This is an arbitrary choice up to the developer, but the rule of thumb should
be:

_If you want to include multiple `Operator`'s as a group, you should create a
`Space` subclass and implement any additional logic necessary to forward
messages to individual `Operator`'s in the group._

I could have implemented `WebApp` as a subclass of `Operator`, and created the
web application in a way where I would be the only user, perhaps running it
locally.

But since a typical web application serves multiple users, it may make more
sense to implement it as a `Space` subclass, so that individual users of the web
application can be addressed by other operators using a namespace associated
with the web application _(see below)_.

This is _not_ the only way this could be accomplished but is intended as a
complex example to showcase why one might want to define a `Space` subclass to
group operators when it makes sense.


### Examining the `WebApp` Class

The implementation located [here](./everything/spaces/web_app.py) defines a
simple `Flask` based web application that hosts a single page `React` based chat
UI.

The implementation takes some shortcuts, but in it you'll see that we actually
define two classes, one for the web application, which extends `Space`, called
`WebApp`, and a second class to represent users of the web app, called
`WebAppUser`.

The `WebAppUser` class is where we define the actions that an individual web app
user may expose to others.

Using the `asyncio` library you'll see that we simply forward messages as-is to
the `React` frontend, and allow the client code to handle rendering.

_Please see the source for more detail._


## Namespacing and Adding the Web Application

Now that we've defined our new `WebApp` class, we can add it to `DemoSpace`
with:

```python
demo_space.add(
    WebApp("WebApp", port=os.getenv('WEB_APP_PORT')))
```

Whenever an operator is added to a space, its fully qualified `id` becomes
namespaced by the space's `id`.

For example, the `WebApp`, being an operator as well, receives and `id` of
`"WebApp.DemoSpace"` after running the line above.

At this point, we have the following operators listed using their fully qualified `id`'s
- `"DemoSpace"` - The root space
- `"ChattyAI.DemoSpace"` - ChattyAI's fully qualified `id`
- `"WebApp.DemoSpace"` - the root of the `"WebApp"` space


Users of the web application, as they log in or out, may be added dynamically to
the space and may use their own `id` namespaced under `"WebApp"`, 

So, if `"Dan"` logs in, their `id` within the environment would be:
`"Dan.WebApp.DemoSpace"`.


_(Please note that login/out functionality is not fully implemented as of this
writing)_


## Adding OS Access with the `Host` class

At this point, we have a system where human users of the web application can
chat with ChattyAI, using just a single action called `"say"` that both
`Operator` classes implement.

Now we'll add an `Operator` class that exposes many different actions, the
[`Host`](./everything/operators/host.py) class.

The `Host` class allows access to the host operating system where the python
application is running. It exposes actions such as `read_file` and
`shell_command` which allow other operators to take actions on the host.

This class is a good example of one with potentially dangerous actions that need
to be accessed with care. So, you'll notice that all the methods in the `Host`
class have been given the access policy:

```python
@access_policy(ACCESS_REQUESTED)
```

By declaring this access policy, all actions on the host will require a
confirmation from the terminal where the application is being run. This is
thanks to the implementation of `_request_permission()` in the `Host` class.

Note that this implementation of `_request_permission()` is just one
possibility. We could have implemented, for example, a phone notification for a
human to review from anywhere.


## Discovering and Invoking Actions

At this point, we 

# TODO

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


## Adding an Environment-Aware Agent

Finally we get to what we've been working towards!

We'll now add an intelligent agent into this environment and see that it is
easily able to understand and interact with any of the systems or humans we've
connected thus far.

# TODO








# Hypothetical Examples

The following examples are not implemented, but are presented to give you an
idea of other ways that this API could be used.

```python
Space([

    # Integrate access to a remote server
    Server("Ubuntu",
        ip="192.168.1.100"),

    # Add a voice assistant interface
    VoiceAssistant("Sirilexa")

    # One could connect and send/receive messages via email
    Email("Dan", address="dan@dan.com"),

    # AI agents can access other ML systems, like for images
    DiffusionModel("ImageAI"),

    # Horizontal scaling could be achieved by simply duplicating operators
    # (notice we repeat the last one)
    DiffusionModel("ImageAI"),

    # Existing AI agent frameworks may integrate as well
    LangChainAgent("MyLangChainAgent"))

    # Development related tasks like model training may also be accomplished.
    # You would only need to add one new `Operator` that reads a data set and
    # sends it as messages to the `Operator` class used for inference, provided
    # the underlying model is first switched to a training mode. For example:
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
simplify some agent development workflows. See the hypothetical examples above.

So, `everything` is a simple but more general framework intended to support
agent development and to ultimately enable agents to safely integrate with
anything, in any way imaginable.


# Contributing

Please do!

If you're looking to open a PR I'd like to keep to the following guidelines to
start:

- The core classes (`Operator` and `Space`) should be kept minimal and focused
on common application concerns such as speed, security, and messaging.
- If you'd like to add specific implementations of `Operator`'s and `Spaces`
they can go into their respective folders.
- Changes to core classes should be accompanied by tests if possible.


If you have any questions, suggestions, or problems, please open an
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
And make sure to commit your changes.


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
  real world use. [So please let me
  know!](https://github.com/operand/everything/issues)
- **Documentation**:
  I hope to ensure documentation is kept small, accurate and up to date. This
  readme serves as a start.


## Planned Work
- Add examples
  - simple function channel
  - web app i/o examples
    - image
    - audio
    - video
  - model training example
  - multimodal model example
- Add message broker/networking support (RabbitMQ)
- Add integration example for [mlc-llm](https://github.com/mlc-ai/mlc-llm)
- Add integration example for [gorilla](https://github.com/ShishirPatil/gorilla)
- Add integration example for LangChain
- Consider storage API
- Consider prior work on distributed access control
- Consider cross-compilation to C or other languages
- Add docker assets to encourage using it
- [_feel free to make
suggestions_](https://github.com/operand/everything/issues)


<p align="center">
  <img src="https://i.ibb.co/p1Y41QX/logo-3.png" alt="logo-3" border="0" width=128>
</p>
