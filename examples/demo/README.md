# Summary

This demo application is maintained as an experimental development environment
as well as a showcase of library features. You are encouraged to use the source
as a reference point for your own projects but be aware that the quality of the
demo application is proof-of-concept only and should not be considered
production ready.


# Running the demo

First ensure you have Docker installed on your system, then:

1. Run:

        git clone git@github.com:operand/agency.git
        cd agency/examples/demo
        cp .env.example .env

1. Open and populate the demo directory's `.env` file with appropriate
environment values.

1. Decide which application you'd like to run AMQP or native
    1. To run the AMQP based application:
        ```sh
        ...
        ```

    1. To run the native (single process) application:
        ```sh
        ...
        ```

1. Visit [http://localhost:8080](http://localhost:8080) and try chatting!
