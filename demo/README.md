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
