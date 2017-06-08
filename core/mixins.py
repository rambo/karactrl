import itertools
import json
import logging

import zmq
import zmq.eventloop
import zmq.eventloop.future
from tornado.ioloop import PeriodicCallback
from zmq.eventloop.zmqstream import ZMQStream

from .decorators import log_exceptions


class ReloadMixin(object):
    """Base mixin for everything implementing reload method so that we can call super on the mixins"""

    def reload(self, *args, **kwargs):
        """no-op but needed for parent calls to work"""
        pass


class CleanupMixin(object):
    """Base mixin for everything implementing cleanup method so that we can call super on the mixins"""

    def cleanup(self, *args, **kwargs):
        """no-op but needed for parent calls to work"""
        pass


class LoggerMixin(ReloadMixin):
    logger = None

    def __init__(self, *args, **kwargs):
        """Init ensures required parameters are present"""
        loggername = kwargs.pop('logger_name', None)
        if not loggername:
            raise RuntimeError('"logger_name" must be provided to __init__ when using LoggerMixin')
        self.logger = logging.getLogger(loggername)
        super(LoggerMixin, self).__init__(*args, **kwargs)

    def reload(self, *args, **kwargs):
        """Resets the logging-level according to configuration"""
        super(LoggerMixin, self).reload(*args, **kwargs)
        if 'log_level' in self.config:
            self.logger.setLevel(self.config['log_level'])


class ConfigMixin(LoggerMixin):
    config = {}
    config_file = None
    config_root_name = None

    def __init__(self, *args, **kwargs):
        """Init ensures required parameters are present"""
        self.config_file = kwargs.pop('config_file', None)
        if not self.config_file:
            raise RuntimeError('"config_file" must be provided to __init__ when using ConfigMixin')
        self.config_root_name = kwargs.pop('config_root_name', None)
        if not self.config_root_name:
            raise RuntimeError('"config_root_name" must be provided to __init__ when using ConfigMixin')
        super(ConfigMixin, self).__init__(*args, **kwargs)

    def reload(self, *args, **kwargs):
        """(Re-)reads the configuration file and checks whether we're using single or separate configuration file(s).
        then populates self.config accordingly.

        Due to the config-file reloading being usually first thing required, we do it before calling parents reload method"""
        self.logger.info("Loading configuration from {}".format(self.config_file))
        with open(self.config_file) as f:
            config = json.load(f)
            if self.config_root_name in config:
                self.logger.debug("Found root-key {} in config. using it".format(self.config_root_name))
                self.config = config[self.config_root_name]
            else:
                self.config = config
        super(ConfigMixin, self).reload(*args, **kwargs)


class TimersMixin(LoggerMixin, CleanupMixin):
    """Mixin to implement handling of multiple periodic timers"""
    timers = []

    def clear_timers(self):
        for timer in self.timers:
            if not timer:
                continue
            self.logger.debug("Stopping timer {}".format(repr(timer)))
            timer.stop()
        self.timers = []

    def cleanup(self, *args, **kwargs):
        """Clear timers before a clean exit"""
        self.clear_timers()
        super(TimersMixin, self).cleanup(*args, **kwargs)

    def reload(self, *args, **kwargs):
        """Clears all active timers"""
        super(TimersMixin, self).reload(*args, **kwargs)
        self.clear_timers()

    def add_timer(self, callback, timeout, *args, **kwargs):
        """Adds a periodic call to callback with given timeout"""
        self.logger.debug("Adding {timeout}ms timer to {callback}".format(timeout=timeout, callback=repr(callback)))
        timer = PeriodicCallback(callback, timeout, *args, **kwargs)
        timer.start()
        self.timers.append(timer)
        return timer

    def remove_timer(self, timer):
        """Stops and removes given timer"""
        timer.stop()
        # Interestingly enough this triggers "ValueError: list.remove(x): x not in list"
        # self.timers.remove(timer)


