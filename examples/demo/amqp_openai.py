from agency.space import AMQPSpace
from agents.openai_completion_agent import OpenAICompletionAgent
from agents.openai_function_agent import OpenAIFunctionAgent
import os
import pika
import time


if __name__ == '__main__':

    # NOTE The following connection parameters are hardcoded to use a heartbeat
    # of 0. This is to workaround a bug that is currently being worked on. See:
    # https://github.com/operand/agency/issues/60
    space = AMQPSpace(
        pika_connection_params=pika.ConnectionParameters(
            heartbeat=0,
            host=os.environ.get('AMQP_HOST', 'localhost'),
            port=os.environ.get('AMQP_PORT', 5672),
            virtual_host=os.environ.get('AMQP_VHOST', '/'),
            credentials=pika.PlainCredentials(
                os.environ.get('AMQP_USERNAME', 'guest'),
                os.environ.get('AMQP_PASSWORD', 'guest'),
            ),
        )
    )

    # Add an OpenAI function API agent to the space
    space.add(
        OpenAIFunctionAgent("FunctionAI",
                            model="gpt-3.5-turbo-16k",
                            openai_api_key=os.getenv("OPENAI_API_KEY"),
                            # user_id determines the "user" role in the OpenAI chat API
                            user_id="Dan"))

    # Add another OpenAI agent based on the completion API
    space.add(
        OpenAICompletionAgent("CompletionAI",
            model="text-davinci-003",
            openai_api_key=os.getenv("OPENAI_API_KEY")))

    # keep alive
    while True:
        time.sleep(1)
