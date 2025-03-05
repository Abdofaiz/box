#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root${NC}"
    exit 1
fi

# Function to print colored messages
print_message() {
    echo -e "${GREEN}[INFO] $1${NC}"
}

print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Update system
print_message "Updating system..."
apt update && apt upgrade -y

# Install required packages
print_message "Installing required packages..."
apt install -y curl wget git python3 python3-pip nodejs npm nginx certbot python3-certbot-nginx \
    openssh-server dropbear squid udpgw slowdns \
    openvpn easy-rsa \
    xl2tpd strongswan \
    fail2ban \
    iptables-persistent

# Install Python packages
print_message "Installing Python packages..."
pip3 install -r requirements.txt

# Create necessary directories
print_message "Creating directories..."
mkdir -p /etc/boxvps
mkdir -p /etc/boxvps/scripts
mkdir -p /etc/boxvps/config
mkdir -p /etc/boxvps/logs
mkdir -p /etc/boxvps/backup
mkdir -p /etc/boxvps/data

# Download and install Xray
print_message "Installing Xray..."
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install

# Install UDPGW
print_message "Installing UDPGW..."
wget -O /usr/bin/udpgw "https://raw.githubusercontent.com/boxvps/udpgw/master/udpgw"
chmod +x /usr/bin/udpgw

# Install SlowDNS
print_message "Installing SlowDNS..."
wget -O /usr/bin/slowdns "https://raw.githubusercontent.com/boxvps/slowdns/master/slowdns"
chmod +x /usr/bin/slowdns

# Setup OpenVPN
print_message "Setting up OpenVPN..."
cd /etc/openvpn
easyrsa init-pki
easyrsa build-ca nopass
easyrsa build-server-full server nopass
easyrsa gen-dh
cp pki/ca.crt pki/issued/server.crt pki/private/server.key pki/dh.pem /etc/openvpn/

# Setup fail2ban
print_message "Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << EOF
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
EOF

# Setup iptables
print_message "Configuring iptables..."
cat > /etc/iptables/rules.v4 << EOF
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p tcp --dport 22 -j ACCEPT
-A INPUT -p tcp --dport 443 -j ACCEPT
-A INPUT -p tcp --dport 80 -j ACCEPT
-A INPUT -p udp --dport 1194 -j ACCEPT
-A INPUT -p udp --dport 1701 -j ACCEPT
-A INPUT -p udp --dport 500 -j ACCEPT
-A INPUT -p udp --dport 4500 -j ACCEPT
-A INPUT -j DROP
COMMIT

*nat
:PREROUTING ACCEPT [0:0]
:INPUT ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
:POSTROUTING ACCEPT [0:0]
-A POSTROUTING -o eth0 -j MASQUERADE
COMMIT
EOF

# Apply iptables rules
iptables-restore < /etc/iptables/rules.v4

# Enable IP forwarding
echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-sysctl.conf
sysctl -p

# Copy configuration files
print_message "Copying configuration files..."
cp -r scripts/* /etc/boxvps/scripts/
cp -r config/* /etc/boxvps/config/

# Set permissions
print_message "Setting permissions..."
chmod +x /etc/boxvps/scripts/*

# Create systemd service
print_message "Creating systemd service..."
cat > /etc/systemd/system/boxvps.service << EOF
[Unit]
Description=BoxVPS Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/etc/boxvps
ExecStart=/usr/bin/python3 /etc/boxvps/scripts/main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
print_message "Reloading systemd..."
systemctl daemon-reload

# Start services
print_message "Starting services..."
systemctl enable boxvps
systemctl enable fail2ban
systemctl enable openvpn
systemctl enable xl2tpd
systemctl enable strongswan
systemctl start boxvps
systemctl start fail2ban
systemctl start openvpn
systemctl start xl2tpd
systemctl start strongswan

# Create command line tool
print_message "Creating command line tool..."
cat > /usr/bin/boxvps << EOF
#!/bin/bash
python3 /etc/boxvps/scripts/cli.py "\$@"
EOF
chmod +x /usr/bin/boxvps

print_message "Installation completed successfully!"
print_message "Please configure your Telegram bot token and other settings in /etc/boxvps/config/config.json"
print_message "You can now use the 'boxvps' command to manage your services" 