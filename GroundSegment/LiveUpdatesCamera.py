############ standard libraries ############
import threading
import datetime
from PIL import Image, ImageTk 

############ custom libraries ############
from CommonData import CommonData
from PortCommunication import PortCommunication

############ class ############
class LiveUpdatesCamera(threading.Thread):
    '''
    This class is responsible for requesting a new image and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self,
                frame1_right,
                panel, imgtimestamp):

        super().__init__()
        self.frame1_right = frame1_right
        self.panel = panel
        self.timestamp = imgtimestamp
        self.rate = round(float(32/CommonData.imgbaudrate*8/1000),3)

############ Methods ############

    def run(self):
        try:
            if CommonData.TCPSTATUS == True:
                self.__request_image()
                self.__update_image()
            else:
                print("Not connected to server")
        except Exception as e:
            print(f'An exception occurred: {e}')

    def __request_image(self) -> None:
        self.filename = "receivedimage.jpg"
        client_UDP_socket = PortCommunication.open_UDP(CommonData.camera_port_UDP)
        message = "start:IMend:"
        CommonData.client_TCP_socket.send(message.encode())
        print("Receiving image...")
    
        msg, add = client_UDP_socket.recvfrom(10)
        client_UDP_socket.sendto(str(self.rate).encode(),(CommonData.server_name,CommonData.camera_port_UDP))
        total_size = int(msg.split(b'\n')[0])  # Receive the size of the image
        print("Size: ", total_size)
        received = 0

        with open(self.filename, 'wb') as f:
            while received < total_size:
                bytes_read = client_UDP_socket.recvfrom(32)[0]

                if not bytes_read:
                    break  # The socket is closed
                f.write(bytes_read)
                received += len(bytes_read)

        print("Image has been received.")
        self.timestamp.set(str(datetime.datetime.now().time()) )
        PortCommunication.close_UDP(client_UDP_socket)

    def __update_image(self) -> None:
        img = ImageTk.PhotoImage(Image.open(self.filename).resize((600, 333), Image.Resampling.LANCZOS))
        self.panel.configure(image=img)
        self.panel.image = img

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
