############ standard libraries ############
import threading
import queue

############ custom libraries ############
from CommonData import CommonData
from SendImage import SendImage

############ class ############
class WatchImage(threading.Thread):
    '''
    '''

############ Initializer ############

    def __init__(self):
        super().__init__()

############ Methods ############

    def run(self):
        while True:
            try:

                if CommonData.commandSocketStatus and CommonData.send_image:
                    CommonData.send_image = False
                    UDP_client_info_image = (CommonData.commandAdd, CommonData.imageSocketPort)
                    i = SendImage(CommonData.imageSocket, CommonData.imgbuffer, UDP_client_info_image)
                    i.start()
                    i.join()

            except Exception as e:
                print(f'An exception occurred in the Watch Image: {e}')
