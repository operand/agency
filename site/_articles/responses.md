---
title: Responses and Synchronous Messaging
---

# Responses and Synchronous Messaging

Messages sent using `Agent.send()` are sent asynchronously. This is in line with
the expectations in an actor model.

Often though, we'd like to send a message to an agent and receive an associated
response. Agents have multiple options for doing this.


## Replying to Messages

The most basic response can be achieved simply using `Agent.send()` along with
`Agent.current_message()`. For example:

```py
class MyAgent(Agent):
    @action
    def say(self, content: str):
        ...
        self.send({
            "to": self.current_message()["from"], # reply to the sender
            "action": {
                "name": "say",
                "args": {
                    "content": "Hello!"
                }
            }
        })
```

The above will send the `say` action back to the original sender.


## Using `Agent.respond_with` for Value Responses

Often it's useful to send a _value_ back to the sender of a message, similar
to a return value from a function. In these cases, `Agent.respond_with` may be
used. Take the following two simple agents as an example.

```py
class MyAgent(Agent):
    @action
    def ping(self):
        self.respond_with("pong")

class SenderAgent(Agent):
    ...
    def handle_action_value(self, value):
        print(value)
```

When an instance of `SenderAgent` sends a `ping` action to `MyAgent`, the
`handle_action_value` callback on `SenderAgent` will be invoked with the value
`"pong"`.

Note that `respond_with()` may be called multiple times in a single action. Each
call will invoke the `handle_action_value` callback on the sender.


## Using `Agent.raise_with` for Error Responses

Similar to `Agent.respond_with`, `Agent.raise_with` may be used to send an
exception back to the sender of a message. For example:

```py
class MyAgent(Agent):
    @action
    def ping(self):
        self.raise_with(Exception("oops"))

class SenderAgent(Agent):
    ...
    def handle_action_error(self, error: ActionError):
        print(error.message)
```

In this example, an instance of `SenderAgent` sends a `ping` action to `MyAgent`.
The `handle_action_error` callback on `MyAgent` will be invoked with the exception
`ActionError("Exception: oops")`.

Similar to `respond_with`, `raise_with` may be called multiple times in a single
action. Each call will invoke the `handle_action_error` callback on the sender.

Note that when an action raises an exception, `raise_with` will be automatically
invoked for you, sending the exception back to the sender.


## Using `Agent.request()` for Synchronous Messaging

The `Agent.request()` method is a synchronous version of the `send()` method
that allows you to call an action and receive its return value or exception
synchronously without using the `handle_action_*` callbacks.

If the action responds with an error, an `ActionError` will be raised containing
the original error message.

Here's an example of how you might use `request()`:

```python
try:
    return_value = self.request({
      "to": "ExampleAgent",
      "action": {
        "name": "example_action",
        "args": {
          "content": "hello"
        }
      }
    }, timeout=5)
except ActionError as e:
    print(e.message)
```

Note that `request()` may not be called within the `after_add()` and
`before_remove()` callbacks, but may be used within actions or other callbacks.

Also notice the timeout value. The default is 3 seconds. Make sure to increase
this appropriately for longer running requests.
