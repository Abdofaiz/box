#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root"
    exit 1
fi

# Download files from GitHub
download_files() {
    print_step "Downloading required files from GitHub..."
    
    # Create temporary directory
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR" || exit 1
    
    # Download setup script
    print_info "Downloading setup script..."
    wget -q https://raw.githubusercontent.com/scriptvpskita/okdeinekejsksidjndv1/main/setup.sh || { print_error "Failed to download setup script"; exit 1; }
    chmod +x setup.sh
    
    # Create required directories
    mkdir -p /etc/boxvps/{config,data,backup,scripts}
    mkdir -p /var/log/boxvps
    
    # Run setup script in tmux
    print_info "Running setup script in tmux..."
    tmux new-session -s script './setup.sh' || { print_error "Failed to run setup script"; exit 1; }
    
    # Clean up
    cd - > /dev/null
    rm -rf "$TEMP_DIR"
}

# Check system requirements
check_system() {
    print_step "Checking system requirements..."
    
    # Check OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VERSION=$VERSION_ID
    else
        print_error "Could not detect OS"
        exit 1
    fi
    
    # Check architecture
    ARCH=$(uname -m)
    if [ "$ARCH" != "x86_64" ] && [ "$ARCH" != "aarch64" ]; then
        print_error "Unsupported architecture: $ARCH"
        exit 1
    fi
    
    # Check memory
    MEM=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$MEM" -lt 512 ]; then
        print_error "Insufficient memory. Required: 512MB, Available: ${MEM}MB"
        exit 1
    fi
    
    # Check disk space
    DISK=$(df -m / | awk 'NR==2 {print $4}')
    if [ "$DISK" -lt 1024 ]; then
        print_error "Insufficient disk space. Required: 1GB, Available: ${DISK}MB"
        exit 1
    fi
    
    print_info "System requirements met:"
    print_info "OS: $OS $VERSION"
    print_info "Architecture: $ARCH"
    print_info "Memory: ${MEM}MB"
    print_info "Disk Space: ${DISK}MB"
}

# Update system
update_system() {
    print_step "Updating system..."
    apt update || { print_error "Failed to update package list"; exit 1; }
    DEBIAN_FRONTEND=noninteractive apt upgrade -y || { print_error "Failed to upgrade system"; exit 1; }
}

# Install required packages
install_packages() {
    print_step "Installing required packages..."
    
    # Install basic packages
    DEBIAN_FRONTEND=noninteractive apt install -y \
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
        python3-openssl \
        python3-cryptography \
        libssl-dev \
        libffi-dev \
        curl \
        wget \
        git \
        unzip \
        build-essential || { print_error "Failed to install basic packages"; exit 1; }
    
    # Install Python packages
    print_step "Installing Python dependencies..."
    
    # Create and activate virtual environment
    print_info "Creating virtual environment..."
    python3 -m venv /etc/boxvps/venv || { print_error "Failed to create virtual environment"; exit 1; }
    source /etc/boxvps/venv/bin/activate || { print_error "Failed to activate virtual environment"; exit 1; }
    
    # Upgrade pip and install wheel
    print_info "Upgrading pip and installing wheel..."
    pip install --upgrade pip wheel setuptools || { print_error "Failed to upgrade pip"; exit 1; }
    
    # Install dependencies in specific order
    print_info "Installing core dependencies..."
    pip install pyOpenSSL==23.2.0 || { print_error "Failed to install pyOpenSSL"; exit 1; }
    pip install cryptography==41.0.7 || { print_error "Failed to install cryptography"; exit 1; }
    
    # Install other dependencies
    print_info "Installing additional dependencies..."
    pip install \
        fastapi==0.104.1 \
        uvicorn==0.24.0 \
        python-telegram-bot==20.7 \
        python-dotenv==1.0.0 \
        requests==2.31.0 \
        pydantic==2.5.2 \
        python-jose==3.3.0 \
        passlib==1.7.4 \
        python-multipart==0.0.6 \
        aiohttp==3.9.1 \
        asyncio==3.4.3 \
        psutil==5.9.6 \
        netifaces==0.11.0 \
        python-iptables==1.0.0 || { print_error "Failed to install additional dependencies"; exit 1; }
    
    # Deactivate virtual environment
    deactivate
    
    # Update the systemd service to use the virtual environment
    print_info "Updating systemd service..."
    cat > /etc/systemd/system/boxvps.service << EOF
[Unit]
Description=BoxVPS Service
After=network.target

[Service]
Type=simple
Environment=PATH=/etc/boxvps/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/etc/boxvps/venv/bin/python /etc/boxvps/scripts/main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    
    # Update the CLI tool to use the virtual environment
    print_info "Updating CLI tool..."
    cat > /usr/local/bin/boxvps << EOF
#!/bin/bash
source /etc/boxvps/venv/bin/activate
python /etc/boxvps/scripts/cli.py "\$@"
EOF
    chmod +x /usr/local/bin/boxvps
}

# Install Xray
install_xray() {
    print_step "Installing Xray..."
    bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install || { print_error "Failed to install Xray"; exit 1; }
}

