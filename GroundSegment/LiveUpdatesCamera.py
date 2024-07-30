############ standard libraries ############
import threading
import socket
import tkinter as tk
import time
from PIL import Image, ImageTk 

############ custom libraries ############
from CommonData import CommonData

############ class ############
class LiveUpdatesCamera(threading.Thread):

    def __init__(self,
                queue,
                frame1_right,
                panel):

        super().__init__()
        self.queue = queue
        self.frame1_right = frame1_right
        self.panel = panel

    def run(self):
        while True:
            time.sleep(10)
            try:
                if CommonData.TCPSTATUS == True:
                    self.__request_image()
                    self.__update_image()
            except Exception as e:
                print(f'An exception occurred: {e}')

    def __request_image(self):
        self.filename = "receivedimage.jpg"
        self.__open_UDP_img() 
        message = "image"
        CommonData.client_TCP_socket.send(message.encode())
        print("Receiving image...")
    
        msg, add = self.client_UDP_socket_img.recvfrom(1024)
        total_size = int(msg.split(b'\n')[0])  # Receive the size of the image
        print("Size: ", total_size)
        received = 0

        with open(self.filename, 'wb') as f:
            while received < total_size:
                bytes_read = self.client_UDP_socket_img.recvfrom(1024)[0]

                if not bytes_read:
                    break  # The socket is closed
                f.write(bytes_read)
                received += len(bytes_read)

        print("Image has been received." , bytes_read)
        self.__close_UDP_img()

    def __open_UDP_img(self):
        # UDP
        client_UDP_port = 15000
        UDP_info = ("", client_UDP_port)
        self.client_UDP_socket_img = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_UDP_socket_img.bind(UDP_info)

    def __close_UDP_img(self):
        self.client_UDP_socket_img.close()

    def __update_image(self):
        img = ImageTk.PhotoImage(Image.open(self.filename).resize((320, 200), Image.Resampling.LANCZOS))
        self.panel.configure(image=img)
        self.panel.image = img

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
