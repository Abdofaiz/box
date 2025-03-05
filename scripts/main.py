#!/usr/bin/env python3
import os
import json
import logging
from fastapi import FastAPI, HTTPException, Depends
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
import uvicorn
from typing import Dict, Any, Optional
from service_manager import ServiceManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='/etc/boxvps/logs/boxvps.log'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="BoxVPS API")

# Initialize ServiceManager
service_manager = ServiceManager()

# Dependency for admin check
async def check_admin(update: Update) -> bool:
    config = service_manager.config
    return str(update.effective_user.id) in config.get("admin_ids", [])

# Telegram bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        await update.message.reply_text("Unauthorized access.")
        return
    await update.message.reply_text("Welcome to BoxVPS Bot! Use /help to see available commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        await update.message.reply_text("Unauthorized access.")
        return
    help_text = """
Available commands:
/adduser - Add new user
/deluser - Delete user
/listuser - List all users
/status - Check service status
/backup - Backup data
/restore - Restore data
/change_port - Change service ports
/change_domain - Change domain
/block_user - Block user
/unblock_user - Unblock user
    """
    await update.message.reply_text(help_text)

async def add_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        await update.message.reply_text("Unauthorized access.")
        return
    
    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("Usage: /adduser <username> <password> <service> [quota]")
            return
        
        username, password, service = args[:3]
        quota = int(args[3]) if len(args) > 3 else None
        
        if service_manager.add_user(username, password, service, quota):
            await update.message.reply_text(f"User {username} added successfully!")
        else:
            await update.message.reply_text("Failed to add user.")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def delete_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        await update.message.reply_text("Unauthorized access.")
        return
    
    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("Usage: /deluser <username>")
            return
        
        username = args[0]
        if service_manager.delete_user(username):
            await update.message.reply_text(f"User {username} deleted successfully!")
        else:
            await update.message.reply_text("Failed to delete user.")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def list_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        await update.message.reply_text("Unauthorized access.")
        return
    
    try:
        users = service_manager._load_users()
        if not users:
            await update.message.reply_text("No users found.")
            return
        
        user_list = "Users:\n"
        for username, data in users.items():
            user_list += f"\nUsername: {username}\n"
            user_list += f"Service: {'Xray' if 'uuid' in data else 'SSH'}\n"
            user_list += f"Quota: {data.get('quota', 'Unlimited')}GB\n"
            user_list += f"Status: {'Banned' if data.get('banned') else 'Active'}\n"
        
        await update.message.reply_text(user_list)
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# API endpoints
@app.get("/api/status")
async def get_status():
    return {"status": "running"}

@app.post("/api/user/add")
async def add_user(user_data: Dict[str, Any]):
    try:
        success = service_manager.add_user(
            user_data["username"],
            user_data["password"],
            user_data["service"],
            user_data.get("quota")
        )
        if success:
            return {"status": "success", "message": "User added successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to add user")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/user/{username}")
async def delete_user(username: str):
    try:
        success = service_manager.delete_user(username)
        if success:
            return {"status": "success", "message": "User deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users")
async def list_users():
    try:
        users = service_manager._load_users()
        return {"status": "success", "users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backup")
async def backup_data():
    try:
        backup_file = service_manager.backup_data()
        if backup_file:
            return {"status": "success", "backup_file": backup_file}
        else:
            raise HTTPException(status_code=500, detail="Failed to create backup")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/restore")
async def restore_data(backup_data: Dict[str, Any]):
    try:
        success = service_manager.restore_data(backup_data["backup_file"])
        if success:
            return {"status": "success", "message": "Data restored successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to restore data")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Main function
async def main():
    config = service_manager.config
    
    # Initialize Telegram bot
    application = Application.builder().token(config["telegram_bot_token"]).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("adduser", add_user_command))
    application.add_handler(CommandHandler("deluser", delete_user_command))
    application.add_handler(CommandHandler("listuser", list_users_command))
    
    # Start bot
    await application.initialize()
    await application.start()
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
    
    # Start FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=8000) 