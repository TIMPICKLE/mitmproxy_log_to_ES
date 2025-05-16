#!/usr/bin/env python3
"""
Main entry point for the Copilot logs to Elasticsearch application
"""
import os
import sys
import time
import logging
import signal
import argparse
from datetime import datetime

import schedule

import config
import utils
from es_client import ESClient
from log_processor import LogProcessor
from file_watcher import FileWatcher

logger = None  # Will be initialized in main()

def process_logs():
    """Process logs and upload to Elasticsearch"""
    try:
        logger.info("开始日志处理周期")
        
        # Initialize processor and ES client
        processor = LogProcessor()
        es_client = ESClient()
        
        # Process files (limit to max per batch)
        documents = processor.process_files(config.MAX_FILES_PER_BATCH)
        
        if documents:
            # Upload to Elasticsearch using bulk API
            success_count = es_client.bulk_index(documents)
            logger.info(f"已成功索引 {success_count}/{len(documents)} 个文档到Elasticsearch")
        else:
            logger.info("没有新文档需要索引")
            
    except Exception as e:
        logger.error(f"日志处理出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def run_scheduled():
    """Run with scheduling"""
    logger.info("启动定时执行模式")
    
    # Schedule processing at regular intervals
    interval_minutes = config.PROCESS_INTERVAL // 60 or 1  # Convert to minutes, minimum 1
    logger.info(f"设置处理间隔为 {interval_minutes} 分钟")
    schedule.every(interval_minutes).minutes.do(process_logs)
    
    # Add a heartbeat log every hour
    schedule.every(60).minutes.do(lambda: logger.info(f"程序心跳 - 定时执行模式仍在运行中 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
    
    # Run once immediately
    logger.info("立即执行第一次处理")
    process_logs()
    
    # Keep running until interrupted
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("用户中断，定时执行已停止")
    except Exception as e:
        logger.error(f"定时执行出错: {str(e)}")
        raise

def run_watcher():
    """Run with file watcher"""
    logger.info("启动文件监视模式")
    logger.info(f"监视目录: {config.LOG_SOURCE_DIRS}")
    
    # Initialize file watcher with callback
    watcher = FileWatcher(callback=process_logs)
    
    # Handle SIGTERM gracefully
    def handle_sigterm(signum, frame):
        logger.info("收到SIGTERM信号，正在关闭...")
        watcher.stop()
        sys.exit(0)
        
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    # Start watcher
    watcher.start()
    
def run_once():
    """Run process once and exit"""
    logger.info("启动单次执行模式")
    process_logs()
    logger.info("单次执行完成")

def main():
    """Main entry point"""
    global logger
    
    # Set up logging
    logger = utils.setup_logging()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='处理GitHub Copilot日志并上传到Elasticsearch')
    parser.add_argument('--once', action='store_true', help='单次执行模式(执行一次后退出)')
    parser.add_argument('--schedule', action='store_true', help='定时执行模式(按固定间隔运行)')
    parser.add_argument('--watch', action='store_true', help='文件监视模式(监视文件变化)')
    args = parser.parse_args()
    
    try:
        current_time = datetime.now().isoformat()
        logger.info(f"GitHub Copilot日志到Elasticsearch应用程序启动于 {current_time}")
        logger.info(f"日志源目录: {config.LOGS_BASE_DIR}")
        logger.info(f"用户日志目录: {config.LOG_SOURCE_DIRS}")
        logger.info(f"Elasticsearch: {config.ES_HOST}:{config.ES_PORT}")
        
        # Determine run mode
        if args.once:
            run_once()
        elif args.schedule:
            run_scheduled()
        elif args.watch:
            run_watcher()
        else:
            # Default: run with file watcher
            logger.info("未指定运行模式，默认使用文件监视模式")
            run_watcher()
            
    except Exception as e:
        logger.critical(f"未处理的异常: {str(e)}")
        import traceback
        logger.critical(traceback.format_exc())
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