class ZMQMixin(LoggerMixin, CleanupMixin):
    zmq_sockets = {}
    zmq_streams = {}
    mainloop = None

    def remove_socket(self, socket_addr):
        """Closes and removed given socket, used when it seems to be broken somehow"""
        if socket_addr in self.zmq_sockets and not self.zmq_sockets[socket_addr].closed:
            self.zmq_sockets[socket_addr].close()
            del(self.zmq_sockets[socket_addr])

    @log_exceptions
    def request(self, socket_addr, *msgparts):
        """Sends a REQuest to given socket and returns a Future"""
        if not self.mainloop:
            raise RuntimeError("self.mainloop must exist before we can setup ZMQ message streams")
        zmq_ctx = zmq.eventloop.future.Context.instance()
        if socket_addr not in self.zmq_sockets or self.zmq_sockets[socket_addr].closed:
            self.zmq_sockets[socket_addr] = zmq_ctx.socket(zmq.REQ)
            self.logger.info("Connecting REQ socket to {}".format(socket_addr))
            self.zmq_sockets[socket_addr].connect(socket_addr)
        req = self.zmq_sockets[socket_addr]
        self.logger.debug("Sending REQ {msg} to {sock}".format(msg=repr(msgparts), sock=socket_addr))
        req.send_multipart(msgparts)
        resp = req.recv_multipart()
        return resp

    @log_exceptions
    def reply(self, socket_addr, callback):
        """Sets up a REPly socket and registers a callback for messages in it"""
        if not self.mainloop:
            raise RuntimeError("self.mainloop must exist before we can setup ZMQ message streams")
        zmq_ctx = zmq.eventloop.future.Context.instance()
        if socket_addr not in self.zmq_sockets or self.zmq_sockets[socket_addr].closed:
            self.zmq_sockets[socket_addr] = zmq_ctx.socket(zmq.REP)
            self.logger.info("Binding REP socket to {}".format(socket_addr))
            self.zmq_sockets[socket_addr].bind(socket_addr)
        rep = self.zmq_sockets[socket_addr]
        if socket_addr not in self.zmq_streams:
            self.zmq_streams[socket_addr] = ZMQStream(rep, self.mainloop)
        stream = self.zmq_streams[socket_addr]
        stream.on_recv_stream(callback)

    @log_exceptions
    def unsubscribe(self, socket_addr, topic):
        """Unsubscribes from given zmq socket+topic combination"""
        if self.mainloop.__class__.__name__ == 'GObjectIOLoop':
            return self._unsubscribe_gobject(socket_addr, topic)
        return self._unsubscribe_stdtornado(socket_addr, topic)

    @log_exceptions
    def _unsubscribe_stdtornado(self, socket_addr, topic):
        """Unsubsribe from socket (now naively assumes there's only one subscription per socket"""
        if socket_addr not in self.zmq_streams:
            self.logger.error("Trying to close non-existing socket {}".format(socket_addr))
            return
        self.zmq_streams[socket_addr].close()
        self.zmq_sockets[socket_addr].close()
        del(self.zmq_streams[socket_addr], self.zmq_sockets[socket_addr])

    @log_exceptions
    def _subscribe_stdtornado(self, socket_addr, topic, callback):
        """Handle the Tornado specific parts of subscribing to ZMQ """
        self.logger.debug("Standard tornado ZMQ stream")
        sub = self.zmq_sockets[socket_addr]
        if socket_addr not in self.zmq_streams:
            self.zmq_streams[socket_addr] = ZMQStream(sub, self.mainloop)
        stream = self.zmq_streams[socket_addr]
        stream.on_recv(callback)

    @log_exceptions
    def subscribe(self, socket_addr, topic, callback):
        """SUBscribes a callback to given socket/topic combination with transparent connection handling"""
        if not self.mainloop:
            raise RuntimeError("self.mainloop must exist before we can SUBscribe via ZMQ")
        if not isinstance(topic, bytes):  # ZMQ uses always bytes
            topic = topic.encode('utf-8')
        zmq_ctx = zmq.Context.instance()
        if socket_addr not in self.zmq_sockets or self.zmq_sockets[socket_addr].closed:
            self.zmq_sockets[socket_addr] = zmq_ctx.socket(zmq.SUB)
            self.logger.debug("Connecting SUB socket to {}".format(socket_addr))
            self.zmq_sockets[socket_addr].connect(socket_addr)
        sub = self.zmq_sockets[socket_addr]
        self.logger.info("SUBScribing to {}/{}".format(socket_addr, topic))
        sub.setsockopt(zmq.SUBSCRIBE, topic)
        # Check against the class name string so we don't have to import the library with all it's side-effects
        if self.mainloop.__class__.__name__ == 'GObjectIOLoop':
            return self._subscribe_gobject(socket_addr, topic, callback)
        return self._subscribe_stdtornado(socket_addr, topic, callback)

# Enable only for debugging, or prove that having it enabled always does not hurt performance
#    @log_exceptions
    def publish(self, socket_addr, topic, *msgparts):
        """PUBlishes a 0 to N part message on given socket/topic combination with transparent connection binding"""
        if not self.mainloop:
            raise RuntimeError("self.mainloop must exist before we can PUBlish via ZMQ")
        if not isinstance(topic, bytes):  # ZMQ uses always bytes
            topic = topic.encode('utf-8')
        zmq_ctx = zmq.Context.instance()
        if socket_addr not in self.zmq_sockets or self.zmq_sockets[socket_addr].closed:
            self.zmq_sockets[socket_addr] = zmq_ctx.socket(zmq.PUB)
            self.logger.info("Binding PUB socket to {}".format(socket_addr))
            self.zmq_sockets[socket_addr].bind(socket_addr)
            if 'zmq_sndhwm' in self.config:
                self.zmq_sockets[socket_addr].setsockopt(zmq.SNDHWM, self.config['zmq_sndhwm'])
        pub = self.zmq_sockets[socket_addr]
        self.logger.debug("PUBlishing on {}/{}".format(socket_addr, topic))
        pub.send_multipart((topic,) + msgparts)

    @log_exceptions
    def close_all_zmq_sockets(self):
        """Closes all streams and sockets and cleans up the dictionaries holding them"""
        for zmqs in itertools.chain(self.zmq_sockets.values(), self.zmq_streams.values()):
            if not zmqs or zmqs.closed:
                continue
            zmqs.close()
        self.zmq_sockets = {}
        self.zmq_streams = {}

    @log_exceptions
    def reload(self, *args, **kwargs):
        """Close sockets on reload, they will get re-opened if needed"""
        self.close_all_zmq_sockets()
        super(ZMQMixin, self).reload(*args, **kwargs)

    @log_exceptions
    def cleanup(self, *args, **kwargs):
        """We must ensure the sockets get closed for a clean exit"""
        self.close_all_zmq_sockets()
        super(ZMQMixin, self).cleanup(*args, **kwargs)
