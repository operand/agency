# Demo Application Walkthrough

The following walkthrough will guide you through the basic concepts of Agency's
API, and how to use it to build your own agent systems.


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
