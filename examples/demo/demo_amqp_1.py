from agency.spaces.amqp_space import AMQPSpace
from agents.host import Host
from apps.gradio_app import demo, gradio_user


# Create the space instance
space = AMQPSpace()

# Add a host agent to the space, exposing access to the host system
space.add(Host("Host"))

# Connect the Gradio app user to the space
space.add(gradio_user)


if __name__ == '__main__':
    # Importing and launching the Gradio demo from this file allows us to use
    # the `gradio` command line for live reloading
    demo.launch()
