import multiprocessing
import queue
import threading
import time
from multiprocessing import Event, Process
from typing import Dict, Type

from agency.agent import Agent, QueueProtocol
from agency.schema import Message, validate_message
from agency.space import Space

multiprocessing.set_start_method('spawn', force=True)


class _AgentProcess():
    def __init__(
            self,
            agent_type: Type[Agent],
            agent_id: str,
            agent_kwargs: Dict,
            inbound_queue: QueueProtocol,
            outbound_queue: QueueProtocol):
        self.__agent_type: Type[Agent] = agent_type
        self.__agent_id: str = agent_id
        self.__agent_kwargs: Dict = agent_kwargs
        self.inbound_queue: QueueProtocol = inbound_queue
        self.outbound_queue: QueueProtocol = outbound_queue

    def start(self):
        self.__started = Event()
        self.__stopping = Event()
        self.__process = Process(
            target=self._process,
            args=(
                self.__agent_type,
                self.__agent_id,
                self.__agent_kwargs,
                self.inbound_queue,
                self.outbound_queue,
                self.__started,
                self.__stopping,
            )
        )
        self.__process.start()

        if not self.__started.wait(timeout=10):
            # it couldn't start, force stop the process and raise an exception
            self.stop()
            raise Exception("Process could not be started.")

    def stop(self):
        self.__stopping.set()
        if self.__process.is_alive():
            self.__process.join(timeout=10)
        if self.__process.is_alive():
            raise Exception("Process could not be stopped.")

    def _process(self, agent_type, agent_id, agent_kwargs, inbound_queue, outbound_queue, started, stopping):
        agent: Agent = agent_type(
            agent_id,
            outbound_queue=outbound_queue,
            **agent_kwargs,
        )
        agent.after_add()
        started.set()
        while not stopping.is_set():
            time.sleep(0.001)
            try:
                message = inbound_queue.get(block=False)
                agent._receive(message)
            except queue.Empty:
                pass
        agent.before_remove()


class MultiprocessSpace(Space):
    """
    A Space implementation that uses the multiprocessing module.
    """

    def __init__(self):
        self.__agent_processes: Dict[str, _AgentProcess] = {}
        router_thread = threading.Thread(
            target=self.__router_thread, daemon=True)
        router_thread.start()

    def __router_thread(self):
        """
        A thread that processes outbound messages for all agents, routing them
        to other agents.
        """
        while True:
            time.sleep(0.001)
            for agent_process in list(self.__agent_processes.values()):
                outbound_queue = agent_process.outbound_queue
                try:
                    # process one message per agent per loop
                    message = outbound_queue.get(block=False)
                    self._route(message)
                except queue.Empty:
                    pass

    def _route(self, message: Message):
        message = validate_message(message)
        if message["to"] == "*":
            for agent_thread in self.__agent_processes.values():
                agent_thread.inbound_queue.put(message)
        else:
            self.__agent_processes[message["to"]].inbound_queue.put(message)

    def add(self, agent_type: Type[Agent], agent_id: str, **agent_kwargs) -> Agent:
        if agent_id in self.__agent_processes.keys():
            raise ValueError(f"Agent id already exists: '{agent_id}'")

        try:
            self.__agent_processes[agent_id] = _AgentProcess(
                agent_type=agent_type,
                agent_id=agent_id,
                agent_kwargs=agent_kwargs,
                inbound_queue=multiprocessing.Queue(),
                outbound_queue=multiprocessing.Queue(),
            )
            self.__agent_processes[agent_id].start()

        except:
            # clean up if an error occurs
            self.remove(agent_id)
            raise

    def remove(self, agent_id: str):
        agent_process = self.__agent_processes[agent_id]
        agent_process.stop()
        del self.__agent_processes[agent_id]

    def remove_all(self):
        agent_ids = list(self.__agent_processes.keys())
        for agent_id in agent_ids:
            self.remove(agent_id)
