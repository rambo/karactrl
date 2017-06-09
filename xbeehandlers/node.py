import struct

from core.decorators import log_exceptions
from core.mixins import LoggerMixin


class XbeeNode(LoggerMixin):
    """Simple encapsulation for an XBee node, makes it less painfull to handle all the bookkeeping"""
    node_identifier = None
    short_addr = None
    long_addr = None
    xb = None  # xbee instance
    rx_callbacks = []
    alive = True

    def __init__(self, xbee, *args, **kwargs):
        self.xb = xbee
        self.short_addr = kwargs.pop('short_addr')
        self.long_addr = kwargs.pop('long_addr')
        self.node_identifier = kwargs.pop('node_identifier')
        super().__init__(*args, **kwargs)

    @log_exceptions
    def rx(self, packet, *args):
        """Received packet, fire the callbacks"""
        self.alive = True
        for cb in self.rx_callbacks:
            cb(packet, self)

    @log_exceptions
    def tx(self, *args):
        """Send data to target node, each argument is single byte to send (if you have a tuple/list mydata you can pass it as arguments with *mydata"""
        data_packed = struct.pack("%dB" % len(args), *args)
        self.xb.tx(dest_addr=self.short_addr, dest_addr_long=self.long_addr, data=data_packed)

    @log_exceptions
    def tx_string(self, send_bytes):
        """Send a string (ASCII) to node, this will handle unpacking of the string to list of bytes and passing it correctly"""
        if not isinstance(send_bytes, bytes):  # ZMQ uses always bytes
            send_bytes = send_bytes.encode('utf-8')
        send_args = list(send_bytes)
        self.tx(*send_args)
