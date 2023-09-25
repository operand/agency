---
title: Messaging
---

# Messaging

The following details cover the message schema and other messaging behavior.

## Message Schema

All messages are validated upon sending and must conform to the message schema.

Note that when sending, you normally do not supply the entire structure. The
`meta.id`, `meta.parent_id`, and `from` fields are automatically populated for
you.

The full message schema is summarized by this example:

```python
{
    "meta": {
        "id": "a string to identify the message",
        "parent_id": "meta.id of the parent message, if any",
        "anything": "else here",
    },
    "from": "TheSender",
    # The following fields must be specified when sending
    "to": "TheReceiver",
    "action": {
        "name": "the_action_name",
        "args": {
            "the": "args",
        }
    }
}
```

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

## The `to` and `from` Fields

The `to` and `from` fields are used for addressing messages.

All messages require the `to` field to be specified. The `to` field should be
the `id` of an agent in the space (point-to-point) or the special id `*` for
a broadcast (see below).

The `from` field is automatically populated for you when sending.

## The `action` Field

The action field contains the body of the action invocation. It carries the
action `name` and the arguments to pass as a dictionary object called `args`.

## The `meta` Field

The `meta` field may be used to store arbitrary key-value metadata about the
message. It is optional to define, though the `meta.id` and `meta.parent_id`
fields will be populated automatically by default.

Example uses of the `meta` field include:

* Storing "thoughts" associated with an action. This is a common pattern used
  with LLM agents. For example, an LLM agent may send the following message:
  ```python
  {
      "meta": {
          "thoughts": "I should say hello to everyone",
      },
      "to": "*",
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

## Broadcasting Messages

Sending a message to the special id `*` will broadcast the message to all agents
in the space.

By default, agents receive their own broadcasts, but you may change this
behavior with the `receive_own_broadcasts` argument when creating the agent. For
example:

```python
my_agent = MyAgent("MyAgent", receive_own_broadcasts=False)
```

## Messaging to Non-Existent Agents or Actions

If you send a message to a non-existent agent `id`, it will silently fail. This
is in line with the actor model.

If you send a message to an existent agent, but specify a non-existent action,
you will receive an `error` response which you may handle in the
`handle_action_error` callback.

If you send a _broadcast_ that specifies a non-existent action on some agents,
those agents will silently ignore the error.
