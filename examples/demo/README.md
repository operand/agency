# Summary

This demo application is maintained as an experimental development environment
as well as a showcase of library features. You are encouraged to use the source
as a reference point but beware that the quality is proof-of-concept only and
should not be considered production ready.


# Running the demo

1. Ensure you have Docker installed on your system.

1. Run:

        git clone git@github.com:operand/agency.git
        cd agency/examples/demo
        cp .env.example .env

1. Open and populate the `.env` file with appropriate values.

1. Start the application.

      To run the single-container `NativeSpace` application:
      ```sh
      demo run native
      ```

      To run the multi-container `AMQPSpace` application:
      ```sh
      demo run amqp
      ```

1. Visit [http://localhost:8080](http://localhost:8080) and try it out!
