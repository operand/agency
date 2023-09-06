---
title: Messaging Schema
---

# Messaging Schema

All messages are validated upon sending and must conform to the message schema.

The full message schema is summarized by this example:

```python
{
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
`meta` field is entirely optional. Additionally, the `from` field is
automatically populated for you in the `send()` and `request()` methods.

An example of calling `Agent.send()` with only the minimum fields would look
like:

```python
self.send({
    "to": "some_agent",
    "action": {
        "name": "say",
        "args": {
            "content": "Hello, world!"
        }
    }
})
```

See
[agency/schema.py](https://github.com/operand/agency/tree/main/agency/schema.py)
for the pydantic model definition used for validation.


## The `meta` Field

TODO


### Using the `meta.id` Field

The `meta.id` field is used to correlate an incoming responses with a previously
sent message, for example to associate response data with the request.

The `meta.id` field is _not_ populated by default. To use the `id` field, you
must specify it in the outgoing message object. You can set it to any string
identifier you choose.





TODO



---




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
        "name": "[response]",
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

Broadcasts which specify a non-existent action are silently ignored.
