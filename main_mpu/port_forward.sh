#!/usr/bin/env bash
# Forward the CUBESAT command/telemetry ports through the EBOX so the ground
# station reaches both boards via a single IP (172.16.18.191).
#
#   EBOX :8016  ->  192.168.78.2:8006   (CUBESAT command)
#   EBOX :8015  ->  192.168.78.2:8005   (CUBESAT telemetry)
#   EBOX :1238  ->  192.168.78.2:1234   (CUBESAT RTSP, TCP+UDP)
#
# On the frontend, point the CUBESAT panel at the EBOX IP with the forwarded
# ports:   IP 172.16.18.191   cmd 8016   telem 8015
#
# Run on the EBOX as root.
set -euo pipefail

IF_IN="eth0"          # interface where 172.16.18.191 lives (ground)
IF_OUT="eth1"         # interface where 192.168.78.2 lives (cubesat link)
SRC_IP="172.16.18.191"
DST_IP="192.168.78.2"

# proto:listen_port:dst_port pairs
FORWARDS=(
  "tcp:8016:8006"   # CUBESAT command
  "tcp:8015:8005"   # CUBESAT telemetry
  # "udp:1238:1234"   # CUBESAT RTSP (RTP/RTSP over UDP)
  # "tcp:1238:1234"   # CUBESAT RTSP (fallback over TCP)
)

if [[ $EUID -ne 0 ]]; then
  echo "Error: must run as root." >&2
  exit 1
fi

# Enable IP forwarding in the kernel
sysctl -w net.ipv4.ip_forward=1 >/dev/null

add_fwd() {
  local proto="$1" lport="$2" tport="$3"

  # Flush any stale rules for this mapping (idempotent)
  iptables -t nat -D PREROUTING  -i "$IF_IN" -p "$proto" -d "$SRC_IP" --dport "$lport" -j DNAT --to-destination "$DST_IP:$tport" 2>/dev/null || true
  iptables -t nat -D POSTROUTING -o "$IF_OUT" -p "$proto" -d "$DST_IP" --dport "$tport" -j MASQUERADE                         2>/dev/null || true
  iptables -D FORWARD -i "$IF_IN" -o "$IF_OUT" -p "$proto" -d "$DST_IP" --dport "$tport" -j ACCEPT                              2>/dev/null || true
  iptables -D FORWARD -i "$IF_OUT" -o "$IF_IN" -p "$proto" -s "$DST_IP" --sport "$tport" -j ACCEPT                              2>/dev/null || true

  # DNAT: incoming connections to SRC_IP:lport -> DST_IP:tport
  iptables -t nat -A PREROUTING  -i "$IF_IN" -p "$proto" -d "$SRC_IP" --dport "$lport" -j DNAT --to-destination "$DST_IP:$tport"

  # MASQUERADE: reply packets from the destination exit via this machine
  iptables -t nat -A POSTROUTING -o "$IF_OUT" -p "$proto" -d "$DST_IP" --dport "$tport" -j MASQUERADE

  # FORWARD chain: allow forwarded traffic both ways
  iptables -A FORWARD -i "$IF_IN"  -o "$IF_OUT" -p "$proto" -d "$DST_IP" --dport "$tport" -j ACCEPT
  iptables -A FORWARD -i "$IF_OUT" -o "$IF_IN"  -p "$proto" -s "$DST_IP" --sport "$tport" -j ACCEPT

  echo "Forwarding: $SRC_IP:$lport ($IF_IN) -> $DST_IP:$tport ($IF_OUT) proto=$proto"
}

for fwd in "${FORWARDS[@]}"; do
  add_fwd "${fwd%%:*}" "$(echo "$fwd" | cut -d: -f2)" "$(echo "$fwd" | cut -d: -f3)"
done

echo "Port forwarding active for ${#FORWARDS[@]} mappings."