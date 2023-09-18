---
title: Synchronous Messaging
---

# Synchronous Messaging

The `Agent.request()` method is a synchronous version of the `send()` method
that allows you to call an action and receive its return value or exception
synchronously. If the action responds with an error, an `ActionError` will be
raised containing the original error message.

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

Note that `request()` may not be called during the `after_add()` and
`before_remove()` callbacks, but may be used within actions or other callbacks.

Also notice the timeout value. The default is 3 seconds. Make sure to increase
this appropriately for longer running actions.
