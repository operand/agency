from agency.spaces.amqp_space import AMQPSpace
from agents.host import Host
from examples.demo.apps.gradio_app import GradioApp


# Create the space instance
space = AMQPSpace()

# Add a host agent to the space, exposing access to the host system
space.add(Host, "Host")

# Connect the Gradio app user to the space
space.add(GradioApp, "User")