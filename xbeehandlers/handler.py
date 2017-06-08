import atexit
import binascii

from xbee import ZigBee

from core.decorators import log_exceptions
from core.mixins import LoggerMixin

from .node import XbeeNode


class handler(LoggerMixin):
    port = None
    nodes_by_identifier = {}
    nodes_by_shortaddr = {}
    xb = None

    def __init__(self, port, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.port = port
        self.xb = ZigBee(
            self.port,
            callback=self.xbee_callback,
            error_callback=self.error_callback,
            escaped=False
        )
        self.discover_nodes()

    @log_exceptions
    def xbee_callback(self, *args, **kwargs):
        print("!!! WOOOF!!!!")
        self.logger.debug("args: {} kwargs: {}", args, kwargs)
        packet = args[0]

        node_discovery_info = None
        if (packet['id'] == 'at_response'
                and packet['command'] == 'ND'):
            node_discovery_info = packet['parameter']

        if (packet['id'] == 'node_id_indicator'):
            node_discovery_info = packet
            node_discovery_info['node_identifier'] = packet['node_id']

        if (node_discovery_info
                and node_discovery_info.has_key('node_identifier')
                and node_discovery_info.has_key('source_addr')
                and node_discovery_info.has_key('source_addr_long')):
            # Node discovery packet
            node = XbeeNode(
                self.xb,
                short_addr=node_discovery_info['source_addr'],
                long_addr=node_discovery_info['source_addr_long'],
                node_identifier=node_discovery_info['node_identifier']
            )
            self.nodes_by_identifier[node.node_identifier] = node
            sa_hex = binascii.hexlify(node.short_addr)
            self.nodes_by_shortaddr[sa_hex] = node

            self.logger.info("New node {} at 0x{}", node.node_identifier, sa_hex)

    @log_exceptions
    def error_callback(self, *args):
        self.logger.error("Got error args: {}", args)
        try:
            raise args[0]
        except Exception:
            self.logger.exception("Raised exception via callback")

    @log_exceptions
    def quit(self, *args, **kwargs):
        self.xb.halt()
        self.port.close()

    @log_exceptions
    def discover_nodes(self):
        self.logger.debug("Calling ND")
        self.xb.at(command=b'ND')

    @log_exceptions
    def ping_nodes(self):
        """Ping each known node to make sure it's still alive, if not remove from node list (or maybe just mark dead somehow)"""
        # TODO: Implement
        pass

    @log_exceptions
    def tx_all(self, *args):
        for nodeid in self.nodes_by_identifier.keys():
            self.logger.debug("Sending to %s" % nodeid)
            self.nodes_by_identifier[nodeid].tx(*args)
        self.logger.debug("All sent")

    @log_exceptions
    def tx_string_all(self, *args):
        for nodeid in self.nodes_by_identifier.keys():
            self.logger.debug("Sending to %s" % nodeid)
            self.nodes_by_identifier[nodeid].tx_string(*args)
        self.logger.debug("All sent")
