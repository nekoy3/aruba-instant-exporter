# aruba-instant-exporter

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

Prometheus exporter for **Aruba Instant Access Points** (IAP).

Collects metrics that SNMP cannot provide — CPU usage, memory, per-radio wireless statistics, and channel quality — by combining **SSH** and the **Web CGI API**.

---

## Overview

Standard SNMP monitoring of Aruba Instant APs gives you client counts, but misses the most important health signals: CPU, memory, and radio-level diagnostics.

`aruba-instant-exporter` fills that gap using two collection paths:

- **SSH** — retrieves CPU, memory, and wired interface counters via CLI
- **Web CGI** — retrieves radio stats, channel quality, client info, and AP uptime

Tested on **Aruba Instant 505**. Other Aruba Instant series APs are likely compatible.

---

## Architecture

```
 ┌──────────────────────────────────────┐
 │          Aruba Instant AP            │
 │                                      │
 │  SSH :22        Web CGI :4343/HTTPS  │
 └────────┬─────────────────┬───────────┘
          │                 │
          ▼                 ▼
 ┌──────────────────────────────────────┐
 │        aruba-instant-exporter        │
 │                                      │
 │  ssh_collector.py  cgi_collector.py  │
 │        └──────────┬──────────┘       │
 │              metrics.py              │
 │           main.py (HTTP :9877)       │
 └──────────────────┬───────────────────┘
                    │  /metrics
                    ▼
 ┌──────────────────────────────────────┐
 │             Prometheus               │
 └──────────────────┬───────────────────┘
                    ▼
 ┌──────────────────────────────────────┐
 │              Grafana                 │
 └──────────────────────────────────────┘
```

### Metrics by Collection Path

Each collector can be disabled independently via `ENABLE_SSH` / `ENABLE_CGI`. Disabling a collector will stop collecting the corresponding metrics.

| Path | Commands Used | Metrics Collected |
|------|--------------|-------------------|
| **SSH** | `show cpu`<br>`show memory`<br>`show interface counters` | CPU usage<br>Memory (total/free/available/cached/buffers/slab)<br>Wired interface (speed, RX/TX, errors) |
| **Web CGI** | `show ap monitor status`<br>`show ap debug radio-stats 0`<br>`show ap debug radio-stats 1`<br>`show ap arm rf-summary`<br>`show clients` | AP info & uptime<br>Radio stats (packets, bytes, PPS, CRC errors)<br>Radio stats (channel, EIRP, noise floor)<br>Channel quality (2.4GHz only)<br>Client info |

---

## Metrics

### AP Info

| Metric | Description | Labels |
|--------|-------------|--------|
| `aruba_instant_ap_info` | AP information (always 1) | `ap_name`, `ap_type`, `country_code` |
| `aruba_instant_uptime_seconds` | AP uptime in seconds | — |

### CPU

| Metric | Description | Labels |
|--------|-------------|--------|
| `aruba_instant_cpu_usage_ratio` | CPU usage ratio (0.0–1.0) | `cpu`, `mode` (user/system/idle/iowait/etc.) |

### Memory

| Metric | Description | Labels |
|--------|-------------|--------|
| `aruba_instant_memory_bytes` | Memory in bytes | `type` (total/free/available/cached/buffers/slab) |

### Wired Interface

| Metric | Description | Labels |
|--------|-------------|--------|
| `aruba_instant_interface_up` | Interface link state (1=up) | `interface` |
| `aruba_instant_interface_speed_mbps` | Interface speed (Mbps) | `interface` |
| `aruba_instant_interface_rx_bytes_total` | Received bytes | `interface` |
| `aruba_instant_interface_tx_bytes_total` | Transmitted bytes | `interface` |
| `aruba_instant_interface_rx_packets_total` | Received packets | `interface` |
| `aruba_instant_interface_tx_packets_total` | Transmitted packets | `interface` |
| `aruba_instant_interface_rx_errors_total` | Receive errors | `interface` |
| `aruba_instant_interface_tx_errors_total` | Transmit errors | `interface` |

### Radio

| Metric | Description | Labels |
|--------|-------------|--------|
| `aruba_instant_radio_channel` | Current channel number | `radio`, `phy_type` |
| `aruba_instant_radio_eirp_dbm` | Transmit power (dBm) | `radio` |
| `aruba_instant_radio_max_eirp_dbm` | Maximum transmit power (dBm) | `radio` |
| `aruba_instant_radio_noise_floor_dbm` | Noise floor (dBm) | `radio` |
| `aruba_instant_radio_packets_read_total` | Total packets read | `radio` |
| `aruba_instant_radio_bytes_read_total` | Total bytes read | `radio` |
| `aruba_instant_radio_cur_pps` | Current packets per second | `radio` |
| `aruba_instant_radio_max_pps` | Maximum packets per second | `radio` |
| `aruba_instant_radio_data_packets_total` | Total data packets | `radio` |
| `aruba_instant_radio_data_bytes_total` | Total data bytes | `radio` |
| `aruba_instant_radio_data_cur_pps` | Current data packets per second | `radio` |
| `aruba_instant_radio_data_cur_bps` | Current data bytes per second | `radio` |
| `aruba_instant_radio_mgmt_packets_total` | Total management packets | `radio` |
| `aruba_instant_radio_mgmt_bytes_total` | Total management bytes | `radio` |
| `aruba_instant_radio_ctrl_packets_total` | Total control packets | `radio` |
| `aruba_instant_radio_ctrl_bytes_total` | Total control bytes | `radio` |
| `aruba_instant_radio_tx_frames_transmitted_total` | Total TX frames transmitted | `radio` |
| `aruba_instant_radio_tx_retries_total` | Total TX retries | `radio` |
| `aruba_instant_radio_rx_crc_errors_total` | Total RX CRC errors | `radio` |
| `aruba_instant_radio_resets_total` | Total radio resets | `radio` |
| `aruba_instant_radio_channel_changes_total` | Total channel changes | `radio` |
| `aruba_instant_radio_tx_power_changes_total` | Total TX power changes | `radio` |
| `aruba_instant_radio_buffer_overflows_total` | Total buffer overflows | `radio` |
| `aruba_instant_channel_quality` | Channel quality (0–100, 2.4GHz only) | `radio`, `channel` |
| `aruba_instant_channel_noise_dbm` | Channel noise level in dBm (2.4GHz only) | `radio`, `channel` |
| `aruba_instant_channel_utilization_percent` | Channel utilization % (2.4GHz only) | `radio`, `channel` |

