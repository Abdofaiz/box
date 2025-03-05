#!/usr/bin/env python3
import os
import json
import subprocess
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from protocol_manager import ProtocolManager
from monitoring_manager import MonitoringManager

logger = logging.getLogger(__name__)

class ServiceManager:
    def __init__(self, config_path: str = '/etc/boxvps/config/config.json'):
        self.config_path = config_path
        self.config = self._load_config()
        self.users_file = '/etc/boxvps/data/users.json'
        self._ensure_data_directory()
        self.protocol_manager = ProtocolManager(self.config)
        self.monitoring_manager = MonitoringManager(self.config)

    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def _save_config(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)

    def _ensure_data_directory(self):
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
        if not os.path.exists(self.users_file):
            self._save_users({})

    def _load_users(self) -> Dict[str, Any]:
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def _save_users(self, users: Dict[str, Any]):
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=4)

    def setup_argo(self) -> bool:
        """Setup Argo SSH & Xray"""
        try:
            # Install Argo
            subprocess.run(['curl', '-fsSL', 'https://raw.githubusercontent.com/cloudflare/cloudflared/master/cloudflared-installer.sh', '-o', 'cloudflared-installer.sh'])
            subprocess.run(['chmod', '+x', 'cloudflared-installer.sh'])
            subprocess.run(['./cloudflared-installer.sh'])
            
            # Configure Argo
            os.makedirs('/etc/cloudflared', exist_ok=True)
            with open('/etc/cloudflared/config.yml', 'w') as f:
                f.write(f"""
tunnel: {uuid.uuid4()}
credentials-file: /etc/cloudflared/credentials.json
ingress:
  - hostname: {self.config['domain']}
    service: http://localhost:{self.config['ssh_port']}
  - hostname: {self.config['domain']}
    service: http://localhost:{self.config['xray_port']}
""")
            
            # Start Argo service
            subprocess.run(['systemctl', 'enable', 'cloudflared'])
            subprocess.run(['systemctl', 'start', 'cloudflared'])
            
            return True
        except Exception as e:
            logger.error(f"Error setting up Argo: {str(e)}")
            return False

    def add_user(self, username: str, password: str, service: str, quota: Optional[int] = None) -> bool:
        """Add new user"""
        try:
            users = self._load_users()
            if username in users:
                return False

            user_data = {
                'password': password,
                'created_at': datetime.now().isoformat(),
                'quota': quota,
                'quota_used': 0,
                'banned': False,
                'locked': False,
                'last_login': None,
                'login_attempts': 0
            }

            if service == 'xray':
                user_data['uuid'] = str(uuid.uuid4())

            users[username] = user_data
            self._save_users(users)

            # Create system user for SSH
            if service == 'ssh':
                subprocess.run(['useradd', '-m', '-s', '/bin/bash', username])
                subprocess.run(['chpasswd'], input=f'{username}:{password}'.encode())

            # Update service configurations
            if service == 'xray':
                self.protocol_manager.update_xray_users(users)

            # Initialize user traffic stats
            self.monitoring_manager.update_user_traffic(username, 0, 0)

            return True
        except Exception as e:
            logger.error(f"Error adding user: {str(e)}")
            return False

    def delete_user(self, username: str) -> bool:
        """Delete user"""
        try:
            users = self._load_users()
            if username not in users:
                return False

            # Remove system user
            subprocess.run(['userdel', '-r', username], check=False)

            # Remove from users database
            del users[username]
            self._save_users(users)

            # Update service configurations
            self.protocol_manager.update_xray_users(users)

            # Remove user traffic stats
            self.monitoring_manager.reset_user_traffic(username)

            return True
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            return False

    def ban_user(self, username: str, service: str) -> bool:
        """Ban user"""
        try:
            users = self._load_users()
            if username not in users:
                return False

            users[username]['banned'] = True
            users[username]['banned_at'] = datetime.now().isoformat()
            self._save_users(users)

            if service == 'ssh':
                # Add to fail2ban
                subprocess.run(['fail2ban-client', 'set', 'sshd', 'banip', username])
            elif service == 'xray':
                self.protocol_manager.update_xray_users(users)

            return True
        except Exception as e:
            logger.error(f"Error banning user: {str(e)}")
            return False

    def unban_user(self, username: str, service: str) -> bool:
        """Unban user"""
        try:
            users = self._load_users()
            if username not in users:
                return False

            users[username]['banned'] = False
            users[username]['banned_at'] = None
            self._save_users(users)

            if service == 'ssh':
                # Remove from fail2ban
                subprocess.run(['fail2ban-client', 'set', 'sshd', 'unbanip', username])
            elif service == 'xray':
                self.protocol_manager.update_xray_users(users)

            return True
        except Exception as e:
            logger.error(f"Error unbanning user: {str(e)}")
            return False

    def set_quota(self, username: str, service: str, quota: int) -> bool:
        """Set user quota"""
        try:
            users = self._load_users()
            if username not in users:
                return False

            users[username]['quota'] = quota
            self._save_users(users)
            return True
        except Exception as e:
            logger.error(f"Error setting quota: {str(e)}")
            return False

    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information"""
        users = self._load_users()
        user_data = users.get(username)
        if user_data:
            traffic = self.monitoring_manager.get_user_traffic(username)
            if traffic:
                user_data['traffic'] = traffic
        return user_data

    def change_uuid(self, username: str) -> bool:
        """Change Xray UUID"""
        try:
            users = self._load_users()
            if username not in users:
                return False

            users[username]['uuid'] = str(uuid.uuid4())
            self._save_users(users)
            self.protocol_manager.update_xray_users(users)
            return True
        except Exception as e:
            logger.error(f"Error changing UUID: {str(e)}")
            return False

    def configure_services(self) -> bool:
        """Configure all services"""
        try:
            # Configure SSH
            if self.config['services']['ssh']['enabled']:
                self.protocol_manager.configure_ssh(
                    self.config['ssh_port'],
                    self.config['services']['ssh']['protocols']
                )

            # Configure Xray
            if self.config['services']['xray']['enabled']:
                self.protocol_manager.configure_xray(
                    self.config['xray_port'],
                    self.config['services']['xray']['protocols']
                )

            # Configure OpenVPN
            if self.config['services']['ssh']['ovpn']['enabled']:
                self.protocol_manager.configure_ovpn(
                    self.config['services']['ssh']['ovpn']
                )

            # Configure L2TP
            if self.config['services']['l2tp']['enabled']:
                self.protocol_manager.configure_l2tp()

            return True
        except Exception as e:
            logger.error(f"Error configuring services: {str(e)}")
            return False

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        try:
            return {
                'system': self.monitoring_manager.get_system_stats(),
                'services': self.monitoring_manager.get_service_status(),
                'active_users': self.monitoring_manager.get_active_users()
            }
        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            return {}

    def backup_data(self) -> str:
        """Backup all data"""
        try:
            backup_dir = '/etc/boxvps/backup'
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"{backup_dir}/backup_{timestamp}.tar.gz"

            # Create backup
            subprocess.run([
                'tar', '-czf', backup_file,
                '/etc/boxvps/data',
                '/etc/boxvps/config',
                '/usr/local/etc/xray',
                '/etc/ssh',
                '/etc/openvpn',
                '/etc/xl2tpd',
                '/etc/ipsec.conf'
            ])

            return backup_file
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return ""

    def restore_data(self, backup_file: str) -> bool:
        """Restore data from backup"""
        try:
            if not os.path.exists(backup_file):
                return False

            # Restore backup
            subprocess.run(['tar', '-xzf', backup_file, '-C', '/'])
            
            # Restart services
            subprocess.run(['systemctl', 'restart', 'xray'])
            subprocess.run(['systemctl', 'restart', 'sshd'])
            subprocess.run(['systemctl', 'restart', 'openvpn'])
            subprocess.run(['systemctl', 'restart', 'xl2tpd'])
            subprocess.run(['systemctl', 'restart', 'strongswan'])
            
            return True
        except Exception as e:
            logger.error(f"Error restoring backup: {str(e)}")
            return False 