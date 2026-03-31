#!/usr/bin/env python3
"""Aruba Instant Exporter - Prometheus exporter for Aruba Instant APs.

Collects CPU, memory, interface, client, radio, and channel metrics
via SSH and HTTPS CGI from Aruba Instant (IAP) access points.

Aruba Instant Exporter - Aruba Instant AP 向け Prometheus エクスポーター。

SSH と HTTPS CGI 経由で CPU・メモリ・インターフェース・クライアント・
Radio・チャネルメトリクスを収集し /metrics エンドポイントで公開する。
"""

import sys
import time
import signal
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .config import Config
from .ssh_collector import SSHCollector
from .cgi_collector import CGICollector

logger = logging.getLogger("aruba_instant_exporter")

_shutdown = threading.Event()


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler serving Prometheus metrics.

    Prometheus メトリクスを配信する HTTP ハンドラー。"""

    def do_GET(self):
        if self.path == "/metrics":
            output = generate_latest()
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.send_header("Content-Length", str(len(output)))
            self.end_headers()
            self.wfile.write(output)
        elif self.path == "/health" or self.path == "/healthz":
            body = b'{"status": "ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/":
            body = b"""<html>
<head><title>Aruba Instant Exporter</title></head>
<body>
<h1>Aruba Instant Exporter</h1>
<p><a href="/metrics">Metrics</a></p>
<p><a href="/health">Health</a></p>
</body></html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        if "/health" not in str(args):
            logger.debug("HTTP %s", format % args)


def collection_loop(config):
    """Background loop that periodically collects metrics.

    定期的にメトリクスを収集するバックグラウンドループ。"""
    ssh_collector = SSHCollector(config) if config.enable_ssh else None
    cgi_collector = CGICollector(config) if config.enable_cgi else None

    while not _shutdown.is_set():
        logger.info("Starting metric collection cycle")
        t0 = time.time()

        if ssh_collector:
            try:
                ssh_collector.collect()
            except Exception:
                logger.exception("SSH collection error (unhandled)")

        if cgi_collector:
            try:
                cgi_collector.collect()
            except Exception:
                logger.exception("CGI collection error (unhandled)")

        elapsed = time.time() - t0
        logger.info("Collection cycle completed in %.2fs", elapsed)

        remaining = max(0, config.collect_interval - elapsed)
        _shutdown.wait(timeout=remaining)


def main():
    config = Config()

    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    logger.info("Aruba Instant Exporter starting")
    logger.info("Config: %s", config)

    try:
        config.validate()
    except ValueError as e:
        logger.critical("Configuration validation failed: %s", e)
        sys.exit(1)

    # Graceful shutdown
    # グレースフルシャットダウン処理
    def handle_signal(signum, frame):
        logger.info("Received signal %d, shutting down", signum)
        _shutdown.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Start background collection thread
    # バックグラウンド収集スレッドを開始
    collector_thread = threading.Thread(
        target=collection_loop, args=(config,), daemon=True, name="collector"
    )
    collector_thread.start()
    logger.info("Background collector started (interval=%ds)", config.collect_interval)

    # Start HTTP server
    # HTTPサーバーを開始
    server = HTTPServer(("0.0.0.0", config.exporter_port), MetricsHandler)
    server.timeout = 1
    logger.info("Serving metrics on http://0.0.0.0:%d/metrics", config.exporter_port)

    while not _shutdown.is_set():
        server.handle_request()

    logger.info("Exporter stopped")


if __name__ == "__main__":
    main()
