import queue
import time
import multiprocessing
from multiprocessing import Event, Manager, Process
from typing import Dict, Type

from agency.agent import Agent, RouterProtocol
from agency.schema import Message, validate_message
from agency.space import Space
from agency.util import debug

multiprocessing.set_start_method('spawn', force=True)


class _AgentProcess():
    def __init__(
            self,
            agent_type: Type[Agent],
            agent_id: str,
            agent_kwargs: Dict,
            message_queue: multiprocessing.Queue,
            router: RouterProtocol):
        self.__agent_type: Type[Agent] = agent_type
        self.__agent_id: str = agent_id
        self.__agent_kwargs: Dict = agent_kwargs
        self.__message_queue: multiprocessing.Queue = message_queue
        self.__router: RouterProtocol = router

    def start(self):
        self.__started = Event()
        self.__stopping = Event()
        self.__process = Process(
            target=self._process,
            args=(
                self.__agent_type,
                self.__agent_id,
                self.__agent_kwargs,
                self.__message_queue,
                self.__router,
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

    def _process(self, agent_type, agent_id, agent_kwargs, message_queue, router, started, stopping):
        agent: Agent = agent_type(
            agent_id,
            router=router,
            **agent_kwargs,
        )
        agent.after_add()
        started.set()
        while not stopping.is_set():
            time.sleep(0.001)
            try:
                message = message_queue.get(block=False)
                agent._receive(message)
            except queue.Empty:
                pass
        agent.before_remove()


class _MultiprocessRouter():
    def __init__(self):
        self.manager = Manager()
        self.__agent_queues = self.manager.list()  # Manager list for queues
        self.__agent_mapping = self.manager.dict()  # Manager dict for agent_id to index mapping

    def route(self, message: Message):
        message = validate_message(message)
        if message["to"] == "*":
            for agent_queue in self.__agent_queues.values():
                agent_queue.put(message)
        else:
            self.__agent_queues[message["to"]].put(message)

    def add_queue(self, agent_id: str):
        new_queue = multiprocessing.Queue()
        self.__agent_queues.append(new_queue)
        self.__agent_mapping[agent_id] = len(self.__agent_queues) - 1

    def remove_queue(self, agent_id: str):
        index = self.__agent_mapping[agent_id]
        self.__agent_queues[index] = None
        del self.__agent_mapping[agent_id]

    def get_queue(self, agent_id: str):
        index = self.__agent_mapping[agent_id]
        return self.__agent_queues[index]


class MultiprocessSpace(Space):
    """
    A Space implementation that uses the multiprocessing module.
    """

    def __init__(self):
        self.__agent_processes: Dict[str, _AgentProcess] = {}
        self.__router = _MultiprocessRouter()

    def add(self, agent_type: Type[Agent], agent_id: str, **agent_kwargs) -> Agent:
        if agent_id in self.__agent_processes.keys():
            raise ValueError(f"Agent id already exists: '{agent_id}'")

        try:
            self.__router.add_queue(agent_id)
            self.__agent_processes[agent_id] = _AgentProcess(
                agent_type=agent_type,
                agent_id=agent_id,
                agent_kwargs=agent_kwargs,
                message_queue=self.__router.get_queue(agent_id),
                router=self.__router,
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
