---
title: Demo Application Walkthrough
nav_order: 0
---

# Demo Application Walkthrough

The following walkthrough will guide you through the basic concepts of Agency's
API, and how to use it to build a simple agent system, using the main demo
application as an example.

In this walkthrough, we'll be using the `MultiprocessSpace` class for connecting
agents. Usage is exactly the same as with any other space type, such as
`ThreadSpace` or `AMQPSpace`. The Space type determines both the concurrency and
communication implementation used for the space.

## Creating a Space and adding Agents

The following snippet, adapted from the [demo
application](https://github.com/operand/agency/tree/main/examples/demo/), shows
how to instantiate a space and add several agents to it.

The application includes `OpenAIFunctionAgent` which uses the OpenAI API, a
local LLM chat agent named `ChattyAI`, operating system access via the `Host`
agent, and a Gradio based chat application which adds its user to the space as
an agent as well.

```python
# Create the space instance
space = MultiprocessSpace()

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

# GradioApp adds its user as an agent named "User" to the space
GradioApp(space).demo().launch()
```

Notice that each agent is given a unique `id`. An agent's `id` is used to
identify the agent within the space. Other agents may send messages to `Chatty`
or `Host` by using their `id`'s, as we'll see later.

## Defining an Agent and its Actions

To create an Agent type, simply extend the `Agent` class. We'll use the
`ChattyAI` agent as an example.

```python
class ChattyAI(Agent):
    ...
```

Then to define actions, you define instance methods and use the `@action`
decorator. For example the following defines an action called `say` that takes a
single string argument `content`.

```python
@action
def say(self, content: str):
    """Use this action to say something to Chatty"""
    ...
```

By defining an action, we allow other agents in a common space to discover and
invoke the action on the agent. Other agents may invoke this action by sending a
message to `Chatty` as we'll see below.

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
            "content": response_content,
        }
    }
})
```

This demonstrates the basic idea of how to send a message to invoke an action
on another agent.

When an agent receives a message, it invokes the actions method, passing
`action.args` as keyword arguments.

So here, Chatty is invoking the `say` action on the sender of the original
message, passing the response as the `content` argument. This way, the original
sender and Chatty can have a conversation.

Note the use of the `current_message()` method. That method may be used during
an action to inspect the entire message which invoked the current action.


## Discovering Actions

At this point, we can demonstrate how action discovery works from the
perspective of an agent.

Each agent in the space implements a `help` action, which returns a dictionary
of their available actions.

To discover the other agents and their available actions across a space, an
agent may send the following message:
```python
self.send({
    "to": "*",
    "action": {
        "name": "help"
    }
})
```

Each agent in the space will respond with a dictionary of their available
actions.

To request help on a specific agent, simply address the agent's `id`:
```python
self.send({
    "to": "Chatty",
    "action": {
        "name": "help",
    }
})
```

To request help on a specific action, you may supply the action name as an
argument:
```python
self.send({
    "to": "Chatty",
    "action": {
        "name": "help",
        "args": {
            "action_name": "say"
        }
    }
})
```

## Adding an Intelligent Agent

Finally we can add an intelligent agent into the space and allow them to
discover and invoke actions.

To add the
[`OpenAIFunctionAgent`](https://github.com/operand/agency/tree/main/agency/agents/demo_agent.py)
to the environment:

```python
space.add(OpenAIFunctionAgent,
          "FunctionAI",
          model="gpt-3.5-turbo-16k",
          openai_api_key=os.getenv("OPENAI_API_KEY"),
          # user_id determines the "user" role in the chat API
          user_id="User")
```

If you inspect the implementation, you'll see that this agent uses the
`after_add` callback to immediately request help information from the other
agents in the space when added. It later uses that information to provide a list
of functions to the OpenAI function calling API.

This demonstrates how an agent may discover and invoke actions across a space.

## Running the Demo

This concludes the demo walkthrough. To try the demo, please jump to the
[examples/demo](https://github.com/operand/agency/tree/main/examples/demo/)
directory.
