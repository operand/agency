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

### Using the `meta.id` Field

The `meta.id` field is used by the `original_message()` method during the
`handle_action_value()` and `handle_action_error()` callbacks to return the
original message that the value or error corresponds to.

If you make use of the `handle_action_value` and `handle_action_error`
callbacks, you should populate the `meta.id` field to allow this correlation.


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
