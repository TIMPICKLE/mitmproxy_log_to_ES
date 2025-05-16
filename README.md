# GitHub Copilot 日志到 Elasticsearch

这个Python应用程序定时将mitmproxy捕获的GitHub Copilot聊天日志从指定目录获取，解析并上传至Elasticsearch数据库，支持通过Grafana进行可视化分析。

## 功能特点

- 监控指定目录下的JSON日志文件
- 解析并转换JSON数据为Elasticsearch友好格式
- 将日志数据存储至Elasticsearch
- 支持多种运行模式（单次执行、定时执行）
- 提供详细中文日志记录
- 支持断点续传（记录处理过的文件）
- 可配置的Elasticsearch连接参数和索引设置

## 系统要求

- Python 3.8+
- Ubuntu服务器
- mitmproxy（已安装，用于生成日志）
- Elasticsearch 7.x+ 实例
- Grafana（用于数据可视化，可选）

## 安装

### 在有网络环境下安装

1. 克隆此代码库或下载源代码到服务器：

```bash
git clone <repository-url>
cd ESscript
```

2. 创建虚拟环境并安装依赖：

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 在无网络环境下安装（使用离线包）

1. 将整个项目目录（包含`offline_packages`文件夹）传送到服务器

2. 在服务器上创建虚拟环境：

```bash
cd ESscript
sudo python3 -m venv venv
source venv/bin/activate
```

3. 安装Ubuntu所需的虚拟环境包：

```bash
# 如果未安装python3-venv
sudo apt install python3.9-venv  # 或适合您Python版本的包
```

4. 使用离线包安装依赖：

```bash
pip install --no-index --find-links=offline_packages -r requirements.txt
```

> **注意**：在Ubuntu环境下，某些Windows版本的wheel包可能不兼容。如果安装失败，请修改requirements.txt，注释掉不兼容的包（如watchdog、PyYAML等），然后重新安装。主要功能在没有这些依赖的情况下仍然可以正常工作。

## 配置

修改`config.py`文件，根据您的环境设置相关参数：

```python
# 日志源目录
LOG_SOURCE_DIR = "替换为你的日志源目录path"

# Elasticsearch配置
ES_HOST = "localhost"  # Elasticsearch主机
ES_PORT = 9200         # Elasticsearch端口
ES_USERNAME = None     # ES用户名（如果启用了认证）
ES_PASSWORD = None     # ES密码（如果启用了认证）
ES_INDEX_PREFIX = "copilot-logs"  # 索引前缀

# 处理配置
PROCESS_INTERVAL = 3000  # 处理间隔（秒，默认50分钟）
MAX_FILES_PER_BATCH = 100  # 每批次最大处理文件数
```

## 使用方法

### 运行模式

本程序支持多种运行模式，您可以通过命令行参数来选择：

1. **单次执行模式**（推荐无网络环境使用）：
   ```bash
   python main.py --once
   ```
   这种模式下，程序会处理一次未处理的日志文件，然后退出。适合通过cron等外部调度器运行。不需要额外的依赖包。

2. **定时执行模式**（推荐无网络环境使用）：
   ```bash
   python main.py --schedule
   ```
   这种模式下，程序会按照`config.py`中设置的间隔时间(`PROCESS_INTERVAL`，默认为3000秒/50分钟)定期执行处理任务。不需要额外的依赖包。

3. **文件监视模式**（默认模式，需要watchdog依赖）：
   ```bash
   python main.py
   ```
   或明确指定：
   ```bash
   python main.py --watch
   ```
   这种模式下，程序会持续监视日志目录中的新文件。**注意：此模式需要安装watchdog库，在离线环境可能无法使用**。

> **重要提示**：在无网络环境的Ubuntu服务器上，建议使用`--schedule`或`--once`模式，避免使用需要额外依赖的文件监视模式。

### 设置为定时任务（使用systemd）

1. 创建systemd服务文件：

```bash
sudo nano /etc/systemd/system/copilot-log-es.service
```

2. 添加以下内容（注意使用--schedule参数）：

```
[Unit]
Description=GitHub Copilot Log to Elasticsearch Service
After=network.target elasticsearch.service

[Service]
Type=simple
User=sysadm
WorkingDirectory=/path/to/ESscript
ExecStart=/path/to/ESscript/venv/bin/python main.py --schedule
Restart=always
RestartSec=300

[Install]
WantedBy=multi-user.target
```

