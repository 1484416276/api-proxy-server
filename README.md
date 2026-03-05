# API 聚合代理服务器

一个强大的 API 聚合代理服务器，支持多个 LLM 提供商的统一接入、自动重试、负载均衡和详细日志记录。

## ✨ 功能特性

- 🔀 **多提供商支持**：支持 OpenAI、智谱 AI、DeepSeek、硅基流动等多个 LLM 提供商
- 🔄 **自动重试**：自动处理 429 错误（请求过多），支持自定义重试策略
- 📊 **详细日志**：记录所有请求的详细信息，包括客户端 IP、请求头、请求体等
- 🔑 **密钥管理**：支持创建、编辑、删除 API 密钥，每个密钥可映射多个模型
- 🌐 **Web 管理界面**：提供友好的 Web UI 进行配置和管理
- 🚀 **高性能**：基于 Python 的异步 HTTP 服务器，支持高并发

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置服务器

复制示例配置文件：

```bash
cp config.json.example config.json
```

编辑 `config.json`：

```json
{
  "proxy_port": 8080,
  "use_https": false,
  "admin_key": "your-admin-key-here"
}
```

### 3. 生成 SSL 证书（可选）

如果需要 HTTPS 支持：

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

### 4. 启动服务器

```bash
python3 proxy.py
```

服务器将在 `http://localhost:8080` 启动。

## 📖 使用指南

### 访问管理界面

打开浏览器访问：`http://your-server:8080/`

### 创建 API 密钥

1. 点击 "Create Key" 标签
2. 输入 Admin Key（默认：admin123）
3. 配置提供商 API 密钥
4. 选择要使用的模型
5. 点击 "Create Key" 生成聚合密钥

### 使用 API 密钥

在客户端配置：

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-your-aggregated-key",
    base_url="http://your-server:8080/v1"
)

response = client.chat.completions.create(
    model="your-model-name",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## 🔧 配置说明

### 提供商配置

支持以下提供商：

- **OpenAI**: `openai`
- **智谱 AI**: `zhipu`, `zhipu_coding`
- **DeepSeek**: `deepseek`
- **硅基流动**: `siliconflow`
- **Anthropic**: `anthropic`
- **阿里云**: `alibaba`
- **百度**: `baidu`
- **腾讯**: `tencent`
- **Moonshot**: `moonshot`
- **MiniMax**: `minimax`
- **零一万物**: `yi`

### 模型映射

每个 API 密钥可以映射多个模型：

```json
{
  "model_mappings": {
    "my_gpt4": {
      "provider": "openai",
      "real_model": "gpt-4",
      "retry_on_429": true,
      "retry_delay": 1,
      "max_retries": 999999
    }
  }
}
```

## 📊 日志查看

### 查看实时日志

```bash
tail -f requests.log
```

### 查看最近日志

```bash
tail -50 requests.log
```

## 🔒 安全建议

1. **修改默认 Admin Key**：在配置文件中设置强密码
2. **使用 HTTPS**：在生产环境中启用 HTTPS
3. **限制访问**：使用防火墙限制访问 IP
4. **定期更新密钥**：定期轮换 API 密钥

## 📝 API 文档

### 管理接口

- `GET /` - 管理界面
- `GET /config` - 获取配置
- `POST /config` - 更新配置
- `GET /keys` - 获取所有密钥（需要 Admin Key）
- `POST /keys` - 创建新密钥（需要 Admin Key）
- `GET /keys/{id}` - 获取指定密钥
- `PUT /keys/{id}` - 更新密钥（需要 Admin Key）
- `DELETE /keys/{id}` - 删除密钥（需要 Admin Key）

### 代理接口

- `GET /v1/models` - 获取模型列表
- `POST /v1/chat/completions` - 聊天补全
- `POST /v1/embeddings` - 文本嵌入
- `POST /v1/completions` - 文本补全

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

感谢所有 LLM 提供商的支持！
