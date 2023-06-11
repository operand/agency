from eventlet import wsgi
from everything.things.operator import ACCESS_PERMITTED, Operator, access_policy
from everything.things.schema import MessageSchema
from everything.things.space import Space
from flask import Flask, render_template, request
from flask.logging import default_handler
from flask_socketio import SocketIO
import eventlet
import logging


class WebAppUser(Operator):
    """Represents a user of the WebApp"""

    def _request_permission(self, proposed_message: MessageSchema) -> bool:
        """
        Raises an alert in the users browser and returns true if the user
        approves the action
        """
        self.space.socketio.server.emit(
            'permission_request', proposed_message)

    # We use the _after_action__ method to pass through all messages to the
    # socketio web client
    def _after_action__(self, original_message: MessageSchema, return_value: str, error: str):
        self.space.socketio.server.emit(
          'message', original_message, room=self.connected_sid)

    # We define pass through methods to whitelist the actions we allow
    @access_policy(ACCESS_PERMITTED)
    def _action__say(self, content: str):
        pass

    # Allow return values to be passed through
    @access_policy(ACCESS_PERMITTED)
    def _action__return(self, original_message: MessageSchema, return_value: str):
        pass

    # Allow errors to be passed through
    @access_policy(ACCESS_PERMITTED)
    def _action__error(self, original_message: MessageSchema, error: str):
        pass


class WebApp(Space):
    """
    Encapsulates a simple Flask web application "space" which can be used to
    connect multiple users to a space.
    """

    def __init__(self, id, **kwargs):
        """
        Run Flask server in a separate thread
        """
        super().__init__(id)
        self.__kwargs = kwargs
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

        # NOTE: We're simplifying here by hardcoding a single operator named
        # "Dan" representing a user of the WebApp. In a real application this
        # could be handled dynamically as users log on/off.
        self.add(WebAppUser("Dan"))

        # Define routes
        @app.route('/')
        def index():
            return render_template(
                'index.html',
                operator_id=f"{self.current_operator().id()}")

        @self.socketio.on('connect')
        def handle_connect():
            # When a client connects, store the socketio session ID
            self.current_operator().connected_sid = request.sid

        @self.socketio.on('message')
        def handle_action(action):
            """
            Handles incoming actions from the web interface
            """
            # NOTE we must send it as the _user_, not the space
            self.current_operator()._send(action)

        @self.socketio.on('permission_response')
        def handle_alert_response(allowed: bool):
            """
            Handles incoming alert response from the web interface
            """
            raise NotImplementedError

        # Wrap the Flask application with wsgi middleware and start
        def run_server():
            wsgi.server(eventlet.listen(
              ('', int(self.__kwargs['port']))), app, log=eventlet_logger)
        eventlet.spawn(run_server)

    def current_operator(self):
        # NOTE current_operator would normally be determined via login but for
        # now we hardcode it to the first operator, "Dan". (see above)
        return self.operators[0]
