############ standard libraries ############
import threading

############ custom libraries ############


############ class ############
class ProbeTCP(threading.Thread):
    '''
    This class is responsible for requesting a new telemtry package and updating it in the GUI
    '''


############ Initializer ############

    def __init__(self, queue,socket,address,port):
        super().__init__()
        #Define selfs here
        self.queue = queue
        self.socket = socket
        self.info = (address, port)

############ Methods ############

    def run(self):
        try:
            msg = "ACK"
            self.socket.sendto(msg.encode(), self.info)
            print("Sent it mate")
            ack = self.socket.recv(3)
            print("Received it mate")
            if ack.decode() == "ACK":
                status = True
            else:
                status = False
            self.queue.put((status))
        except Exception as e:
            print(f'An exception occurred: {e}')

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
