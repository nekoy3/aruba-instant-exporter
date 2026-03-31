"""SSH-based metric collector for Aruba Instant AP.

Collects CPU, memory, and interface metrics via SSH interactive shell.
Aruba Instant APs don't support SSH exec_command; invoke_shell is required.

SSHベースの Aruba Instant AP メトリクスコレクター。

SSH インタラクティブシェル経由で CPU・メモリ・インターフェース統計を収集する。
Aruba Instant AP は SSH exec_command に対応していないため invoke_shell を使用する。
"""

import re
import time
import logging

import paramiko

from . import metrics as m

logger = logging.getLogger(__name__)

# Regex patterns for parsing SSH output
# SSH出力のパース用正規表現パターン
CPU_LINE_RE = re.compile(
    r"(total|cpu\d+):\s+"
    r"user\s+(\d+)%\s+nice\s+(\d+)%\s+system\s+(\d+)%\s+"
    r"idle\s+(\d+)%\s+io\s+(\d+)%\s+irq\s+(\d+)%\s+softirq\s+(\d+)%"
)
MEM_LINE_RE = re.compile(r"^(\w[\w()]+):\s+(\d+)\s+kB", re.MULTILINE)
IFACE_HEADER_RE = re.compile(r"^(\S+)\s+is\s+(up|down)", re.MULTILINE)
IFACE_SPEED_RE = re.compile(r"Speed\s+(\d+)Mb/s")
IFACE_COUNTER_RE = re.compile(r"^([\w\s]+?)\s{2,}(\d+)\s*$", re.MULTILINE)


