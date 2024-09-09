############ standard libraries ############
import threading
import time

############ custom libraries ############


############ class ############
class Sleeper(threading.Thread):
    '''
    This class is responsible for requesting a new telemtry package and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self, timer):
        super().__init__()
        self.timer = timer

############ Methods ############

    def run(self):
        time.sleep(self.timer)

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
