"""Prometheus metric definitions for Aruba Instant Exporter."""

from prometheus_client import Gauge, Info

PREFIX = "aruba_instant"

# ── AP Info ──────────────────────────────────────────────────────────
# ── AP情報 ───────────────────────────────────────────────────────────
ap_info = Info(
    f"{PREFIX}_ap",
    "Aruba Instant AP information",
)
uptime_seconds = Gauge(
    f"{PREFIX}_uptime_seconds",
    "AP uptime in seconds",
)

# ── CPU ──────────────────────────────────────────────────────────────
# ── CPU ─────────────────────────────────────────────────────────────
cpu_usage_ratio = Gauge(
    f"{PREFIX}_cpu_usage_ratio",
    "CPU usage ratio (0.0-1.0)",
    ["cpu", "mode"],
)

# ── Memory ───────────────────────────────────────────────────────────
# ── メモリ ───────────────────────────────────────────────────────────
memory_bytes = Gauge(
    f"{PREFIX}_memory_bytes",
    "Memory in bytes",
    ["type"],
)

# ── Wired Interface ──────────────────────────────────────────────────
# ── 有線インターフェース ────────────────────────────────────────────────
interface_up = Gauge(
    f"{PREFIX}_interface_up",
    "Interface link status (1=up, 0=down)",
    ["interface"],
)
interface_speed_mbps = Gauge(
    f"{PREFIX}_interface_speed_mbps",
    "Interface speed in Mbps",
    ["interface"],
)
interface_rx_packets_total = Gauge(
    f"{PREFIX}_interface_rx_packets_total",
    "Total received packets",
    ["interface"],
)
interface_rx_bytes_total = Gauge(
    f"{PREFIX}_interface_rx_bytes_total",
    "Total received bytes",
    ["interface"],
)
interface_tx_packets_total = Gauge(
    f"{PREFIX}_interface_tx_packets_total",
    "Total transmitted packets",
    ["interface"],
)
interface_tx_bytes_total = Gauge(
    f"{PREFIX}_interface_tx_bytes_total",
    "Total transmitted bytes",
    ["interface"],
)
interface_rx_errors_total = Gauge(
    f"{PREFIX}_interface_rx_errors_total",
    "Total receive errors",
    ["interface"],
)
interface_tx_errors_total = Gauge(
    f"{PREFIX}_interface_tx_errors_total",
    "Total transmit errors",
    ["interface"],
)
interface_rx_dropped_total = Gauge(
    f"{PREFIX}_interface_rx_dropped_total",
    "Total receive dropped",
    ["interface"],
)
interface_tx_dropped_total = Gauge(
    f"{PREFIX}_interface_tx_dropped_total",
    "Total transmit dropped",
    ["interface"],
)

# ── WiFi Clients ─────────────────────────────────────────────────────
# ── Wi-Fiクライアント ───────────────────────────────────────────────
clients_total = Gauge(
    f"{PREFIX}_clients_total",
    "Total number of connected WiFi clients",
)
client_signal_dbm = Gauge(
    f"{PREFIX}_client_signal_dbm",
    "Client signal strength in dBm (negative)",
    ["name", "mac", "ip", "essid", "channel", "type"],
)
client_speed_mbps = Gauge(
    f"{PREFIX}_client_speed_mbps",
    "Client connection speed in Mbps",
    ["name", "mac", "ip", "essid", "channel", "type"],
)

# ── Radio (per-interface: wifi0, wifi1) ──────────────────────────────
# ── Radio（wifi0・wifi1 インターフェース別）──────────────────────────
radio_channel = Gauge(
    f"{PREFIX}_radio_channel",
    "Current radio channel",
    ["radio", "phy_type"],
)
radio_packets_read_total = Gauge(
    f"{PREFIX}_radio_packets_read_total",
    "Total packets read by radio",
    ["radio"],
)
radio_bytes_read_total = Gauge(
    f"{PREFIX}_radio_bytes_read_total",
    "Total bytes read by radio",
    ["radio"],
)
radio_buffer_overflows_total = Gauge(
    f"{PREFIX}_radio_buffer_overflows_total",
    "Total radio buffer overflows",
    ["radio"],
)
radio_max_pps = Gauge(
    f"{PREFIX}_radio_max_pps",
    "Maximum packets per second observed",
    ["radio"],
)
radio_cur_pps = Gauge(
    f"{PREFIX}_radio_cur_pps",
    "Current packets per second",
    ["radio"],
)