3. 启用并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable copilot-log-es
sudo systemctl start copilot-log-es
```

4. 查看服务状态：

```bash
sudo systemctl status copilot-log-es
```

### 设置为定时任务（使用cron）

1. 编辑crontab：

```bash
crontab -e
```

2. 添加以下内容（每小时执行一次）：

```
如果在虚拟环境中运行 Python 脚本，使用 cron 定时任务时必须显式激活虚拟环境或指定虚拟环境的 Python 解释器路径
# 假设虚拟环境目录为 `/path/to/venv`
/path/to/venv/bin/python
然后使用此命令
*/60 * * * * /path/to/venv/bin/python /path/to/script.py > /path/to/output.log 2>&1

```

注意：在使用cron时，建议使用`--once`模式，因为cron本身已经提供了定时执行功能。

## 日志输出

程序提供详细的中文日志输出，包括：

- 启动信息（包括运行模式）
- 处理过程中的状态
- Elasticsearch连接和索引信息
- 错误和警告信息

日志文件位于 `logs/application.log`，默认保留5个10MB的轮转日志文件。

```bash
# 查看日志
tail -f logs/application.log
```

## 数据结构

应用程序将每个Copilot日志文件转换为Elasticsearch文档，主要包含以下字段：

- `timestamp`: 日志记录时间
- `user_id`: 用户ID（从路径提取）
- `file_name`: 原始日志文件名
- `conversation`: 对话内容数组
  - `role`: 消息发送者角色（user/assistant）
  - `content`: 消息内容
  - `timestamp`: 消息时间（如可用）
- `metadata`: 其他元数据
  - `proxy_time_consumed`: 代理时间消耗
  - `ip_address`: 用户IP
  - `machine_id`: 机器ID
  - `editor_version`: 编辑器版本
  - `model`: 使用的模型

## Grafana 配置与使用

### 配置 Elasticsearch 数据源

1. 登录 Grafana 管理界面
2. 进入 "Configuration" > "Data Sources"
3. 点击 "Add data source"
4. 选择 "Elasticsearch"
5. 配置数据源参数：
   - Name: Copilot Logs
   - URL: http://elasticsearch:9200 (根据您的环境调整)
   - Access: Server (default)
   - 如果需要认证，填写 Basic Auth 相关信息
   - Index name: copilot-chat-logs (使用通配符匹配所有相关索引)
   - Time field name: timestamp
   - Version: 选择您的 Elasticsearch 版本

### 创建 Grafana 仪表盘

1. 点击左侧菜单中的 "+" 按钮，选择 "Dashboard"
2. 点击 "Add new panel"
3. 配置查询：
   - 数据源选择您刚配置的 Elasticsearch 数据源
   - 在"查询"输入框中输入Lucene查询语法

### Grafana Lucene查询示例

以下是一些有用的 Grafana Lucene 查询示例：

**查看所有对话记录**:
```
*
```

**按特定用户搜索**:
```
user_id:"nihao.Dong"
```

**搜索包含特定关键词的对话**:
```
conversation.content:"python"
```

**组合查询条件**:
```
user_id:"nihao.li" AND conversation.content:"elasticsearch"
```

**查询特定编辑器版本的记录**:
```
metadata.editor_version:"vscode-1.87.0"
```

**查询特定模型的记录**:
```
metadata.model:"gpt-4"
```

## 监控与维护

### 检查处理状态

```bash
cat processed_files.log
```

### 重置处理状态（从头开始处理）

```bash
rm processed_files.log
```

### 确认数据已成功索引到Elasticsearch

```bash
# 查看索引是否存在
curl -X GET "http://localhost:9200/_cat/indices?v"

# 查看指定索引中的文档数量
curl -X GET "http://localhost:9200/copilot-logs-2025-04/_count"

# 查看索引中的一些文档示例
curl -X GET "http://localhost:9200/copilot-logs-2025-04/_search?pretty&size=5"
```

## 故障排除

### 常见问题

1. **程序无法连接到Elasticsearch**
   - 确认Elasticsearch服务运行状态
   - 检查配置中的主机名和端口
   - 验证网络连接和防火墙设置

2. **找不到日志文件**
   - 确认LOG_SOURCE_DIR路径配置正确
   - 检查目录权限

3. **JSON解析错误**
   - 检查日志中的错误详情
   - 验证日志文件格式是否符合预期

4. **依赖包缺失错误**
   - 在无网络环境下，某些依赖可能无法安装（如watchdog）
   - 使用`--schedule`或`--once`模式来避免需要全部依赖的功能
   - 必要时，修改requirements.txt，注释掉不兼容的包

5. **虚拟环境创建失败**
   - 在Ubuntu系统上，可能需要安装python3-venv包：
   ```bash
   sudo apt install python3.9-venv  # 或适合您Python版本的包
   ```

6. **Grafana 无法显示数据**
   - 确认 Elasticsearch 数据源配置正确
   - 验证索引名称匹配 (`copilot-logs-*`)
   - 检查时间范围设置是否合适

### 支持

如有问题或建议，请联系。
