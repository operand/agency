import threading
from abc import ABC, ABCMeta, abstractmethod
from concurrent.futures import Executor
from typing import Dict, List, Type

from agency.agent import Agent
from agency.logger import log
from agency.processor import Processor, _EventProtocol
from agency.queue import Queue
from agency.resources import ResourceManager


class Space(ABC, metaclass=ABCMeta):
    """
    A Space is where Agents communicate.
    """

    def __init__(self):
        self.processors: Dict[str, Processor] = {}
        self._processors_lock: threading.Lock = threading.Lock()

    def __enter__(self):
        log("debug", "Entering Space context")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            log("debug", "Exiting Space context with exception", {
                "exc_type": exc_type,
                "exc_val": exc_val,
                "exc_tb": exc_tb,
            })
        self.destroy()

    def add(self,
            agent_type: Type[Agent],
            agent_id: str,
            *agent_args,
            **agent_kwargs):
        """
        Adds an agent to the space allowing it to communicate.

        This method adds the agent in a subprocess. The agent may not be
        directly accessed from the main thread.

        Args:
            agent_type: The type of agent to add
            agent_id: The id of the agent to add

            All other arguments are passed to the Agent constructor

        Raises:
            ValueError: If the agent ID is already in use
        """
        self._add(foreground=False,
                  agent_type=agent_type,
                  agent_id=agent_id,
                  *agent_args,
                  **agent_kwargs)

    def add_foreground(self,
                       agent_type: Type[Agent],
                       agent_id: str,
                       *agent_args,
                       **agent_kwargs) -> Agent:
        """
        Adds an agent to the space and returns it in the current thread.

        This method adds an agent using threading. The agent instance is
        returned allowing direct access.

        It is recommended to use the `add` method instead of this method in most
        cases. Agents added this way may block other agents or threads in the
        main process. Use this method when direct access to the agent instance
        is desired.

        Args:
            agent_type: The type of agent to add
            agent_id: The id of the agent to add

            All other arguments are passed to the Agent constructor

        Returns:
            The agent

        Raises:
            ValueError: If the agent ID is already in use
        """
        agent = self._add(foreground=True,
                          agent_type=agent_type,
                          agent_id=agent_id,
                          *agent_args,
                          **agent_kwargs)
        return agent

    def remove(self, agent_id: str):
        """
        Removes an agent from the space by id.

        This method cannot remove an agent added from a different instance. In
        other words, a Space instance cannot remove an agent that it did not
        add.

        Args:
            agent_id: The id of the agent to remove

        Raises:
            ValueError: If the agent is not present in the space
        """
        self._stop_processor(agent_id)
        log("info", f"{agent_id}: removed from space")

    def destroy(self):
        """
        Cleans up resources used by this space.

        Subclasses should call super().destroy() when overriding.
        """
        self._stop_all_processors()

    def _add(self,
             foreground: bool,
             agent_type: Type[Agent],
             agent_id: str,
             *agent_args,
             **agent_kwargs) -> Agent:

        try:
            agent = self._start_processor(
                foreground=foreground,
                agent_type=agent_type,
                agent_id=agent_id,
                agent_args=agent_args,
                agent_kwargs=agent_kwargs,
            )
            log("info", f"{agent_id}: added to space")
            return agent
        except:
            # clean up if an error occurs
            self.remove(agent_id)
            raise

    def _start_processor(self,
                         foreground: bool,
                         agent_type: Type[Agent],
                         agent_id: str,
                         agent_args: List,
                         agent_kwargs: Dict):
        with self._processors_lock:
            # Early existence check. Processor.start() will also check. This is
            # because Spaces may be distributed.
            if agent_id in self.processors.keys():
                raise ValueError(f"Agent '{agent_id}' already exists")

            self.processors[agent_id] = Processor(
                agent_type=agent_type,
                agent_id=agent_id,
                agent_args=agent_args,
                agent_kwargs=agent_kwargs,
                inbound_queue=self._create_inbound_queue(agent_id),
                outbound_queue=self._create_outbound_queue(agent_id),
                started=self._define_event(foreground=foreground),
                stopping=self._define_event(foreground=foreground),
                new_message_event=self._define_event(foreground=foreground),
                executor=self._get_executor(foreground=foreground),
            )
            return self.processors[agent_id].start()

    def _stop_processor_unsafe(self, agent_id: str):
        self.processors[agent_id].stop()
        self.processors.pop(agent_id)

    def _stop_processor(self, agent_id: str):
        with self._processors_lock:
            self._stop_processor_unsafe(agent_id)

    def _stop_all_processors(self):
        for agent_id in list(self.processors.keys()):
            try:
                with self._processors_lock:
                    self._stop_processor_unsafe(agent_id)
            except Exception as e:
                log("error",
                    f"{agent_id}: processor failed to stop", e)

    def _get_executor(self, foreground: bool = False) -> Executor:
        if foreground:
            return ResourceManager().thread_pool_executor
        else:
            return ResourceManager().process_pool_executor

    def _define_event(self, foreground: bool = False) -> _EventProtocol:
        if foreground:
            return threading.Event()
        else:
            return ResourceManager().multiprocessing_manager.Event()

    @abstractmethod
    def _create_inbound_queue(self, agent_id) -> Queue:
        """
        Returns a Queue suitable for receiving messages
        """
        raise NotImplementedError

    @abstractmethod
    def _create_outbound_queue(self, agent_id) -> Queue:
        """
        Returns a Queue suitable for sending messages
        """
        raise NotImplementedError
