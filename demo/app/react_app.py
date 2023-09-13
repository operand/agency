import os

import uvicorn
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from agency.agent import ActionError, Agent, QueueProtocol, action
from agency.schema import Message
from agency.space import Space


class ReactApp:
    """
    A React app that uses the FastAPI framework
    """

    def __init__(self, space: Space, port: int, user_agent_id: str):
        self.__space = space
        self.__host = "0.0.0.0"
        self.__port = port
        self.__user_agent_id = user_agent_id

    async def handle_connect(self, websocket: WebSocket):
        await websocket.accept()
        # add the user to the space
        self.__space.add(ReactAppUser,
                         self.__user_agent_id,
                         websocket=websocket)

    async def handle_disconnect(self):
        # remove the user from the space
        self.__space.remove(self.__user_agent_id)

    async def handle_send(self, action):
        raise NotImplementedError
        self.__current_user.send(action)

    def start(self):
        app = FastAPI()
        templates_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "templates")
        templates = Jinja2Templates(directory=templates_dir)

        @app.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            return templates.TemplateResponse("index.html", {
                "request": request,
                "username": self.__user_agent_id
            })

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.handle_connect(websocket)
            try:
                while True:
                    data = await websocket.receive_text()
                    await self.handle_send(data)
            except Exception as e:
                print(e)
            finally:
                await self.handle_disconnect()

        uvicorn.run(app, host=self.__host, port=self.__port)


class ReactAppUser(Agent):
    def __init__(self,
                 id: str,
                 outbound_queue: QueueProtocol,
                 websocket: WebSocket):
        super().__init__(id, outbound_queue, receive_own_broadcasts=False)
        self.websocket = websocket

    async def request_permission(self, proposed_message: Message) -> bool:
        await self.websocket.send_text('permission_request', proposed_message)

    @action
    async def say(self, content: str):
        await self.websocket.send_text('message', self.current_message())

    async def handle_action_value(self, value):
        await self.websocket.send_text('message', self.current_message())

    async def handle_action_error(self, error: ActionError):
        await self.websocket.send_text('message', self.current_message())
