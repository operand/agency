import multiprocessing
import queue
import threading
import time
import traceback
from multiprocessing import Event, Process
from typing import Dict, Type

from agency.agent import Agent, _QueueProtocol
from agency.logger import log
from agency.schema import Message, validate_message
from agency.space import Space


class _AgentProcess():
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

    def start(self):
        self.started = Event()
        self.stopping = Event()
        error_queue = multiprocessing.Queue()
        self.process = Process(
            target=self._process,
            args=(
                self.agent_type,
                self.agent_id,
                self.agent_kwargs,
                self.inbound_queue,
                self.outbound_queue,
                self.started,
                self.stopping,
                error_queue,
            )
        )
        self.process.start()

        if not self.started.wait(timeout=10):
            # it couldn't start, force stop the process and raise an exception
            self.stop()
            try:
                error = error_queue.get(block=False)
                raise error
            except queue.Empty:
                raise Exception("Process could not be started.")

    def stop(self):
        self.stopping.set()
        if self.process.is_alive():
            self.process.join(timeout=10)
        if self.process.is_alive():
            raise Exception("Process could not be stopped.")

    def _process(self,
                 agent_type,
                 agent_id,
                 agent_kwargs,
                 inbound_queue,
                 outbound_queue,
                 started,
                 stopping,
                 error_queue):
        try:
            agent: Agent = agent_type(
                agent_id,
                outbound_queue=outbound_queue,
                **agent_kwargs,
            )
            agent.after_add()
            log("info", f"{agent.id()} added to space")
            agent._is_processing = True
            started.set()
            while not stopping.is_set():
                time.sleep(0.001)
                try:
                    message = inbound_queue.get(block=False)
                    agent._receive(message)
                except queue.Empty:
                    pass
        except KeyboardInterrupt:
            pass
        except Exception as e:
            log("error", f"{agent.id()} process failed with exception", traceback.format_exc())
            error_queue.put(e)
        finally:
            agent._is_processing = False
            agent.before_remove()
            log("info", f"{agent.id()} removed from space")


class MultiprocessSpace(Space):
    """
    A Space implementation that uses the multiprocessing module.

    This Space type is recommended in most cases over ThreadSpace for single
    host systems since it offers better parallelism.
    """

    def __init__(self):
        self.__agent_processes: Dict[str, _AgentProcess] = {}
        router_thread = threading.Thread(
            target=self.__router_thread, daemon=True)
        router_thread.start()

    def __router_thread(self):
        """
        Processes and routes outbound messages for all agents
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
        recipient_processes = [
            agent_process
            for agent_process in list(self.__agent_processes.values())
            if message["to"] == agent_process.agent_id or message["to"] == "*"
        ]
        for recipient_process in recipient_processes:
            recipient_process.inbound_queue.put(message)

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
