#!/usr/bin/env python3
import http.server
import socketserver
import ssl
import requests
import json
import time
import os
import uuid
import secrets
from urllib.parse import urlparse, urljoin
from datetime import datetime

CONFIG_FILE = "config.json"
KEYS_FILE = "keys.json"

DEFAULT_CONFIG = {
    "proxy_port": 8443,
    "use_https": True,
    "admin_key": "admin123"
}

PROVIDERS = {
    "zhipu": {
        "name": "智谱AI",
        "base_url": "https://open.bigmodel.cn",
        "api_path": "/api/paas/v4",
        "models_api": "/api/paas/v4/models",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer "
    },
    "zhipu_coding": {
        "name": "智谱AI Coding",
        "base_url": "https://open.bigmodel.cn",
        "api_path": "/api/coding/paas/v4",
        "models_api": "/api/coding/paas/v4/models",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer "
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com",
        "api_path": "/v1",
        "models_api": "/v1/models",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer "
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "api_path": "/v1",
        "models_api": "/v1/models",
        "auth_header": "x-api-key",
        "auth_prefix": ""
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "api_path": "/v1",
        "models_api": "/v1/models",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer "
    },
    "alibaba": {
        "name": "阿里云通义千问",
        "base_url": "https://dashscope.aliyuncs.com/api/v1",
        "api_path": "/services/aigc/text-generation/generation",
        "models_api": "/services/aigc/text-generation/generation",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer "
    },
    "baidu": {
        "name": "百度文心一言",
        "base_url": "https://aip.baidubce.com",
        "api_path": "/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
        "models_api": "/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer "
    },
    "tencent": {
        "name": "腾讯混元",
        "base_url": "https://hunyuan.tencentcloudapi.com",
        "api_path": "/",
        "models_api": "/",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer "
    },
    "moonshot": {
        "name": "Moonshot AI",
        "base_url": "https://api.moonshot.cn",
        "api_path": "/v1",
        "models_api": "/v1/models",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer "
    },
    "minimax": {
        "name": "MiniMax",
        "base_url": "https://api.minimax.chat",
        "api_path": "/v1",
        "models_api": "/v1/models",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer "
    },
    "yi": {
        "name": "零一万物",
        "base_url": "https://api.lingyiwanwu.com",
        "api_path": "/v1",
        "models_api": "/v1/models",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer "
    },
    "siliconflow": {
        "name": "硅基流动",
        "base_url": "https://api.siliconflow.cn",
        "api_path": "/v1",
        "models_api": "/v1/models",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer "
    }
}

config = DEFAULT_CONFIG.copy()
api_keys = {}

def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                loaded = json.load(f)
                config.update(loaded)
        except:
            pass

def save_config():
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_keys():
    global api_keys
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, 'r') as f:
                api_keys = json.load(f)
        except:
            api_keys = {}

def save_keys():
    with open(KEYS_FILE, 'w') as f:
        json.dump(api_keys, f, indent=2)

load_config()
load_keys()

LOG_FILE = "requests.log"