### Clients

| Metric | Description | Labels |
|--------|-------------|--------|
| `aruba_instant_clients` | Total associated clients | — |
| `aruba_instant_client_signal_dbm` | Client signal strength (dBm) | `mac`, `name`, `channel`, `essid`, `ip`, `type` |
| `aruba_instant_client_speed_mbps` | Client connection speed (Mbps) | `mac`, `name`, `channel`, `essid`, `ip`, `type` |

### Collector Health

| Metric | Description | Labels |
|--------|-------------|--------|
| `aruba_instant_collector_success` | 1 if last collection succeeded | `collector` (ssh/cgi) |
| `aruba_instant_collector_duration_seconds` | Collection duration | `collector` |
| `aruba_instant_collector_last_success_timestamp` | Unix timestamp of last success | `collector` |

---

## Requirements

### AP Side

SSH must be enabled on the Aruba Instant AP:

1. Log in to the Aruba Instant web UI
2. Go to **Settings → System → Admin**
3. Enable **SSH**

### Host Side

- Docker + Docker Compose, **or** Python 3.8+

---

## Getting Started

### Using Docker Compose (recommended)

**1. Clone the repository**

```bash
git clone https://github.com/nekoy3/aruba-instant-exporter.git
cd aruba-instant-exporter
```

**2. Create your `.env` file**

```bash
cp .env.example .env
```

Edit `.env` with your AP's address and credentials:

```env
ARUBA_HOST=192.168.10.2
ARUBA_SSH_USERNAME=admin
ARUBA_SSH_PASSWORD=your_password
```

**3. Start the exporter**

```bash
docker compose up -d
```

**4. Verify**

```bash
curl http://localhost:9877/metrics | grep aruba_instant_cpu
```

### Using Python directly

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env
python3 -m exporter.main
```

---

## Configuration

All settings are via environment variables (or `.env` file).

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ARUBA_HOST` | ✅ | — | AP IP address or hostname |
| `ARUBA_SSH_USERNAME` | ✅ | — | SSH username |
| `ARUBA_SSH_PASSWORD` | ✅ | — | SSH password |
| `ARUBA_WEB_USERNAME` | | same as SSH | Web GUI username (if different) |
| `ARUBA_WEB_PASSWORD` | | same as SSH | Web GUI password (if different) |
| `ARUBA_WEB_PORT` | | `4343` | Web GUI HTTPS port |
| `EXPORTER_PORT` | | `9877` | HTTP port to expose `/metrics` |
| `COLLECT_INTERVAL` | | `30` | Scrape interval in seconds |
| `ENABLE_SSH` | | `true` | Enable SSH collector |
| `ENABLE_CGI` | | `true` | Enable CGI collector |
| `SSH_TIMEOUT` | | `15` | SSH connection timeout (seconds) |
| `CGI_TIMEOUT` | | `15` | CGI request timeout (seconds) |
| `LOG_LEVEL` | | `INFO` | Log level: DEBUG / INFO / WARNING / ERROR |

> **Note**: `COLLECT_INTERVAL` controls how often the exporter polls the AP internally.  
> Set Prometheus `scrape_interval` to the same value or longer (e.g., `30s`).

---

## Prometheus Integration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: aruba-instant
    static_configs:
      - targets: ['localhost:9877']
    scrape_interval: 30s
    scrape_timeout: 20s
```

---

## Troubleshooting

### SSH connection failed

```
aruba_instant_collector_success{collector="ssh"} 0
```

- Check `ARUBA_HOST`, `ARUBA_SSH_USERNAME`, `ARUBA_SSH_PASSWORD` in `.env`
- Verify SSH is enabled on the AP (Settings → System → Admin → SSH)
- Test manually: `ssh admin@<AP_IP>`

### CGI login failed

```
aruba_instant_collector_success{collector="cgi"} 0
```

- The Web GUI uses HTTPS with a self-signed certificate — the exporter handles this automatically
- Verify web credentials (`ARUBA_WEB_USERNAME` / `ARUBA_WEB_PASSWORD`)
- Check `ARUBA_WEB_PORT` (default `4343`)

### Metrics are empty / no data

- Check the exporter logs: `docker compose logs -f`
- Query the health metrics:
  ```
  aruba_instant_collector_success
  aruba_instant_collector_duration_seconds
  aruba_instant_collector_last_success_timestamp
  ```

### Channel quality missing for 5GHz

`show ap arm rf-summary` returns channel quality history only for 2.4GHz (wifi1) by design of Aruba ARM (Adaptive Radio Management). ARM does not generate channel quality scores for 5GHz — instead it manages the 5GHz radio via Noise Floor, EIRP, and DFS. This was confirmed from actual API responses (only channels 1/6/11 returned, which are 2.4GHz-only channels).

---

## License

MIT License — see [LICENSE](LICENSE) for details.
