#!/usr/bin/env python3
"""Server to talk to xbee radios to control the linear actuators and to web client"""
import os

import serial
import tornado.web

from core import main
from core.decorators import log_exceptions
from core.mixins import ConfigMixin, ControllerMixin, TimersMixin, ZMQMixin
from xbeehandlers import xbee_handler

template_root = os.path.join(os.path.dirname(__file__), 'templates')


class MainHandler(ControllerMixin, tornado.web.RequestHandler):
    """Returns our index.html, rendered via template engine"""

    def get(self):
        self.render(
            "index.html",
        )


class KaraCRTL(ConfigMixin, ZMQMixin, TimersMixin):
    xbeehandler = None
    serialport = None

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
    def reload(self, *args, **kwargs):
        super().reload(*args, **kwargs)
        if self.xbeehandler:
            self.xbeehandler.quit()
        self.serialport = serial.Serial(**self.config['serial'])
        self.xbeehandler = xbee_handler(
            self.serialport,
            logger_name=self.logger_name
        )
        self.ws_app = tornado.web.Application([
            (r'/', MainHandler, {'controller': self}),
        ], template_path=template_root, debug=self.config['tornado_debug'])
        self.logger.info("Binding to port %d" % self.config['http_server_port'])
        self.ws_app.listen(self.config['http_server_port'])

    @log_exceptions
    def cleanup(self, *args, **kwargs):
        """Cleanup SHOULD be called before quitting mainloop.
        remember to use super() to call all mixin/parent cleanup methods too"""
        super().cleanup(*args, **kwargs)
        if self.xbeehandler:
            self.xbeehandler.quit()

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
