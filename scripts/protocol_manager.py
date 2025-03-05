#!/usr/bin/env python3
import json
import subprocess
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ProtocolManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.xray_config = '/usr/local/etc/xray/config.json'
        self.ssh_config = '/etc/ssh/sshd_config'
        self.ovpn_config = '/etc/openvpn/server.conf'
        self.l2tp_config = '/etc/xl2tpd/xl2tpd.conf'
        self.ipsec_config = '/etc/ipsec.conf'

    def configure_ssh(self, port: int, protocols: Dict[str, Any]) -> bool:
        """Configure SSH protocols"""
        try:
            # Configure OpenSSH
            if protocols.get('openssh', {}).get('enabled', True):
                self._configure_openssh(port)

            # Configure Dropbear
            if protocols.get('dropbear', {}).get('enabled', False):
                self._configure_dropbear(port)

            # Configure Squid
            if protocols.get('squid', {}).get('enabled', False):
                self._configure_squid(port)

            # Configure UDPGW
            if protocols.get('udpgw', {}).get('enabled', False):
                self._configure_udpgw(port)

            # Configure SlowDNS
            if protocols.get('slowdns', {}).get('enabled', False):
                self._configure_slowdns(port)

            # Configure WebSocket
            if protocols.get('websocket', {}).get('enabled', False):
                self._configure_websocket(port)

            # Restart SSH service
            subprocess.run(['systemctl', 'restart', 'sshd'])
            return True
        except Exception as e:
            logger.error(f"Error configuring SSH: {str(e)}")
            return False

    def _configure_openssh(self, port: int):
        """Configure OpenSSH"""
        with open(self.ssh_config, 'w') as f:
            f.write(f"""
Port {port}
PermitRootLogin no
PasswordAuthentication yes
X11Forwarding no
MaxSessions 1
ClientAliveInterval 60
ClientAliveCountMax 3
""")

    def _configure_dropbear(self, port: int):
        """Configure Dropbear"""
        with open('/etc/default/dropbear', 'w') as f:
            f.write(f"""
DROPBEAR_PORT={port}
DROPBEAR_EXTRA_ARGS="-w -g"
""")

    def _configure_squid(self, port: int):
        """Configure Squid"""
        with open('/etc/squid/squid.conf', 'w') as f:
            f.write(f"""
http_port {port}
visible_hostname boxvps
""")

    def _configure_udpgw(self, port: int):
        """Configure UDPGW"""
        with open('/etc/systemd/system/udpgw.service', 'w') as f:
            f.write(f"""
[Unit]
Description=UDPGW Service
After=network.target

[Service]
ExecStart=/usr/bin/udpgw -l {port} -s 127.0.0.1:22
Restart=always

[Install]
WantedBy=multi-user.target
""")

    def _configure_slowdns(self, port: int):
        """Configure SlowDNS"""
        with open('/etc/systemd/system/slowdns.service', 'w') as f:
            f.write(f"""
[Unit]
Description=SlowDNS Service
After=network.target

[Service]
ExecStart=/usr/bin/slowdns -l {port} -s 127.0.0.1:22
Restart=always

[Install]
WantedBy=multi-user.target
""")

    def _configure_websocket(self, port: int):
        """Configure WebSocket"""
        with open('/etc/nginx/conf.d/websocket.conf', 'w') as f:
            f.write(f"""
server {{
    listen {port};
    server_name {self.config['domain']};

    location / {{
        proxy_pass http://127.0.0.1:22;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
""")

    def configure_xray(self, port: int, protocols: Dict[str, Any]) -> bool:
        """Configure Xray protocols"""
        try:
            config = {
                'inbounds': [],
                'outbounds': [
                    {
                        'protocol': 'freedom',
                        'settings': {}
                    }
                ]
            }

            # Configure VMess
            if protocols.get('vmess', {}).get('enabled', True):
                config['inbounds'].append({
                    'port': port,
                    'protocol': 'vmess',
                    'settings': {
                        'clients': []
                    },
                    'streamSettings': {
                        'network': 'ws',
                        'wsSettings': {
                            'path': '/vmess'
                        }
                    }
                })

            # Configure VLESS
            if protocols.get('vless', {}).get('enabled', False):
                config['inbounds'].append({
                    'port': port + 1,
                    'protocol': 'vless',
                    'settings': {
                        'clients': []
                    },
                    'streamSettings': {
                        'network': 'ws',
                        'wsSettings': {
                            'path': '/vless'
                        }
                    }
                })

            # Configure Trojan
            if protocols.get('trojan', {}).get('enabled', False):
                config['inbounds'].append({
                    'port': port + 2,
                    'protocol': 'trojan',
                    'settings': {
                        'clients': []
                    },
                    'streamSettings': {
                        'network': 'ws',
                        'wsSettings': {
                            'path': '/trojan'
                        }
                    }
                })

            # Save configuration
            with open(self.xray_config, 'w') as f:
                json.dump(config, f, indent=4)

            # Restart Xray service
            subprocess.run(['systemctl', 'restart', 'xray'])
            return True
        except Exception as e:
            logger.error(f"Error configuring Xray: {str(e)}")
            return False

    def configure_ovpn(self, config: Dict[str, Any]) -> bool:
        """Configure OpenVPN protocols"""
        try:
            # Configure OpenVPN server
            with open(self.ovpn_config, 'w') as f:
                f.write(f"""
port {config['port']}
proto {config['protocol']}
dev tun
ca /etc/openvpn/ca.crt
cert /etc/openvpn/server.crt
key /etc/openvpn/server.key
dh /etc/openvpn/dh.pem
server 10.8.0.0 255.255.255.0
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 8.8.8.8"
push "dhcp-option DNS 8.8.4.4"
keepalive 10 120
cipher AES-256-CBC
user nobody
group nogroup
persist-key
persist-tun
status /etc/openvpn/openvpn-status.log
verb 3
""")

            # Configure WebSocket if enabled
            if config.get('websocket', {}).get('enabled', False):
                with open('/etc/nginx/conf.d/ovpn-ws.conf', 'w') as f:
                    f.write(f"""
server {{
    listen {config['websocket']['port']};
    server_name {self.config['domain']};

    location /ovpn {{
        proxy_pass http://127.0.0.1:{config['port']};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
""")

            # Restart OpenVPN service
            subprocess.run(['systemctl', 'restart', 'openvpn'])
            return True
        except Exception as e:
            logger.error(f"Error configuring OpenVPN: {str(e)}")
            return False

    def configure_l2tp(self) -> bool:
        """Configure L2TP"""
        try:
            # Configure xl2tpd
            with open(self.l2tp_config, 'w') as f:
                f.write(f"""
[global]
ipsec saref = yes
saref refinfo = 30

[lns default]
ip range = 10.8.0.2-10.8.0.254
local ip = 10.8.0.1
require chap = yes
refuse pap = yes
require authentication = yes
name = l2tpd
pppoptfile = /etc/ppp/options.xl2tpd
length bit = yes
""")

            # Configure IPsec
            with open(self.ipsec_config, 'w') as f:
                f.write(f"""
config setup
    charondebug="ike 1, knl 1, cfg 0"
    uniqueids=no

conn L2TP-PSK-NAT
    type=transport
    keyexchange=ikev1
    authby=secret
    keyingtries=3
    rekey=no
    left=%defaultroute
    leftprotoport=17/1701
    right=%any
    rightprotoport=17/%any
    forceencaps=yes
    auto=add
""")

            # Restart services
            subprocess.run(['systemctl', 'restart', 'xl2tpd'])
            subprocess.run(['systemctl', 'restart', 'strongswan'])
            return True
        except Exception as e:
            logger.error(f"Error configuring L2TP: {str(e)}")
            return False

    def update_xray_users(self, users: Dict[str, Any]) -> bool:
        """Update Xray user configurations"""
        try:
            with open(self.xray_config, 'r') as f:
                config = json.load(f)

            # Update VMess users
            for inbound in config['inbounds']:
                if inbound['protocol'] == 'vmess':
                    inbound['settings']['clients'] = [
                        {
                            'id': users[username]['uuid'],
                            'alterId': 0
                        }
                        for username, user_data in users.items()
                        if not user_data.get('banned', False)
                    ]
                elif inbound['protocol'] == 'vless':
                    inbound['settings']['clients'] = [
                        {
                            'id': users[username]['uuid']
                        }
                        for username, user_data in users.items()
                        if not user_data.get('banned', False)
                    ]
                elif inbound['protocol'] == 'trojan':
                    inbound['settings']['clients'] = [
                        {
                            'password': users[username]['uuid']
                        }
                        for username, user_data in users.items()
                        if not user_data.get('banned', False)
                    ]

            # Save configuration
            with open(self.xray_config, 'w') as f:
                json.dump(config, f, indent=4)

            # Restart Xray service
            subprocess.run(['systemctl', 'restart', 'xray'])
            return True
        except Exception as e:
            logger.error(f"Error updating Xray users: {str(e)}")
            return False 