# Radio DATA counters
# Radio DATAフレームカウンター
radio_data_packets_total = Gauge(
    f"{PREFIX}_radio_data_packets_total",
    "Total data packets",
    ["radio"],
)
radio_data_bytes_total = Gauge(
    f"{PREFIX}_radio_data_bytes_total",
    "Total data bytes",
    ["radio"],
)
radio_data_cur_pps = Gauge(
    f"{PREFIX}_radio_data_cur_pps",
    "Current data packets per second",
    ["radio"],
)
radio_data_cur_bps = Gauge(
    f"{PREFIX}_radio_data_cur_bps",
    "Current data bytes per second",
    ["radio"],
)

# Radio MGMT counters
# Radio MANAGEMENTフレームカウンター
radio_mgmt_packets_total = Gauge(
    f"{PREFIX}_radio_mgmt_packets_total",
    "Total management packets",
    ["radio"],
)
radio_mgmt_bytes_total = Gauge(
    f"{PREFIX}_radio_mgmt_bytes_total",
    "Total management bytes",
    ["radio"],
)

# Radio CTRL counters
# Radio CONTROLフレームカウンター
radio_ctrl_packets_total = Gauge(
    f"{PREFIX}_radio_ctrl_packets_total",
    "Total control packets",
    ["radio"],
)
radio_ctrl_bytes_total = Gauge(
    f"{PREFIX}_radio_ctrl_bytes_total",
    "Total control bytes",
    ["radio"],
)

# Radio stats (from show ap debug radio-stats)
# Radioステータス（show ap debug radio-stats から取得）
radio_noise_floor_dbm = Gauge(
    f"{PREFIX}_radio_noise_floor_dbm",
    "Current noise floor in dBm (negative value)",
    ["radio"],
)
radio_eirp_dbm = Gauge(
    f"{PREFIX}_radio_eirp_dbm",
    "Current EIRP in dBm",
    ["radio"],
)
radio_max_eirp_dbm = Gauge(
    f"{PREFIX}_radio_max_eirp_dbm",
    "Maximum EIRP in dBm",
    ["radio"],
)
radio_resets_total = Gauge(
    f"{PREFIX}_radio_resets_total",
    "Total radio resets",
    ["radio"],
)
radio_channel_changes_total = Gauge(
    f"{PREFIX}_radio_channel_changes_total",
    "Total channel changes",
    ["radio"],
)
radio_tx_power_changes_total = Gauge(
    f"{PREFIX}_radio_tx_power_changes_total",
    "Total TX power changes",
    ["radio"],
)
radio_tx_frames_total = Gauge(
    f"{PREFIX}_radio_tx_frames_transmitted_total",
    "Total TX frames transmitted",
    ["radio"],
)
radio_tx_retries_total = Gauge(
    f"{PREFIX}_radio_tx_retries_total",
    "Total TX retries",
    ["radio"],
)
radio_rx_crc_errors_total = Gauge(
    f"{PREFIX}_radio_rx_crc_errors_total",
    "Total RX CRC errors",
    ["radio"],
)

# ── Channel Quality (from ARM RF summary) ────────────────────────────
# ── チャネル品質（ARM RFサマリーから取得）──────────────────────────
channel_quality = Gauge(
    f"{PREFIX}_channel_quality",
    "Channel quality score (0-100)",
    ["radio", "channel"],
)
channel_noise_dbm = Gauge(
    f"{PREFIX}_channel_noise_dbm",
    "Channel noise level in dBm (negative value)",
    ["radio", "channel"],
)
channel_utilization_percent = Gauge(
    f"{PREFIX}_channel_utilization_percent",
    "Channel utilization percentage",
    ["radio", "channel"],
)

# ── Wired stats (from monitor status) ────────────────────────────────
# ── 有線統計（monitor status から取得）──────────────────────────────
wired_packets_total = Gauge(
    f"{PREFIX}_wired_packets_total",
    "Total wired interface packets",
    ["interface"],
)

# ── Collector health ─────────────────────────────────────────────────
# ── コレクターヘルス（収集状態メトリクス）─────────────────────────
collector_success = Gauge(
    f"{PREFIX}_collector_success",
    "Whether the last collection succeeded (1=success, 0=failure)",
    ["collector"],
)
collector_duration_seconds = Gauge(
    f"{PREFIX}_collector_duration_seconds",
    "Duration of last collection in seconds",
    ["collector"],
)
collector_last_scrape_timestamp = Gauge(
    f"{PREFIX}_collector_last_scrape_timestamp",
    "Unix timestamp of last scrape attempt",
    ["collector"],
)
