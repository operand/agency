import logging

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from agency.agent import ActionError, Agent, action
from agency.schema import Message
from agency.space import Space

app = FastAPI()
templates = Jinja2Templates(directory="templates")


class ReactApp:
    def __init__(self, space: Space, port: int, demo_username: str):
        self.__space = space
        self.__port = port
        self.__demo_username = demo_username
        self.__current_user = None

    async def handle_connect(self, websocket: WebSocket):
        await websocket.accept()
        self.__current_user = ReactAppUser(
            name=self.__demo_username,
            app=self,
            websocket=websocket
        )
        self.__space.add(self.__current_user)

    async def handle_disconnect(self):
        self.__space.remove(self.__current_user)
        self.__current_user = None

    async def handle_action(self, action):
        self.__current_user.send(action)

    async def handle_alert_response(self, allowed: bool):
        raise NotImplementedError()


@app.get("/", response_class=HTMLResponse)
async def index():
    return templates.TemplateResponse("index.html", {
        "request": None,
        "username": app.state.react_app.__demo_username
    })


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await app.state.react_app.handle_connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await app.state.react_app.handle_action(data)
    except Exception as e:
        print(e)
    finally:
        await app.state.react_app.handle_disconnect()


class ReactAppUser(Agent):
    def __init__(self, name: str, app: ReactApp, websocket: WebSocket) -> None:
        super().__init__(id=name)
        self.name = name
        self.app = app
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
