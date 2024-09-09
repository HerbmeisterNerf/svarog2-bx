############ standard libraries ############
import threading

############ custom libraries ############


############ class ############
class WaitForConnection(threading.Thread):
    '''
    This class is responsible for requesting a new telemtry package and updating it in the GUI
    '''


############ Initializer ############

    def __init__(self, queue, socket):
        super().__init__()
        #Define selfs here
        self.queue = queue
        self.socket = socket

############ Methods ############

    def run(self):
        try:
            self.socket.listen(1)
            print('Command socket open waiting for connection...')
            self.socket, TCPadd = self.socket.accept()
            print('Connection established with ' + TCPadd[0])
            status= True
            self.queue.put((self.socket,status,TCPadd[0]))
        except Exception as e:
            print(f'An exception occurred: {e}')

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
