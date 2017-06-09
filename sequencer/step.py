import time

from core.decorators import log_exceptions
from core.mixins import LoggerMixin


class SequenceStep(LoggerMixin):
    """
    Single step in a sequence, stepconfig is dict
    {
        "motors": {
            "Motor1": [20, 100] # Move to 20% at 100% speed, 
        }
        "dwell": 1.5 # seconds
    }
    """
    started = None
    dwell_started = None

    def __init__(self, stepconfig, motors, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = stepconfig
        self.motors = motors

    @log_exceptions
    def start(self):
        if self.started:
            raise RuntimeError("Can only be started once")
        self.started = time.time()
        for mkey in self.config['motors'].keys():
            if mkey not in self.motors:
                self.logger.warning("Configured motor '{}' is not available".format(mkey))
            motor = self.motors[mkey]
            pos, speed = self.config['motors'][mkey]
            if not motor.ready:
                self.logger.warning("Motor '{}' is not ready".format(mkey))
            motor.go_to(pos, speed)

    @log_exceptions
    def _motors_done(self):
        ret = True
        for mkey in self.config['motors'].keys():
            if mkey not in self.motors:
                continue
            if not self.motors[mkey].ready:
                ret = False
                break
        return ret

    @log_exceptions
    def done(self):
        if not self._motors_done():
            return False
        if not self.dwell_started:
            self.logger.debug("Motors done, starting {}s dwell".format(self.config['dwell']))
            self.dwell_started = time.time()
            return False
        if (time.time() - self.dwell_started) < self.config['dwell']:
            return False
        return True