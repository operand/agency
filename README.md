# `agency`

A fast and minimal actor model framework for building agent-integrated systems


## What is `agency`?

`agency` defines a common communication and action framework for integrating
AI agents, humans, and traditional computing systems.

`agency` allows you to establish shared environments called "spaces" where any
number of humans, artificial, or other computing systems may equally address
each other as individual "agents" that you may perform "actions" on.

`agency` handles the details of the common messaging protocol and allows
discovering and invoking actions across all parties, automatically handling
things such as reporting exceptions, enforcing access restrictions, and more.

The API accommodates agent integration with systems as varied as:

- UI driven applications
- terminal environments
- software APIs
- other AI agents
- people
- ...
- anything


# Install
> **WARNING:**\
Running `agency` may result in exposing your computer to access by any connected
`Agent` class. Please understand the risks before using this software and do not
configure it for OS access otherwise.\
\
If you want to enable OS access, to allow for file I/O for example, I HIGHLY
RECOMMEND running your project within a Docker container to prevent direct
access to your host, allowing you to limit the resources and directories that
may be accessed.

```sh
pip install agency
```


# API Overview

`agency` is an implementation of the [Actor
model](https://en.wikipedia.org/wiki/Actor_model) intended for integrating AI,
human, and traditional computing systems.

In `agency`, all entities are called "agents" and represented as instances
of the `Agent` class. This includes all humans, software, and AI-driven agents.

The `Agent` class is a base class similar to "Object" in many object-oriented
languages. All agents may expose "actions" that other agents can discover and
invoke at run time. Actions also specify an access policy, allowing you to
monitor and control actions to ensure safety.

A `Space` is also an `Agent` and is used to group multiple agents together. A
space can be thought of as both a collection of agents and a facilitator for
their communication. An agent cannot communicate with others until it is first
added to a space.

Spaces may be nested, allowing for namespacing and hierarchical organization of
the agents in your application.

To summarize, the two classes of `Agent` and `Space` together create a simple
API for creating applications that may mix AI, human, and traditional computing
systems, in a way that is intended for all to equally understand and use.

Let's walk through a thorough example to see how this works in practice.


# Example Walkthrough

> Please note that the example agent classes used in this walkthrough are
implemented for you to explore and try out, but should be considered "proof of
concept" quality at this time.

The following snippet is the full resulting implementation (minus imports) of
the example walkthrough that you can try out on your own, including two OpenAI
agent examples and the HuggingFace based `ChattyAI`. Note that `Space.run()`
starts a thread, so we simply keep the application alive with a while loop.

```python
# demo.py

if __name__ == '__main__':

    space = Space("DemoSpace")

    space.add(
        WebApp("WebApp",
            demo_user_id="Dan", # hardcoded for simplicity
            port='8080'))

    space.add(
        ChattyAI("Chatty",
            model="EleutherAI/gpt-neo-125m"))

    space.add(
        Host("Host"))

    space.add(
        OpenAIFunctionAgent("FunctionAI",
            model="gpt-3.5-turbo-16k",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            # user_id determines the "user" role in the OpenAI chat
            user_id="Dan.WebApp.DemoSpace"))

    space.add(
        OpenAICompletionAgent("CompletionAI",
            model="text-davinci-003",
            openai_api_key=os.getenv("OPENAI_API_KEY")))

    space.run()

    print("pop!")

    # keep alive
    while True:
        time.sleep(1)
```


## Creating a `Space`

Let's start by instantiating a demo space.

```python
space = Space("DemoSpace")
```

`Space`'s, like all `Agent`'s, must be given an `id`. So the line above
instantiates a single space called `"DemoSpace"` that we can now add agents to.


## Adding an `Agent` to a `Space`

Now, let's add our first agent to the space, a simple transformers library
backed chatbot class named `ChattyAI`. You can browse the source code for
`ChattyAI` [here](./agency/agents/chattyai.py).

```python
space.add(ChattyAI("Chatty", model="EleutherAI/gpt-neo-125m"))
```

The line above adds a new `ChattyAI` instance to the space, with the `id` of
`"Chatty"`. It also passes the `model` argument to the constructor, which is
used to initialize the HuggingFace transformers language model.

At this point "Chatty" has a fully qualified `id` of `"Chatty.DemoSpace"`.  This
is because `"Chatty"` is a member of the `"DemoSpace"` space.

This way, spaces establish a namespace for their member agents which can later
be used to address them.


## Defining Actions

Looking at `ChattyAI`'s source code, you'll see that it is a subclass of
`Agent`, and that it exposes a single action called `say`.

The `say` action is defined as a method on the `ChattyAI` class, using the
following signature:

```python
def _action__say(self, content: str):
    """Use this action to say something to Chatty"""
    ...
```

The prefix `_action__` is used to indicate that this is an action that can be
invoked by other agents. The suffix `say` is the name of the action.

The `say` action takes a single string argument `content`. This action is
intended to allow other agents to chat with Chatty, as expressed in its
docstring.

When `ChattyAI` receives a `say` action, it will generate a response using its
prompt format with the language model, and return the result to the sender.


## Invoking Actions

At the end of the `ChattyAI._action__say()` method, we see an example of using
`agency`'s messaging protocol. `ChattyAI` returns a response to the sender
by calling:

```python
...
self._send({
    "to": self._current_message['from'],
    "thoughts": "",
    "action": "say",
    "args": {
      "content": response_content,
    }
})
```

This is a simple implementation that demonstrates the basic idea of how to
invoke an action on another agent.

When an agent receives a message, it invokes the action method specified by the
`"action"` field of the message, passing the `"args"` to the action method as
keyword arguments.

So here we see that Chatty is invoking the `say` action on the sender of the
original message, passing the response as the `"content"` argument.


## The Common Message Schema

In the example above, we see the format that is used when sending actions.

In describing the messaging format, there are two terms that are used similarly:
"action" and "message".

An "action" is the format you use when sending, as seen in the `_send()` call
above. You do not specify the `"from"` field, as it will be automatically added
when routing.

A "message" then, is a "received action" which includes the additional
`"from"` field containing the sender's fully qualified `id`.

Continuing the example above, the original sender would receive a response
message from Chatty that would look something like:

```python
{
    "from": "Chatty.DemoSpace",
    "to": "Sender.DemoSpace",
    "thoughts": "",
    "action": "say",
    "args": {
      "content": "Whatever Chatty said",
    }
}
```

This is an example of the full message schema that is used for all messages sent
between agents in `agency`. This format is intended to be simple and extensible
enough to support any use case while remaining human readable.

Note that the `"thoughts"` field is defined as a distinct argument for providing
a natural language explanation to accompany any action, but as of this writing
`ChattyAI` does not make use of it. `OpenAICompletionAgent` discussed below,
does.

For more details on the common message schema see
[schema.py](./agency/schema.py).


## Access Control

All actions must declare an access policy like the following example seen above
the `ChattyAI._action__say()` method:

```python
@access_policy(ACCESS_PERMITTED)
def _action__say(self, content: str):
    """Use this action to say something to Chatty"""
    ...
```

Access policies are used to control what actions can be invoked by other agents.

An access policy can currently be one of three values:

- `ACCESS_PERMITTED` - which permits any agent to use that action at
any time
- `ACCESS_DENIED` - which prevents use
- `ACCESS_REQUESTED` - which will prompt the receiving agent for permission
when access is attempted. Access will await approval or denial. If denied, the
sender is notified of the denial.

If `ACCESS_REQUESTED` is used, the receiving agent will be prompted at run
time to approve the action.

If any actions require permission, you must implement the
`_request_permission()` method with the following signature:

```python
def _request_permission(self, proposed_message: MessageSchema) -> bool:
    ...
```

This method is called when an agent attempts to invoke an action that has been
marked as `ACCESS_REQUESTED`. Your method should inspect `proposed_message` and
return a boolean indicating whether or not to permit the action.

You can use this approach to protect against dangerous actions being taken. For
example if you allow terminal access, you may want to review commands before
they are invoked.

This implementation of access control is just a start, and further development
of the functionality is a priority for this project.


## Adding Human Users With the `WebApp` Class

A single chatting AI wouldn't be useful without someone to chat with, so now
let's add humans into the space so that they can chat with "Chatty". To do
this, we'll use the `WebApp` class, which is a subclass of `Space`.

Why choose to subclass `Space` and not `Agent`? This is an arbitrary choice up
to the developer, and may depend on what they want to accomplish.

We could implement `WebApp` as a subclass of `Agent`. This would represent the
web application as a single agent within the system. Users of the web
application would not be able to be addressed individually by other agents.

But since a typical web application serves multiple users, it may make sense to
implement it as a `Space` subclass, so that individual users of the web
application can be addressed by other agents using a namespace associated with
the web application, as we'll see below.

So this is _not_ the only way this could be accomplished but is intended as a
complex example to showcase why one might want to define a `Space` subclass to
group agents when it makes sense.


### Examining the `WebApp` Class

The implementation located [here](./agency/spaces/web_app.py) defines a simple
`Flask` based web application that hosts a single page `React` based chat UI.

The implementation takes some shortcuts, but in it you'll see that we actually
define two classes, one for the web application which extends `Space`, called
`WebApp`, and a second class to represent users of the web app which extends
`Agent` and is called `WebAppUser`.

The `WebAppUser` class is where we define the actions that an individual web app
user may expose to others.

Using the `asyncio` library you'll see that we simply forward messages as-is to
the `React` frontend, and allow the client code to handle rendering and parsing
of input as actions back to the `Flask` application, which forwards them to
their intended receiver in the space.


## Namespacing and Adding the Web Application

Now that we've defined our new `WebApp` class, we can add it to `DemoSpace`
with:

```python
space.add(
    WebApp("WebApp", port='8080'))
```

Whenever any agent is added to a space, its fully qualified `id` becomes
namespaced with the space's `id`.

For example, after running the line above the `WebApp` being an agent as well,
receives an `id` of `"WebApp.DemoSpace"`.

At this point, we have integrated the following agents listed using their fully
qualified `id`'s:

- `"DemoSpace"` - The root space
- `"ChattyAI.DemoSpace"` - ChattyAI's fully qualified `id`
- `"WebApp.DemoSpace"` - the root of the `"WebApp"` space

Users of the web application, as they log in or out, may be added dynamically
under the `"WebApp"` namespace allowing them to be addressed with a fully
qualified `id` of, for example:

- `"Dan.WebApp.DemoSpace"`.

This way, we allow individual web users to appear as individual agents to others
in the space.

_(Note that login/out functionality is not implemented as of this writing.)_


## Adding OS Access with the `Host` class

At this point, we have a system where human users of the web application can
chat with `ChattyAI`, using just a single action called `"say"` that both
`Agent` classes implement.

Now we'll add an agent that exposes many different actions, the
[`Host`](./agency/agents/host.py) class.

```python
space.add(Host("Host"))
```

The `Host` class allows access to the host operating system where the python
application is running. It exposes actions such as `read_file` and
`shell_command` which allow other agents to interact with the host.

This class is a good example of one with potentially dangerous actions that must
be accessed with care. You'll notice that all the methods in the `Host` class
have been given the access policy:

```python
@access_policy(ACCESS_REQUESTED)
```

By declaring this access policy, all actions on the host will require a
confirmation from the terminal where the application is being run. This is
thanks to the implementation of `_request_permission()` in the `Host` class.

Note that this implementation of `_request_permission()` is just one
possibility. We could have implemented, for example, a phone notification for a
human to review from elsewhere.


## Discovering Actions

At this point, we can demonstrate how discovery works from the perspective of
a human user of the web application.

Once added to a space, each agent may send a `help` message to discover other
agents and actions that are available in the space.

The `WebApp` application hosts a simple chat UI that supports a "slash" syntax
summarized here:

```python
/actionname arg1:val1 arg2:val2 ...
```

So a person using the chat UI can discover available actions by typing:

```
/help
```

This will broadcast a `help` action to all other agents, who will individually
respond with a list of their available actions. The returned list of actions
would look something like:

```python
[
    {
        "to": "Host.DemoSpace",
        "action": "delete_file",
        "thoughts": "Delete a file",
        "args": {
          "filepath": "str"
        }
    },
    {
        "to": "Host.DemoSpace",
        "action": "list_files",
        "thoughts": "List files in a directory",
        "args": {
          "directory_path": "str"
        }
    },
    ...
]
```

Notice that each action lists the fully qualified `id` of the agent in the
`"to"` field, the docstring of the action's method in the `"thoughts"` field,
and each argument along with its type in the `"args"` field.

So a person using the web app UI can invoke the `list_files` action on
`"Host.DemoSpace"` with the following syntax:

```
/list_files to:Host.DemoSpace directory_path:/app
```

This will send the `list_files` action to the `Host` agent who will (after being
granted permission) return the results back to `"Dan.WebApp.DemoSpace"`
rendering it to the web user interface as a message.


## Broadcast vs Point-to-Point Messaging

Note the use of the fully qualified `id` of `Host.DemoSpace` used with the `to:`
field.

If we omit the `to:Host.DemoSpace` portion of the command above, the message
will be broadcast, and any agents who implement a `list_files` action will
respond.

This is also how the `/help` command works. If you want to request help from
just a single agent you can use something like:

```
/help to:Host.DemoSpace
```

Note that point-to-point messages (messages that define the `"to"` field) will
result in an error if the action is not defined on the target agent.

Broadcast messages will _not_ return an error, but will silently be ignored by
agents who do not implement the given action.


## Adding an Environment-Aware Agent

Finally we get to the good part!

We'll now add an intelligent agent into this environment and see that it is able
to understand and interact with any of the systems or humans we've connected
thus far.

> Note that the following `OpenAIFunctionAgent` class uses the newly released
[openai function calling
API](https://platform.openai.com/docs/guides/gpt/function-calling).

To add the [`OpenAIFunctionAgent`](./agency/agents/demo_agent.py) class to the
environment:
```python
space.add(
    OpenAIFunctionAgent("FunctionAI",
        model="gpt-3.5-turbo-16k",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        # user_id determines the "user" role in the chat API
        user_id="Dan.WebApp.DemoSpace"))
```

The `user_id` argument determines which agent is represented as the "user" role
to the chat API. Since the chat API is limited to a predefined set of roles, we
need to indicate which is the main "user".

For an implementation that uses a plain text completion API, see
[`OpenAICompletionAgent`](./agency/agents/openai_completion_agent.py).


## Running the Example

If you run the python script provided at the beginning of this walkthrough,
after a short boot time you can visit the web app at `http://localhost:8080` and
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
`agency` (see [`agents/`](./agency/agents/)), it is not intended to be a
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

  Other forms of multiprocessing to avoid the GIL will be considered.

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

The goal is to maintain a minimal, natural, and practical API for bringing
human, artificial, and other computing systems together, with the following
priorities.


## Priorities
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
  creating agent systems. I hope to ensure the API is kept small, and
  compatible with a wide variety of use cases.
- **Documentation**:
  I hope to ensure documentation is kept organized, clear, and accurate. This
  readme serves as a start.


## Planned Work

[Please see the issues page.](https://github.com/operand/agency/issues)

If you have any suggestions or otherwise, feel free to add an issue!
