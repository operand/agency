# API Walkthrough

This walkthrough will guide you through the basic concepts of `agency`'s API,
and how to use them to build your own agents.

## Creating an `agency` Application

The snippet below is a taken from the demo application located at
[examples/demo/](./examples/demo/). Basic instructions for how to run the demo
are located in that directory.

The demo can be run as both a single `NativeSpace` implementation, or a
distributed `AMQPSpace` implementation.

For this walkthrough, we'll be using the `NativeSpace` implementation. Usage is
exactly the same as with the `AMQPSpace` class, except that a `NativeSpace` is
for agents in the same process, and does not require an AMQP server.

This demo application includes two different OpenAI agent classes, a
transformers based chat agent named `ChattyAI`, operating system access, and a
Flask/React based web application hosted at `http://localhost:8080`, all
integrated with the following implementation.


```python
# native_demo.py

if __name__ == '__main__':

    # Create a space
    space = NativeSpace()

    # Add a host agent to the space, exposing access to the host system
    space.add(Host("Host"))

    # Add a simple HF based chat agent to the space
    space.add(
        ChattyAI("Chatty",
                 model="EleutherAI/gpt-neo-125m"))

    # Add an OpenAI function API agent to the space
    space.add(
        OpenAIFunctionAgent("FunctionAI",
                            model="gpt-3.5-turbo-16k",
                            openai_api_key=os.getenv("OPENAI_API_KEY"),
                            # user_id determines the "user" role in the OpenAI chat API
                            user_id="Dan"))

    # Add another OpenAI agent based on the completion API
    space.add(
        OpenAICompletionAgent("CompletionAI",
                              model="text-davinci-003",
                              openai_api_key=os.getenv("OPENAI_API_KEY")))

    # Create and start a web app to connect human users to the space.
    # As users connect they are added to the space as agents.
    web_app = WebApp(space,
                     port=os.getenv("WEB_APP_PORT"),
                     # NOTE We're hardcoding a single demo user for simplicity
                     demo_username="Dan")
    web_app.start()

    print("pop!")

    # keep alive
    while True:
        time.sleep(1)
```


## Creating a `Space`

Now let's see how this is implemented. Let's start simply by instantiating the
space.

```python
space = NativeSpace()
```


## Adding an `Agent` to a `Space`

Now, let's add our first agent to the space, a simple transformers library
backed chatbot named `ChattyAI`. You can browse the source code for `ChattyAI`
[here](./agency/agents/chattyai.py).

```python
space.add(ChattyAI("Chatty", model="EleutherAI/gpt-neo-125m"))
```

The line above adds a new `ChattyAI` instance to the space, with the `id` of
`"Chatty"`. It also passes the `model` argument to the constructor, which is
used to initialize the HuggingFace transformers language model.

The `id` parameter is used to identify the agent within the space. Other agents
may send messages to Chatty by using that `id`, as we'll see later.

Note that `id`'s are not unique. Two agents may declare the same `id` and would
receive duplicate messages.


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
underlying language model, and return the result to the sender.


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
original message, passing the response as the `"content"` argument. This way,
the original sender and Chatty can have a conversation.


## The Common Message Format

In the example above, we see the format that is used when sending actions.

In describing the messaging format, there are two terms that are used similarly:
"action" and "message".

An "action" is the format you use when sending, as seen in the `_send()` call
above. You do not specify the `"from"` field, as it will be set when routing.

A "message" then, is a "received action" which includes the additional `"from"`
field containing the sender's `id`.

Continuing the example above, the original sender would receive a response
message from Chatty that would look something like:

```python
{
    "from": "Chatty",
    "to": "Sender",
    "thoughts": "Chatty's thoughts",
    "action": "say",
    "args": {
      "content": "Whatever Chatty said",
    }
}
```

This is an example of the full message schema that is used for all messages sent
between agents in `agency`. This format is intended to be simple and extensible
enough to support most use cases while remaining human readable.

Custom message format are a possibility in the future. If you'd like to see
support for custom message formats, please open an issue.


## Access Control

All actions must declare an access policy like the following example:

```python
@access_policy(ACCESS_PERMITTED)
def _action__say(self, content: str):
    """Use this action to say something to Chatty"""
    ...
```

Access policies are used to control when actions can be invoked by other agents.

An access policy can currently be one of three values:

