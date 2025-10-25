from typing import Dict, Any, Optional, List
import json
import os
import time
from datetime import datetime
from base64 import b64encode
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import redis

class ConfigManager:
    """Secure configuration manager using Redis with encryption"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = redis.from_url(self.redis_url)
        
        # Initialize encryption
        self.encryption_key = self._get_or_create_key()
        self.fernet = Fernet(self.encryption_key)
        
    def _get_or_create_key(self) -> bytes:
        """Get existing encryption key or create a new one"""
        key = self.redis.get("encryption_key")
        if not key:
            # Generate a new key
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=480000,
            )
            key = b64encode(kdf.derive(os.urandom(32)))
            # Store the key in Redis
            self.redis.set("encryption_key", key)
        return key

    def _encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.fernet.encrypt(data.encode()).decode()

    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()

    def save_mcp_config(self, server_id: str, config: Dict[str, Any]) -> bool:
        """Save MCP server configuration with encrypted sensitive data"""
        try:
            # Encrypt sensitive fields
            if "headers" in config:
                encrypted_headers = {
                    k: self._encrypt(v) if k.lower().contains(("key", "token", "secret", "password", "auth"))
                    else v
                    for k, v in config["headers"].items()
                }
                config["headers"] = encrypted_headers

            # Store configuration
            self.redis.hset("mcp_servers", server_id, json.dumps(config))
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save MCP config: {e}")
            return False

    def get_mcp_config(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve MCP server configuration and decrypt sensitive data"""
        try:
            config_data = self.redis.hget("mcp_servers", server_id)
            if not config_data:
                return None
                
            config = json.loads(config_data)
            
            # Decrypt sensitive fields
            if "headers" in config:
                decrypted_headers = {
                    k: self._decrypt(v) if k.lower().contains(("key", "token", "secret", "password", "auth"))
                    else v
                    for k, v in config["headers"].items()
                }
                config["headers"] = decrypted_headers
                
            return config
        except Exception as e:
            print(f"[ERROR] Failed to get MCP config: {e}")
            return None

    def list_mcp_servers(self) -> Dict[str, Dict[str, Any]]:
        """List all MCP server configurations"""
        try:
            servers = {}
            for server_id, config_data in self.redis.hgetall("mcp_servers").items():
                server_id = server_id.decode()
                config = self.get_mcp_config(server_id)
                if config:
                    servers[server_id] = config
            return servers
        except Exception as e:
            print(f"[ERROR] Failed to list MCP servers: {e}")
            return {}

    def delete_mcp_config(self, server_id: str) -> bool:
        """Delete MCP server configuration"""
        try:
            self.redis.hdel("mcp_servers", server_id)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete MCP config: {e}")
            return False

    def save_llm_config(self, config: Dict[str, Any]) -> bool:
        """Save LLM configuration with encrypted API keys"""
        try:
            # Encrypt sensitive data
            if "apiKey" in config:
                config["apiKey"] = self._encrypt(config["apiKey"])
            
            self.redis.set("llm_config", json.dumps(config))
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save LLM config: {e}")
            return False

    def get_llm_config(self) -> Optional[Dict[str, Any]]:
        """Retrieve LLM configuration and decrypt API keys"""
        try:
            config_data = self.redis.get("llm_config")
            if not config_data:
                return None
                
            config = json.loads(config_data)
            
            # Decrypt API key
            if "apiKey" in config:
                config["apiKey"] = self._decrypt(config["apiKey"])
                
            return config
        except Exception as e:
            print(f"[ERROR] Failed to get LLM config: {e}")
            return None

    def backup_configs(self) -> str:
        """Create a backup of all configurations"""
        try:
            backup = {
                "mcp_servers": self.list_mcp_servers(),
                "llm_config": self.get_llm_config(),
                "timestamp": datetime.now().isoformat()
            }
            backup_id = f"backup_{int(time.time())}"
            self.redis.set(f"config_backup_{backup_id}", json.dumps(backup))
            return backup_id
        except Exception as e:
            print(f"[ERROR] Failed to create backup: {e}")
            return None

    def restore_backup(self, backup_id: str) -> bool:
        """Restore configurations from a backup"""
        try:
            backup_data = self.redis.get(f"config_backup_{backup_id}")
            if not backup_data:
                return False
                
            backup = json.loads(backup_data)
            
            # Restore MCP configurations
            for server_id, config in backup["mcp_servers"].items():
                self.save_mcp_config(server_id, config)
                
            # Restore LLM configuration
            if backup["llm_config"]:
                self.save_llm_config(backup["llm_config"])
                
            return True
        except Exception as e:
            print(f"[ERROR] Failed to restore backup: {e}")
            return False

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all configuration backups"""
        try:
            backups = []
            for key in self.redis.keys("config_backup_*"):
                backup_data = self.redis.get(key)
                if backup_data:
                    backup = json.loads(backup_data)
                    backups.append({
                        "id": key.decode().replace("config_backup_", ""),
                        "timestamp": backup["timestamp"],
                        "num_servers": len(backup["mcp_servers"]),
                        "has_llm_config": bool(backup["llm_config"])
                    })
            return sorted(backups, key=lambda x: x["timestamp"], reverse=True)
        except Exception as e:
            print(f"[ERROR] Failed to list backups: {e}")
            return []