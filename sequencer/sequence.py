from core.decorators import log_exceptions
from core.mixins import LoggerMixin

from .step import SequenceStep


class Sequence(LoggerMixin, object):
    """
    sequenceconfig is dict
    {
        "loop": True,
        "start_with_home": False
        "steps": [ ... ]  # list of SequenceStep configurations
    }
    """
    current_step_no = -1
    current_step_obj = None
    done = False

    def __init__(self, sequenceconfig, motors, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.debug("initializing sequencer")
        self.config = sequenceconfig
        self.motors = motors
        if self.config['start_with_home']:
            for mkey in self.motors.keys():
                self.logger.debug("Homing {}".format(mkey))
                self.motors[mkey].home()

    @log_exceptions
    def motors_ready(self):
        ret = True
        for mkey in self.motors.keys():
            if not self.motors[mkey].ready:
                self.logger.debug("{} is NOT ready".format(mkey))
                ret = False
            else:
                self.logger.debug("{} is READY".format(mkey))
        return ret

    @log_exceptions
    def iterate(self):
        """Runs a step if previous one is ready"""
        if self.done:
            raise StopIteration()
        if self.current_step_no == -1:
            # Still homing ot otherwise not ready.
            if not self.motors_ready():
                self.logger.debug("Waiting for motors before starting sequence")
                return False
        if self.current_step_obj and not self.current_step_obj.done():
            self.logger.debug("Waiting for step to complete")
            return False
        self.current_step_no += 1
        if self.config['loop']:
            self.current_step_no = self.current_step_no % len(self.config['steps'])
        else:
            if self.current_step_no >= len(self.config['steps']):
                self.done = True
                return False
        self.current_step_obj = SequenceStep(
            self.config['steps'][self.current_step_no],
            self.motors,
            logger_name=self.logger_name
        )
        self.current_step_obj.start()
        return True