- `ACCESS_PERMITTED` - which permits any agent to use that action at
any time
- `ACCESS_DENIED` - which prevents use
- `ACCESS_REQUESTED` - which will prompt the receiving agent for permission
when access is attempted. Access will await approval or denial.

If `ACCESS_REQUESTED` is used, the receiving agent will be prompted at run time
to approve the action via the `_request_permission()` callback method.

If any actions require permission, you must implement the
`_request_permission()` method with the following signature in order to receive
permission requests.

```python
def _request_permission(self, proposed_message: MessageSchema) -> bool:
    ...
```

Your implementation should inspect `proposed_message` and return a boolean
indicating whether or not to permit the action.

You can use this approach to protect against dangerous actions being taken. For
example if you allow terminal access, you may want to review commands before
they are invoked.


## Adding Human Users With the `WebApp` Class

A single chatting AI wouldn't be useful without someone to chat with, so now
let's add humans into the space so that they can chat with "Chatty". To do this,
we'll use the `WebApp` class.



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

Now that we've defined our new `WebApp` class, we can add it to the space
with:

```python
space.add(
    WebApp("WebApp", port='8080'))
```

Whenever any agent is added to a space, its fully qualified `id` becomes
namespaced with the space's `id`.

For example, after running the line above the `WebApp` being an agent as well,
receives an `id` of `"WebApp"`.

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
[`Host`](../examples/demo/agents/host.py) class.

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
...
```

Thanks to the implementation of `_request_permission()` in the `Host` class, all
actions on the host will require a confirmation from the terminal where the
application is being run.

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
        "to": "Host",
        "action": "delete_file",
        "thoughts": "Delete a file",
        "args": {
          "filepath": "str"
        }
    },
    {
        "to": "Host",
        "action": "list_files",
        "thoughts": "List files in a directory",
        "args": {
          "directory_path": "str"
        }
    },
    ...
]
```

Notice that each action lists the `id` of the agent in the `"to"` field, the
docstring from the action's method in the `"thoughts"` field, and each argument
along with its type in the `"args"` field.

So a person using the web app UI can invoke the `list_files` action on
`"Host"` with the following syntax:

```
/list_files to:Host directory_path:/app
```

This will send the `list_files` action to the `Host` agent who will (after being
granted permission) return the results back to the web user interface as a
message.


## Broadcast vs Point-to-Point Messaging

Note the use of the `id` of `Host` used with the `to:` field.

If we omit the `to:Host` portion of the command above, the message
will be broadcast, and any agents who implement a `list_files` action will
respond.

This is also how the `/help` command works. If you want to request help from
just a single agent you can use something like:

```
/help to:Host
```

Note that point-to-point messages (messages that define the `"to"` field) will
result in an error if the action is not defined on the target agent, or if no
agent with that `id` exists in the space.

Broadcast messages will _not_ return an error, but will silently be ignored by
agents who do not implement the given action.


## Adding an Environment-Aware Agent

Finally we get to the good part!

We'll now add an intelligent agent into the environment and see that it is able
to understand and interact with any of the systems or humans we've connected
thus far.

> Note that the following `OpenAIFunctionAgent` class uses the [openai function
calling API](https://platform.openai.com/docs/guides/gpt/function-calling).

To add the [`OpenAIFunctionAgent`](./agency/agents/demo_agent.py) class to the
environment:
```python
space.add(
    OpenAIFunctionAgent("FunctionAI",
        model="gpt-3.5-turbo-16k",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        # user_id determines the "user" role in the chat API
        user_id="Dan"))
```

The `user_id` argument determines which agent is represented as the "user" role
to the chat API. Since the chat API is limited to a predefined set of roles, we
need to indicate which is the main "user".

For an implementation that uses a plain text completion API, see
[`OpenAICompletionAgent`](./agency/agents/openai_completion_agent.py).


# Important Notes on Using `AMQPSpace` and the `amqp` Protocol

When using AMQP, you have many options for connectivity that may affect your
experience. By default, the `AMQPSpace` class will read the environment
variables seen in [`examples/demo/.env.example`](...) for basic settings, and
otherwise will use default settings.

Finer grained connection options are possible (heartbeat, ssl, etc.) if you
provide your own
[`pika.ConnectionParameters`](https://pika.readthedocs.io/en/stable/modules/parameters.html)
object when instantiating an `AMQPSpace`. Please take a look at those options if
you experience dropped connections, or have other connection related issues.
