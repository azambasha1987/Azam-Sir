#!/usr/bin/env bash
# ==============================================================================
# azambasha-update-banner.sh
# Regenerates /etc/issue with the current live IP address at every boot.
# Installed as a systemd one-shot service so the console banner is always correct.
# ==============================================================================

# Prefer pnet0 (the bridge), fall back to any routed interface
get_ip() {
    local ip
    ip=$(ip -4 addr show pnet0 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 | head -n1)
    [ -n "$ip" ] && echo "$ip" && return

    ip=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -n1)
    [ -n "$ip" ] && echo "$ip" && return

    ip=$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -v '^127\.' | head -n1)
    [ -n "$ip" ] && echo "$ip" && return

    echo "127.0.0.1"
}

HOST_IP="$(get_ip)"

cat > /etc/issue << EOF

============================================================
           Azam Basha v8 Virtual Network Emulator
============================================================
  Web UI Access   : https://${HOST_IP}/
  Default User    : admin
  Default Pass    : azam
  SSH Management  : ssh root@${HOST_IP} (Password: azam)
============================================================

\S (\l)

EOF

cp -f /etc/issue /etc/issue.net 2>/dev/null || true
echo "[azambasha-banner] Updated /etc/issue -> IP: ${HOST_IP}"
