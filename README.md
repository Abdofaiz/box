# BoxVPS - SSH & Xray Management Script

A comprehensive management script for SSH and Xray services with advanced features.

## Features

### Core Features
- Setup Argo SSH & Xray (via CLI)
- Autoban Account SSH & Xray (via CLI)
- Lock Account Xray & SSH (via Bot/API)
- Limit Quota SSH & Xray (via CLI/Bot/API)
- Unban/Unlock SSH & Xray (via CLI/Bot/API)
- Check User Login SSH with Quota (via CLI/Bot/API)
- Check User Login Xray with Quota (via CLI/Bot/API)
- Change Domain/Host (via CLI)
- Change Port & AltPort (via CLI)
- Change UUID/Pass Xray (via CLI/Bot/API)
- Backup Data via Telegram Bot (via CLI)
- Restore Data (via CLI)

### Advanced Features
- All in One Port 443 SSH & Xray
- Multi Port 80 SSH & Xray HTTP/NTLS
- Configure Limit Login SSH & Xray
- API Documentation
- Easy to Use Interface
- Auto Block Torrent Xray
- Enable/Disable Block Scanner Cert
- Multi-Server Management via Single Bot
- Create & Delete Xray Account without Service Restart

### Supported Protocols
- SSH (OpenSSH, Dropbear, Squid, UDPGW, WS HTTP, WS HTTPS, UDP, SlowDNS)
- OVPN (UDP, TCP, WS HTTP)
- L2TP
- Xray:
  - VMess (WS, gRPC, TCP HTTP)
  - VLESS (WS, gRPC, XTLS)
  - Trojan (WS, gRPC, TCP)

## Installation

```bash
wget -O install.sh https://raw.githubusercontent.com/box/blob/main/install.sh
chmod +x install.sh
./install.sh
```

## Usage

### CLI Commands
```bash
boxvps [command] [options]
```

### Telegram Bot
Add the bot to your Telegram and use the following commands:
- /start - Start the bot
- /help - Show help menu
- /adduser - Add new user
- /deluser - Delete user
- /listuser - List all users
- /status - Check service status
- /backup - Backup data
- /restore - Restore data

### API Documentation
API documentation is available at `/docs` endpoint after installation.

## Requirements
- Ubuntu 20.04 or higher
- Debian 10 or higher
- 1GB RAM minimum
- 10GB storage minimum

## License
MIT License 