# Install UDPGW
install_udpgw() {
    print_step "Installing UDPGW..."
    if [ -f /usr/bin/udpgw ]; then
        rm /usr/bin/udpgw
    fi

    print_info "Building UDPGW from source..."

    # Install dependencies for building
    apt install -y cmake || { print_error "Failed to install build dependencies"; exit 1; }

    # Create temporary directory
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR" || exit 1

    # Clone UDPGW repository
    git clone https://github.com/ambrop72/badvpn.git || { print_error "Failed to clone UDPGW repository"; exit 1; }
    cd badvpn || exit 1

    # Build UDPGW
    mkdir build && cd build
    cmake .. -DBUILD_NOTHING_BY_DEFAULT=1 -DBUILD_UDPGW=1 || { print_error "Failed to configure UDPGW build"; exit 1; }
    make || { print_error "Failed to build UDPGW"; exit 1; }

    # Copy binary
    cp udpgw/badvpn-udpgw /usr/bin/udpgw || { print_error "Failed to copy UDPGW binary"; exit 1; }

    # Clean up
    cd - > /dev/null
    rm -rf "$TEMP_DIR"

    chmod +x /usr/bin/udpgw
    print_info "UDPGW installed successfully"
}

# Install SlowDNS
install_slowdns() {
    print_step "Installing SlowDNS..."
    if [ -f /usr/bin/slowdns ]; then
        rm /usr/bin/slowdns
    fi
    wget -O /usr/bin/slowdns https://raw.githubusercontent.com/scriptvpskita/okdeinekejsksidjndv1/main/slowdns || { print_error "Failed to download SlowDNS"; exit 1; }
    chmod +x /usr/bin/slowdns
}

# Setup OpenVPN
setup_openvpn() {
    print_step "Setting up OpenVPN..."
    
    # Create OpenVPN directory
    mkdir -p /etc/openvpn
    
    # Check and install easy-rsa if needed
    if [ ! -f /usr/share/easy-rsa/easyrsa ]; then
        print_warn "easy-rsa not found. Installing..."
        apt install -y easy-rsa || { print_error "Failed to install easy-rsa"; exit 1; }
    fi
    
    # Initialize PKI
    cd /etc/openvpn || exit 1
    /usr/share/easy-rsa/easyrsa init-pki || { print_error "Failed to initialize PKI"; exit 1; }
    echo -en "\n" | /usr/share/easy-rsa/easyrsa build-ca nopass || { print_error "Failed to build CA"; exit 1; }
    echo -en "\n" | /usr/share/easy-rsa/easyrsa gen-req server nopass || { print_error "Failed to generate server request"; exit 1; }
    echo -en "yes\n" | /usr/share/easy-rsa/easyrsa sign-req server server || { print_error "Failed to sign server request"; exit 1; }
    /usr/share/easy-rsa/easyrsa gen-dh || { print_error "Failed to generate DH parameters"; exit 1; }
    
    # Copy certificates
    cp pki/ca.crt /etc/openvpn/ || { print_error "Failed to copy CA certificate"; exit 1; }
    cp pki/issued/server.crt /etc/openvpn/ || { print_error "Failed to copy server certificate"; exit 1; }
    cp pki/private/server.key /etc/openvpn/ || { print_error "Failed to copy server key"; exit 1; }
    cp pki/dh.pem /etc/openvpn/ || { print_error "Failed to copy DH parameters"; exit 1; }
}

# Configure fail2ban
setup_fail2ban() {
    print_step "Configuring fail2ban..."
    mkdir -p /etc/fail2ban
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
}

# Configure iptables
setup_iptables() {
    print_step "Configuring iptables..."
    mkdir -p /etc/iptables
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
}

# Setup systemd service
setup_systemd() {
    print_step "Setting up systemd service..."
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
}

# Main installation process
main() {
    print_info "Starting BoxVPS installation..."
    
    # Check system requirements
    check_system
    
    # Update system
    update_system
    
    # Download required files
    download_files
    
    # Install packages
    install_packages
    
    # Install additional components
    install_xray
    install_udpgw
    install_slowdns
    
    # Setup services
    setup_openvpn
    setup_fail2ban
    setup_iptables
    
    # Set permissions
    print_step "Setting permissions..."
    chmod +x /etc/boxvps/scripts/*
    
    # Setup systemd service
    setup_systemd
    
    # Reload systemd
    print_step "Reloading systemd..."
    systemctl daemon-reload
    
    # Start services
    print_step "Starting services..."
    systemctl enable boxvps fail2ban openvpn xl2tpd || { print_error "Failed to enable services"; exit 1; }
    systemctl start boxvps fail2ban openvpn xl2tpd || { print_error "Failed to start services"; exit 1; }
    
    # Create command line tool
    print_step "Creating command line tool..."
    cat > /usr/local/bin/boxvps << EOF
#!/bin/bash
python3 /etc/boxvps/scripts/cli.py "\$@"
EOF
    chmod +x /usr/local/bin/boxvps
    
    print_info "Installation completed successfully!"
    print_info "Please configure your Telegram bot token and other settings in /etc/boxvps/config/config.json"
    print_info "You can now use the 'boxvps' command to manage your services"
}

# Run main installation process
main 