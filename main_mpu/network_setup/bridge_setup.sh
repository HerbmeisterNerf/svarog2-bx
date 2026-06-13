#!/bin/bash
# EBOX R3B network bridge setup
# Run once at boot (before flight software starts) via systemd unit below.
#
# Physical topology:
#   eth0 = gondola Ethernet (from antenna → ground station)
#   eth1 = fiber optic modem port (→ CubeSat R3B)
#
# A kernel-level bridge (br0) is created joining both interfaces.
# The bridge runs in kernel space — if the Python flight software crashes,
# packets still pass through and the CubeSat remains reachable from ground.
#
# EBOX R3B itself gets an IP on br0 (192.168.1.10).
# CubeSat R3B should be configured with a static IP of 192.168.1.20/24.
# Ground station connects to both via the same subnet.

set -e

EBOX_IP="192.168.1.10/24"
ETH_GROUND="eth0"
ETH_FIBER="eth1"
BRIDGE="br0"

echo "[network_setup] Bringing up bridge ${BRIDGE}"

# Flush any existing addresses on member interfaces
ip addr flush dev ${ETH_GROUND} 2>/dev/null || true
ip addr flush dev ${ETH_FIBER}  2>/dev/null || true

# Create bridge if it doesn't already exist
ip link show ${BRIDGE} &>/dev/null || ip link add name ${BRIDGE} type bridge

# Add both interfaces to the bridge
ip link set ${ETH_GROUND} master ${BRIDGE}
ip link set ${ETH_FIBER}  master ${BRIDGE}

# Bring everything up
ip link set ${ETH_GROUND} up
ip link set ${ETH_FIBER}  up
ip link set ${BRIDGE} up

# Assign EBOX R3B's own IP on the bridge interface
ip addr add ${EBOX_IP} dev ${BRIDGE} 2>/dev/null || true

echo "[network_setup] Bridge up. EBOX IP: ${EBOX_IP}"
echo "[network_setup] Ground reachable via ${ETH_GROUND}, CubeSat via ${ETH_FIBER}"
