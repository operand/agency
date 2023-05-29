import eventlet
import logging
from eventlet import wsgi
from flask import Flask, render_template, request
from flask.logging import default_handler
from flask_socketio import SocketIO
from things.util import parse_slash_syntax_action
from everything.channels.channel import ACCESS_ALWAYS, Channel, access_policy


class WebChannel(Channel):
  """
  Encapsulates a simple web-based channel
  Currently implemented using Flask
  """

  def __init__(self, operator, **kwargs):
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
    def handle_message(message_text):
      """
      Handles incoming messages from the user interface
      """
      action = {
        "from": self.id(),
        "thoughts": "",
      }
      action.update(**parse_slash_syntax_action(message_text))
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

  def _ask_permission(self, proposed_message: dict) -> bool:
    """
    Raises an alert in the users browser and returns true if the user
    approves the action"""
    self.socketio.server.emit('permission_request', proposed_message)

  # We use the _after_action__ method to pass through all messages to the
  # socketio web client
  def _after_action___(self, original_message, return_value, error):
    self.socketio.server.emit('message', original_message, room=self.connected_sid)

  # And define pass through methods to whitelist the actions we want to allow
  @access_policy(ACCESS_ALWAYS)
  def _action__say(self, content: str):
    pass

  @access_policy(ACCESS_ALWAYS)
  def _action__error(self, original_message, error_message: dict):
    """
    Define this action to handle errors from an action
    """
    # TODO send the error to the user
    raise NotImplementedError
