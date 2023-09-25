import multiprocessing
import queue
import threading
from abc import ABC, ABCMeta
from concurrent.futures import (Executor, Future)
from typing import Dict, List, Protocol, Type

from agency.agent import Agent
from agency.logger import log
from agency.queue import Queue


class _EventProtocol(Protocol):
    def set(self) -> None:
        pass

    def clear(self) -> None:
        pass

    def is_set(self) -> bool:
        pass

    def wait(self, timeout: float = None) -> bool:
        pass


class Processor(ABC, metaclass=ABCMeta):
    """
    Encapsulates a running Agent instance
    """
    def __init__(self,
                 agent_type: Type[Agent],
                 agent_id: str,
                 agent_args: List,
                 agent_kwargs: Dict,
                 inbound_queue: Queue,
                 outbound_queue: Queue,
                 started: _EventProtocol,
                 stopping: _EventProtocol,
                 new_message_event: _EventProtocol,
                 executor: Executor):
        self.agent_type: Type[Agent] = agent_type
        self.agent_id: str = agent_id
        self.agent_args: List = agent_args
        self.agent_kwargs: Dict = agent_kwargs
        self.inbound_queue: Queue = inbound_queue
        self.outbound_queue: Queue = outbound_queue
        self.started: _EventProtocol = started
        self.stopping: _EventProtocol = stopping
        self.new_message_event: _EventProtocol = new_message_event
        self.executor: Executor = executor
        # --- non-constructor properties ---
        self._future: Future = None
        self._agent: Agent = None  # Accessible if in foreground

    def start(self) -> Agent:
        log("debug", f"{self.agent_id}: processor starting ...")

        agent_ref: List = []
        self._future = self.executor.submit(
            _process_loop,
            self.agent_type,
            self.agent_id,
            self.agent_args,
            self.agent_kwargs,
            self.inbound_queue,
            self.outbound_queue,
            self.started,
            self.stopping,
            self.new_message_event,
            agent_ref,
        )

        if not self.started.wait(timeout=5):
            # it couldn't start, force stop it and raise an exception
            self.stop()
            error = self._future.exception()
            if error is not None:
                raise error
            else:
                raise Exception("Processor could not be started.")

        log("debug", f"{self.agent_id}: processor started")

        # return the agent if present. only works in foreground
        if agent_ref:
            return agent_ref[0]

    def stop(self):
        log("debug", f"{self.agent_id}: processor stopping ...")
        self.stopping.set()
        if self._future is not None:
            self._future.result()
        log("debug", f"{self.agent_id}: processor stopped")


# Placed at the top-level to play nice with the multiprocessing module
def _process_loop(agent_type: Type[Agent],
                  agent_id: str,
                  agent_args: List,
                  agent_kwargs: Dict,
                  inbound_queue: Queue,
                  outbound_queue: Queue,
                  started: _EventProtocol,
                  stopping: _EventProtocol,
                  new_message_event: _EventProtocol,
                  agent_ref: List):
    """
    The main agent processing loop
    """
    # Set process or thread name
    if isinstance(started, threading.Event):
        threading.current_thread(
        ).name = f"{agent_id}: processor loop thread"
    else:
        multiprocessing.current_process(
        ).name = f"{agent_id}: processor loop process"

    try:
        log("debug", f"{agent_id}: processor loop starting")
        agent: Agent = agent_type(agent_id, *agent_args, **agent_kwargs)
        agent_ref.append(agent)  # set the agent reference
        inbound_queue.connect()
        outbound_queue.connect()
        agent._outbound_queue = outbound_queue
        agent.after_add()
        agent._is_processing = True
        started.set()
        stopping.clear()
        new_message_event.clear()
        while not stopping.is_set():
            new_message_event.wait(timeout=0.1) # TODO make configurable
            if stopping.is_set():
                log("debug",
                    f"{agent_id}: processor loop stopping")
                break
            while True:  # drain inbound_queue
                try:
                    message = inbound_queue.get(block=False)
                    log("debug",
                        f"{agent_id}: processor loop got message", message)
                    agent._receive(message)
                except queue.Empty:
                    break
            new_message_event.clear()
    except KeyboardInterrupt:
        log("debug", f"{agent_id}: processor loop interrupted")
        pass
    except Exception as e:
        log("error", f"{agent_id}: processor loop failed", e)
        raise
    finally:
        log("debug", f"{agent_id}: processor loop cleaning up")
        agent._is_processing = False
        agent.before_remove()
        inbound_queue.disconnect()
        outbound_queue.disconnect()
        log("debug", f"{agent_id}: processor loop stopped")
