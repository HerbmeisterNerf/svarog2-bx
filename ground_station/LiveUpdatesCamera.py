"""Requests and displays one camera snapshot over loss-tolerant UDP.

Flight-compatible camera path (replaces the old TCP/RTSP request): send a
``CMD_CAM_SNAPSHOT`` telecommand, then receive the JPEG back as chunked UDP
datagrams on ``IMG_UDP_PORT`` and reassemble them (see
``shared/image_snapshot.py``). A dropped chunk just means this frame never
completes — we time out and the next WatchCamera tick asks again. No stalls.
"""

############ standard libraries ############
import os
import sys
import threading
import datetime
import socket
from PIL import Image, ImageTk

############ custom libraries ############
from CommonData import CommonData
from PortCommunication import PortCommunication
# SpacePacketComms puts ../shared on sys.path and re-exports the TC builders.
from SpacePacketComms import SpacePacketComms, tc_cam_snapshot

_shared = os.path.join(os.path.dirname(__file__), '..', 'shared')
if _shared not in sys.path:
    sys.path.insert(0, _shared)
from image_snapshot import ImageReassembler, IMG_UDP_PORT

# Index 0 = the addressed node's own camera (/dev/video0), captured locally by
# the flight computer and streamed straight back. Secondary-MPU cameras (1..)
# are future work.
_LOCAL_CAM_INDEX = 0
_RECV_TIMEOUT = 6.0     # seconds to wait for a complete frame before giving up


class LiveUpdatesCamera(threading.Thread):
    '''Requests a single snapshot over UDP and updates the image panel.'''

############ Initializer ############

    def __init__(self, frame1_right, panel, imgtimestamp, save):
        super().__init__(daemon=True)
        self.frame1_right = frame1_right
        self.panel = panel
        self.timestamp = imgtimestamp
        self.save = save
        self.filename = None

############ Methods ############

    def run(self):
        if not CommonData.TCPSTATUS:
            print("Camera: EBOX not connected")
            return
        try:
            jpeg = self.__request_snapshot()
            if jpeg:
                self.__save_and_show(jpeg)
        except Exception as e:
            print(f'An exception occurred in LiveUpdatesCamera: {e}')

    def __request_snapshot(self) -> bytes:
        """Send the snapshot TC and reassemble the chunked JPEG reply."""
        sock = PortCommunication.open_UDP(IMG_UDP_PORT)
        sock.settimeout(_RECV_TIMEOUT)
        try:
            # Ask the flight computer for a fresh frame.
            SpacePacketComms.send_ebox_tc(tc_cam_snapshot(_LOCAL_CAM_INDEX))

            reasm = ImageReassembler()
            while True:
                try:
                    datagram, _ = sock.recvfrom(2048)
                except socket.timeout:
                    print("Camera: snapshot timed out (no/partial frame)")
                    return b""
                jpeg = reasm.add(datagram)
                if jpeg:
                    return jpeg
        finally:
            PortCommunication.close_UDP(sock)

    def __save_and_show(self, jpeg: bytes) -> None:
        if self.save.get() == 1:
            os.makedirs("images", exist_ok=True)
            self.filename = "images/" + datetime.datetime.now().strftime('%d_%H_%M_%S') + ".jpg"
        else:
            os.makedirs("images", exist_ok=True)
            self.filename = "images/receivedimage.jpg"
        with open(self.filename, 'wb') as f:
            f.write(jpeg)
        self.timestamp.set(datetime.datetime.now().strftime('%d_%H_%M_%S'))
        self.__update_image()

    def __update_image(self) -> None:
        img = ImageTk.PhotoImage(
            Image.open(self.filename).resize((600, 333), Image.Resampling.LANCZOS))
        self.panel.configure(image=img)
        self.panel.image = img

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
