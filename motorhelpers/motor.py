from core.decorators import log_exceptions
from core.mixins import LoggerMixin


class KaraMoottori(LoggerMixin):
    node = None
    ready = False

    def __init__(self, node, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node = node
        self.node.rx_callbacks.append(self.node_rx_callback)
        self.config = config

    @log_exceptions
    def node_rx_callback(self, packet, node):
        """Handle messages from node, set ready-state accordingly"""
        pass

    @log_exceptions
    def stop(self, packet, node):
        """Send stop-command to node"""
        raise NotImplemented()

    @log_exceptions
    def go_to(self, len_percent, speed_percent=None):
        """Move to position (given as percentage of full travel), if travel speed is not defined previous value held
        in the controller memory will be used"""
        if speed_percent:
            raise NotImplemented()
        raise NotImplemented()
