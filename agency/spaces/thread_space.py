import queue
import threading
import time
import traceback
from typing import Dict, Type

from agency.agent import Agent, _QueueProtocol
from agency.logger import log
from agency.schema import Message, validate_message
from agency.space import Space


class _AgentThread():
    def __init__(
            self,
            agent_type: Type[Agent],
            agent_id: str,
            agent_kwargs: Dict,
            inbound_queue: _QueueProtocol,
            outbound_queue: _QueueProtocol):
        self.agent_type: Type[Agent] = agent_type
        self.agent_id: str = agent_id
        self.agent_kwargs: Dict = agent_kwargs
        self.inbound_queue: _QueueProtocol = inbound_queue
        self.outbound_queue: _QueueProtocol = outbound_queue
        self.__started = threading.Event()
        self.__stopping = threading.Event()

    def start(self):
        def _thread(exception_info):
            try:
                agent = self.agent_type(
                    self.agent_id,
                    outbound_queue=self.outbound_queue,
                    **self.agent_kwargs,
                )
                agent.after_add()
                log("info", f"{agent.id()} added to space")
                agent._is_processing = True
                self.__started.set()
                while not self.__stopping.is_set():
                    time.sleep(0.001)
                    try:
                        message = self.inbound_queue.get(block=False)
                        agent._receive(message)
                    except queue.Empty:
                        pass
            except KeyboardInterrupt:
                pass
            except Exception as e:
                log("error", f"{self.agent_id} thread failed with exception", traceback.format_exc())
                exception_info["exception"] = e
            finally:
                agent._is_processing = False
                agent.before_remove()
                log("info", f"{agent.id()} removed from space")

        exception_info = {"exception": None}
        self.__thread = threading.Thread(
            target=_thread, args=(exception_info,), daemon=True)
        self.__thread.start()

        if not self.__started.wait(timeout=10):
            # it couldn't start clean up and raise an exception
            self.stop()
            if exception_info["exception"] is not None:
                raise exception_info["exception"]
            else:
                raise Exception("Thread could not be started.")

    def stop(self):
        self.__stopping.set()
        self.__thread.join(timeout=10)
        if self.__thread.is_alive():
            raise Exception("Thread could not be stopped.")


class ThreadSpace(Space):
    """
    A Space implementation that uses the threading module.

    This Space type is recommended for testing or simple applications.
    """

    def __init__(self):
        self.__agent_threads: Dict[str, _AgentThread] = {}
        router_thread = threading.Thread(
            target=self.__router_thread, daemon=True)
        router_thread.start()

    def __router_thread(self):
        """
        Processes and routes outbound messages for all agents
        """
        while True:
            time.sleep(0.001)
            for agent_thread in list(self.__agent_threads.values()):
                outbound_queue = agent_thread.outbound_queue
                try:
                    # process one message per agent per loop
                    message = outbound_queue.get(block=False)
                    self._route(message)
                except queue.Empty:
                    pass

    def _route(self, message: Message):
        message = validate_message(message)
        recipient_threads = [
            agent_thread
            for agent_thread in list(self.__agent_threads.values())
            if message["to"] == agent_thread.agent_id or message["to"] == "*"
        ]
        for recipient_thread in recipient_threads:
            recipient_thread.inbound_queue.put(message)

    def add(self, agent_type: Type[Agent], agent_id: str, **agent_kwargs):
        if agent_id in self.__agent_threads.keys():
            raise ValueError(f"Agent id already exists: '{agent_id}'")

        try:
            self.__agent_threads[agent_id] = _AgentThread(
                agent_type=agent_type,
                agent_id=agent_id,
                agent_kwargs=agent_kwargs,
                inbound_queue=queue.Queue(),
                outbound_queue=queue.Queue(),
            )
            self.__agent_threads[agent_id].start()

        except:
            # clean up if an error occurs
            self.remove(agent_id)
            raise

    def remove(self, agent_id: str):
        agent_thread = self.__agent_threads[agent_id]
        agent_thread.stop()
        del self.__agent_threads[agent_id]

    def remove_all(self):
        agent_ids = list(self.__agent_threads.keys())
        for agent_id in agent_ids:
            self.remove(agent_id)
