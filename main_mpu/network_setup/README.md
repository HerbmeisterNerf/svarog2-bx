# EBOX Network Setup

## Topology

```
Ground Station
      |
   Ethernet cable (from antenna)
      |
   EBOX R3B — eth0
   EBOX R3B — eth1 ──── Fiber Modem (gondola side)
                              |
                         Fiber + slip ring
                              |
                         Fiber Modem (CubeSat side)
                              |
                         CubeSat R3B — eth0
```

The EBOX R3B bridges `eth0` and `eth1` at the kernel level. Ground can reach
both R3Bs directly. If the EBOX Python software crashes, the bridge keeps
forwarding packets so the CubeSat remains reachable.

## IP Addresses

| Device | IP |
|--------|-----|
| Ground station | 192.168.1.1 |
| EBOX R3B (br0) | 192.168.1.10 |
| CubeSat R3B (eth0) | 192.168.1.20 |

## Installation on EBOX R3B

```bash
sudo cp bridge_setup.sh /usr/local/bin/svarog-bridge-setup.sh
sudo chmod +x /usr/local/bin/svarog-bridge-setup.sh
sudo cp svarog-bridge.service /etc/systemd/system/
sudo systemctl enable svarog-bridge.service
sudo systemctl start svarog-bridge.service
```

## CubeSat R3B static IP

Add to `/etc/network/interfaces` on the CubeSat R3B:

```
auto eth0
iface eth0 inet static
    address 192.168.1.20
    netmask 255.255.255.0
    gateway 192.168.1.1
```

## What survives EBOX software failure

| Failure mode | CubeSat reachable? |
|---|---|
| Python flight software crash | ✓ Yes — bridge is kernel-level |
| Python process hung/deadlocked | ✓ Yes |
| EBOX R3B kernel panic | ✗ No |
| EBOX R3B power loss | ✗ No |
| Fiber slip ring failure | ✗ No |
