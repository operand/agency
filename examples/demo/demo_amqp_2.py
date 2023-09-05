import os

from agents.openai_function_agent import OpenAIFunctionAgent

from agency.spaces.amqp_space import AMQPSpace

if __name__ == "__main__":

    # Create the space instance
    space = AMQPSpace()

    # Add an OpenAI function API agent to the space
    space.add(OpenAIFunctionAgent,
              "FunctionAI",
              model="gpt-3.5-turbo-16k",
              openai_api_key=os.getenv("OPENAI_API_KEY"),
              # user_id determines the "user" role in the OpenAI chat API
              user_id="User")
