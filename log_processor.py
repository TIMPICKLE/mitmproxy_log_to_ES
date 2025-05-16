"""
Log processor for handling Copilot JSON log files
"""
import os
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import traceback

import config
import utils

logger = logging.getLogger(__name__)

class LogProcessor:
    """Process Copilot log files and prepare for Elasticsearch indexing"""
    
    def __init__(self, source_dirs: List[str] = None):
        """Initialize log processor with source directories"""
        self.source_dirs = source_dirs or config.LOG_SOURCE_DIRS
        self.processed_files = utils.get_processed_files()
        
    def get_unprocessed_files(self, max_files: int = None) -> List[Dict[str, str]]:
        """Get list of unprocessed files from all source directories"""
        unprocessed_files = []
        
        for source_dir in self.source_dirs:
            if not os.path.exists(source_dir):
                logger.error(f"源目录不存在: {source_dir}")
                continue
            
            # Extract user_id from this directory
            user_id = config.get_user_id_from_path(source_dir)
                
            for root, _, files in os.walk(source_dir):
                for file in files:
                    if file.endswith('.json'):
                        full_path = os.path.join(root, file)
                        if full_path not in self.processed_files:
                            unprocessed_files.append({
                                'path': full_path,
                                'user_id': user_id
                            })
        
        # Sort by modification time (oldest first)
        unprocessed_files.sort(key=lambda f: os.path.getmtime(f['path']))
        
        # Limit number of files if max_files is specified
        if max_files is not None and max_files > 0:
            unprocessed_files = unprocessed_files[:max_files]
            
        logger.info(f"找到 {len(unprocessed_files)} 个未处理的文件")
        return unprocessed_files
    
    def extract_conversation(self, log_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract conversation messages from log data"""
        conversation = []
        
        try:
            # Get messages from the request content
            if 'request' in log_data and 'content' in log_data['request']:
                request_content = log_data['request']['content']
                
                # Handle case when content is a string (possible JSON string)
                if isinstance(request_content, str):
                    try:
                        request_content = json.loads(request_content)
                    except json.JSONDecodeError:
                        logger.warning("无法将请求内容解析为JSON")
                
                # Now extract messages if available
                if isinstance(request_content, dict) and 'messages' in request_content:
                    for msg in request_content['messages']:
                        if 'role' in msg and 'content' in msg:
                            conversation.append({
                                'role': msg['role'],
                                'content': msg['content'],
                                'timestamp': log_data.get('timestamp')  # Use log timestamp as fallback
                            })
            
            # Extract assistant's response from the response content
            if 'response' in log_data and 'content' in log_data['response']:
                response_content = log_data['response']['content']
                
                # Handle case when content is a string (possible JSON string)
                if isinstance(response_content, str):
                    try:
                        response_content = json.loads(response_content)
                    except json.JSONDecodeError:
                        # If it's not valid JSON, treat it as plain text response
                        conversation.append({
                            'role': 'assistant',
                            'content': response_content,
                            'timestamp': log_data.get('timestamp')
                        })
                        response_content = None  # Skip further processing
                
                # The response might be a list of streaming chunks
                if isinstance(response_content, list):
                    # Reconstruct the complete response
                    assistant_message = ""
                    for chunk in response_content:
                        if isinstance(chunk, dict) and 'choices' in chunk and chunk['choices']:
                            for choice in chunk['choices']:
                                if isinstance(choice, dict) and 'delta' in choice:
                                    delta = choice['delta']
                                    if isinstance(delta, dict) and 'content' in delta and delta['content']:
                                        assistant_message += delta['content']
                    
                    if assistant_message:
                        conversation.append({
                            'role': 'assistant',
                            'content': assistant_message,
                            'timestamp': log_data.get('timestamp')
                        })
                # Handle case where response_content is a dict with direct choices
                elif isinstance(response_content, dict) and 'choices' in response_content:
                    choices = response_content['choices']
                    if isinstance(choices, list) and len(choices) > 0:
                        choice = choices[0]
                        if isinstance(choice, dict) and 'message' in choice:
                            message = choice['message']
                            if isinstance(message, dict) and 'content' in message:
                                conversation.append({
                                    'role': 'assistant',
                                    'content': message['content'],
                                    'timestamp': log_data.get('timestamp')
                                })
                
        except Exception as e:
            logger.error(f"提取对话内容出错: {str(e)}")
            logger.debug(traceback.format_exc())
            
        return conversation
    
    def extract_metadata(self, log_data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Extract metadata from log data and filename"""
        metadata = {}
        
        try:
            # Extract proxy time consumed
            if 'proxy-time-consumed' in log_data:
                metadata['proxy_time_consumed'] = log_data['proxy-time-consumed']
                
            # Extract IP address (from filename and request)
            metadata['ip_address'] = utils.extract_ip_address(os.path.basename(filename))
            
            # Extract machine ID (from filename)
            metadata['machine_id'] = utils.extract_machine_id(os.path.basename(filename))
            
            # Extract editor version (from filename and headers)
            metadata['editor_version'] = utils.extract_editor_version(os.path.basename(filename))
            
            # Extract model information
            if 'request' in log_data and 'content' in log_data['request'] and 'model' in log_data['request']['content']:
                metadata['model'] = log_data['request']['content']['model']
                
        except Exception as e:
            logger.error(f"提取元数据出错: {str(e)}")
            logger.debug(traceback.format_exc())
            
        return metadata
    
    def process_file(self, file_info: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process a single log file and return Elasticsearch document"""
        try:
            file_path = file_info['path']
            user_id = file_info['user_id']
            
            # Load JSON file
            logger.debug(f"开始处理文件: {file_path}")
            log_data = utils.load_json_file(file_path)
            
            # Get file name without path
            file_name = os.path.basename(file_path)
            
            # Create document structure
            document = {
                'timestamp': log_data.get('timestamp', datetime.now().isoformat()),
                'file_name': file_name,
                'user_id': user_id,
                'conversation': self.extract_conversation(log_data),
                'metadata': self.extract_metadata(log_data, file_name)
            }
            
            logger.debug(f"成功解析文件: {file_name}")
            return document
        except Exception as e:
            logger.error(f"处理文件出错 {file_path}: {str(e)}")
            logger.debug(traceback.format_exc())
            return None
    
    def process_files(self, max_files: int = None) -> List[Dict[str, Any]]:
        """Process multiple log files and return list of Elasticsearch documents"""
        # Get unprocessed files
        files_to_process = self.get_unprocessed_files(max_files)
        
        if not files_to_process:
            logger.info("没有文件需要处理")
            return []
        
        logger.info(f"开始处理 {len(files_to_process)} 个文件")
        documents = []
        for file_info in files_to_process:
            try:
                document = self.process_file(file_info)
                file_path = file_info['path']
                
                if document:
                    documents.append(document)
                    # Mark as processed
                    utils.mark_file_as_processed(file_path)
                    logger.info(f"已处理文件: {os.path.basename(file_path)}")
                else:
                    logger.warning(f"文件处理失败: {file_path}")
                    
            except Exception as e:
                logger.error(f"处理文件时出错 {file_info['path']}: {str(e)}")
                logger.debug(traceback.format_exc())
                
        logger.info(f"已成功处理 {len(documents)} 个文件")
        return documents
