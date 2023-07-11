import logging

import eventlet
from eventlet import wsgi
from flask import Flask, render_template
from flask.logging import default_handler
from flask_socketio import SocketIO

from agency.agent import ACCESS_PERMITTED, Agent, access_policy
from agency.schema import MessageSchema
from agency.space import Space


class WebApp():
    """
    A simple Flask/React web application which can be used to connect human
    users to a space.
    """

    def __init__(self, space: Space, port: int, demo_username: str):
        self.__space = space
        self.__port = port
        # NOTE We're hardcoding a single demo user for simplicity
        self.__demo_user = WebUser(demo_username, app=self)

    def start(self):
        """
        Run Flask server in a separate thread
        """
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'secret!'

        # six lines to disable logging...
        app.logger.removeHandler(default_handler)
        app.logger.setLevel(logging.ERROR)
        werkzeug_log = logging.getLogger('werkzeug')
        werkzeug_log.setLevel(logging.ERROR)
        eventlet_logger = logging.getLogger('eventlet.wsgi.server')
        eventlet_logger.setLevel(logging.ERROR)

        # start socketio server
        self.socketio = SocketIO(app, async_mode='eventlet',
                                 logger=False, engineio_logger=False)

        # Define routes
        @app.route('/')
        def index():
            return render_template(
                'index.html',
                username=f"{self.current_user().name}")

        @self.socketio.on('connect')
        def handle_connect():
            # When a client connects add them to the space
            self.__space.add(self.current_user())

        @self.socketio.on('disconnect')
        def handle_disconnect():
            # When a client disconnects remove them from the space
            self.__space.remove(self.current_user())

        @self.socketio.on('message')
        def handle_action(action):
            """
            Handles sending incoming actions from the web interface
            """
            # NOTE we send it as the _user_, not the space
            self.current_user()._send(action)

        @self.socketio.on('permission_response')
        def handle_alert_response(allowed: bool):
            """
            Handles incoming alert response from the web interface
            """
            raise NotImplementedError()

        # Wrap the Flask application with wsgi middleware and start
        def run_server():
            wsgi.server(eventlet.listen(('', int(self.__port))),
                        app, log=eventlet_logger)
        eventlet.spawn(run_server)

    def current_user(self):
        # NOTE: We're simplifying here by hardcoding a single user. In a real
        # application this function would return the user associated with the
        # current session.
        return self.__demo_user


class WebUser(Agent):
    """
    A human user of WebApp
    """

    def __init__(self, name: str, app: WebApp) -> None:
        super().__init__(id=name)
        self.name = name
        self.app = app
        self._connected_sid = None

    def _request_permission(self, proposed_message: MessageSchema) -> bool:
        """
        Raises an alert in the users browser and returns true if the user
        approves the action
        """
        self.app.socketio.server.emit(
            'permission_request', proposed_message)

    # The following methods simply forward incoming messages to the web client

    @access_policy(ACCESS_PERMITTED)
    def _action__say(self, content: str):
        """
        Sends a message to the user
        """
        self.app.socketio.server.emit(
            'message', self._current_message, room=self._connected_sid)

    @access_policy(ACCESS_PERMITTED)
    def _action__return(self, original_message: dict, return_value):
        self.app.socketio.server.emit(
            'message', self._current_message, room=self._connected_sid)

    @access_policy(ACCESS_PERMITTED)
    def _action__error(self, original_message: dict, error: str):
        self.app.socketio.server.emit(
            'message', self._current_message, room=self._connected_sid)
