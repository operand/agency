import json
import eventlet
import logging
from eventlet import wsgi
from everything.things import util
from everything.things.operator import Operator
from everything.things.schema import MessageSchema
from flask import Flask, render_template, request
from flask.logging import default_handler
from flask_socketio import SocketIO
from everything.things.channel import ACCESS_PERMITTED, Channel, access_policy


class WebChannel(Channel):
  """
  Encapsulates a simple web-based channel
  Currently implemented using Flask
  """

  def __init__(self, operator: Operator, **kwargs):
    """
    Run Flask server in a separate thread
    """
    super().__init__(operator, **kwargs)
    app = Flask(__name__)

    # six lines to disable logging...
    app.logger.removeHandler(default_handler)
    app.logger.setLevel(logging.ERROR)
    werkzeug_log = logging.getLogger('werkzeug')
    werkzeug_log.setLevel(logging.ERROR)
    eventlet_logger = logging.getLogger('eventlet.wsgi.server')
    eventlet_logger.setLevel(logging.ERROR)

    app.config['SECRET_KEY'] = 'secret!'
    # app.config['DEBUG'] = True
    self.socketio = SocketIO(app, async_mode='eventlet',
                             logger=False, engineio_logger=False)  # seven!

    # Define routes
    @app.route('/')
    def index():
      return render_template('index.html', channel_id=self.id())

    @self.socketio.on('connect')
    def handle_connect():
      # When a client connects, store the session ID
      # TODO: allow for multiple clients
      self.connected_sid = request.sid

    @self.socketio.on('message')
    def handle_action(action):
      """
      Handles incoming actions from the web user interface
      """
      self._send(action)

    @self.socketio.on('permission_response')
    def handle_alert_response(allowed: bool):
      """
      Handles incoming alert responses
      """
      raise NotImplementedError

    # Wrap the Flask application with wsgi middleware and start
    def run_server():
      wsgi.server(eventlet.listen(
        ('', int(self.kwargs['port']))), app, log=eventlet_logger)
    eventlet.spawn(run_server)

  def _request_permission(self, proposed_message: MessageSchema) -> bool:
    """
    Raises an alert in the users browser and returns true if the user
    approves the action"""
    self.socketio.server.emit('permission_request', proposed_message)

  # We use the _after_action__ method to pass through all messages to the
  # socketio web client
  def _after_action___(self, original_message: MessageSchema, return_value: str, error: str):
    self.socketio.server.emit(
      'message', original_message, room=self.connected_sid)

  # And define pass through methods to whitelist the actions we allow
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
