import struct

from core.decorators import log_exceptions
from core.mixins import LoggerMixin


class XbeeNode(LoggerMixin):
    """Simple encapsulation for an XBee node, makes it less painfull to handle all the bookkeeping"""
    node_identifier = None
    short_addr = None
    long_addr = None
    xb = None  # xbee instance

    def __init__(self, xbee, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.xb = xbee
        self.short_addr = kwargs['short_addr']
        # TODO: autodiscover this if not given
        self.long_addr = kwargs['long_addr']
        self.node_identifier = kwargs['node_identifier']

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
        send_args = [ord(x) for x in send_bytes]
        self.tx(*send_args)