def log_request(method, path, status_code, extra_info="", headers=None, body=None, client_ip=None):
    timestamp = datetime.now().isoformat()
    log_line = f"[{timestamp}] {method} {path} - {status_code}"
    if extra_info:
        log_line += f" - {extra_info}"
    print(log_line)
    
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_line + '\n')
            if client_ip:
                f.write(f"  Client: {client_ip}\n")
            if headers:
                f.write("  Headers:\n")
                for key, value in headers.items():
                    if key.lower() in ['authorization', 'x-admin-key']:
                        value = value[:20] + '...' if len(value) > 20 else value
                    f.write(f"    {key}: {value}\n")
            if body:
                f.write(f"  Body: {body[:500]}\n" if len(body) > 500 else f"  Body: {body}\n")
            f.write("-" * 80 + "\n")
    except:
        pass

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def send_error_response(self, message, status=400):
        self.send_json_response({"error": message}, status)

    def do_GET(self):
        client_ip = self.client_address[0]
        log_request("GET", self.path, 0, "request received", client_ip=client_ip)
        if self.path == '/':
            self.send_html_page()
        elif self.path == '/config':
            self.send_json_response(config)
        elif self.path == '/providers':
            self.send_json_response(PROVIDERS)
        elif self.path == '/keys':
            admin_key = self.headers.get('X-Admin-Key', '')
            if admin_key != config.get('admin_key'):
                self.send_error_response("Unauthorized", 401)
                return
            self.send_json_response(api_keys)
        elif self.path == '/v1/models':
            self.handle_list_models()
        elif self.path.startswith('/keys/'):
            admin_key = self.headers.get('X-Admin-Key', '')
            if admin_key != config.get('admin_key'):
                self.send_error_response("Unauthorized", 401)
                return
            key_id = self.path.split('/')[-1]
            if key_id in api_keys:
                self.send_json_response(api_keys[key_id])
            else:
                self.send_error_response("Key not found", 404)
        elif self.path.startswith('/providers/'):
            if self.command == 'GET':
                self.handle_provider_models()
            elif self.command == 'POST':
                self.handle_temp_provider_models()
        else:
            self.proxy_request()

    def do_POST(self):
        client_ip = self.client_address[0]
        log_request("POST", self.path, 0, "request received", client_ip=client_ip)
        if self.path == '/config':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                new_config = json.loads(post_data.decode('utf-8'))
                config.update(new_config)
                save_config()
                self.send_json_response({"status": "success"})
            except Exception as e:
                self.send_error_response(str(e))
        
        elif self.path == '/keys':
            admin_key = self.headers.get('X-Admin-Key', '')
            if admin_key != config.get('admin_key'):
                self.send_error_response("Unauthorized", 401)
                return
            
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                key_config = json.loads(post_data.decode('utf-8'))
                
                if not key_config.get('name'):
                    self.send_error_response("Missing required field: name")
                    return
                
                if not key_config.get('providers'):
                    self.send_error_response("Missing required field: providers")
                    return
                
                key_id = str(uuid.uuid4())
                access_key = f"sk-{secrets.token_urlsafe(32)}"
                
                api_keys[key_id] = {
                    "id": key_id,
                    "access_key": access_key,
                    "name": key_config['name'],
                    "providers": key_config['providers'],
                    "model_mappings": key_config.get('model_mappings', {}),
                    "created_at": datetime.now().isoformat(),
                    "usage_count": 0
                }
                
                save_keys()
                self.send_json_response(api_keys[key_id])
            except Exception as e:
                self.send_error_response(str(e))
        
        elif self.path.startswith('/providers/'):
            self.handle_temp_provider_models()
        
        else:
            self.proxy_request()

    def do_DELETE(self):
        client_ip = self.client_address[0]
        log_request("DELETE", self.path, 0, "request received", client_ip=client_ip)
        if self.path.startswith('/keys/'):
            admin_key = self.headers.get('X-Admin-Key', '')
            if admin_key != config.get('admin_key'):
                self.send_error_response("Unauthorized", 401)
                return
            
            key_id = self.path.split('/')[-1]
            if key_id in api_keys:
                del api_keys[key_id]
                save_keys()
                self.send_json_response({"status": "deleted"})
            else:
                self.send_error_response("Key not found", 404)
        else:
            self.proxy_request()

    def do_PUT(self):
        client_ip = self.client_address[0]
        log_request("PUT", self.path, 0, "request received", client_ip=client_ip)
        if self.path.startswith('/keys/'):
            admin_key = self.headers.get('X-Admin-Key', '')
            if admin_key != config.get('admin_key'):
                self.send_error_response("Unauthorized", 401)
                return
            
            key_id = self.path.split('/')[-1]
            if key_id not in api_keys:
                self.send_error_response("Key not found", 404)
                return
            
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                updates = json.loads(post_data.decode('utf-8'))
                
                for key in ['name', 'providers', 'model_mappings']:
                    if key in updates:
                        api_keys[key_id][key] = updates[key]
                
                save_keys()
                self.send_json_response(api_keys[key_id])
            except Exception as e:
                self.send_error_response(str(e))
        else:
            self.proxy_request()

    def do_PATCH(self):
        client_ip = self.client_address[0]
        log_request("PATCH", self.path, 0, "request received", client_ip=client_ip)
        self.proxy_request()
    
    def do_OPTIONS(self):
        client_ip = self.client_address[0]
        log_request("OPTIONS", self.path, 0, "CORS preflight request", 
                   client_ip=client_ip, headers=dict(self.headers))
        
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, PATCH, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()
    
    def do_HEAD(self):
        client_ip = self.client_address[0]
        log_request("HEAD", self.path, 0, "request received", client_ip=client_ip)
        self.send_response(200)
        self.end_headers()

    def handle_provider_models(self):
        auth_header = self.headers.get('Authorization', '') or self.headers.get('X-Api-Key', '')
        key_config = self.get_key_config(auth_header)
        
        if not key_config:
            self.send_error_response("Invalid API key", 401)
            return
        
        parts = self.path.split('/')
        if len(parts) < 3:
            self.send_error_response("Invalid path", 400)
            return
        
        provider_id = parts[2]
        
        if provider_id not in PROVIDERS:
            self.send_error_response("Unknown provider", 400)
            return
        
        provider_info = PROVIDERS[provider_id]
        provider_config = key_config['providers'].get(provider_id, {})
        
        if not provider_config:
            self.send_error_response("Provider not configured", 400)
            return
        
        try:
            api_key = provider_config['api_key']
            base_url = provider_config.get('base_url') or provider_info['base_url']
            models_api = provider_info['models_api']
            
            headers = {}
            headers[provider_info['auth_header']] = provider_info['auth_prefix'] + api_key
            
            response = requests.get(
                base_url + models_api,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                models_data = response.json()
                self.send_json_response(models_data)
            else:
                self.send_error_response(f"Failed to fetch models: {response.status_code}", 500)
        except Exception as e:
            self.send_error_response(f"Error fetching models: {str(e)}", 500)

    def handle_temp_provider_models(self):
        admin_key = self.headers.get('X-Admin-Key', '')
        if admin_key != config.get('admin_key'):
            self.send_error_response("Unauthorized", 401)
            return
        
        parts = self.path.split('/')
        if len(parts) < 3:
            self.send_error_response("Invalid path", 400)
            return
        
        provider_id = parts[2]
        
        if provider_id not in PROVIDERS:
            self.send_error_response("Unknown provider", 400)
            return
        
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_error_response("Missing request body", 400)
            return
        
        try:
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            api_key = data.get('api_key')
            base_url = data.get('base_url')
            
            if not api_key:
                self.send_error_response("Missing api_key", 400)
                return
            
            provider_info = PROVIDERS[provider_id]
            base_url = base_url or provider_info['base_url']
            models_api = provider_info['models_api']
            
            headers = {}
            headers[provider_info['auth_header']] = provider_info['auth_prefix'] + api_key
            
            response = requests.get(
                base_url + models_api,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                models_data = response.json()
                self.send_json_response(models_data)
            else:
                self.send_error_response(f"Failed to fetch models: {response.status_code}", 500)
        except Exception as e:
            self.send_error_response(f"Error fetching models: {str(e)}", 500)

    def handle_list_models(self):
        client_ip = self.client_address[0]
        log_request(self.command, self.path, 0, "list models request", client_ip=client_ip)
        auth_header = self.headers.get('Authorization', '') or self.headers.get('X-Api-Key', '')
        key_config = self.get_key_config(auth_header)
        
        if not key_config:
            log_request(self.command, self.path, 401, "Invalid API key", client_ip=client_ip)
            self.send_error_response("Invalid API key", 401)
            return
        
        model_mappings = key_config.get('model_mappings', {})
        
        models_list = []
        for custom_name, mapping in model_mappings.items():
            models_list.append({
                "id": custom_name,
                "object": "model",
                "created": int(time.time()),
                "owned_by": mapping.get('provider', 'unknown')
            })
        
        log_request(self.command, self.path, 200, f"returned {len(models_list)} models", client_ip=client_ip)
        self.send_json_response({
            "object": "list",
            "data": models_list
        })

    def get_key_config(self, auth_header):
        if not auth_header:
            return None
        
        if auth_header.startswith('Bearer '):
            access_key = auth_header[7:]
        else:
            access_key = auth_header
        
        for key_id, key_config in api_keys.items():
            if key_config['access_key'] == access_key:
                return key_config
        
        return None

    def get_model_mapping(self, key_config, model_name):
        model_mappings = key_config.get('model_mappings', {})
        return model_mappings.get(model_name)

    def proxy_request(self):
        client_ip = self.client_address[0]
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else None
        
        request_body = {}
        if body:
            try:
                request_body = json.loads(body.decode('utf-8'))
            except:
                pass
        
        log_request(self.command, self.path, 0, "incoming request", 
                   client_ip=client_ip, headers=dict(self.headers), 
                   body=json.dumps(request_body) if request_body else None)
        
        auth_header = self.headers.get('Authorization', '') or self.headers.get('X-Api-Key', '')
        key_config = self.get_key_config(auth_header)
        
        if not key_config:
            log_request(self.command, self.path, 401, "Invalid API key", 
                       client_ip=client_ip, headers=dict(self.headers), 
                       body=json.dumps(request_body) if request_body else None)
            self.send_error_response("Invalid API key", 401)
            return
        
        model_name = request_body.get('model', '')
        model_mapping = self.get_model_mapping(key_config, model_name)
        
        if not model_mapping:
            log_request(self.command, self.path, 400, f"Model '{model_name}' not found", 
                       client_ip=client_ip, body=json.dumps(request_body))
            self.send_error_response(f"Model '{model_name}' not found in mappings", 400)
            return
        
        provider_id = model_mapping.get('provider')
        real_model = model_mapping.get('real_model', model_name)
        
        provider_config = key_config['providers'].get(provider_id, {})
        
        if not provider_config:
            log_request(self.command, self.path, 400, f"Provider '{provider_id}' not configured", 
                       client_ip=client_ip, body=json.dumps(request_body))
            self.send_error_response(f"Provider '{provider_id}' not configured", 400)
            return
        
        base_url = provider_config.get('base_url') or (PROVIDERS.get(provider_id, {}).get('base_url', ''))
        api_path = provider_config.get('api_path') or (PROVIDERS.get(provider_id, {}).get('api_path', '/v1'))
        
        if not base_url:
            log_request(self.command, self.path, 400, f"Base URL not configured for '{provider_id}'", 
                       client_ip=client_ip, body=json.dumps(request_body))
            self.send_error_response(f"Base URL not configured for provider '{provider_id}'", 400)
            return
        
        target_url = base_url.rstrip('/') + api_path + self.path.replace('/v1', '')
        log_request(self.command, self.path, 0, f"model={model_name} -> {target_url}", 
                   client_ip=client_ip, headers=dict(self.headers), body=json.dumps(request_body))
        
        request_body['model'] = real_model
        modified_body = json.dumps(request_body).encode('utf-8')
        
        headers = {}
        for key, value in self.headers.items():
            if key.lower() not in ['host', 'content-length', 'authorization']:
                headers[key] = value
        
        auth_header = PROVIDERS.get(provider_id, {}).get('auth_header', 'Authorization')
        auth_prefix = PROVIDERS.get(provider_id, {}).get('auth_prefix', 'Bearer ')
        headers[auth_header] = auth_prefix + provider_config['api_key']
        headers['Content-Length'] = str(len(modified_body))

        retry_count = 0
        max_retries = model_mapping.get('max_retries', 999999)
        retry_on_429 = model_mapping.get('retry_on_429', True)
        retry_delay = model_mapping.get('retry_delay', 1)
        
        while True:
            try:
                method = self.command
                response = requests.request(
                    method=method,
                    url=target_url,
                    headers=headers,
                    data=modified_body,
                    allow_redirects=False,
                    timeout=300,
                    stream=True
                )

                if response.status_code == 429 and retry_on_429 and retry_count < max_retries:
                    retry_count += 1
                    log_request(self.command, self.path, 429, f"retry {retry_count}/{max_retries} in {retry_delay}s", 
                               client_ip=client_ip)
                    time.sleep(retry_delay)
                    continue

                api_keys[key_config['id']]['usage_count'] += 1
                api_keys[key_config['id']]['last_used'] = datetime.now().isoformat()
                save_keys()
                
                log_request(self.command, self.path, response.status_code, f"success, model={real_model}", 
                           client_ip=client_ip)

                self.send_response(response.status_code)
                for key, value in response.headers.items():
                    if key.lower() not in ['content-encoding', 'transfer-encoding', 'connection']:
                        self.send_header(key, value)
                self.end_headers()
                
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        self.wfile.write(chunk)
                break

            except requests.exceptions.RequestException as e:
                log_request(self.command, self.path, 502, f"Proxy error: {str(e)}", 
                           client_ip=client_ip, body=json.dumps(request_body))
                self.send_response(502)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {"error": f"Proxy error: {str(e)}"}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
                break

    def send_html_page(self):
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>API Aggregation Platform</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }
        .header h1 { margin: 0 0 10px 0; }
        .header p { margin: 0; opacity: 0.9; }
        .card { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: 600; color: #333; }
        input[type="text"], input[type="number"], select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }
        button { background: #667eea; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; margin-right: 10px; margin-top: 5px; }
        button:hover { background: #5568d3; }
        button.danger { background: #e53e3e; }
        button.success { background: #48bb78; }
        button.small { padding: 5px 10px; font-size: 12px; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab { padding: 10px 20px; background: white; border: none; border-radius: 5px; cursor: pointer; }
        .tab.active { background: #667eea; color: white; }
        .model-selector { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }
        .model-list { border: 1px solid #ddd; border-radius: 5px; padding: 15px; max-height: 400px; overflow-y: auto; }
        .model-item { padding: 10px; border-bottom: 1px solid #eee; cursor: pointer; }
        .model-item:hover { background: #f8f9fa; }
        .model-item.selected { background: #e6fffa; border-left: 3px solid #48bb78; }
        .selected-models { background: #f8f9fa; }
        .selected-model-item { display: flex; justify-content: space-between; align-items: center; padding: 10px; background: white; margin: 5px 0; border-radius: 5px; }
        .status { margin-top: 20px; padding: 10px; border-radius: 5px; }
        .success { background: #c6f6d5; color: #22543d; }
        .error { background: #fed7d7; color: #742a2a; }
        .info { background: #bee3f8; color: #2a4365; padding: 15px; border-radius: 5px; margin-top: 20px; }
        code { background: #e2e8f0; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
        .provider-config { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 3px solid #667eea; }
        .search-box { margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔑 API Aggregation Platform</h1>
        <p>One key to access multiple AI providers with custom model names</p>
    </div>

    <div class="tabs">
        <button class="tab active" onclick="showTab('keys', this)">API Keys</button>
        <button class="tab" onclick="showTab('create', this)">Create Key</button>
        <button class="tab" onclick="showTab('settings', this)">Settings</button>
    </div>

    <div id="keys-tab" class="card">
        <h2>📋 Your API Keys</h2>
        <div class="form-group">
            <label>Admin Key:</label>
            <input type="text" id="admin_key" placeholder="Enter admin key to view keys">
        </div>
        <button onclick="loadKeys()">Load Keys</button>
        <div id="key-list"></div>
    </div>

    <div id="create-tab" class="card" style="display:none">
        <h2>➕ Create New Aggregation Key</h2>
        
        <div class="form-group">
            <label>Admin Key:</label>
            <input type="text" id="create_admin_key" placeholder="Enter admin key (default: admin123)">
        </div>
        
        <div class="form-group">
            <label>Key Name:</label>
            <input type="text" id="key_name" placeholder="My Aggregation Key">
        </div>
        
        <h3>1. Configure Providers</h3>
        <div id="providers-container"></div>
        <button class="success" onclick="addProvider()">+ Add Provider</button>
        
        <h3 style="margin-top: 30px;">2. Select Models</h3>
        <p style="color: #666; font-size: 14px;">Click on models to select them. Selected models will be shown on the right.</p>
        
        <div class="model-selector">
            <div>
                <h4>Available Models</h4>
                <div class="search-box">
                    <input type="text" id="model_search" placeholder="Search models..." onkeyup="filterModels()">
                </div>
                <div class="model-list" id="available-models"></div>
            </div>
            <div>
                <h4>Selected Models</h4>
                <div class="model-list selected-models" id="selected-models"></div>
            </div>
        </div>
        
        <button onclick="createKey()" style="margin-top: 20px;">Create Key</button>
        <div id="create-status"></div>
    </div>

    <div id="settings-tab" class="card" style="display:none">
        <h2>⚙️ Settings</h2>
        <div class="form-group">
            <label>Proxy Port:</label>
            <input type="number" id="proxy_port" value="8443">
        </div>
        <div class="form-group">
            <label>Use HTTPS:</label>
            <input type="checkbox" id="use_https" checked>
        </div>
        <div class="form-group">
            <label>Admin Key:</label>
            <input type="text" id="settings_admin_key">
        </div>
        <button onclick="saveSettings()">Save Settings</button>
        <div id="settings-status"></div>
    </div>

    <div class="info">
        <strong>📖 How to use:</strong><br>
        1. Configure your provider API keys<br>
        2. Select models you want to use<br>
        3. Create an aggregation key<br>
        4. Use the generated key: <code>Authorization: Bearer sk-xxx</code><br>
        5. Call models with custom names: <code>{"model": "zhipu_glm5", ...}</code>
    </div>

    <script>
        let providers = {};
        let selectedModels = {};
        
        async function loadProviders() {
            try {
                const response = await fetch('/providers');
                providers = await response.json();
                console.log('Providers loaded:', Object.keys(providers));
            } catch (e) {
                console.error('Failed to load providers:', e);
            }
        }

        function renderProviders() {
            const container = document.getElementById('providers-container');
            container.innerHTML = '';
            
            Object.keys(providers).forEach(providerId => {
                const provider = providers[providerId];
                const div = document.createElement('div');
                div.className = 'provider-config';
                div.innerHTML = `
                    <h4>${provider.name}</h4>
                    <div class="form-group">
                        <label>API Key:</label>
                        <input type="text" class="provider-api-key" data-provider="${providerId}" placeholder="Enter your ${provider.name} API key">
                    </div>
                    <div class="form-group">
                        <label>Base URL (optional, default: ${provider.base_url}):</label>
                        <input type="text" class="provider-base-url" data-provider="${providerId}" placeholder="${provider.base_url}">
                    </div>
                    <button class="small" onclick="fetchModels('${providerId}')">Fetch Models</button>
                    <button class="danger small" onclick="this.parentElement.remove()">Remove</button>
                `;
                container.appendChild(div);
            });
        }

        function addProvider() {
            const providerIds = Object.keys(providers);
            if (providerIds.length === 0) {
                alert('Providers not loaded yet. Please wait...');
                return;
            }
            
            const container = document.getElementById('providers-container');
            const div = document.createElement('div');
            div.className = 'provider-config';
            
            const providerOptions = providerIds.map(id => 
                '<option value="' + id + '">' + providers[id].name + ' (' + id + ')</option>'
            ).join('');
            
            div.innerHTML = `
                <div class="form-group">
                    <label>Select Provider:</label>
                    <select class="provider-select" onchange="onProviderSelect(this)">
                        <option value="">-- Select a provider --</option>
                        ${providerOptions}
                        <option value="__custom__">+ Custom Provider</option>
                    </select>
                </div>
                <div class="provider-fields" style="display:none">
                    <div class="form-group">
                        <label>Provider ID:</label>
                        <input type="text" class="provider-id" readonly>
                    </div>
                    <div class="form-group">
                        <label>Provider Name:</label>
                        <input type="text" class="provider-name" readonly>
                    </div>
                    <div class="form-group">
                        <label>API Key:</label>
                        <input type="text" class="provider-api-key" placeholder="Enter your API key">
                    </div>
                    <div class="form-group">
                        <label>Base URL:</label>
                        <input type="text" class="provider-base-url" placeholder="https://api.example.com">
                    </div>
                    <div class="form-group">
                        <label>API Path:</label>
                        <input type="text" class="provider-api-path" placeholder="/v1">
                    </div>
                    <button class="small success" onclick="fetchModelsForProvider(this)">Fetch Models</button>
                    <button class="danger small" onclick="this.closest('.provider-config').remove()">Remove</button>
                </div>
            `;
            container.appendChild(div);
        }
        
        function onProviderSelect(select) {
            const config = select.closest('.provider-config');
            const fields = config.querySelector('.provider-fields');
            const providerIdInput = config.querySelector('.provider-id');
            const providerNameInput = config.querySelector('.provider-name');
            const baseUrlInput = config.querySelector('.provider-base-url');
            const apiPathInput = config.querySelector('.provider-api-path');
            
            if (select.value === '__custom__') {
                providerIdInput.value = '';
                providerIdInput.readOnly = false;
                providerNameInput.value = '';
                providerNameInput.readOnly = false;
                baseUrlInput.value = '';
                apiPathInput.value = '/v1';
                fields.style.display = 'block';
            } else if (select.value) {
                const provider = providers[select.value];
                providerIdInput.value = select.value;
                providerIdInput.readOnly = true;
                providerNameInput.value = provider.name;
                providerNameInput.readOnly = true;
                baseUrlInput.value = provider.base_url;
                apiPathInput.value = provider.api_path;
                fields.style.display = 'block';
            } else {
                fields.style.display = 'none';
            }
        }
        
        async function fetchModelsForProvider(btn) {
            const config = btn.closest('.provider-config');
            const providerId = config.querySelector('.provider-id').value;
            const apiKey = config.querySelector('.provider-api-key').value;
            const baseUrl = config.querySelector('.provider-base-url').value;
            
            if (!providerId) {
                alert('Please select or enter a provider ID');
                return;
            }
            if (!apiKey) {
                alert('Please enter API key');
                return;
            }
            
            const body = {
                api_key: apiKey,
                base_url: baseUrl
            };
            
            try {
                const response = await fetch('/providers/' + providerId, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-Admin-Key': getAccessKey()
                    },
                    body: JSON.stringify(body)
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    alert('Failed to fetch models: ' + (error.error || 'Unknown error'));
                    return;
                }
                
                const data = await response.json();
                displayModels(providerId, data);
            } catch (e) {
                alert('Error fetching models: ' + e.message);
            }
        }

        function displayModels(providerId, data) {
            const container = document.getElementById('available-models');
            const models = data.data || data.models || [data];
            const providerName = providers[providerId] ? providers[providerId].name : providerId;
            
            models.forEach(model => {
                const modelId = model.id || model;
                const div = document.createElement('div');
                div.className = 'model-item';
                div.innerHTML = '<div><strong>' + modelId + '</strong></div>' +
                    '<div style="font-size: 12px; color: #666;">' + providerName + '</div>';
                div.onclick = () => selectModel(providerId, modelId, providerName);
                container.appendChild(div);
            });
        }

        function selectModel(providerId, modelId, providerName) {
            const defaultName = providerId + '_' + modelId.replace(/[^a-zA-Z0-9]/g, '_');
            const customName = prompt('Enter custom name for ' + modelId + ':', defaultName);
            
            if (customName) {
                const retryConfig = {
                    retry_on_429: true,
                    retry_delay: 1,
                    max_retries: 999999
                };
                
                const retryInput = prompt('Retry config for ' + modelId + '\\nFormat: delay_seconds,max_retries\\nExample: 1,999999\\nPress Cancel for defaults (1s, 999999 retries)');
                if (retryInput) {
                    const parts = retryInput.split(',');
                    if (parts.length >= 2) {
                        retryConfig.retry_delay = parseInt(parts[0]) || 1;
                        retryConfig.max_retries = parseInt(parts[1]) || 999999;
                    }
                }
                
                selectedModels[customName] = {
                    provider: providerId,
                    real_model: modelId,
                    provider_name: providerName,
                    retry_on_429: retryConfig.retry_on_429,
                    retry_delay: retryConfig.retry_delay,
                    max_retries: retryConfig.max_retries
                };
                renderSelectedModels();
            }
        }

        function renderSelectedModels() {
            const container = document.getElementById('selected-models');
            container.innerHTML = '';
            
            Object.entries(selectedModels).forEach(([customName, mapping]) => {
                const providerName = mapping.provider_name || (providers[mapping.provider] ? providers[mapping.provider].name : mapping.provider);
                const retryInfo = mapping.retry_delay + 's, ' + mapping.max_retries + ' retries';
                const div = document.createElement('div');
                div.className = 'selected-model-item';
                div.innerHTML = '<div>' +
                    '<strong>' + customName + '</strong><br>' +
                    '<small>' + mapping.real_model + ' @ ' + providerName + '</small><br>' +
                    '<small style="color: #667eea;">Retry: ' + retryInfo + '</small>' +
                    '</div>' +
                    '<button class="danger small" onclick="removeModel(\\'' + customName + '\\')">Remove</button>';
                container.appendChild(div);
            });
        }

        function removeModel(customName) {
            delete selectedModels[customName];
            renderSelectedModels();
        }

        function filterModels() {
            const search = document.getElementById('model_search').value.toLowerCase();
            document.querySelectorAll('.model-item').forEach(item => {
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(search) ? '' : 'none';
            });
        }

        function getAccessKey() {
            return document.getElementById('create_admin_key').value;
        }

        async function createKey() {
            const adminKey = document.getElementById('create_admin_key').value;
            
            const providerConfigs = {};
            document.querySelectorAll('.provider-config').forEach(config => {
                const fields = config.querySelector('.provider-fields');
                if (fields && fields.style.display !== 'none') {
                    const providerId = config.querySelector('.provider-id').value;
                    const apiKey = config.querySelector('.provider-api-key').value;
                    const baseUrl = config.querySelector('.provider-base-url').value;
                    const apiPath = config.querySelector('.provider-api-path').value;
                    
                    if (providerId && apiKey) {
                        providerConfigs[providerId] = {
                            api_key: apiKey,
                            base_url: baseUrl,
                            api_path: apiPath || '/v1'
                        };
                    }
                }
            });
            
            const modelMappings = {};
            Object.entries(selectedModels).forEach(([customName, mapping]) => {
                modelMappings[customName] = {
                    provider: mapping.provider,
                    real_model: mapping.real_model,
                    retry_on_429: mapping.retry_on_429,
                    retry_delay: mapping.retry_delay,
                    max_retries: mapping.max_retries
                };
            });
            
            const keyConfig = {
                name: document.getElementById('key_name').value,
                providers: providerConfigs,
                model_mappings: modelMappings
            };
            
            try {
                const response = await fetch('/keys', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Admin-Key': adminKey
                    },
                    body: JSON.stringify(keyConfig)
                });
                const result = await response.json();
                
                const status = document.getElementById('create-status');
                if (result.error) {
                    status.className = 'status error';
                    status.innerHTML = '✗ ' + result.error;
                } else {
                    status.className = 'status success';
                    status.innerHTML = `✓ Key created!<br>Access Key: <code>${result.access_key}</code><br>Models: ${Object.keys(selectedModels).join(', ')}`;
                }
            } catch (e) {
                alert('Failed to create key: ' + e.message);
            }
        }

        function showTab(tab, btn) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.card').forEach(c => c.style.display = 'none');
            document.getElementById(tab + '-tab').style.display = 'block';
            if (btn) btn.classList.add('active');
        }

        async function loadKeys() {
            const adminKey = document.getElementById('admin_key').value;
            try {
                const response = await fetch('/keys', {
                    headers: { 'X-Admin-Key': adminKey }
                });
                const keys = await response.json();
                
                if (keys.error) {
                    alert(keys.error);
                    return;
                }
                
                const listHtml = Object.values(keys).map(key => `
                    <div class="provider-config">
                        <div style="display: flex; justify-content: space-between;">
                            <h3>${key.name}</h3>
                            <div>
                                <button class="success small" onclick="editKey('${key.id}', '${adminKey}')">Edit</button>
                                <button class="danger small" onclick="deleteKey('${key.id}', '${adminKey}')">Delete</button>
                            </div>
                        </div>
                        <p><strong>Access Key:</strong> <code>${key.access_key}</code></p>
                        <p><strong>Usage:</strong> ${key.usage_count} requests</p>
                        <p><strong>Models:</strong></p>
                        <ul>
                            ${Object.entries(key.model_mappings || {}).map(([name, mapping]) => 
                                `<li><strong>${name}</strong> → ${mapping.real_model} @ ${mapping.provider}</li>`
                            ).join('')}
                        </ul>
                    </div>
                `).join('');
                
                document.getElementById('key-list').innerHTML = listHtml || '<p>No keys found</p>';
            } catch (e) {
                alert('Failed to load keys: ' + e.message);
            }
        }

        async function deleteKey(keyId, adminKey) {
            if (!confirm('Are you sure you want to delete this key?')) return;
            
            try {
                const response = await fetch('/keys/' + keyId, {
                    method: 'DELETE',
                    headers: { 'X-Admin-Key': adminKey }
                });
                const result = await response.json();
                
                if (result.status === 'deleted') {
                    loadKeys();
                } else {
                    alert(result.error || 'Failed to delete key');
                }
            } catch (e) {
                alert('Failed to delete key: ' + e.message);
            }
        }

        async function editKey(keyId, adminKey) {
            try {
                const response = await fetch('/keys/' + keyId, {
                    headers: { 'X-Admin-Key': adminKey }
                });
                const keyData = await response.json();
                
                if (keyData.error) {
                    alert(keyData.error);
                    return;
                }
                
                const newModels = prompt(
                    '添加新模型（格式：自定义名称,提供商,真实模型名称）\\n' +
                    '例如：my_glm4,zhipu_coding,glm-4\\n' +
                    '多个模型用分号分隔',
                    ''
                );
                
                if (!newModels) return;
                
                const models = newModels.split(';').map(m => m.trim()).filter(m => m);
                const updates = { model_mappings: keyData.model_mappings || {} };
                
                models.forEach(modelStr => {
                    const parts = modelStr.split(',');
                    if (parts.length === 3) {
                        const [customName, provider, realModel] = parts;
                        updates.model_mappings[customName.trim()] = {
                            provider: provider.trim(),
                            real_model: realModel.trim(),
                            retry_on_429: true,
                            retry_delay: 1,
                            max_retries: 999999
                        };
                    }
                });
                
                const updateResponse = await fetch('/keys/' + keyId, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Admin-Key': adminKey
                    },
                    body: JSON.stringify(updates)
                });
                const result = await updateResponse.json();
                
                if (result.error) {
                    alert('Failed to update key: ' + result.error);
                } else {
                    alert('Key updated successfully!');
                    loadKeys();
                }
            } catch (e) {
                alert('Failed to edit key: ' + e.message);
            }
        }

        async function saveSettings() {
            const settings = {
                proxy_port: parseInt(document.getElementById('proxy_port').value),
                use_https: document.getElementById('use_https').checked,
                admin_key: document.getElementById('settings_admin_key').value
            };
            
            try {
                const response = await fetch('/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settings)
                });
                const result = await response.json();
                
                const status = document.getElementById('settings-status');
                if (result.status === 'success') {
                    status.className = 'status success';
                    status.innerHTML = '✓ Settings saved!';
                } else {
                    status.className = 'status error';
                    status.innerHTML = '✗ ' + (result.error || 'Failed to save settings');
                }
            } catch (e) {
                alert('Failed to save settings: ' + e.message);
            }
        }

        async function loadSettings() {
            try {
                const response = await fetch('/config');
                const config = await response.json();
                document.getElementById('proxy_port').value = config.proxy_port || 8443;
                document.getElementById('use_https').checked = config.use_https !== false;
                document.getElementById('settings_admin_key').value = config.admin_key || '';
            } catch (e) {
                console.error('Failed to load settings:', e);
            }
        }

        loadProviders();
        loadSettings();
    </script>
</body>
</html>"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

def run_server():
    port = config['proxy_port']
    use_https = config.get('use_https', True)
    
    with socketserver.ThreadingTCPServer(("", port), ProxyHandler) as httpd:
        if use_https:
            cert_file = 'cert.pem'
            key_file = 'key.pem'
            
            if not os.path.exists(cert_file) or not os.path.exists(key_file):
                print("❌ SSL certificates not found!")
                print("Please generate them with:")
                print("  openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes")
                return
            
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert_file, key_file)
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
            
            print(f"🚀 API Aggregation Platform running on https://localhost:{port}")
            print(f"⚙️  Management UI: https://localhost:{port}/")
        else:
            print(f"🚀 API Aggregation Platform running on http://localhost:{port}")
            print(f"⚙️  Management UI: http://localhost:{port}/")
        
        print(f"🔑 Total keys: {len(api_keys)}")
        print(f"📋 Pre-configured providers: {len(PROVIDERS)}")
        print(f"🔄 Auto-retry on 429 errors enabled")
        print("\nPress Ctrl+C to stop the server\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down proxy server...")

if __name__ == "__main__":
    run_server()
