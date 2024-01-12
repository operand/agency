import asyncio
from typing import Coroutine, Dict, List

from app.agency.agent import Agent
from app.agency.processor import Processor
from app.logger import log
from app.agency.schema import ActionHelp, MessageModel


class Space():
    """
    A Space is where Agents communicate.
    """

    def __init__(self):
        log("debug", "Initializing Space...")
        self.processors: Dict[str, Processor] = {}
        self._processors_lock: asyncio.Lock = asyncio.Lock()
        self._stop_router_event: asyncio.Event = asyncio.Event()
        self._outbound_message_event: asyncio.Event = asyncio.Event()
        self._router_coroutine: Coroutine = asyncio.create_task(
            self._start_router_task())
        self._all_help: Dict[str, List[ActionHelp]] = {}
        """Maps agent id to list of action help."""

    async def __enter__(self):
        log("debug", "Entering Space context")
        return self

    async def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            log("debug", "Exiting Space context with exception", {
                "exc_type": exc_type,
                "exc_val": exc_val,
                "exc_tb": exc_tb,
            })
        await self.destroy()

    async def add(self, agent: Agent):
        """
        Adds an agent to the Space allowing it to communicate.

        Args:
            agent: The agent to add

        Raises:
            ValueError: If the agent ID is already in use
        """
        try:
            log("info", f"{agent.id}: joining space")
            agent._all_help = self._all_help  # set reference in agent
            await self._start_processor(agent=agent)
            self._all_help[agent.id] = agent._help()
            log("info", f"{agent.id}: added to space")
        except:
            # clean up if an error occurs
            self.remove(agent.id)
            raise

    async def remove(self, agent_id: str):
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
        self._all_help.pop(agent_id)
        await self._stop_processor(agent_id)
        log("info", f"{agent_id}: removed from space")

    async def destroy(self):
        """
        Cleans up resources used by this space.

        Subclasses should call super().destroy() when overriding.
        """
        await self._stop_router_task()
        await self._stop_all_processors()

    async def _start_processor(self, agent: Agent):
        async with self._processors_lock:
            # Early existence check. Processor.start() will also check. This is
            # because Spaces may be distributed.
            if agent.id in self.processors.keys():
                raise ValueError(f"Agent '{agent.id}' already exists")

            self.processors[agent.id] = Processor(
                agent=agent,
                inbound_queue=asyncio.Queue(),
                outbound_queue=asyncio.Queue(),
                started=asyncio.Event(),
                stopping=asyncio.Event(),
                new_message_event=asyncio.Event(),
            )
            await self.processors[agent.id].start()

    async def _stop_processor_unsafe(self, agent_id: str):
        await self.processors[agent_id].stop()
        self.processors.pop(agent_id)

    async def _stop_processor(self, agent_id: str):
        async with self._processors_lock:
            self._stop_processor_unsafe(agent_id)

    async def _stop_all_processors(self):
        for agent_id in list(self.processors.keys()):
            try:
                async with self._processors_lock:
                    await self._stop_processor_unsafe(agent_id)
            except Exception as e:
                log("error",
                    f"{agent_id}: processor failed to stop", e)

    async def _start_router_task(self) -> Coroutine:
        async def _router_task():
            """Routes outbound messages"""
            log("debug", "Space: router task starting")
            while not self._stop_router_event.is_set():
                # wait a bit for any outbound messages
                try:
                    await asyncio.wait_for(
                        self._outbound_message_event.wait(), timeout=1)
                except asyncio.TimeoutError:
                    pass
                if self._stop_router_event.is_set():
                    log("debug", "Space: router task stopping")
                    break
                self._outbound_message_event.clear()
                # drain each outbound queue
                processors = list(self.processors.values())
                for processor in processors:
                    outbound_queue = processor.outbound_queue
                    while True:
                        try:
                            message: MessageModel = outbound_queue.get_nowait()
                            recipient_processors = [
                                processor for processor in processors
                                if message.to == processor.agent.id
                            ]
                            for recipient_processor in recipient_processors:
                                log("debug",
                                    f"Space: routing message to '{recipient_processor.agent.id}'", message.uuid)
                                await recipient_processor.inbound_queue.put(message)
                        except asyncio.queues.QueueEmpty:
                            break
            log("debug", "Space: router task stopped")

        # start the router async task
        return asyncio.create_task(_router_task())

    async def _stop_router_task(self):
        log("debug", "Space: stopping router task ...")
        self._stop_router_event.set()
        await self._router_coroutine
