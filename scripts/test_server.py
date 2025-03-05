#!/usr/bin/env python3
import os
import sys
import json
import logging
import subprocess
import time
from typing import Dict, Any, List
from service_manager import ServiceManager
from protocol_manager import ProtocolManager

logger = logging.getLogger(__name__)

class ServerTester:
    def __init__(self):
        self.service_manager = ServiceManager()
        self.protocol_manager = ProtocolManager(self.service_manager.config)
        self.test_users = {
            'ssh': {
                'username': 'test_ssh',
                'password': 'test123'
            },
            'xray': {
                'username': 'test_xray',
                'password': 'test456'
            }
        }

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/var/log/boxvps/test.log'),
                logging.StreamHandler()
            ]
        )

    def test_system_requirements(self) -> bool:
        """Test system requirements"""
        logger.info("Testing system requirements...")
        try:
            # Check required packages
            required_packages = [
                'openssh-server', 'dropbear', 'squid', 'udpgw', 'slowdns',
                'openvpn', 'xl2tpd', 'strongswan', 'fail2ban', 'nginx',
                'cloudflared', 'xray'
            ]
            
            for package in required_packages:
                result = subprocess.run(['dpkg', '-l', package], capture_output=True, text=True)
                if package not in result.stdout:
                    logger.error(f"Required package {package} is not installed")
                    return False
            
            # Check required directories
            required_dirs = [
                '/etc/boxvps',
                '/etc/boxvps/config',
                '/etc/boxvps/data',
                '/etc/boxvps/backup',
                '/var/log/boxvps'
            ]
            
            for directory in required_dirs:
                if not os.path.exists(directory):
                    logger.error(f"Required directory {directory} does not exist")
                    return False
            
            logger.info("System requirements check passed")
            return True
        except Exception as e:
            logger.error(f"Error checking system requirements: {str(e)}")
            return False

    def test_services(self) -> bool:
        """Test service configurations"""
        logger.info("Testing service configurations...")
        try:
            # Test SSH configuration
            if not self._test_ssh():
                return False

            # Test Xray configuration
            if not self._test_xray():
                return False

            # Test OpenVPN configuration
            if not self._test_ovpn():
                return False

            # Test L2TP configuration
            if not self._test_l2tp():
                return False

            logger.info("Service configurations test passed")
            return True
        except Exception as e:
            logger.error(f"Error testing services: {str(e)}")
            return False

    def _test_ssh(self) -> bool:
        """Test SSH configuration"""
        try:
            # Test OpenSSH
            result = subprocess.run(['systemctl', 'is-active', 'sshd'], capture_output=True, text=True)
            if result.stdout.strip() != 'active':
                logger.error("OpenSSH service is not running")
                return False

            # Test Dropbear
            result = subprocess.run(['systemctl', 'is-active', 'dropbear'], capture_output=True, text=True)
            if result.stdout.strip() != 'active':
                logger.error("Dropbear service is not running")
                return False

            # Test Squid
            result = subprocess.run(['systemctl', 'is-active', 'squid'], capture_output=True, text=True)
            if result.stdout.strip() != 'active':
                logger.error("Squid service is not running")
                return False

            return True
        except Exception as e:
            logger.error(f"Error testing SSH: {str(e)}")
            return False

    def _test_xray(self) -> bool:
        """Test Xray configuration"""
        try:
            # Check Xray service
            result = subprocess.run(['systemctl', 'is-active', 'xray'], capture_output=True, text=True)
            if result.stdout.strip() != 'active':
                logger.error("Xray service is not running")
                return False

            # Check Xray config
            if not os.path.exists('/usr/local/etc/xray/config.json'):
                logger.error("Xray configuration file not found")
                return False

            return True
        except Exception as e:
            logger.error(f"Error testing Xray: {str(e)}")
            return False

    def _test_ovpn(self) -> bool:
        """Test OpenVPN configuration"""
        try:
            # Check OpenVPN service
            result = subprocess.run(['systemctl', 'is-active', 'openvpn'], capture_output=True, text=True)
            if result.stdout.strip() != 'active':
                logger.error("OpenVPN service is not running")
                return False

            # Check certificates
            required_certs = ['ca.crt', 'server.crt', 'server.key', 'dh.pem']
            for cert in required_certs:
                if not os.path.exists(f'/etc/openvpn/{cert}'):
                    logger.error(f"OpenVPN certificate {cert} not found")
                    return False

            return True
        except Exception as e:
            logger.error(f"Error testing OpenVPN: {str(e)}")
            return False

    def _test_l2tp(self) -> bool:
        """Test L2TP configuration"""
        try:
            # Check xl2tpd service
            result = subprocess.run(['systemctl', 'is-active', 'xl2tpd'], capture_output=True, text=True)
            if result.stdout.strip() != 'active':
                logger.error("xl2tpd service is not running")
                return False

            # Check strongswan service
            result = subprocess.run(['systemctl', 'is-active', 'strongswan'], capture_output=True, text=True)
            if result.stdout.strip() != 'active':
                logger.error("strongswan service is not running")
                return False

            return True
        except Exception as e:
            logger.error(f"Error testing L2TP: {str(e)}")
            return False

    def test_user_management(self) -> bool:
        """Test user management"""
        logger.info("Testing user management...")
        try:
            # Test adding users
            for service, user in self.test_users.items():
                if not self.service_manager.add_user(user['username'], user['password'], service, 10):
                    logger.error(f"Failed to add {service} user {user['username']}")
                    return False

            # Test user info
            for service, user in self.test_users.items():
                user_info = self.service_manager.get_user_info(user['username'])
                if not user_info:
                    logger.error(f"Failed to get info for {service} user {user['username']}")
                    return False

            # Test banning users
            for service, user in self.test_users.items():
                if not self.service_manager.ban_user(user['username'], service):
                    logger.error(f"Failed to ban {service} user {user['username']}")
                    return False

            # Test unbanning users
            for service, user in self.test_users.items():
                if not self.service_manager.unban_user(user['username'], service):
                    logger.error(f"Failed to unban {service} user {user['username']}")
                    return False

            # Test deleting users
            for service, user in self.test_users.items():
                if not self.service_manager.delete_user(user['username']):
                    logger.error(f"Failed to delete {service} user {user['username']}")
                    return False

            logger.info("User management test passed")
            return True
        except Exception as e:
            logger.error(f"Error testing user management: {str(e)}")
            return False

    def test_backup_restore(self) -> bool:
        """Test backup and restore functionality"""
        logger.info("Testing backup and restore...")
        try:
            # Create backup
            backup_file = self.service_manager.backup_data()
            if not backup_file:
                logger.error("Failed to create backup")
                return False

            # Restore backup
            if not self.service_manager.restore_data(backup_file):
                logger.error("Failed to restore backup")
                return False

            logger.info("Backup and restore test passed")
            return True
        except Exception as e:
            logger.error(f"Error testing backup and restore: {str(e)}")
            return False

    def test_monitoring(self) -> bool:
        """Test monitoring functionality"""
        logger.info("Testing monitoring...")
        try:
            # Test system status
            status = self.service_manager.get_system_status()
            if not status:
                logger.error("Failed to get system status")
                return False

            # Test service status
            services = status.get('services', {})
            required_services = ['ssh', 'xray', 'openvpn', 'l2tp', 'strongswan', 'cloudflared']
            for service in required_services:
                if service not in services or not services[service].get('running'):
                    logger.error(f"Service {service} is not running")
                    return False

            logger.info("Monitoring test passed")
            return True
        except Exception as e:
            logger.error(f"Error testing monitoring: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all tests"""
        self.setup_logging()
        logger.info("Starting BoxVPS server tests...")

        tests = [
            ("System Requirements", self.test_system_requirements),
            ("Service Configurations", self.test_services),
            ("User Management", self.test_user_management),
            ("Backup and Restore", self.test_backup_restore),
            ("Monitoring", self.test_monitoring)
        ]

        all_passed = True
        for test_name, test_func in tests:
            logger.info(f"\nRunning {test_name} test...")
            if not test_func():
                logger.error(f"{test_name} test failed")
                all_passed = False
            time.sleep(1)  # Add delay between tests

        if all_passed:
            logger.info("\nAll tests passed successfully!")
        else:
            logger.error("\nSome tests failed. Check the logs for details.")
            sys.exit(1)

if __name__ == '__main__':
    tester = ServerTester()
    tester.run_all_tests() 