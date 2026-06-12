from queue import Queue
from queue import Empty as QueueEmptyException, Full as QueueFullException
from declarations import *

class TempController(threading.Thread):
    """This a very basic PI controller with difference eqn:
        y = ax[n] + bx[n-1] + cn[n-2] etc."""

    def __init__(self, peripheral_name: str, coeffs = [0.2]*5):
        """driver name of peripheral in peripheral_requests """
        super().__init__()
        self.coeffs = np.array(coeffs)
        self.function_size = len(self.coeffs)
        self.input_queue = Queue(maxsize=self.function_size*2)
        self.setpoint = 30  # degrees C?
        self.setpoint_lock = threading.Lock()
        self.g = np.zeros(self.function_size)
        self.peripheral_name = peripheral_name
        self.continue_run = True
        self.active = True

    def run(self):
        print(f"Tempcontroller {self.peripheral_name} started")
        while self.continue_run:
            if not self.active: continue
            time.sleep(1)
            r = 0
            if not self.input_queue.empty():
                for i in range(self.function_size-1, -1, -1):
                    try:
                        r += self.coeffs[i]*self.input_queue.get()
                    except QueueEmptyException:
                        break
                # self.input_queue.task_done()
                with self.setpoint_lock:
                    with peripheral_requests_lock:
                        if r < self.setpoint:  # start heating
                            peripheral_requests[self.peripheral_name] = 1
                            print(f"Controller requests {self.peripheral_name} ON")
                        else:
                            peripheral_requests[self.peripheral_name] = 0
                            print(f"Controller requests {self.peripheral_name} OFF")
            else:
                print(f"Controller {self.peripheral_name} has no data!")       
    def stop_t(self):
        self.continue_run = False

    def start_t(self):
        self.continue_run = True

    def update_setpoint(self, sp):
        with self.setpoint_lock:
            self.setpoint = sp

    def add_datapoint(self,x):
        if self.input_queue.full():
            self.input_queue.get()
        try:
            self.input_queue.put(x,block=True,timeout=0.0001)
            self.input_queue.task_done()
            print(f"Sent data {x} to controller {self.peripheral_name}")
        except QueueFullException:
            print(f"Failed to send temp data {x} to controller {self.peripheral_name}")