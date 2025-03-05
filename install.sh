#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Print with color
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root"
    exit 1
fi

# Update system
print_info "Updating system..."
apt update && apt upgrade -y

# Install required packages
print_info "Installing required packages..."
apt install -y \
    openssh-server \
    dropbear \
    squid \
    openvpn \
    easy-rsa \
    xl2tpd \
    strongswan \
    fail2ban \
    iptables-persistent \
    nginx \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    git \
    unzip \
    build-essential

# Install Xray
print_info "Installing Xray..."
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install

# Install UDPGW
print_info "Installing UDPGW..."
wget -O /usr/bin/udpgw https://raw.githubusercontent.com/boxvps/udpgw/master/udpgw
chmod +x /usr/bin/udpgw

# Install SlowDNS
print_info "Installing SlowDNS..."
wget -O /usr/bin/slowdns https://raw.githubusercontent.com/boxvps/slowdns/master/slowdns
chmod +x /usr/bin/slowdns

# Create required directories
print_info "Creating required directories..."
mkdir -p /etc/boxvps/{config,data,backup,scripts}
mkdir -p /var/log/boxvps
mkdir -p /etc/openvpn
mkdir -p /etc/iptables

# Setup OpenVPN
print_info "Setting up OpenVPN..."
cd /etc/openvpn
easyrsa init-pki
echo -en "\n" | easyrsa build-ca nopass
echo -en "\n" | easyrsa gen-req server nopass
echo -en "yes\n" | easyrsa sign-req server server
easyrsa gen-dh
cp pki/ca.crt /etc/openvpn/
cp pki/issued/server.crt /etc/openvpn/
cp pki/private/server.key /etc/openvpn/
cp pki/dh.pem /etc/openvpn/

# Configure fail2ban
print_info "Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF

# Configure iptables
print_info "Configuring iptables..."
cat > /etc/iptables/rules.v4 << EOF
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p tcp --dport 22 -j ACCEPT
-A INPUT -p tcp --dport 80 -j ACCEPT
-A INPUT -p tcp --dport 443 -j ACCEPT
-A INPUT -p tcp --dport 1194 -j ACCEPT
-A INPUT -p udp --dport 1194 -j ACCEPT
-A INPUT -p udp --dport 1701 -j ACCEPT
-A INPUT -p udp --dport 500 -j ACCEPT
-A INPUT -p udp --dport 4500 -j ACCEPT
-A INPUT -i lo -j ACCEPT
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

# Enable IP forwarding
print_info "Enabling IP forwarding..."
echo "net.ipv4.ip_forward = 1" > /etc/sysctl.d/99-sysctl.conf
sysctl -p

# Apply iptables rules
print_info "Applying iptables rules..."
iptables-restore < /etc/iptables/rules.v4

# Copy configuration files
print_info "Copying configuration files..."
cp -r scripts/* /etc/boxvps/scripts/
cp -r config/* /etc/boxvps/config/

# Set permissions
print_info "Setting permissions..."
chmod +x /etc/boxvps/scripts/*

# Create systemd service
print_info "Creating systemd service..."
cat > /etc/systemd/system/boxvps.service << EOF
[Unit]
Description=BoxVPS Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /etc/boxvps/scripts/main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
print_info "Reloading systemd..."
systemctl daemon-reload

# Start services
print_info "Starting services..."
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
print_info "Creating command line tool..."
cat > /usr/local/bin/boxvps << EOF
#!/bin/bash
python3 /etc/boxvps/scripts/cli.py "\$@"
EOF
chmod +x /usr/local/bin/boxvps

# Install Python dependencies
print_info "Installing Python dependencies..."
pip3 install -r requirements.txt

print_info "Installation completed successfully!"
print_info "Please configure your Telegram bot token and other settings in /etc/boxvps/config/config.json"
print_info "You can now use the 'boxvps' command to manage your services" 