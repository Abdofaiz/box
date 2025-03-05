#!/usr/bin/env python3
import os
import sys
import json
import logging
import argparse
from typing import Dict, Any, Optional
from service_manager import ServiceManager
from protocol_manager import ProtocolManager

logger = logging.getLogger(__name__)

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/var/log/boxvps/cli.log'),
            logging.StreamHandler()
        ]
    )

def load_config() -> Dict[str, Any]:
    """Load configuration file"""
    config_path = '/etc/boxvps/config/config.json'
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)

def setup_argo(args):
    """Setup Argo SSH & Xray"""
    service_manager = ServiceManager()
    if service_manager.setup_argo():
        print("Argo setup completed successfully")
    else:
        print("Failed to setup Argo")

def add_user(args):
    """Add new user"""
    service_manager = ServiceManager()
    if service_manager.add_user(args.username, args.password, args.service, args.quota):
        print(f"User {args.username} added successfully")
    else:
        print(f"Failed to add user {args.username}")

def delete_user(args):
    """Delete user"""
    service_manager = ServiceManager()
    if service_manager.delete_user(args.username):
        print(f"User {args.username} deleted successfully")
    else:
        print(f"Failed to delete user {args.username}")

def ban_user(args):
    """Ban user"""
    service_manager = ServiceManager()
    if service_manager.ban_user(args.username, args.service):
        print(f"User {args.username} banned successfully")
    else:
        print(f"Failed to ban user {args.username}")

def unban_user(args):
    """Unban user"""
    service_manager = ServiceManager()
    if service_manager.unban_user(args.username, args.service):
        print(f"User {args.username} unbanned successfully")
    else:
        print(f"Failed to unban user {args.username}")

def set_quota(args):
    """Set user quota"""
    service_manager = ServiceManager()
    if service_manager.set_quota(args.username, args.service, args.quota):
        print(f"Quota set successfully for user {args.username}")
    else:
        print(f"Failed to set quota for user {args.username}")

def change_uuid(args):
    """Change Xray UUID"""
    service_manager = ServiceManager()
    if service_manager.change_uuid(args.username):
        print(f"UUID changed successfully for user {args.username}")
    else:
        print(f"Failed to change UUID for user {args.username}")

def get_user_info(args):
    """Get user information"""
    service_manager = ServiceManager()
    user_info = service_manager.get_user_info(args.username)
    if user_info:
        print(json.dumps(user_info, indent=4))
    else:
        print(f"User {args.username} not found")

def get_system_status(args):
    """Get system status"""
    service_manager = ServiceManager()
    status = service_manager.get_system_status()
    print(json.dumps(status, indent=4))

def backup_data(args):
    """Backup data"""
    service_manager = ServiceManager()
    backup_file = service_manager.backup_data()
    if backup_file:
        print(f"Backup created successfully: {backup_file}")
    else:
        print("Failed to create backup")

def restore_data(args):
    """Restore data"""
    service_manager = ServiceManager()
    if service_manager.restore_data(args.backup_file):
        print("Data restored successfully")
    else:
        print("Failed to restore data")

def configure_services(args):
    """Configure services"""
    service_manager = ServiceManager()
    if service_manager.configure_services():
        print("Services configured successfully")
    else:
        print("Failed to configure services")

def main():
    """Main function"""
    setup_logging()
    parser = argparse.ArgumentParser(description='BoxVPS CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Setup Argo
    setup_parser = subparsers.add_parser('setup-argo', help='Setup Argo SSH & Xray')

    # User management
    add_parser = subparsers.add_parser('add-user', help='Add new user')
    add_parser.add_argument('username', help='Username')
    add_parser.add_argument('password', help='Password')
    add_parser.add_argument('service', choices=['ssh', 'xray'], help='Service type')
    add_parser.add_argument('--quota', type=int, help='Quota in GB')

    delete_parser = subparsers.add_parser('delete-user', help='Delete user')
    delete_parser.add_argument('username', help='Username')

    ban_parser = subparsers.add_parser('ban-user', help='Ban user')
    ban_parser.add_argument('username', help='Username')
    ban_parser.add_argument('service', choices=['ssh', 'xray'], help='Service type')

    unban_parser = subparsers.add_parser('unban-user', help='Unban user')
    unban_parser.add_argument('username', help='Username')
    unban_parser.add_argument('service', choices=['ssh', 'xray'], help='Service type')

    quota_parser = subparsers.add_parser('set-quota', help='Set user quota')
    quota_parser.add_argument('username', help='Username')
    quota_parser.add_argument('service', choices=['ssh', 'xray'], help='Service type')
    quota_parser.add_argument('quota', type=int, help='Quota in GB')

    uuid_parser = subparsers.add_parser('change-uuid', help='Change Xray UUID')
    uuid_parser.add_argument('username', help='Username')

    info_parser = subparsers.add_parser('user-info', help='Get user information')
    info_parser.add_argument('username', help='Username')

    # System management
    status_parser = subparsers.add_parser('status', help='Get system status')

    backup_parser = subparsers.add_parser('backup', help='Backup data')

    restore_parser = subparsers.add_parser('restore', help='Restore data')
    restore_parser.add_argument('backup_file', help='Backup file path')

    config_parser = subparsers.add_parser('configure', help='Configure services')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    commands = {
        'setup-argo': setup_argo,
        'add-user': add_user,
        'delete-user': delete_user,
        'ban-user': ban_user,
        'unban-user': unban_user,
        'set-quota': set_quota,
        'change-uuid': change_uuid,
        'user-info': get_user_info,
        'status': get_system_status,
        'backup': backup_data,
        'restore': restore_data,
        'configure': configure_services
    }

    try:
        commands[args.command](args)
    except Exception as e:
        logger.error(f"Error executing command {args.command}: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 