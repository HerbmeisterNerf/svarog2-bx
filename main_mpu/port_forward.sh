#!/usr/bin/env bash
# Port-forward 172.16.18.191:4000 (eth0) <-> 192.168.78.2:4000 (eth1)
# Both directions: incoming connections to :4000 are DNAT'd to the destination,
# and reply traffic is SNAT'd so the return path works via conntrack.
set -euo pipefail

IF_IN="eth0"          # interface where 172.16.18.191 lives
IF_OUT="eth1"         # interface where 192.168.78.2 lives
SRC_IP="172.16.18.191"
DST_IP="192.168.78.2"
PORT="4000"

if [[ $EUID -ne 0 ]]; then
  echo "Error: must run as root." >&2
  exit 1
fi

# Enable IP forwarding in the kernel
sysctl -w net.ipv4.ip_forward=1 >/dev/null

# Flush any stale rules for this port (idempotent)
iptables -t nat -D PREROUTING  -i "$IF_IN" -p tcp -d "$SRC_IP" --dport "$PORT" -j DNAT --to-destination "$DST_IP:$PORT" 2>/dev/null || true
iptables -t nat -D POSTROUTING -o "$IF_OUT" -p tcp -d "$DST_IP" --dport "$PORT" -j MASQUERADE                         2>/dev/null || true
iptables -D FORWARD -i "$IF_IN" -o "$IF_OUT" -p tcp -d "$DST_IP" --dport "$PORT" -j ACCEPT                              2>/dev/null || true
iptables -D FORWARD -i "$IF_OUT" -o "$IF_IN"  -p tcp -s "$DST_IP" --sport "$PORT" -j ACCEPT                              2>/dev/null || true

# --- DNAT: incoming connections to 172.16.18.191:4000 -> 192.168.78.2:4000 ---
iptables -t nat -A PREROUTING  -i "$IF_IN" -p tcp -d "$SRC_IP" --dport "$PORT" -j DNAT --to-destination "$DST_IP:$PORT"

# --- MASQUERADE: reply packets from 192.168.78.2 exit via this machine --------
iptables -t nat -A POSTROUTING -o "$IF_OUT" -p tcp -d "$DST_IP" --dport "$PORT" -j MASQUERADE

# --- FORWARD chain: allow the forwarded traffic both ways --------------------
iptables -A FORWARD -i "$IF_IN"  -o "$IF_OUT" -p tcp -d "$DST_IP" --dport "$PORT" -j ACCEPT
iptables -A FORWARD -i "$IF_OUT" -o "$IF_IN"  -p tcp -s "$DST_IP" --sport "$PORT" -j ACCEPT

echo "Port forwarding active: $SRC_IP:$PORT ($IF_IN) <-> $DST_IP:$PORT ($IF_OUT)"
