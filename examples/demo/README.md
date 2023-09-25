# Summary

This demo application is maintained as an experimental development environment
and a showcase for library features. You are encouraged to use the source as a
reference but beware that the quality is intended to be proof-of-concept only.


## Example Classes

By default the demo includes the following two `Agent` classes:

* `OpenAIFunctionAgent` - An LLM agent that uses the OpenAI function calling API
* `Host` - An agent that exposes operating system access to the host system

More agent examples are located under the [./agents](./agents/) directory.


## Running the demo

The demo application uses docker-compose for orchestration. Configuration is
included for running the demo using the different space types. To run the demo:

1. Ensure you have Docker installed on your system.

1. Run:

        git clone git@github.com:operand/agency.git
        cd agency/examples/demo
        cp .env.example .env

1. Open and populate the `.env` file with appropriate values.

1. Start the application.

      To run the `LocalSpace` application:
      ```sh
      ./demo run local
      ```

      To run the `AMQPSpace` application:
      ```sh
      ./demo run amqp
      ```

1. Visit [http://localhost:8080](http://localhost:8080) and try it out!


## The Gradio UI

The Gradio UI is a [`Chatbot`](https://www.gradio.app/docs/chatbot) based
application used for development and demonstration.

It is defined in
[examples/demo/apps/gradio_app.py](https://github.com/operand/agency/tree/main/examples/demo/apps/gradio_app.py)
and simply needs to be imported and used like so:

```python
from examples.demo.apps.gradio_app import GradioApp
...
demo = GradioApp(space).demo()
demo.launch()
```

The Gradio application automatically adds its user (you) to the space as an
agent, allowing you to chat and invoke actions on the other agents.

The application is designed to convert plain text input into a `say` action
which is broadcast to the other agents in the space. For example, simply
writing:

```
Hello, world!
```

will invoke the `say` action on all other agents in the space, passing the
`content` argument as `Hello, world!`. Any agents which implement a `say` action
will receive and process this message.


## Gradio App - Command Syntax

The Gradio application also supports a command syntax for more control over
invoking actions on other agents.

For example, to send a point-to-point message to a specific agent, or to call
actions other than `say`, you can use the following format:

```
/agent_id.action_name arg1:"value 1" arg2:"value 2"
```

A broadcast to all agents in the space is also supported using the `*` wildcard.
For example, the following will broadcast the `say` action to all other agents,
similar to how it would work without the slash syntax:

```
/*.say content:"Hello, world!"
```
