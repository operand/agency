---
title: Access Control
---

# Access Control

> ❗️Access control is experimental. Please share your feedback.

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
