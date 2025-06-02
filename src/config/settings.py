import os
import json
from pathlib import Path
from cryptography.fernet import Fernet
import logging

class Settings:
    """アプリケーション設定管理クラス"""
    
    def __init__(self):
        self.app_name = "NotiFetch"
        self.version = "1.0.0"
        self.config_dir = Path.home() / ".notifetch"
        self.config_file = self.config_dir / "config.json"
        self.key_file = self.config_dir / "key.key"
        
        # ディレクトリを作成
        self.config_dir.mkdir(exist_ok=True)
        
        # 暗号化キーの初期化
        self._init_encryption_key()
        
        # 設定の読み込み
        self.config = self._load_config()
        
        # ログ設定
        self._setup_logging()
    
    def _init_encryption_key(self):
        """暗号化キーの初期化"""
        if not self.key_file.exists():
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as key_file:
                key_file.write(key)
        
        with open(self.key_file, 'rb') as key_file:
            self.key = key_file.read()
        
        self.cipher_suite = Fernet(self.key)
    
    def _load_config(self):
        """設定ファイルの読み込み"""
        default_config = {
            "notion": {
                "token": "",
                "last_page_id": ""
            },
            "gemini": {
                "api_key": ""
            },
            "ui": {
                "theme": "light",
                "language": "ja",
                "csv_encoding": "utf-8"
            },
            "data": {
                "cache_enabled": True,
                "max_cache_size": 100
            }
        }
        
        if not self.config_file.exists():
            self._save_config(default_config)
            return default_config
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self._save_config(default_config)
            return default_config
    
    def _save_config(self, config):
        """設定ファイルの保存"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def _setup_logging(self):
        """ログ設定"""
        log_dir = self.config_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / "notifetch.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def get_notion_token(self):
        """Notionトークンの取得（復号化）"""
        encrypted_token = self.config.get("notion", {}).get("token", "")
        if encrypted_token:
            try:
                return self.cipher_suite.decrypt(encrypted_token.encode()).decode()
            except:
                return ""
        return ""
    
    def set_notion_token(self, token):
        """Notionトークンの設定（暗号化）"""
        if token:
            encrypted_token = self.cipher_suite.encrypt(token.encode()).decode()
            self.config["notion"]["token"] = encrypted_token
        else:
            self.config["notion"]["token"] = ""
        self._save_config(self.config)
    
    def get_gemini_api_key(self):
        """Gemini APIキーの取得（復号化）"""
        encrypted_key = self.config.get("gemini", {}).get("api_key", "")
        if encrypted_key:
            try:
                return self.cipher_suite.decrypt(encrypted_key.encode()).decode()
            except:
                return ""
        return ""
    
    def set_gemini_api_key(self, api_key):
        """Gemini APIキーの設定（暗号化）"""
        if api_key:
            encrypted_key = self.cipher_suite.encrypt(api_key.encode()).decode()
            self.config["gemini"]["api_key"] = encrypted_key
        else:
            self.config["gemini"]["api_key"] = ""
        self._save_config(self.config)
    
    def get_last_page_id(self):
        """最後に使用したページIDの取得"""
        return self.config.get("notion", {}).get("last_page_id", "")
    
    def set_last_page_id(self, page_id):
        """最後に使用したページIDの設定"""
        self.config["notion"]["last_page_id"] = page_id
        self._save_config(self.config)
    
    def get_ui_setting(self, key, default=None):
        """UI設定の取得"""
        return self.config.get("ui", {}).get(key, default)
    
    def set_ui_setting(self, key, value):
        """UI設定の設定"""
        if "ui" not in self.config:
            self.config["ui"] = {}
        self.config["ui"][key] = value
        self._save_config(self.config) 