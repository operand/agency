from agents.host import Host

from agency.spaces.amqp_space import AMQPSpace
from examples.demo.apps.gradio_app import GradioApp

if __name__ == "__main__":

    # Create the space instance
    space = AMQPSpace()

    # Add a host agent to the space, exposing access to the host system
    space.add(Host, "Host")

    # GradioApp adds its own user to the space in its constructor
    demo = GradioApp(space).demo()
    demo.launch()
