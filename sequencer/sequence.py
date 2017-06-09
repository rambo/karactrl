from core.decorators import log_exceptions
from core.mixins import LoggerMixin

from .step import SequenceStep


class Sequence(LoggerMixin):
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

    def __init__(self, sequenceconfig, motors, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = sequenceconfig
        self.motors = motors
        if self.config['start_with_home']:
            for mkey in self.motors.keys():
                self.motors[mkey].home()

    @log_exceptions
    def _motors_done(self):
        ret = True
        for mkey in self.motors.keys():
            if not self.motors[mkey].ready:
                ret = False
                break
        return ret

    @log_exceptions
    def iterate(self):
        if self.current_step_no == -1:
            # Still homing ot otherwise not ready.
            if not self._motors_done():
                return False
        if self.current_step_obj and not self.current_step_obj.done():
            return False
        self.current_step_no = (self.current_step_no + 1) % len(self.config['steps'])
        self.current_step_obj = SequenceStep(self.config['steps'][self.current_step_no])
        self.current_step_obj.start()