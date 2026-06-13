"""UDP telemetry receiver — dispatches TM Space Packets to the correct queue.

A single instance handles both nodes:
  APID 0x001  (EBOX TM)    → CommonData.ebox_telem_queue
  APID 0x002  (CubeSat TM) → CommonData.cs_telem_queue

Replaces the old TCPTelemReader which pulled from a TCP stream.  The flight
computers now broadcast TM datagrams to 255.255.255.255:8006 every 5 s;
this thread receives them on any network interface.
"""

import socket
import threading
import time

from CommonData import CommonData
from SpacePacketComms import SpacePacketComms

import os
import sys
_shared = os.path.join(os.path.dirname(__file__), '..', 'shared')
sys.path.insert(0, _shared)
from space_packet import TM_UDP_PORT, APID_EBOX_TM, APID_CS_TM


class UDPTelemReader(threading.Thread):
    """Daemon thread — start once at application startup, runs forever."""

    def __init__(self):
        super().__init__(daemon=True)

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", TM_UDP_PORT))
        sock.settimeout(1.0)

        while True:
            try:
                raw, addr = sock.recvfrom(4096)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"UDPTelemReader recv error: {e}")
                time.sleep(0.5)
                continue

            result = SpacePacketComms.parse_tm(raw)
            if result is None:
                print(f"UDPTelemReader: bad/corrupt packet from {addr}")
                continue

            apid        = result["apid"]
            csv_payload = result["csv_payload"]

            if apid == APID_EBOX_TM:
                CommonData.last_ebox_tc_ack = result["last_tc_seq"]
                CommonData.last_ebox_tm_time = time.time()
                queue = CommonData.ebox_telem_queue
            elif apid == APID_CS_TM:
                CommonData.last_cs_tc_ack = result["last_tc_seq"]
                CommonData.last_cs_tm_time = time.time()
                queue = CommonData.cs_telem_queue
            else:
                print(f"UDPTelemReader: unknown APID 0x{apid:03X} from {addr}")
                continue

            # Discard any stale packet; keep only the freshest
            while not queue.empty():
                try:
                    queue.get_nowait()
                except Exception:
                    break
            queue.put(csv_payload)
