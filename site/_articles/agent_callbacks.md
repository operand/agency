---
title: Agent Callbacks
---

# Agent Callbacks

The following list describes all available agent callbacks, with a link to their
API documentation. Please see the API docs for more detailed descriptions of
these callbacks.

### [`after_add`](../api_docs/agency/agent.html#Agent.after_add)
Called after an agent is added to a space, but before it begins processing
messages.

### [`before_remove`](../api_docs/agency/agent.html#Agent.before_remove)
Called before an agent is removed from a space and will no longer process more
messages.

### [`handle_action_value`](../api_docs/agency/agent.html#Agent.handle_action_value)
If an action method returns a value, this method will be called with the value.

### [`handle_action_error`](../api_docs/agency/agent.html#Agent.handle_action_error)
Receives any error messages from an action invoked by the agent.

### [`before_action`](../api_docs/agency/agent.html#Agent.before_action)
Called before an action is attempted.

### [`after_action`](../api_docs/agency/agent.html#Agent.after_action)
Called after an action is attempted.

### [`request_permission`](../api_docs/agency/agent.html#Agent.request_permission)
Called when an agent attempts to perform an action that requires permission.
