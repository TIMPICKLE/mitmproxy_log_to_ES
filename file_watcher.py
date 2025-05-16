"""
File watcher to monitor log directory for changes
"""
import os
import time
import logging
from typing import Callable, Optional, List

import config

logger = logging.getLogger(__name__)

class FileWatcher:
    """Watch multiple directories for file changes and trigger processing"""
    
    def __init__(self, directories: List[str] = None, callback: Optional[Callable] = None):
        """Initialize file watcher with directories and callback function"""
        self.directories = directories or config.LOG_SOURCE_DIRS
        self.callback = callback
        self.last_processed_time = time.time()
        self._running = False
        
    def start(self, interval: int = None):
        """Start watching directories at specified interval"""
        interval = interval or config.PROCESS_INTERVAL
        self._running = True
        
        logger.info(f"开始监视目录: {self.directories}")
        logger.info(f"设置处理间隔为: {interval} 秒")
        
        try:
            while self._running:
                # Check if enough time has passed since last processing
                current_time = time.time()
                if (current_time - self.last_processed_time) >= interval:
                    logger.debug(f"已达到处理间隔时间 ({interval}秒)，开始处理")
                    
                    # Call the callback function if provided
                    if self.callback:
                        try:
                            logger.debug("调用回调函数处理文件")
                            self.callback()
                        except Exception as e:
                            logger.error(f"回调函数执行出错: {str(e)}")
                            
                    # Update last processed time
                    self.last_processed_time = time.time()
                    logger.debug(f"处理完成，更新最后处理时间为: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.last_processed_time))}")
                
                # Sleep to prevent high CPU usage
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("检测到键盘中断，文件监视器正在停止")
            self.stop()
        except Exception as e:
            logger.error(f"文件监视器出现错误: {str(e)}")
            self.stop()
            raise
            
    def stop(self):
        """Stop the file watcher"""
        logger.info("正在停止文件监视器...")
        self._running = False
        logger.info("文件监视器已停止")
