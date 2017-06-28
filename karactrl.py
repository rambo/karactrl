#!/usr/bin/env python3
"""Server to talk to xbee radios to control the linear actuators and to web client"""
import json
import os

import serial
import tornado.web
import tornado.websocket

from core import main
from core.decorators import log_exceptions
from core.mixins import ConfigMixin, ControllerMixin, TimersMixin, ZMQMixin
from motorhelpers import KaraMoottori
from sequencer import Sequence
from xbeehandlers import xbee_handler

template_root = os.path.join(os.path.dirname(__file__), 'templates')
js_root = os.path.join(os.path.dirname(__file__), 'jsdist')


class MainHandler(ControllerMixin, tornado.web.RequestHandler):
    """Returns our index.html, rendered via template engine"""

    def get(self):
        self.render(
            "index.html",
        )


class MotorWebsocketHandler(tornado.websocket.WebSocketHandler):

    def __init__(self, application, request, *args, **kwargs):
        """Initialize with references to controller and logger"""
        self.controller = kwargs.pop('controller')
        self.logger = self.controller.logger
        super(MotorWebsocketHandler, self).__init__(application, request, **kwargs)

    @log_exceptions
    def open(self, *args, **kwargs):
        """new WS connection"""
        self.logger.info("New WS stream handled by %s, args=%s kwargs=%s" % (self.__class__.__name__, repr(args), repr(kwargs)))

    @log_exceptions
    def on_close(self, *args, **kwargs):
        """Connection closed"""
        self.logger.debug("WS stream closed, args=%s kwargs=%s" % (repr(args), repr(kwargs)))

    @log_exceptions
    def check_origin(self, origin):
        """NOP implementation for checking WebSocket origin"""
        self.logger.debug("check_origin called for {}".format(origin))
        return True

    @log_exceptions
    def on_message(self, message, *args, **kwargs):
        """Got message"""
        self.logger.debug("got message {}".format(message))
        msg = json.loads(message)
        self.write_message(json.dumps({ 'type': 'pong'}))
        if 'cmd' in msg:
            if msg['cmd'] == 'get_sequence':
                with open(self.controller.config['sequence_file'], 'rt') as fp:
                    sequence_config = json.load(fp)
                reply = {
                    'type': 'sequence',
                    'sequence': sequence_config,
                }
                self.logger.info("Sending back sequence")
                self.write_message(json.dumps(reply))

            if msg['cmd'] == 'save_sequence':
                with open(self.controller.config['sequence_file'], 'wt') as fp:
                    sequence_config = msg['sequence']
                    json.dump(sequence_config, fp, separators=(',', ' : '), indent=2)
                    self.controller.sequence_reload()


class KaraCRTL(ConfigMixin, ZMQMixin, TimersMixin):
    xbeehandler = None
    serialport = None
    motors = {}
    sequencer = None
    seqtimer = None

    def __init__(self, *args, **kwargs):
        self.mainloop = kwargs.pop('mainloop')
        if not self.mainloop:
            raise RuntimeError('"mainloop" must be provided to __init__')
        super().__init__(*args, **kwargs)
        self.reload()

    def hook_signals(self):
        """Hooks POSIX signals to correct callbacks, call only from the main thread!"""
        import signal as posixsignal
        posixsignal.signal(posixsignal.SIGTERM, self.quit)
        try:
            posixsignal.signal(posixsignal.SIGQUIT, self.quit)
            posixsignal.signal(posixsignal.SIGHUP, self.reload)
        except AttributeError:
            pass

    @log_exceptions
    def wait_for_motors(self):
        if len(self.motors) < 1:
            #self.logger.debug("No motors yet, not starting sequencer")
            return
        self.sequence_reload()

    @log_exceptions
    def sequence_reload(self):
        self.seqtimer.stop()
        with open(self.config['sequence_file'], 'rt') as fp:
            sequence_config = json.load(fp)
        self.sequencer = Sequence(
            sequence_config,
            self.motors,
            logger_name=self.logger_name
        )
        self.seqtimer = self.add_timer(self._iterate_sequencer, self.config['sequence_timer'])

    @log_exceptions
    def _iterate_sequencer(self):
        if self.sequencer.done:
            self.self.seqtimer.stop()
        self.sequencer.iterate()

    @log_exceptions
    def reload(self, *args, **kwargs):
        super().reload(*args, **kwargs)
        if self.xbeehandler:
            self.xbeehandler.quit()
            self.motors = {}
        if 'disable' in self.config['serial'] and self.config['serial']['disable']:
            self.logger.warning("*** Serial port disabled ***")
        else:
            self.serialport = serial.Serial(**self.config['serial'])
            self.xbeehandler = xbee_handler(
                self.serialport,
                logger_name=self.logger_name
            )
            self.xbeehandler.new_node_callbacks.append(self.new_xbee_node)
        self.seqtimer = self.add_timer(self.wait_for_motors, 500)

        self.ws_app = tornado.web.Application([
            (r'/', MainHandler, {'controller': self}),
            (r'/ws/?', MotorWebsocketHandler, {'controller': self}),
            (r'/js/(.*)', tornado.web.StaticFileHandler, {'path': js_root}),
        ], template_path=template_root, debug=self.config['tornado_debug'])
        self.logger.info("Binding to port %d" % self.config['http_server_port'])
        self.ws_app.listen(self.config['http_server_port'])

    @log_exceptions
    def new_xbee_node(self, node, *args, **kwargs):
        if not node.node_identifier.startswith(b'Motor'):
            self.logger.debug("Don't know what to do with node {}".format(repr(node.node_identifier)))
            return
        strid = node.node_identifier.decode('ascii')
        self.motors[strid] = KaraMoottori(node, self.config['motors'], logger_name=self.logger_name)
        self.logger.info("Added motor {}".format(node.node_identifier))

    @log_exceptions
    def cleanup(self, *args, **kwargs):
        """Cleanup SHOULD be called before quitting mainloop.
        remember to use super() to call all mixin/parent cleanup methods too"""
        if self.xbeehandler:
            self.xbeehandler.quit()
        super().cleanup(*args, **kwargs)

    @log_exceptions
    def quit(self, *args):
        """Cleans up and stops mainloop"""
        self.logger.info("Quitting")
        self.logger.debug("Calling cleanup")
        self.cleanup()
        self.logger.debug("Stopping mainloop")
        self.mainloop.stop()

    @log_exceptions
    def run(self):
        """Starts the mainloop, will only return when mainloop stops"""
        self.logger.info("Starting mainloop")
        self.mainloop.start()
        self.logger.debug("Closing mainloop")
        self.mainloop.close()


if __name__ == '__main__':
    instance = main(__file__, KaraCRTL)
