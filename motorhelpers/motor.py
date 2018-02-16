import binascii
import struct

from core.decorators import log_exceptions
from core.mixins import LoggerMixin


class KaraMoottori(LoggerMixin):
    name = None
    node = None
    ready = False
    homing = True
    target_pos = 0.0
    current_pos = 0.0

    def __init__(self, node, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.node = node
        self.name = self.node.node_identifier
        self.node.rx_callbacks.append(self.node_rx_callback)

    @log_exceptions
    def node_rx_callback(self, packet, node):
        """Handle messages from node, set ready-state accordingly"""
        data = packet['rf_data']
        if data[0] != ord('M'):
            self.logger.warning("{}: Got packet that did not start with 'M' don't know how to handle those".format(self.name))
            return

        # AVRs may be little-endian but we packe these values manually to network byte order
        current_steps = struct.unpack('>i', data[2:6])[0]
        target_steps = struct.unpack('>i', data[6:10])[0]
        self.target_pos = (target_steps / self.config['max_steps']) * 100
        self.current_pos = (current_steps / self.config['max_steps']) * 100

        if target_steps == current_steps:
            self.ready = True

        if data[:2] == b'MT':
            # Timed report
            if data[10]:
                self.ready = False
                self.homing = True
            else:
                self.homing = False
        if data[:2] == b'MS':
            # Stop callback
            self.ready = True

        self.logger.debug("{}: Current position {}% ({}), target position {}% ({})".format(
            self.name,
            self.current_pos,
            current_steps,
            self.target_pos,
            target_steps
        ))

    @log_exceptions
    def home(self):
        """Send stop-command to node"""
        self.ready = False
        self.node.tx_string(b"H")

    @log_exceptions
    def stop(self):
        """Send stop-command to node"""
        self.node.tx_string(b"S")

    def hex_encode_uint16_t(self, input):
        be = struct.pack('>H', input)
        return binascii.hexlify(be).upper()

    def hex_encode_int32_t(self, input):
        be = struct.pack('>i', input)
        return binascii.hexlify(be).upper()

    @log_exceptions
    def go_to(self, len_percent, speed_percent=None):
        """Move to position (given as percentage of full travel), if travel speed is not defined previous value held
        in the controller memory will be used"""
        self.ready = False
        len_percent = float(len_percent)
        speed_percent = float(speed_percent)
        if speed_percent:
            pps = int((self.config['max_speed'] / 100) * speed_percent)
            # sanity check
            if pps < 1:
                pps = 15
            msg = b"F" + self.hex_encode_uint16_t(pps)
            self.logger.debug("{}: Sending {}, pps={}".format(self.name, msg, pps))
            self.node.tx_string(msg)
        target_pos = int((self.config['max_steps'] / 100) * len_percent)
        msg = b"G" + self.hex_encode_int32_t(target_pos)
        self.logger.debug("{}: Sending {}, target_pos={} ({}%)".format(self.name, msg, target_pos, len_percent))
        self.node.tx_string(msg)
