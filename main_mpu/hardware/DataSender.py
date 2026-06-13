"""Gathers sensor data every 5 s and broadcasts a TM Space Packet over UDP.

Transport change (vs. TCP push):
  Old: write CSV + newline to a TCP socket held open by the ground station
  New: sendto UDP broadcast 255.255.255.255:8006 with a CCSDS Space Packet header
       and CRC-16-CCITT — no connection required, link drops cause no stalls
"""

import asyncio
import os
import sys
import time
import threading

from declarations import (
    peripheral_requests, peripheral_requests_lock,
    gpio_MOTCON_EFUSE_FLT,
)
from node_config import (
    NODE_ID, NUM_SECONDARY_MPUS, NUM_BW, NUM_HEATERS,
    NUM_TEMP_SENSORS, HEATER_SENSOR_PAIRS,
)
from RADXA_SPI_INTERFACE import PDU_ADC, THERMAL_ADC

_shared = os.path.join(os.path.dirname(__file__), '..', '..', 'shared')
sys.path.insert(0, _shared)

from space_packet import (
    build_packet, build_tm_data_field,
    PKT_TYPE_TM, APID_EBOX_TM, APID_CS_TM, TM_UDP_PORT,
)

_TM_BROADCAST = "255.255.255.255"

if NODE_ID == "CUBESAT":
    from cubesat_message_pack import CubeSatMessagePack
    from secondary_mpu_client import SecondaryMPUClient
    _secondary_client = SecondaryMPUClient()
    _TM_APID = APID_CS_TM
else:
    from ebox_message_pack import EBoxMessagePack
    _TM_APID = APID_EBOX_TM


class SendTelem(threading.Thread):
    """Broadcasts a TM Space Packet every 5 s over a UDP broadcast socket."""

    def __init__(self, tx_sock, temp_controllers, uart_flywheel=None, tc_ack=None):
        super().__init__(daemon=True)
        self._sock = tx_sock
        self.pdu_adc = PDU_ADC()
        self.thermal_adc = THERMAL_ADC()
        self.controllers = temp_controllers
        self.uart_flywheel = uart_flywheel
        self.tc_ack = tc_ack if tc_ack is not None else {"seq": 0}
        self._pkg_count = 0

    def run(self):
        while True:
            time.sleep(5)
            try:
                asyncio.run(self._telem_loop())
            except Exception as e:
                print(f"[{NODE_ID}] Telem error: {e}")

    async def _telem_loop(self):
        pdu, thermal = await self._read_adcs()

        csv_str = (self._build_cubesat(pdu, thermal) if NODE_ID == "CUBESAT"
                   else self._build_ebox(pdu, thermal))

        if thermal != "ERROR":
            for ctrl in self.controllers:
                idx = HEATER_SENSOR_PAIRS[ctrl.peripheral_name]
                ctrl.add_datapoint(thermal[idx])

        data_field = build_tm_data_field(int(time.time()), self.tc_ack["seq"], csv_str)
        packet = build_packet(_TM_APID, PKT_TYPE_TM, self._pkg_count & 0x3FFF, data_field)
        self._sock.sendto(packet, (_TM_BROADCAST, TM_UDP_PORT))
        self._pkg_count += 1

    # ------------------------------------------------------------------ EBOX

    def _build_ebox(self, pdu, thermal):
        p = EBoxMessagePack()
        p.package_count = self._pkg_count
        p.timestamp = int(time.time())

        if pdu != "ERROR":
            p.voltage_5V   = round(pdu[0], 3)
            p.voltage_12V  = round(pdu[1], 3)
            p.voltage_24V  = round(pdu[2], 3)
            p.voltage_28V  = round(pdu[3], 3)
            p.current_5V   = round(pdu[4], 3)
            p.current_12V  = round(pdu[5], 3)
            p.current_24V  = round(pdu[6], 3)

        if thermal != "ERROR":
            p.ebox_temp = round(thermal[0], 1)
            for i in range(min(NUM_TEMP_SENSORS, 6)):
                setattr(p, f"temp_{i+1}_status", round(thermal[i], 1))

        with peripheral_requests_lock:
            for n in range(1, NUM_HEATERS + 1):
                setattr(p, f"heater_{n}_status",
                        peripheral_requests.get(f"HEAT_{n}", 0))
            for n in range(1, min(NUM_BW, 2) + 1):
                setattr(p, f"burn_wire_{n}_status",
                        peripheral_requests.get(f"BW_{n}", 0))

        try:
            p.motor_fault = gpio_MOTCON_EFUSE_FLT.read()
        except Exception:
            pass

        if self.uart_flywheel:
            try:
                self.uart_flywheel.send("GS_0\n")
                resp = self.uart_flywheel.receive(timeout=1.0)
                if resp:
                    parts = resp.strip().split(",")
                    if len(parts) >= 2:
                        p.motor_speed = float(parts[1])
            except Exception:
                pass

        return p.generate_string()

    # --------------------------------------------------------------- CubeSat

    def _build_cubesat(self, pdu, thermal):
        p = CubeSatMessagePack()
        p.package_count = self._pkg_count
        p.timestamp = int(time.time())

        if pdu != "ERROR":
            p.voltage_5V   = round(pdu[0], 3)
            p.voltage_12V  = round(pdu[1], 3)
            p.voltage_28V  = round(pdu[3], 3)
            p.current_5V   = round(pdu[4], 3)
            p.current_12V  = round(pdu[5], 3)

        if thermal != "ERROR":
            p.cs_temp = round(thermal[0], 1)
            for i in range(min(NUM_TEMP_SENSORS, 6)):
                setattr(p, f"temp_{i+1}_status", round(thermal[i], 1))

        with peripheral_requests_lock:
            for n in range(1, NUM_HEATERS + 1):
                setattr(p, f"heater_{n}_status",
                        peripheral_requests.get(f"HEAT_{n}", 0))
            for n in range(1, NUM_BW + 1):
                setattr(p, f"bw_{n}_status",
                        peripheral_requests.get(f"BW_{n}", 0))

        for i in range(1, min(NUM_SECONDARY_MPUS, 2) + 1):
            status = _secondary_client.get_status(i)
            setattr(p, f"rz_{i}_status", 1 if status.get("alive") else 0)

        if self.uart_flywheel:
            try:
                self.uart_flywheel.send("GS_0\n")
                resp = self.uart_flywheel.receive(timeout=1.0)
                if resp:
                    parts = resp.strip().split(",")
                    if len(parts) >= 2:
                        p.flywheel_speed = float(parts[1])
                        p.flywheel_mode = int(parts[2]) if len(parts) > 2 else 0
            except Exception:
                pass

        return p.generate_string()

    # ------------------------------------------------------------------ ADCs

    async def _read_adcs(self):
        try:
            pdu = self.pdu_adc.poll()
        except Exception as e:
            pdu = "ERROR"
            print(f"[{NODE_ID}] PDU ADC read failed: {e}")
        try:
            thermal = self.thermal_adc.poll()
        except Exception as e:
            thermal = "ERROR"
            print(f"[{NODE_ID}] Thermal ADC read failed: {e}")
        return pdu, thermal
