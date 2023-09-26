---
title: Example Application Walkthrough
nav_order: 0
---

# Example Application Walkthrough

The following walkthrough will guide you through the basic concepts of Agency's
API, and how to use it to build a simple agent system.

In this walkthrough, we'll be using the `LocalSpace` class for connecting
agents. Usage is exactly the same as with `AMQPSpace`. The Space type used
determines the communication implementation used for the space.


## Creating a Space and adding Agents

The following snippet, adapted from the [demo
application](https://github.com/operand/agency/tree/main/examples/demo/), shows
how to instantiate a space and add several agents to it.

The application includes `OpenAIFunctionAgent` which uses the OpenAI API, a
local LLM chat agent named `ChattyAI`, the `Host` agent which allows access to
the host system, and a Gradio based chat application which allows its user to
communicate within the space as an agent as well.

```python
# Create the space instance
space = LocalSpace()

# Add a Host agent to the space, exposing access to the host system
space.add(Host, "Host")

# Add a local chat agent to the space
space.add(ChattyAI,
          "Chatty",
          model="EleutherAI/gpt-neo-125m")

# Add an OpenAI function API agent to the space
space.add(OpenAIFunctionAgent,
          "FunctionAI",
          model="gpt-3.5-turbo-16k",
          openai_api_key=os.getenv("OPENAI_API_KEY"),
          # user_id determines the "user" role in the OpenAI chat API
          user_id="User")

# Connect the Gradio user to the space
gradio_user = space.add_foreground(GradioUser, "User")

# Launch the gradio UI allowing the user to communicate
gradio_user.demo().launch()
```

Let's break this example down step by step.


## Agent `id`s

Notice first that each agent is given a string `id` like `"Host"` or `"Chatty"`.

An agent's `id` is used to uniquely identify the agent within the space.  Other
agents may send messages to `Chatty` or `Host` by using their `id`'s, as we'll
see later.


## Defining an Agent and its Actions

To define an Agent type like `ChattyAI`, simply extend the `Agent` class. For
example:

```python
class ChattyAI(Agent):
    ...
```

__Actions__ are publicly available methods that agents expose within a space,
and may be invoked by other agents.

To define actions, you simply define instance methods on the Agent class, and
use the `@action` decorator. For example the following defines an action called
`say` that takes a single string argument `content`.

```python
@action
def say(self, content: str):
    """Use this action to say something to Chatty"""
    ...
```

Other agents may invoke this action by sending a message to `Chatty` as we'll
see below.

## Invoking Actions

When agents are added to a space, they may send messages to other agents to
invoke their actions.

An example of invoking an action can be seen here, taken from the
`ChattyAI.say()` implementation.

```python
...
self.send({
    "to": self.current_message()['from'], # reply to the sender
    "action": {
        "name": "say",
        "args": {
            "content": "Hello from Chatty!",
        }
    }
})
```

This demonstrates the basic idea of how to send a message to invoke an action
on another agent.

When an agent receives a message, it invokes the actions method, passing
`action.args` as keyword arguments to the method.

So here, Chatty is invoking the `say` action on the sender of the current
message that they received. This simple approach allows the original sender and
Chatty to have a conversation using only the `say` action.

Note the use of `current_message()`. That method may be used during an action to
inspect the entire message which invoked the current action.


## Discovering Agents and their Actions

At this point, we can demonstrate how agent and action discovery works from the
perspective of an agent.

All agents implement a `help` action, which returns a dictionary of their
available actions for other agents to discover.

To request `help` information, an agent may send something like the
following:

```python
self.send({
    "to": "Chatty"
    "action": {
        "name": "help"
    }
})
```

`"Chatty"` will respond by returning a message with a dictionary of available
actions. For example, if `"Chatty"` implements a single `say` action as shown
above, it will respond with:

```js
{
    "say": {
      "description": "Use this action to say something to Chatty",
      "args": {
          "content": {
              "type": "string",
              "description": "What to say to Chatty"
          },
      },
    }
}
```

This is how agents may discover available actions on other agents.


### Broadcasting `help`

But how does an agent know which agents are present in the space?

To discover all agents in the space, an agent can broadcast a message using the
special id `*`. For example:

```py
self.send({
    "to": "*",
    "action": {
        "name": "help",
    }
})
```

The above will broadcast the `help` message to all agents in the space, who will
individually respond with their available actions. This way, an agent may
discover all the agents in the space and their actions.

To request help on a specific action, you may supply the action name as an
argument:

```python
self.send({
    "to": "*",
    "action": {
        "name": "help",
        "args": {
            "action_name": "say"
        }
    }
})
```

The above will broadcast the `help` action, requesting help specifically on the
`say` action.

Note that broadcasts may be used for other messages as well. See [the messaging
article](https://createwith.agency/articles/messaging) for more details.


## Adding an Intelligent Agent

Now that we understand how agents communicate and discover each other, let's
add an intelligent agent to the space which can use these abilities.

To add the `OpenAIFunctionAgent` to the space:

```python
space.add(OpenAIFunctionAgent,
          "FunctionAI",
          model="gpt-3.5-turbo-16k",
          openai_api_key=os.getenv("OPENAI_API_KEY"),
          # user_id determines the "user" role in the chat API
          user_id="User")
```

If you inspect [the
implementation](https://github.com/operand/agency/tree/main/agency/agents/demo_agent.py)
of `OpenAIFunctionAgent`, you'll see that this agent uses the `after_add`
callback to immediately request help information from the other agents in the
space when added. It later uses that information to provide a list of functions
to the OpenAI function calling API, allowing the LLM to see agent actions as
functions it may invoke.

In this way, the `OpenAIFunctionAgent` can discover other agents in the space
and interact with them intelligently as needed.


## Adding a User Interface

There are two general approaches you might follow to implement a user-facing
application which interacts with a space:

1. You may represent the user-facing application as an individual
    agent, having it act as a "liason" between the user and the space. User
    intentions can be mapped to actions that the "liason" agent can invoke on
    behalf of the user. In this approach, users would not need to know the
    details of the underlying communication.

2. Individual human users may be represented as individual agents in a space.
    This approach allows your application to provide direct interaction with
    agents by users and has the benefit of allowing actions to be invoked
    directly, enabling more powerful interactive possibilities.
    
    This is the approach taken in [the demo
    application](https://github.com/operand/agency/tree/main/examples/demo).

    For example, the demo UI (currently implemented in
    [Gradio](https://gradio.app)) allows users to directly invoke actions via a
    "slash" syntax similar to the following:

    ```
    /Chatty.say content:"Hello"
    ```

    This allows the user to work hand-in-hand with intelligent agents, and is
    one of the driving visions behind Agency's design.
    
    See the [demo
    application](https://github.com/operand/agency/tree/main/examples/demo/) for
    a full working example of this approach.


## Next Steps

This concludes the example walkthrough. To try out the working demo, please jump
to the
[examples/demo](https://github.com/operand/agency/tree/main/examples/demo/)
directory.
