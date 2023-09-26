import multiprocessing
import queue
import threading
from concurrent.futures import Future

from agency.logger import log
from agency.queue import Queue
from agency.resources import ResourceManager
from agency.schema import Message
from agency.space import Space


class _LocalQueue(Queue):
    """A multiprocessing based implementation of Queue"""

    def __init__(self, outbound_message_event: multiprocessing.Event = None):
        self.outbound_message_event = outbound_message_event
        self._queue = ResourceManager().multiprocessing_manager.Queue()

    def put(self, message: Message):
        self._queue.put(message)
        if self.outbound_message_event is not None:
            self.outbound_message_event.set()

    def get(self, block: bool = True, timeout: float = None) -> Message:
        return self._queue.get(block=block, timeout=timeout)


class LocalSpace(Space):
    """
    A LocalSpace allows Agents to communicate within the python application
    """

    def __init__(self):
        super().__init__()
        self._stop_router_event: threading.Event = threading.Event()
        self._outbound_message_event: multiprocessing.Event = ResourceManager(
        ).multiprocessing_manager.Event()
        self._router_future: Future = self._start_router_thread()

    def destroy(self):
        self._stop_router_thread()
        super().destroy()

    def _start_router_thread(self):
        def _router_thread():
            """Routes outbound messages"""
            log("debug", "LocalSpace: router thread starting")
            while not self._stop_router_event.is_set():
                self._outbound_message_event.wait(timeout=0.1)
                if self._stop_router_event.is_set():
                    log("debug", "LocalSpace: router thread stopping")
                    break
                self._outbound_message_event.clear()
                # drain each outbound queue
                processors = list(self.processors.values())
                for processor in processors:
                    outbound_queue = processor.outbound_queue
                    while True:
                        try:
                            message = outbound_queue.get(block=False)
                            log("debug", f"LocalSpace: routing message", message)
                            recipient_processors = [
                                processor for processor in processors
                                if message["to"] == processor.agent_id or message["to"] == "*"
                            ]
                            for recipient_processor in recipient_processors:
                                recipient_processor.inbound_queue.put(message)
                        except queue.Empty:
                            break
            log("debug", "LocalSpace: router thread stopped")

        return ResourceManager().thread_pool_executor.submit(_router_thread)

    def _stop_router_thread(self):
        self._stop_router_event.set()
        self._router_future.result()

    def _create_inbound_queue(self, agent_id) -> Queue:
        return _LocalQueue()

    def _create_outbound_queue(self, agent_id) -> Queue:
        return _LocalQueue(outbound_message_event=self._outbound_message_event)
