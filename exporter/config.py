"""Configuration management for Aruba Instant Exporter.

Aruba Instant Exporter の設定管理モジュール。"""

import os
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration loaded from environment variables.

    環境変数から読み込む設定クラス。"""

    def __init__(self):
        self.aruba_host = os.environ.get("ARUBA_HOST", "")
        self.ssh_username = os.environ.get("ARUBA_SSH_USERNAME", "admin")
        self.ssh_password = os.environ.get("ARUBA_SSH_PASSWORD", "")
        self.web_username = os.environ.get("ARUBA_WEB_USERNAME", "")
        self.web_password = os.environ.get("ARUBA_WEB_PASSWORD", "")
        self.web_port = int(os.environ.get("ARUBA_WEB_PORT", "4343"))

        # Fall back to SSH credentials for web if not set
        # Web認証情報が未設定の場合はSSH認証情報をフォールバックとして使用
        if not self.web_username:
            self.web_username = self.ssh_username
        if not self.web_password:
            self.web_password = self.ssh_password

        self.exporter_port = int(os.environ.get("EXPORTER_PORT", "9877"))
        self.collect_interval = int(os.environ.get("COLLECT_INTERVAL", "30"))
        self.ssh_timeout = int(os.environ.get("SSH_TIMEOUT", "15"))
        self.cgi_timeout = int(os.environ.get("CGI_TIMEOUT", "15"))
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")

        self.enable_ssh = os.environ.get("ENABLE_SSH", "true").lower() == "true"
        self.enable_cgi = os.environ.get("ENABLE_CGI", "true").lower() == "true"

        # Security: SSL verification for CGI (default: disabled for self-signed AP certs)
        # セキュリティ: CGI の SSL 証明書検証（デフォルト: AP の自己署名証明書のため無効）
        self.ssl_verify = os.environ.get("SSL_VERIFY", "false").lower() == "true"

        # Security: SSH host key verification (default: disabled for lab convenience)
        # セキュリティ: SSH ホスト鍵検証（デフォルト: ラボ環境の利便性のため無効）
        self.ssh_strict_host_key = os.environ.get("SSH_STRICT_HOST_KEY", "false").lower() == "true"

    def validate(self):
        """Validate required configuration.

        必須設定項目を検証する。"""
        errors = []
        if not self.aruba_host:
            errors.append("ARUBA_HOST is required")
        if self.enable_ssh and not self.ssh_password:
            errors.append("ARUBA_SSH_PASSWORD is required when SSH is enabled")
        if self.enable_cgi and not self.web_password:
            errors.append("ARUBA_WEB_PASSWORD is required when CGI is enabled")
        if errors:
            for e in errors:
                logger.error("Configuration error: %s", e)
            raise ValueError(f'Configuration errors: {"; ".join(errors)}')
        return True

    def __repr__(self):
        return (
            f"Config(host={self.aruba_host}, ssh={self.enable_ssh}, "
            f"cgi={self.enable_cgi}, interval={self.collect_interval}s)"
        )