class SSHCollector:
    """Collects metrics from Aruba Instant AP via SSH.

    SSH 経由で Aruba Instant AP のメトリクスを収集するクラス。"""

    def __init__(self, config):
        self.config = config
        self._client = None
        self._shell = None

    def _connect(self):
        """Establish SSH connection and interactive shell.

        SSH 接続とインタラクティブシェルを確立する。"""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass

        logger.debug("Connecting to %s via SSH", self.config.aruba_host)
        client = paramiko.SSHClient()
        if self.config.ssh_strict_host_key:
            # Use known_hosts for host key verification (secure default)
            # セキュアなデフォルト設定：known_hosts でホスト鍵を検証
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
        else:
            # Automatically accept any host key (insecure, for lab use)
            # 任意のホスト鍵を自動的に受け入れる（セキュリティ上のリスクあり、ラボ用途向け）
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            self.config.aruba_host,
            username=self.config.ssh_username,
            password=self.config.ssh_password,
            look_for_keys=False,
            allow_agent=False,
            timeout=self.config.ssh_timeout,
        )
        shell = client.invoke_shell(width=250, height=50)
        # Wait for initial prompt
        # 初期プロンプトを待機
        time.sleep(2)
        if shell.recv_ready():
            shell.recv(65535)

        self._client = client
        self._shell = shell
        logger.info("SSH connection established to %s", self.config.aruba_host)

    def _send_command(self, command, wait=2.0):
        """Send a command and return the output.

        コマンドを送信して出力を返す。"""
        if self._shell is None or self._shell.closed:
            self._connect()

        self._shell.send(command + "\n")
        time.sleep(wait)

        output = b""
        deadline = time.time() + 5
        while time.time() < deadline:
            if self._shell.recv_ready():
                chunk = self._shell.recv(65535)
                output += chunk
                if not chunk:
                    break
            else:
                time.sleep(0.2)
                if not self._shell.recv_ready():
                    break

        text = output.decode(errors="replace")
        # Strip the echoed command and trailing prompt
        # エコーバックされたコマンドと末尾プロンプトを除去
        lines = text.split("\n")
        if lines and command in lines[0]:
            lines = lines[1:]
        # Remove trailing prompt line
        # 末尾のプロンプト行を削除
        while lines and lines[-1].strip().endswith("#"):
            lines.pop()
        return "\n".join(lines)

    def collect(self):
        """Run all SSH collections and update Prometheus metrics.

        全 SSH 収集を実行し、Prometheus メトリクスを更新する。"""
        t0 = time.time()
        try:
            self._connect()
            self._collect_cpu()
            self._collect_memory()
            self._collect_interface()
            m.collector_success.labels(collector="ssh").set(1)
            logger.debug("SSH collection completed in %.2fs", time.time() - t0)
        except Exception:
            m.collector_success.labels(collector="ssh").set(0)
            logger.exception("SSH collection failed")
            self._close()
        finally:
            m.collector_duration_seconds.labels(collector="ssh").set(time.time() - t0)
            m.collector_last_scrape_timestamp.labels(collector="ssh").set(time.time())
            self._close()

    def _collect_cpu(self):
        """Parse 'show cpu' output and update metrics.

        'show cpu' の出力を解析してメトリクスを更新する。"""
        output = self._send_command("show cpu")
        modes = ["user", "nice", "system", "idle", "io", "irq", "softirq"]

        for match in CPU_LINE_RE.finditer(output):
            cpu_label = match.group(1)
            values = [int(match.group(i)) for i in range(2, 9)]
            for mode_name, value in zip(modes, values):
                m.cpu_usage_ratio.labels(cpu=cpu_label, mode=mode_name).set(
                    value / 100.0
                )
        logger.debug("CPU metrics updated")

    def _collect_memory(self):
        """Parse 'show memory' output and update metrics.

        'show memory' の出力を解析してメトリクスを更新する。"""
        output = self._send_command("show memory")
        mem_map = {
            "MemTotal": "total",
            "MemFree": "free",
            "MemAvailable": "available",
            "Buffers": "buffers",
            "Cached": "cached",
            "Active": "active",
            "Inactive": "inactive",
            "Slab": "slab",
            "SwapTotal": "swap_total",
            "SwapFree": "swap_free",
        }

        for match in MEM_LINE_RE.finditer(output):
            key = match.group(1)
            kb_value = int(match.group(2))
            if key in mem_map:
                m.memory_bytes.labels(type=mem_map[key]).set(kb_value * 1024)
        logger.debug("Memory metrics updated")

    def _collect_interface(self):
        """Parse 'show interface counters' output and update metrics.

        'show interface counters' の出力を解析してメトリクスを更新する。"""
        output = self._send_command("show interface counters")

        # Parse interface name and status
        # インターフェース名とリンクステータスをパース
        header_match = IFACE_HEADER_RE.search(output)
        if not header_match:
            logger.warning("Could not parse interface header")
            return

        iface = header_match.group(1)
        is_up = header_match.group(2) == "up"
        m.interface_up.labels(interface=iface).set(1 if is_up else 0)

        # Parse speed
        # リンク速度をパース
        speed_match = IFACE_SPEED_RE.search(output)
        if speed_match:
            m.interface_speed_mbps.labels(interface=iface).set(
                int(speed_match.group(1))
            )

        # Parse counters
        # カウンター値をパース
        counter_map = {
            "Received packets": ("rx_packets", m.interface_rx_packets_total),
            "Received bytes": ("rx_bytes", m.interface_rx_bytes_total),
            "Transmitted packets": ("tx_packets", m.interface_tx_packets_total),
            "Transmitted bytes": ("tx_bytes", m.interface_tx_bytes_total),
            "Receive errors": ("rx_errors", m.interface_rx_errors_total),
            "Transmission errors": ("tx_errors", m.interface_tx_errors_total),
            "Receive dropped": ("rx_dropped", m.interface_rx_dropped_total),
            "Transmitted dropped": ("tx_dropped", m.interface_tx_dropped_total),
        }

        for match in IFACE_COUNTER_RE.finditer(output):
            name = match.group(1).strip()
            value = int(match.group(2))
            if name in counter_map:
                _, gauge = counter_map[name]
                gauge.labels(interface=iface).set(value)

        logger.debug("Interface metrics updated for %s", iface)

    def _close(self):
        """Close SSH connection.

        SSH 接続を切断する。"""
        try:
            if self._shell:
                self._shell.close()
        except Exception:
            pass
        try:
            if self._client:
                self._client.close()
        except Exception:
            pass
        self._client = None
        self._shell = None
