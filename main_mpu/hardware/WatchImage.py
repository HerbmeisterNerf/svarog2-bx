############ standard libraries ############
import threading
import queue
import socket
import os

############ custom libraries ############
from declarations import *
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
        imageSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        imageSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        imageSocket.bind(('10.104.81.192', imageSocketPort))
        print("Image socket defined.")
        
        while True:
            try:
                send_bool = True#ImageDeclarations.send_image.get()
                print(send_bool)

                if send_bool:
                    print("qxz")
                    ImageDeclarations.send_image.put(False)
                    UDP_client_info_image = (commandAdd, imageSocketPort)
                    #i = SendImage(imageSocket, imgbuffer, UDP_client_info_image)
                    #i.join()
                    while True:
                        print("Sending image...")
                        path = "RealTime.jpg"
                        total_size = os.path.getsize(path)

                        latest_packet = f"{total_size}".encode('utf-8') + b'\n'  # Send the size of the image
                        print("Size: ", total_size)
                        #self.rate, add = self.socket.recvfrom(10)
                        #print("Rate: ", self.rate.decode())

                        imageSocket.sendto(latest_packet,UDP_client_info_image)

                        print("Socket: ",imageSocket)
                        
                        with open(path, 'rb') as f:
                            
                            # while True:
                            print("Reading file")
                            time.sleep(2)#time.sleep(float(self.rate))
                            #     bytes_read = f.read(self.buffer)
                            #     # print("Bytes: ", bytes_read)
                            #     if not bytes_read:
                            #         break  # File transmitting is done
                                # self.latest_packet == bytes_read
                            latest_packet = f.read(imgbuffer)
                            print("Packet:",latest_packet)
                            # if(latest_packet==""):
                            #     break
                            imageSocket.sendto(latest_packet,UDP_client_info_image)
                            print("Packet Sent")
                    #i.start()
                    
                
                time.sleep(2)

            except Exception as e:
                print(f'An exception occurred in the Watch Image: {e}')
