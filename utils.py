"""
Utility functions for the Copilot logs to Elasticsearch application
"""
import os
import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Set

import config

# Set up logging
def setup_logging():
    """Configure application logging"""
    log_dir = os.path.dirname(config.LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config.LOG_LEVEL))
    console_formatter = logging.Formatter(config.LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        config.LOG_FILE, 
        maxBytes=config.LOG_MAX_SIZE,
        backupCount=config.LOG_BACKUP_COUNT
    )
    file_handler.setLevel(getattr(logging, config.LOG_LEVEL))
    file_formatter = logging.Formatter(config.LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# File tracking functions
def get_processed_files() -> Set[str]:
    """Read the list of already processed files from the log"""
    if not os.path.exists(config.PROCESSED_FILES_LOG):
        return set()
    
    with open(config.PROCESSED_FILES_LOG, 'r') as f:
        return set(line.strip() for line in f.readlines())

def mark_file_as_processed(file_path: str):
    """Mark a file as processed by appending to the processed files log"""
    with open(config.PROCESSED_FILES_LOG, 'a') as f:
        f.write(f"{file_path}\n")

# JSON handling
def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load and parse a JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON file {file_path}: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {str(e)}")
        raise

def extract_timestamp_from_filename(filename: str) -> str:
    """Extract timestamp from a mitmproxy log filename pattern"""
    # Example filename: 2025-03-26T06-16-09.008386_f8f9e3fd25_10.8.170.31_vscode-1.87.0_chat-panel.json
    try:
        # Extract timestamp part (before first underscore)
        timestamp_part = filename.split('_')[0]
        # Convert to standard ISO format
        timestamp_iso = timestamp_part.replace('-', ':').replace('T', ' ')
        return timestamp_iso
    except Exception as e:
        logging.warning(f"Could not extract timestamp from filename {filename}: {str(e)}")
        return datetime.now().isoformat()

def extract_machine_id(filename: str) -> str:
    """Extract machine ID from a mitmproxy log filename pattern"""
    try:
        # Second part after underscore
        parts = filename.split('_')
        if len(parts) > 1:
            return parts[1]
        return "unknown"
    except Exception:
        return "unknown"

def extract_ip_address(filename: str) -> str:
    """Extract IP address from a mitmproxy log filename pattern"""
    try:
        # Third part after underscore
        parts = filename.split('_')
        if len(parts) > 2:
            return parts[2]
        return "unknown"
    except Exception:
        return "unknown"

def extract_editor_version(filename: str) -> str:
    """Extract editor version from a mitmproxy log filename pattern"""
    try:
        # Fourth part after underscore
        parts = filename.split('_')
        if len(parts) > 3:
            return parts[3]
        return "unknown"
    except Exception:
        return "unknown"
