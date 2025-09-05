from queue import Queue
from queue import Empty as QueueEmptyException
from declarations import *

class TempController(threading.Thread):
    """This a very basic PI controller with difference eqn:
        y = ax[n] + bx[n-1] + cn[n-2] etc."""

    def __init__(self, peripheral_name: str):
        """driver name of peripheral in peripheral_requests """
        self.coeffs = np.array([0.2]*5)
        self.function_size = len(self.coeffs)
        self.input_queue = Queue(maxsize=self.function_size*2)
        self.setpoint = 25  # degrees C?
        self.setpoint_lock = threading.Lock()
        self.g = np.zeros(self.function_size)
        self.peripheral_name = peripheral_name
        self.continue_run = True

    def run(self):
        while self.continue_run:
            time.sleep(0.0001)
            r = 0
            for i in range(self.function_size-1, -1, -1):
                try:
                    r += self.coeffs[i]*self.input_queue.get()
                except QueueEmptyException:
                    break
            self.input_queue.task_done()
            with self.setpoint_lock:
                with peripheral_requests_lock:
                    if r < self.setpoint:  # start heating
                        peripheral_requests[self.peripheral_name] = 1
                    else:
                        peripheral_requests[self.peripheral_name] = 0

    def stop_t(self):
        self.continue_run = False

    def start_t(self):
        self.continue_run = True

    def update_setpoint(self, sp):
        with self.setpoint_lock:
            self.setpoint = sp
