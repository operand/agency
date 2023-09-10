# Summary

> ❗️Please note, this application is no longer actively supported but is kept
here for reference. The following directions may be outdated and no longer work.
If you have any questions or need assistance please reach out.

This directory showcases an example Gradio application integrated with Agency.

The app uses the [`Chatbot`](https://www.gradio.app/docs/chatbot) gradio
component, and allows chatting and sending commands to any connected agent.


## Example Classes

The demo includes the following two `Agent` classes by default:

* `OpenAIFunctionAgent` - An LLM agent that uses the OpenAI function calling API
* `Host` - An agent that exposes operating system access to the host system

See more agent examples are located under the [./agents](./agents/) directory.


## Running the Gradio Demo

This demo uses docker-compose for orchestration. Configuration is included for
running the app using the different space types. To run the app:

1. Ensure you have Docker installed on your system.

1. Run:

        git clone git@github.com:operand/agency.git
        cd agency/examples/gradio_demo
        cp .env.example .env

1. Open and populate the `.env` file with appropriate values.

1. Start the application.

      To run the single-container `MultiprocessSpace` application:
      ```sh
      ./demo run multiprocess
      ```

      To run the single-container `ThreadSpace` application:
      ```sh
      ./demo run threaded
      ```

      To run the multi-container `AMQPSpace` application:
      ```sh
      ./demo run amqp
      ```

1. Visit [http://localhost:8080](http://localhost:8080) and try it out!


## The Gradio UI

The Gradio UI is a [`Chatbot`](https://www.gradio.app/docs/chatbot) based
application.

It is defined in
[examples/gradio_demo/app/gradio_app.py](https://github.com/operand/agency/tree/main/examples/gradio_demo/app/gradio_app.py)
and simply needs to be imported and used like so:

```python
from examples.demo.apps.gradio_app import GradioApp
...
demo = GradioApp(space).demo()
demo.launch()
```

The Gradio application automatically adds its user to the space as an agent,
allowing you (as that agent) to chat with other agents.

The application converts plain text input into a `say` action which is broadcast
to the other agents in the space. For example, simply writing:

```
Hello, world!
```

will invoke the `say` action on all other agents in the space, passing the
`content` argument as `Hello, world!`. Any agents which implement a `say` action
will receive and process this message.


### Gradio App - Command Syntax

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
