import asyncio
import traceback
from abc import ABC, ABCMeta
from asyncio import Queue
from typing import Coroutine

from app.agency.agent import Agent
from app.logger import log
from app.agency.schema import MessageModel


class Processor(ABC, metaclass=ABCMeta):
    """
    A Processor is a running Agent instance.
    """

    def __init__(self,
                 agent: Agent,
                 inbound_queue: Queue[MessageModel],
                 outbound_queue: Queue[MessageModel],
                 started: asyncio.Event,
                 stopping: asyncio.Event,
                 new_message_event: asyncio.Event):
        self.agent: Agent = agent
        self.inbound_queue: Queue[MessageModel] = inbound_queue
        self.outbound_queue: Queue[MessageModel] = outbound_queue
        self.started: asyncio.Event = started
        self.stopping: asyncio.Event = stopping
        self.new_message_event: asyncio.Event = new_message_event
        # --- non-constructor properties ---
        self._coroutine: Coroutine = None

    async def start(self):
        log("debug", f"{self.agent.id}: processor starting ...")
        self._coroutine = asyncio.create_task(
            self._process_loop(
                self.agent,
                self.inbound_queue,
                self.outbound_queue,
                self.started,
                self.stopping,
                self.new_message_event))

        try:
            # wait for started event
            await asyncio.wait_for(self.started.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            # it couldn't start, force stop it and raise an exception
            self.stop()
            error = await self._coroutine.exception()
            if error is not None:
                raise error
            else:
                raise Exception("Processor could not be started.")
        log("debug", f"{self.agent.id}: processor started")

    async def stop(self):
        log("debug", f"{self.agent.id}: processor stopping ...")
        self.stopping.set()
        if self._coroutine is not None:
            await self._coroutine
        log("debug", f"{self.agent.id}: processor stopped")


    async def _process_loop(self,
                      agent: Agent,
                      inbound_queue: Queue[MessageModel],
                      outbound_queue: Queue[MessageModel],
                      started: asyncio.Event,
                      stopping: asyncio.Event,
                      new_message_event: asyncio.Event):
        """
        The main agent processing loop
        """
        try:
            log("debug", f"{agent.id}: processor loop starting")
            agent._outbound_queue = outbound_queue
            await agent.after_add()
            agent._is_processing = True
            started.set()
            stopping.clear()
            new_message_event.clear()
            while not stopping.is_set():
                try:
                    await asyncio.wait_for(new_message_event.wait(), timeout=0.1)
                except asyncio.TimeoutError:
                    pass
                if stopping.is_set():
                    log("debug",
                        f"{agent.id}: processor loop stopping")
                    break
                while True:  # drain inbound_queue
                    try:
                        message: MessageModel = inbound_queue.get_nowait()
                        # log("debug",
                        #     f"{agent.id}: processor loop got message", message.uuid)
                        await agent._receive(message)
                    except asyncio.queues.QueueEmpty:
                        break
                new_message_event.clear()
        except KeyboardInterrupt:
            log("debug", f"{agent.id}: processor loop interrupted")
            pass
        except Exception as e:
            log("error", f"{agent.id}: processor loop failed", e)
            traceback.print_exc()
            raise
        finally:
            log("debug", f"{agent.id}: processor loop cleaning up")
            agent._is_processing = False
            await agent.before_remove()
            log("debug", f"{agent.id}: processor loop stopped")
