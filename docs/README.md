# Documentation

The following could be better organized. Please open an issue if you have
suggestions for how to improve the documentation.


## Table of Contents

* [API Walkthrough](#api-walkthrough)
* [Agent Callbacks](#agent-callbacks)
* [Using `AMQPSpace`](#using-amqpspace)


# API Walkthrough

The following walkthrough will guide you through the basic concepts of
`agency`'s API, and how to use it to build your own agent systems.

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

```python
space = NativeSpace()
```


## Adding an `Agent` to a `Space`

```python
space.add(ChattyAI("Chatty", model="EleutherAI/gpt-neo-125m"))
```

The line above adds a new `ChattyAI` instance to the space, with the `id` of
`"Chatty"`. The `model` argument is used to initialize the HuggingFace
transformers language model.

An agent's `id` is used to identify the agent within the space. Other agents may
send messages to Chatty by using that `id`, as we'll see later.

`id`'s are not necessarily unique. Two agents may declare the same `id` and
will receive duplicate messages.


## Defining Actions

Looking at `ChattyAI`'s source code, you'll see that it is a subclass of
`Agent`, and that it exposes a single action called `say`.

The following is a typical action method implementation taken from `ChattyAI`.

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

An example of invoking an action can be seen here, taken from the same
`ChattyAI._action__say()` method.

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

This is an example of the schema that is used for sending messages in `agency`.
This format is intended to be simple and extensible enough to support most use
cases while remaining human readable.

Custom message formats are a possibility in the future. If you'd like to see
support for custom message formats, please open an issue.



## Special Actions

There are three special actions present on all agents by default:

* `help`\
Sends back to the sender, a list of all actions on this agent. This is used by
agents for action discovery.

* `return`\
Receives the return value of the last action invoked on an agent.

* `error`\
Receives an error message if the last action invoked on an agent raised an
exception.

Override or extend these actions to customize the behavior of your agent.


## Access Control

Access policies are used to control when actions can be invoked by other agents.
All actions must declare an access policy like the following example:

```python
@access_policy(ACCESS_PERMITTED)
def _action__myaction(self):
    ...
```

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
def _request_permission(self, proposed_message: dict) -> bool:
    ...
```

Your implementation should inspect `proposed_message` and return a boolean
indicating whether or not to permit the action.

You can use this approach to protect against dangerous actions being taken. For
example if you allow terminal access, you may want to review commands before
they are invoked.


## The `WebApp` Class

The `WebApp` class is a simple web application that allows human users to
connect to the space and chat with agents. _Please note that this application is
for demonstration purposes, so it currently only supports a single user._

```python
web_app = WebApp(space,
                  port=os.getenv("WEB_APP_PORT"),
                  # NOTE We're hardcoding a single demo user for simplicity
                  demo_username="Dan")
web_app.start()
```

Note that the `WebApp` class is not an agent or space. It is implemented as a
separate process that adds users to the space dynamically as agents.

To see the web application, first run the demo, then open a browser and navigate
to `http://localhost:8080`.

The web UI hosts a simple chat interface that allows you to chat with agents in
the space. You can also invoke actions on agents using a custom "slash" syntax
for finer-grained commands.

To broadcast a message to all other agents in the space, simply type without a
format. The javascript client will automatically convert unformatted text to a
`"say"` action. For example, simply writing:

```
Hello, world!
```
... will be broadcast to all agents as a `"say"` action.

To send a point-to-point message to a specific agent, or to call actions other
than `"say"`, you can use the following format:
```
/action_name to:AgentID arg1:"value 1" arg2:"value 2"
```


## Adding OS Access with the `Host` class

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

Once added to a space, each agent may broadcast a `help` message to discover
other agents and actions that are available in the space.

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
[`OpenAICompletionAgent`](../examples/demo/agents/openai_completion_agent.py).


# Agent Callbacks

* `Agent._before_action`\
Called before an action is attempted. If an exception is raised in
`_before_action`, the action method and `_after_action` callbacks will not be
executed and the error will be returned to the sender.

* `Agent._after_action`\
Called after an action is attempted. Provides the original message, the return
value, and error if applicable. This method is called even if an exception is
raised in the action.

* `Agent._after_add`\
Called after an agent is added to a space and may begin sending/receiving
messages. Use this method to perform any initial setup necessary upon being
added to a space.

* `Agent._before_remove`\
Called before an agent is removed from a space and will no longer send/receive
messages. Use this method to perform any cleanup necessary before being removed
from a space.

* `Agent._request_permission`\
Called when an agent attempts to perform an action that requires permission.
This method should return `True` or `False` to indicate whether the action
should be allowed. A rejected action will be returned as a permission error to
the sender.


# Using AMQPSpace

To use AMQP for multi-process or networked communication, you can first swap the
`AMQPSpace` class for the `NativeSpace` class in the walkthrough above.

Then to take advantage of parallelism, you would also separate your agents into
multiple processes configured to use the same AMQP server.

For example, the following would separate the `Host` agent into its own
application:

```python
if __name__ == '__main__':

    # Create a space
    space = AMQPSpace()

    # Add a host agent to the space
    space.add(Host("Host"))

    # keep alive
    while True:
        time.sleep(1)
```

And the following would separate the `ChattyAI` agent into its own application:

```python
if __name__ == '__main__':

    # Create a space
    space = AMQPSpace()

    # Add a simple HF based chat agent to the space
    space.add(
        ChattyAI("Chatty",
                 model="EleutherAI/gpt-neo-125m"))

    # keep alive
    while True:
        time.sleep(1)
```

Make sure to reuse the same AMQP server and configuration for both applications.

Then you can run both applications at the same time, and the agents will be able
to connect and communicate with each other over AMQP. This approach allows you
to scale your agents across multiple processes or hosts, and avoids the
multithreading limitations of python's GIL.

See the [example application](../examples/demo/) for a full working example.


## Configuring Connectivity

When using AMQP, you have many options for connectivity that may affect your
experience. By default, the `AMQPSpace` class will read the following
environment variables and will otherwise use default settings.

```sh
AMQP_HOST
AMQP_PORT
AMQP_USERNAME
AMQP_PASSWORD
AMQP_VHOST
```

More options are possible like setting the heartbeat rate or enabling ssl, if
you provide your own `AMQPOptions` object when instantiating an `AMQPSpace`.
For example:

```python
space = AMQPSpace(
    amqp_options=AMQPOptions(
        hostname="localhost",
        port=5672,
        username="guest",
        password="guest",
        virtual_host="/",
        use_ssl=True,
        heartbeat=60))
```
