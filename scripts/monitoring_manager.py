#!/usr/bin/env python3
import os
import json
import subprocess
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import psutil
import netifaces

logger = logging.getLogger(__name__)

class MonitoringManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.stats_file = '/etc/boxvps/data/stats.json'
        self._ensure_stats_file()

    def _ensure_stats_file(self):
        """Ensure stats file exists"""
        os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
        if not os.path.exists(self.stats_file):
            self._save_stats({})

    def _load_stats(self) -> Dict[str, Any]:
        """Load statistics"""
        try:
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def _save_stats(self, stats: Dict[str, Any]):
        """Save statistics"""
        with open(self.stats_file, 'w') as f:
            json.dump(stats, f, indent=4)

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            stats = {
                'cpu': {
                    'percent': psutil.cpu_percent(),
                    'count': psutil.cpu_count()
                },
                'memory': {
                    'total': psutil.virtual_memory().total,
                    'used': psutil.virtual_memory().used,
                    'percent': psutil.virtual_memory().percent
                },
                'disk': {
                    'total': psutil.disk_usage('/').total,
                    'used': psutil.disk_usage('/').used,
                    'percent': psutil.disk_usage('/').percent
                },
                'network': self._get_network_stats()
            }
            return stats
        except Exception as e:
            logger.error(f"Error getting system stats: {str(e)}")
            return {}

    def _get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics"""
        try:
            stats = {}
            for interface in netifaces.interfaces():
                if interface != 'lo':
                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_INET in addrs:
                        stats[interface] = {
                            'ip': addrs[netifaces.AF_INET][0]['addr'],
                            'netmask': addrs[netifaces.AF_INET][0]['netmask']
                        }
            return stats
        except Exception as e:
            logger.error(f"Error getting network stats: {str(e)}")
            return {}

    def get_user_traffic(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user traffic statistics"""
        try:
            stats = self._load_stats()
            return stats.get(username, {
                'upload': 0,
                'download': 0,
                'last_reset': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error getting user traffic: {str(e)}")
            return None

    def update_user_traffic(self, username: str, upload: int, download: int) -> bool:
        """Update user traffic statistics"""
        try:
            stats = self._load_stats()
            if username not in stats:
                stats[username] = {
                    'upload': 0,
                    'download': 0,
                    'last_reset': datetime.now().isoformat()
                }

            stats[username]['upload'] += upload
            stats[username]['download'] += download
            self._save_stats(stats)
            return True
        except Exception as e:
            logger.error(f"Error updating user traffic: {str(e)}")
            return False

    def reset_user_traffic(self, username: str) -> bool:
        """Reset user traffic statistics"""
        try:
            stats = self._load_stats()
            if username in stats:
                stats[username]['upload'] = 0
                stats[username]['download'] = 0
                stats[username]['last_reset'] = datetime.now().isoformat()
                self._save_stats(stats)
            return True
        except Exception as e:
            logger.error(f"Error resetting user traffic: {str(e)}")
            return False

    def check_user_quota(self, username: str) -> bool:
        """Check if user has exceeded quota"""
        try:
            stats = self._load_stats()
            if username not in stats:
                return True

            user_stats = stats[username]
            total_traffic = user_stats['upload'] + user_stats['download']
            quota = self._get_user_quota(username)

            if quota is None:
                return True

            return total_traffic < (quota * 1024 * 1024 * 1024)  # Convert GB to bytes
        except Exception as e:
            logger.error(f"Error checking user quota: {str(e)}")
            return True

    def _get_user_quota(self, username: str) -> Optional[int]:
        """Get user quota in GB"""
        try:
            with open('/etc/boxvps/data/users.json', 'r') as f:
                users = json.load(f)
                return users.get(username, {}).get('quota')
        except Exception as e:
            logger.error(f"Error getting user quota: {str(e)}")
            return None

    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services"""
        try:
            services = {
                'ssh': self._check_service('sshd'),
                'xray': self._check_service('xray'),
                'openvpn': self._check_service('openvpn'),
                'l2tp': self._check_service('xl2tpd'),
                'strongswan': self._check_service('strongswan'),
                'cloudflared': self._check_service('cloudflared')
            }
            return services
        except Exception as e:
            logger.error(f"Error getting service status: {str(e)}")
            return {}

    def _check_service(self, service: str) -> Dict[str, Any]:
        """Check service status"""
        try:
            result = subprocess.run(['systemctl', 'is-active', service], capture_output=True, text=True)
            return {
                'status': result.stdout.strip(),
                'running': result.stdout.strip() == 'active'
            }
        except Exception as e:
            logger.error(f"Error checking service {service}: {str(e)}")
            return {'status': 'unknown', 'running': False}

    def get_active_users(self) -> Dict[str, Any]:
        """Get list of active users"""
        try:
            active_users = {
                'ssh': self._get_active_ssh_users(),
                'xray': self._get_active_xray_users(),
                'openvpn': self._get_active_ovpn_users(),
                'l2tp': self._get_active_l2tp_users()
            }
            return active_users
        except Exception as e:
            logger.error(f"Error getting active users: {str(e)}")
            return {}

    def _get_active_ssh_users(self) -> List[str]:
        """Get active SSH users"""
        try:
            result = subprocess.run(['who'], capture_output=True, text=True)
            return [line.split()[0] for line in result.stdout.splitlines()]
        except Exception as e:
            logger.error(f"Error getting active SSH users: {str(e)}")
            return []

    def _get_active_xray_users(self) -> List[str]:
        """Get active Xray users"""
        try:
            with open('/usr/local/etc/xray/config.json', 'r') as f:
                config = json.load(f)
                return [client['id'] for inbound in config['inbounds'] for client in inbound['settings']['clients']]
        except Exception as e:
            logger.error(f"Error getting active Xray users: {str(e)}")
            return []

    def _get_active_ovpn_users(self) -> List[str]:
        """Get active OpenVPN users"""
        try:
            if os.path.exists('/etc/openvpn/openvpn-status.log'):
                with open('/etc/openvpn/openvpn-status.log', 'r') as f:
                    return [line.split(',')[0] for line in f if line.startswith('CLIENT_LIST')]
            return []
        except Exception as e:
            logger.error(f"Error getting active OpenVPN users: {str(e)}")
            return []

    def _get_active_l2tp_users(self) -> List[str]:
        """Get active L2TP users"""
        try:
            result = subprocess.run(['xl2tpd-control', 'show tunnels'], capture_output=True, text=True)
            return [line.split()[0] for line in result.stdout.splitlines() if 'connected' in line]
        except Exception as e:
            logger.error(f"Error getting active L2TP users: {str(e)}")
            return [] 