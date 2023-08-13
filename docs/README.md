# Documentation

## Table of Contents

* [Example Application Walkthrough](#example-application-walkthrough)
* [Agent Implementation](#agent-implementation)
* [Messaging](#messaging)
* [Using AMQPSpace](#using-amqpspace)


# Example Application Walkthrough

The following walkthrough will guide you through the basic concepts of
Agency's API, and how to use it to build your own agent systems.


## Creating an Agency Application

The snippet below is an example of a simple Agency application.

For this walkthrough, we'll be using the `NativeSpace` class for connecting
agents. Usage is exactly the same as with the `AMQPSpace` class, except that a
`NativeSpace` is for agents in the same process, and does not require an AMQP
server.

The following application includes the `OpenAIFunctionAgent` class, a
transformers based chat agent named `ChattyAI`, operating system access, and a
Gradio based web application hosted at `http://localhost:8080`, all integrated
with the following implementation.


```python

# Create a space
space = NativeSpace()

# Add a simple HF based chat agent to the space
space.add(
    ChattyAI("Chatty",
             model="EleutherAI/gpt-neo-125m"))

# Add a host agent to the space, exposing access to the host system
space.add(Host("Host"))

# Add an OpenAI agent to the space
space.add(
    OpenAIFunctionAgent("FunctionAI",
                        model="gpt-3.5-turbo-16k",
                        openai_api_key=os.getenv("OPENAI_API_KEY"),
                        # user_id determines the "user" role in the OpenAI chat API
                        user_id="User"))

# Connect the Gradio app user to the space
space.add(gradio_user)

# Launch Gradio UI
demo.launch()
```


## Creating a `Space` and adding an `Agent`

```python
space = NativeSpace()
space.add(ChattyAI("Chatty", model="EleutherAI/gpt-neo-125m"))
```

This creates a space and adds a new `ChattyAI` instance to it, with the `id` of
`Chatty`.

An agent's `id` is used to identify the agent within the space. Other agents may
send messages to `Chatty` by using that `id`, as we'll see later.

`id`'s are unique. Two agents may not declare the same `id` within the same
space.


## Defining Actions

Looking at `ChattyAI`'s source code, you'll see that it is a subclass of
`Agent`, and that it exposes a single action called `say`.

The following is a typical action method signature taken from `ChattyAI`.

```python
@action
def say(self, content: str):
    """Use this action to say something to Chatty"""
    ...
```

The decorator `@action` is used to indicate that this is an action that can be
invoked by other agents in their space. The method name `say` is the name of the
action by default.

The `say` action takes a single string argument `content`. This action is
intended to allow other agents to chat with Chatty, as expressed in its
docstring.

When `ChattyAI` receives a `say` action, it will generate a response using its
underlying language model, and return the result to the sender.


## Invoking Actions

An example of invoking an action can be seen here, taken from the same
`ChattyAI.say()` method.

```python
...
self.send({
    "to": self._current_message['from'],
    "action": {
        "name": "say",
        "args": {
            "content": response_content,
        }
    }
})
```

This demonstrates the basic idea of how to invoke an action on another agent.

When an agent receives a message, it invokes the action method specified by the
`action.name` field of the message, passing the `action.args` dictionary to the action
method as keyword arguments.

So here Chatty is invoking the `say` action on the sender of the original
message, passing the response as the `content` argument. This way, the original
sender and Chatty can have a conversation.

Note the use of the `_current_message` variable. That variable may be inspected
during an action to access the entire incoming message which invoked the action.


## Access Control

Access policies may be used to control when actions can be invoked by agents.
All actions may declare an access policy like the following example:

```python
@action(access_policy=ACCESS_PERMITTED)
def my_action(self):
    ...
```

An access policy can currently be one of three values:

- `ACCESS_PERMITTED` - (Default) Permits any agent to use that action at
any time.
- `ACCESS_DENIED` - Prevents access to that action.
- `ACCESS_REQUESTED` - Prompts the receiving agent for permission when access is
attempted. Access will await approval or denial.

If `ACCESS_REQUESTED` is used, the receiving agent will be prompted to approve
the action via the `request_permission()` callback method.

If any actions declare a policy of `ACCESS_REQUESTED`, you must implement the
`request_permission()` method with the following signature in order to receive
permission requests.

```python
def request_permission(self, proposed_message: dict) -> bool:
    ...
```

Your implementation should inspect `proposed_message` and return a boolean
indicating whether or not to permit the action.

You can use this approach to protect against dangerous actions being taken. For
example if you allow terminal access, you may want to review commands before
they are invoked.


## The Gradio UI

The Gradio UI is a [`Chatbot`](https://www.gradio.app/docs/chatbot) based
application used for development and demonstration purposes, that allows human
users to connect to a space and chat with the connected agents.

It is defined in
[examples/demo/apps/gradio_app.py](../examples/demo/apps/gradio_app.py) and
simply needs to be imported and used like so:

```python
from apps.gradio_app import demo, gradio_user
...
space.add(gradio_user)
...
demo.launch()
```

You can also invoke actions on agents using a custom "slash" syntax. To
broadcast a message to all other agents in the space, simply type without a
format. The client will automatically convert unformatted text to a `say`
action. For example, simply writing:

```
Hello, world!
```
will be broadcast to all agents as a `say` action.

To send a point-to-point message to a specific agent, or to call actions other
than `say`, you can use the following format:
```
/agent_id.action_name arg1:"value 1" arg2:"value 2"
```


## Adding OS Access with the `Host` class

```python
space.add(Host("Host"))
```

The `Host` class demonstrates allowing access to the host operating system where
the python application is running. It exposes actions such as `read_file` and
`shell_command` which allow other agents to interact with the host.

This class is a good example of one with potentially dangerous actions that must
be accessed with care. You'll notice that all the methods in the `Host` class
have been given the access policy:

```python
@action(access_policy=ACCESS_REQUESTED)
...
```

Thanks to the implementation of `request_permission()` in the `Host` class, all
actions on the host will require a confirmation from the terminal where the
application is being run.

Note that this implementation of `request_permission()` is just one possibility.
We could have implemented for example, a phone notification for a human to
review from elsewhere.


## Discovering Actions

At this point, we can demonstrate how action discovery works from the
perspective of a human user of the web application.

Once added to a space, each agent may broadcast a `help` message to discover
other agents and actions that are available in the space.

So a person using the chat UI can discover all available actions by typing:

```
/*.help
```

Note the use of `*`. This is a reserved name for broadcasting messages to all
agents in the space.

So the above command will broadcast a `help` action to all other agents, who
will individually respond with a dictionary of their available actions.

To invoke an action (like `help`) on a specific agent, you can use the following
syntax:

```
/Host.help action_name:"say"
```

Note the agent name used before the action name. In this case, the `help` action
takes an argument called `action_name`. So this will send the `help` action to
the `Host` agent requesting information on the `say` action.


## Adding an Intelligent Agent

Lastly we can add an intelligent agent into the space.

To add the [`OpenAIFunctionAgent`](../agency/agents/demo_agent.py) class to the
environment:
```python
space.add(
    OpenAIFunctionAgent("FunctionAI",
        model="gpt-3.5-turbo-16k",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        # user_id determines the "user" role in the chat API
        user_id="User"))
```

For more agent examples that you can try, see the
[`examples/demo/agents/`](../examples/demo/agents/) directory.

That concludes the example walkthrough. To try the demo application, please jump
to the [examples/demo/](../examples/demo/) directory.


# Agent Implementation

To create an agent, extend the `Agent` class.

```python
class MyAgent(Agent):
    ...
```

## Defining Actions

Actions are simply instance methods decorated with `@action`. The `@action`
decorator takes the following keyword arguments:

* `name`: The name of the action. Defaults to the method name
* `help`: The description of the action. Defaults to autogenerated object
* `access_policy`: The access policy of the action. Defaults to `ACCESS_PERMITTED`

The `help` attribute may be used for describing the given action when the `help`
action is called.

Below is an example of the help information automatically generated by default
from the `@action` decorator arguments and the method's signature.

```python
{
  "shell_command": {
    "description": "Execute a shell command",
    "args": {
      "command": {
        "type": "string"
        "description": "The command to execute"
      }
    },
    "returns": {
      "type": "string"
      "description": "The output of the command"
    }
  },
  ...
}
```

The following example shows how the above help information can be defined using
a docstring that follows the [Google style
guide](https://github.com/google/styleguide/blob/gh-pages/pyguide.md#383-functions-and-methods):

```python
@action
def shell_command(self, command: str) -> str:
    """
    Execute a shell command

    Args:
        command (str): The command to execute

    Returns:
        str: The output of the command
    """
```

The action name is determined by the method name.

Types are determined by looking at the docstring and the signature, with the
signature type hint taking precedence.

Action and argument descriptions are parsed from the docstring.


### Overriding Help Information

The default help data structure could be customized as well:

```python
@action(
    help={
      "You": "can define",
      "any": {
        "structure": ["you", "want", "here."]
      }
    }
)
def say(self, content: str) -> None:
```

If a `help` object is provided to the decorator, it overrides the generated
object entirely. You can use this to experiment with different help information
schemas.

Merging the two objects, for example in order to only override specific fields,
is not (yet) supported. Let me know if you'd like to see this feature developed.


## Special Actions

There are three special actions present on all agents by default:

Override or extend these actions to customize the behavior of your agent.

* `help`\
Returns a list of all actions on this agent. This is used by agents for action
discovery. You normally do not need to implement this method but you may do so
for example, to control which actions are returned to other agents.

* `response`\
If an action method returns a value, this method will be called with the value.

* `error`\
Receives any error messages from an action invoked by the agent.


## Callbacks

The following is the list of agent callbacks you may implement.

* `before_action`\
Called before an action is attempted. If an exception is raised in
`before_action`, the action method and `after_action` callbacks will not be
executed and the error will be returned to the sender.

* `after_action`\
Called after an action is attempted. Provides the original message, the return
value, and error if applicable. This method is called even if an exception is
raised in the action.

* `after_add`\
Called after an agent is added to a space and may begin sending/receiving
messages. Use this method to perform any initial setup necessary upon being
added to a space.

* `before_remove`\
Called before an agent is removed from a space and will no longer send/receive
messages. Use this method to perform any cleanup necessary before being removed
from a space.

* `request_permission`\
Called when an agent attempts to perform an action that requires permission.
This method should return `True` or `False` to indicate whether the action
should be allowed. A rejected action will be returned as a permission error to
the sender.


# Messaging

## Schema

All messages are validated upon sending and must conform to the message schema.

The full message schema is summarized by this example:

```python
{
    "id": "some optional id",
    "meta": {
        "an": "optional",
        "object": {
            "for": "metadata",
        }
    },
    "from": "the sender's id",
    "to": "the receiver's id",
    "action": {
        "name": "the_action_name",
        "args": {
            "the": "args",
        }
    }
}
```

Note that when sending, you may not need to supply this entire structure. The
`id` and `meta` fields are optional. Additionally, the `from` field is
automatically populated for you in the `send()` method.

A minimal example of calling `Agent.send()` with only the required fields would
look like:

```python
my_agent.send({
    "to": "some_agent",
    "action": {
        "name": "say",
        "args": {
            "content": "Hello, world!"
        }
    }
})
```

See [agency/schema.py](../agency/schema.py) for the pydantic model definition
used for validation.


## Using the `id` Field

The message `id` field may be used to correlate an incoming message with a
previously sent message, for example to associate response data with the
request.

The `id` field is _not_ populated by default. To use the `id` field, you must
explicitly specify it in the outgoing message object. You can set it to any
string identifier you choose.

By default, the `id` field is used by the `response` and `error` actions. If a
`response` or `error` is received, the `original_message_id` argument will be
populated with the `id` of the original message.

For example, say we have an `add` action which returns the sum of its arguments.
```python
@action
def add(self, a: int, b: int) -> int:
    return a + b
```

Sending the following message:
```python
my_agent.send({
    "id": "a custom message id",
    "to": "calculator_agent",
    "action": {
        "name": "add",
        "args": {
            "a": 1,
            "b": 2
        }
    }
})
```

... would result in a subsequent `response` message like the following:
```json
{
    "from": "calculator_agent",
    "to": "my_agent",
    "action": {
        "name": "response",
        "args": {
            "data": 3,
            "original_message_id": "a custom message id"
        }
    }
}
```

Notice the `original_message_id` argument populated with the `id` of the
original message.


## Using the `meta` Field

The `meta` field may be used to store arbitrary key-value metadata about the
message. It is entirely optional. Possible uses of the `meta` field include:

* Storing "thoughts" associated with an action. This is a common pattern used
  with LLM agents. For example, an LLM agent may send the following message:
  ```python
  {
      "meta": {
          "thoughts": "I should say hello to everyone",
      },
      "to": "my_agent",
      "action": {
          "name": "say",
          "args": {
              "content": "Hello, world!"
          }
      }
  }
  ```

* Storing timestamps associated with an action. For example:
  ```python
  {
      "meta": {
          "timestamp": 12345,
      },
      ...
  }
  ```

These are just a couple ideas to illustrate the use of the `meta` field.  


## Broadcast vs Point-to-Point

All messages require the `to` field to be specified. The `to` field should be
the `id` of an agent in the space (point-to-point) or the special id `*` to
broadcast the message to all agents in the space.

By default, agents receive their own broadcasts, but you may change this
behavior with the `receive_own_broadcasts` argument when creating the agent. For
example:

```python
my_agent = MyAgent("MyAgent", receive_own_broadcasts=False)
```


## Non-Existent Agents or Actions

If you send a message to a non-existent agent, it will silently fail.

If you send a message to an existent agent, but specify a non-existent action,
you will receive an `error` message in response.

Broadcasts which specify a non-existent action are silently ignored, so that
broadcasts do not result in many error messages.


# Using AMQPSpace

To use AMQP for multi-process or networked communication, you can simply swap
the `AMQPSpace` class for the `NativeSpace` class.

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


## Configuring AMQP Connectivity

By default, the `AMQPSpace` class will read the following environment variables
and will otherwise use default settings.

```sh
AMQP_HOST
AMQP_PORT
AMQP_USERNAME
AMQP_PASSWORD
AMQP_VHOST
```

You may also customize the full list of options if you provide your own
`AMQPOptions` object when instantiating an `AMQPSpace`. For example:

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
