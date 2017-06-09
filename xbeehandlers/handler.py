import time
import binascii

from xbee import ZigBee

from core.decorators import log_exceptions
from core.mixins import LoggerMixin

from .node import XbeeNode


class handler(LoggerMixin, object):
    port = None
    nodes_by_identifier = {}
    nodes_by_shortaddr = {}
    xb = None
    new_node_callbacks = []
    last_discovery = 0

    def __init__(self, port, *args, **kwargs):
        self.port = port
        self.xb = ZigBee(
            self.port,
            callback=self.xbee_callback,
            error_callback=self.error_callback,
            escaped=False
        )
        super().__init__(*args, **kwargs)
        self.discover_nodes()

    @log_exceptions
    def xbee_callback(self, *args, **kwargs):
        self.logger.debug("args: {} kwargs: {}".format(args, kwargs))
        packet = args[0]

        node_discovery_info = None
        if (packet['id'] == 'at_response'
                and packet['command'] == b'ND'):
            node_discovery_info = packet['parameter']

        if (packet['id'] == 'node_id_indicator'):
            node_discovery_info = packet
            node_discovery_info['node_identifier'] = packet['node_id']

        if (node_discovery_info
                and 'node_identifier' in node_discovery_info
                and 'source_addr' in node_discovery_info
                and 'source_addr_long' in node_discovery_info):
            # Node discovery packet
            node = XbeeNode(
                self.xb,
                short_addr=node_discovery_info['source_addr'],
                long_addr=node_discovery_info['source_addr_long'],
                node_identifier=node_discovery_info['node_identifier'],
                logger_name=self.logger_name
            )
            self.nodes_by_identifier[node.node_identifier] = node
            sa_hex = binascii.hexlify(node.short_addr)
            self.nodes_by_shortaddr[sa_hex] = node

            self.logger.info("New node {} at 0x{}".format(node.node_identifier, sa_hex))
            # Trigger callbacks registered for new nodes
            for cb in self.new_node_callbacks:
                cb(node)

        if packet['id'] == 'rx':
            # Trigger node rx callbacks
            sa_hex = binascii.hexlify(packet['source_addr'])
            if sa_hex not in self.nodes_by_shortaddr:
                self.logger.info("Got message from unkown node {}".format(sa_hex))
                if time.time() - self.last_discovery > 5:
                    self.logger.debug("Triggering new node discovery")
                    self.discover_nodes()
            else:
                self.nodes_by_shortaddr[sa_hex].rx(packet)

    @log_exceptions
    def error_callback(self, *args):
        self.logger.error("Got error args: {}".format(args))
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
        self.last_discovery = time.time()
        self.xb.at(command=b'ND')

    @log_exceptions
    def ping_nodes(self):
        """Ping each known node to make sure it's still alive, if not mark it dead and remove from our list"""
        # TODO: Implement
        pass

    @log_exceptions
    def tx_all(self, *args):
        for nodeid in self.nodes_by_identifier.keys():
            self.logger.debug("Sending to {}".format(nodeid))
            self.nodes_by_identifier[nodeid].tx(*args)
        self.logger.debug("All sent")

    @log_exceptions
    def tx_string_all(self, *args):
        for nodeid in self.nodes_by_identifier.keys():
            self.logger.debug("Sending to {}".format(nodeid))
            self.nodes_by_identifier[nodeid].tx_string(*args)
        self.logger.debug("All sent")
