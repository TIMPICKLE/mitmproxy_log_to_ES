"""
Configuration settings for Copilot logs to Elasticsearch application
"""
import os
from pathlib import Path
import glob

# Logs source directory - base directory where multiple user logs are stored
LOGS_BASE_DIR = "your mother fuck path here"

# User logs directories - will find all */chat-panel directories under the base directory
def get_log_directories():
    """Get all user log directories under the base logs directory"""
    return glob.glob(os.path.join(LOGS_BASE_DIR, "*/chat-panel"))

# Log source directories - dynamically found under the base directory
LOG_SOURCE_DIRS = get_log_directories()

# User ID extraction - this will be determined per directory when processing
def get_user_id_from_path(log_dir):
    """Extract user ID from log directory path"""
    return os.path.basename(os.path.dirname(log_dir))  # Extracts user ID from path

# Application working directory
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Elasticsearch configuration
ES_HOST = "localhost"  # Elasticsearch host
ES_PORT = 9200         # Elasticsearch port
ES_USE_SSL = False     # Whether to use SSL for ES connection
ES_USERNAME = None     # ES username (if authentication is enabled)
ES_PASSWORD = None     # ES password (if authentication is enabled)
ES_TIMEOUT = 30        # Connection timeout in seconds
ES_INDEX_PREFIX = "copilot-chat-logs"  # Prefix for Elasticsearch indices

# Index settings
ES_INDEX_SHARDS = 1
ES_INDEX_REPLICAS = 0
ES_MAX_RESULT_WINDOW = 10000

# Processing configuration
PROCESS_INTERVAL = 3000  # Process files every 3000 seconds (50 minutes)
MAX_FILES_PER_BATCH = 100  # Maximum number of files to process in a single batch
PROCESSED_FILES_LOG = os.path.join(APP_DIR, "processed_files.log")  # File to track processed files

# Logging configuration
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = os.path.join(APP_DIR, "logs", "application.log")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5  # Keep 5 backup files

# Ensure logs directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
