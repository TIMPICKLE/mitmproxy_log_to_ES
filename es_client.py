"""
Elasticsearch client functionality for storing Copilot logs
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import ElasticsearchException

import config

logger = logging.getLogger(__name__)

class ESClient:
    """Elasticsearch client for storing and retrieving Copilot logs"""
    
    def __init__(self):
        """Initialize Elasticsearch client"""
        self.es = None
        self.connect()
        
    def connect(self) -> bool:
        """Connect to Elasticsearch"""
        try:
            # Build connection parameters
            conn_params = {
                'hosts': [{'host': config.ES_HOST, 'port': config.ES_PORT}],
                'timeout': config.ES_TIMEOUT
            }
            
            # Add SSL if enabled
            if config.ES_USE_SSL:
                conn_params['use_ssl'] = True
                conn_params['verify_certs'] = True
                logger.info("启用SSL连接")
                
            # Add authentication if configured
            if config.ES_USERNAME and config.ES_PASSWORD:
                conn_params['http_auth'] = (config.ES_USERNAME, config.ES_PASSWORD)
                logger.info(f"使用认证连接Elasticsearch: 用户名 {config.ES_USERNAME}")
            else:
                logger.info("使用匿名连接Elasticsearch（无认证）")
            
            self.es = Elasticsearch(**conn_params)
            
            # Test connection
            if self.es.ping():
                logger.info(f"已成功连接到Elasticsearch {config.ES_HOST}:{config.ES_PORT}")
                return True
            else:
                logger.error(f"无法连接到Elasticsearch {config.ES_HOST}:{config.ES_PORT}")
                return False
                
        except ElasticsearchException as e:
            logger.error(f"Elasticsearch连接错误: {str(e)}")
            return False
            
    def create_index_if_not_exists(self, index_name: str) -> bool:
        """Create index if it doesn't exist"""
        try:
            if not self.es.indices.exists(index=index_name):
                # Index mapping for proper data types and analysis
                mapping = {
                    "settings": {
                        "number_of_shards": config.ES_INDEX_SHARDS,
                        "number_of_replicas": config.ES_INDEX_REPLICAS,
                        "max_result_window": config.ES_MAX_RESULT_WINDOW,
                    },
                    "mappings": {
                        "properties": {
                            "timestamp": {"type": "date"},
                            "file_name": {"type": "keyword"},
                            "user_id": {"type": "keyword"},
                            "conversation": {
                                "type": "nested",
                                "properties": {
                                    "role": {"type": "keyword"},
                                    "content": {"type": "text", "analyzer": "standard"},
                                    "timestamp": {"type": "date"}
                                }
                            },
                            "metadata": {
                                "properties": {
                                    "proxy_time_consumed": {"type": "keyword"},
                                    "ip_address": {"type": "ip"},
                                    "machine_id": {"type": "keyword"},
                                    "editor_version": {"type": "keyword"},
                                    "model": {"type": "keyword"}
                                }
                            }
                        }
                    }
                }
                
                self.es.indices.create(index=index_name, body=mapping)
                logger.info(f"已创建索引: {index_name}（分片数: {config.ES_INDEX_SHARDS}, 副本数: {config.ES_INDEX_REPLICAS}）")
                return True
                
            logger.debug(f"索引已存在: {index_name}")
            return True
        except ElasticsearchException as e:
            logger.error(f"创建索引出错 {index_name}: {str(e)}")
            return False
            
    def get_index_name(self) -> str:
        """Get index name with date-based suffix (e.g., copilot-logs-2025-03)"""
        today = datetime.now()
        return f"{config.ES_INDEX_PREFIX}"
    
    def index_document(self, document: Dict[str, Any]) -> Optional[str]:
        """Index a single document"""
        try:
            index_name = self.get_index_name()
            
            # Ensure index exists
            if not self.create_index_if_not_exists(index_name):
                return None
                
            # Index document
            response = self.es.index(
                index=index_name,
                document=document
            )
            
            logger.debug(f"已索引文档到 {index_name}, ID: {response['_id']}")
            return response['_id']
        except ElasticsearchException as e:
            logger.error(f"索引文档出错: {str(e)}")
            return None
            
    def bulk_index(self, documents: list) -> int:
        """Bulk index multiple documents"""
        if not documents:
            return 0
            
        index_name = self.get_index_name()
        
        # Ensure index exists
        if not self.create_index_if_not_exists(index_name):
            logger.error(f"创建索引失败: {index_name}，批量索引操作取消")
            return 0
            
        actions = []
        for doc in documents:
            action = {
                "_index": index_name,
                "_source": doc
            }
            actions.append(action)
            
        try:
            success, failed = 0, 0
            
            logger.info(f"开始批量索引 {len(documents)} 个文档到 {index_name}")
            # Use helpers.bulk for efficient bulk indexing
            success, failed = helpers.bulk(
                self.es,
                actions,
                stats_only=True,
                raise_on_error=False
            )
            
            if failed:
                logger.warning(f"批量索引结果: {success} 个成功, {failed} 个失败")
            else:
                logger.info(f"批量索引完成: {success} 个文档已成功处理")
                
            return success
        except ElasticsearchException as e:
            logger.error(f"批量索引过程中出错: {str(e)}")
            return 0
            
    def search_by_user(self, user_id: str, size: int = 10) -> list:
        """Search documents by user ID"""
        try:
            index_name = self.get_index_name()
            
            logger.info(f"搜索用户 '{user_id}' 的文档，最多返回 {size} 条结果")
            
            query = {
                "query": {
                    "match": {
                        "user_id": user_id
                    }
                },
                "sort": [
                    {"timestamp": {"order": "desc"}}
                ],
                "size": size
            }
            
            response = self.es.search(
                index=f"{config.ES_INDEX_PREFIX}-*",
                body=query
            )
            
            result_count = len(response["hits"]["hits"])
            logger.info(f"搜索完成，找到 {result_count} 个匹配的文档")
            
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except ElasticsearchException as e:
            logger.error(f"按用户搜索出错: {str(e)}")
            return []
