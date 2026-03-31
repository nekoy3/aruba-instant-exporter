# aruba-instant-exporter

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

**Aruba Instant アクセスポイント（IAP）向け Prometheus Exporter**

SNMP では取得できない CPU 使用率・メモリ・ラジオ統計・チャネル品質を、**SSH** と **Web CGI API** の 2 系統で収集します。

---

## 概要

Aruba Instant AP を SNMP で監視すると、クライアント数は取れますが、最も重要なヘルス情報（CPU・メモリ・ラジオ診断）が取れません。

`aruba-instant-exporter` はその不足を 2 つの収集経路で補います：

- **SSH** — CLI 経由で CPU・メモリ・有線インターフェースカウンターを取得
- **Web CGI** — ラジオ統計・チャネル品質・クライアント情報・AP 稼働時間を取得

**Aruba Instant 505 で動作確認済み**。他の Aruba Instant シリーズも対応している可能性があります。

---

## アーキテクチャ

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

### 収集経路別メトリクス

`ENABLE_SSH` / `ENABLE_CGI` 環境変数でコレクターを個別に無効化できます。無効化した場合、対応するメトリクスは収集されません。

| 収集経路 | 使用コマンド | 収集対象 |
|---------|------------|---------|
| **SSH** | `show cpu`<br>`show memory`<br>`show interface counters` | CPU 使用率<br>メモリ（total/free/available/cached/buffers/slab）<br>有線インターフェース（速度・RX/TX・エラー） |
| **Web CGI** | `show ap monitor status`<br>`show ap debug radio-stats 0`<br>`show ap debug radio-stats 1`<br>`show ap arm rf-summary`<br>`show clients` | AP 情報・稼働時間<br>ラジオ統計（パケット数・バイト数・PPS・CRC エラー）<br>ラジオ統計（チャネル・EIRP・ノイズフロア）<br>チャネル品質（2.4GHz のみ）<br>クライアント情報 |

---

## 収集メトリクス

### AP 情報

| メトリクス | 説明 | ラベル |
|-----------|------|--------|
| `aruba_instant_ap_info` | AP 情報（常に 1） | `ap_name`, `ap_type`, `country_code`, `ip_addr` |
| `aruba_instant_uptime_seconds` | AP 稼働時間（秒） | — |

### CPU

| メトリクス | 説明 | ラベル |
|-----------|------|--------|
| `aruba_instant_cpu_usage_ratio` | CPU 使用率（0.0〜1.0） | `cpu`, `mode`（user/system/idle/iowait 等） |

### メモリ

| メトリクス | 説明 | ラベル |
|-----------|------|--------|
| `aruba_instant_memory_bytes` | メモリ量（バイト） | `type`（total/free/available/cached/buffers/slab） |

### 有線インターフェース

| メトリクス | 説明 | ラベル |
|-----------|------|--------|
| `aruba_instant_interface_up` | リンク状態（1=UP） | `interface` |
| `aruba_instant_interface_speed_mbps` | インターフェース速度（Mbps） | `interface` |
| `aruba_instant_interface_rx_bytes_total` | 受信バイト数 | `interface` |
| `aruba_instant_interface_tx_bytes_total` | 送信バイト数 | `interface` |
| `aruba_instant_interface_rx_packets_total` | 受信パケット数 | `interface` |
| `aruba_instant_interface_tx_packets_total` | 送信パケット数 | `interface` |
| `aruba_instant_interface_rx_errors_total` | 受信エラー数 | `interface` |
| `aruba_instant_interface_tx_errors_total` | 送信エラー数 | `interface` |

### ラジオ

| メトリクス | 説明 | ラベル |
|-----------|------|--------|
| `aruba_instant_radio_channel` | 使用チャネル番号 | `radio` |
| `aruba_instant_radio_eirp_dbm` | 送信電力（dBm） | `radio` |
| `aruba_instant_radio_max_eirp_dbm` | 最大送信電力（dBm） | `radio` |
| `aruba_instant_radio_noise_floor_dbm` | ノイズフロア（dBm） | `radio` |
| `aruba_instant_radio_packets_read_total` | 受信パケット総数 | `radio` |
| `aruba_instant_radio_bytes_read_total` | 受信バイト総数 | `radio` |
| `aruba_instant_radio_cur_pps` | 現在の PPS | `radio` |
| `aruba_instant_radio_max_pps` | 最大 PPS | `radio` |
| `aruba_instant_radio_data_packets_total` | データパケット総数 | `radio` |
| `aruba_instant_radio_data_bytes_total` | データバイト総数 | `radio` |
| `aruba_instant_radio_data_cur_pps` | 現在のデータ PPS | `radio` |
| `aruba_instant_radio_data_cur_bps` | 現在のデータ BPS | `radio` |
| `aruba_instant_radio_mgmt_packets_total` | 管理パケット総数 | `radio` |
| `aruba_instant_radio_mgmt_bytes_total` | 管理バイト総数 | `radio` |
| `aruba_instant_radio_ctrl_packets_total` | 制御パケット総数 | `radio` |
| `aruba_instant_radio_ctrl_bytes_total` | 制御バイト総数 | `radio` |
| `aruba_instant_radio_tx_frames_transmitted_total` | 送信フレーム総数 | `radio` |
| `aruba_instant_radio_tx_retries_total` | 送信リトライ総数 | `radio` |
| `aruba_instant_radio_rx_crc_errors_total` | 受信 CRC エラー総数 | `radio` |
| `aruba_instant_radio_resets_total` | ラジオリセット総数 | `radio` |
| `aruba_instant_radio_channel_changes_total` | チャネル変更総数 | `radio` |
| `aruba_instant_radio_tx_power_changes_total` | 送信電力変更総数 | `radio` |
| `aruba_instant_radio_buffer_overflows_total` | バッファオーバーフロー総数 | `radio` |
| `aruba_instant_channel_quality` | チャネル品質（0〜100、2.4GHz のみ） | `radio`, `channel` |
| `aruba_instant_channel_noise_dbm` | チャネルノイズレベル（dBm、2.4GHz のみ） | `radio`, `channel` |
| `aruba_instant_channel_utilization_percent` | チャネル使用率（%、2.4GHz のみ） | `radio`, `channel` |

### クライアント

| メトリクス | 説明 | ラベル |
|-----------|------|--------|
| `aruba_instant_clients` | 接続クライアント総数 | — |
| `aruba_instant_client_signal_dbm` | クライアント信号強度（dBm） | `mac`, `name`, `channel`, `essid`, `ip`, `type` |
| `aruba_instant_client_speed_mbps` | クライアント接続速度（Mbps） | `mac`, `name`, `channel`, `essid`, `ip`, `type` |

### コレクターヘルス

| メトリクス | 説明 | ラベル |
|-----------|------|--------|
| `aruba_instant_collector_success` | 収集成功フラグ（1=成功） | `collector` |
| `aruba_instant_collector_duration_seconds` | 収集所要時間（秒） | `collector` |
| `aruba_instant_collector_last_success_timestamp` | 最終成功時刻（Unix タイム） | `collector` |

---

## 前提条件

### AP 側の設定

Aruba Instant AP で SSH を有効化する必要があります：

1. Aruba Instant Web UI にログイン
2. **Settings → System → Admin** に移動
3. **SSH** を有効化

### ホスト側

- Docker + Docker Compose、**または** Python 3.8 以上

---

## クイックスタート

### Docker Compose を使う（推奨）

**1. リポジトリをクローン**

```bash
git clone https://github.com/your-username/aruba-instant-exporter.git
cd aruba-instant-exporter
```

**2. `.env` ファイルを作成**

```bash
cp .env.example .env
```

`.env` を編集して AP のアドレスと認証情報を設定：

```env
ARUBA_HOST=192.168.10.2
ARUBA_SSH_USERNAME=admin
ARUBA_SSH_PASSWORD=your_password
```

**3. Exporter を起動**

```bash
docker compose up -d
```

**4. 動作確認**

```bash
curl http://localhost:9877/metrics | grep aruba_instant_cpu
```

### Python で直接実行する

```bash
pip install -r requirements.txt
cp .env.example .env
# .env を編集
python3 -m exporter.main
```

---

## 設定

すべての設定は環境変数（または `.env` ファイル）で行います。

| 変数名 | 必須 | デフォルト | 説明 |
|--------|------|-----------|------|
| `ARUBA_HOST` | ✅ | — | AP の IP アドレスまたはホスト名 |
| `ARUBA_SSH_USERNAME` | ✅ | — | SSH ユーザー名 |
| `ARUBA_SSH_PASSWORD` | ✅ | — | SSH パスワード |
| `ARUBA_WEB_USERNAME` | | SSH と同じ | Web GUI ユーザー名（SSH と異なる場合） |
| `ARUBA_WEB_PASSWORD` | | SSH と同じ | Web GUI パスワード（SSH と異なる場合） |
| `ARUBA_WEB_PORT` | | `4343` | Web GUI の HTTPS ポート |
| `EXPORTER_PORT` | | `9877` | `/metrics` を公開する HTTP ポート |
| `COLLECT_INTERVAL` | | `30` | AP へのポーリング間隔（秒） |
| `ENABLE_SSH` | | `true` | SSH コレクターの有効/無効 |
| `ENABLE_CGI` | | `true` | CGI コレクターの有効/無効 |
| `SSH_TIMEOUT` | | `15` | SSH 接続タイムアウト（秒） |
| `CGI_TIMEOUT` | | `15` | CGI リクエストタイムアウト（秒） |
| `LOG_LEVEL` | | `INFO` | ログレベル: DEBUG / INFO / WARNING / ERROR |

> **注意**: `COLLECT_INTERVAL` は exporter が AP をポーリングする間隔です。  
> Prometheus の `scrape_interval` は同じ値か、それ以上に設定してください（例：`30s`）。

---

## Prometheus 設定

`prometheus.yml` に以下を追加：

```yaml
scrape_configs:
  - job_name: aruba-instant
    static_configs:
      - targets: ['localhost:9877']
    scrape_interval: 30s
    scrape_timeout: 20s
```

---

## トラブルシューティング

### SSH 接続に失敗する

```
aruba_instant_collector_success{collector="ssh"} 0
```

- `.env` の `ARUBA_HOST`・`ARUBA_SSH_USERNAME`・`ARUBA_SSH_PASSWORD` を確認
- AP で SSH が有効になっているか確認（Settings → System → Admin → SSH）
- 手動で接続テスト: `ssh admin@<AP_IP>`

### CGI ログインに失敗する

```
aruba_instant_collector_success{collector="cgi"} 0
```

- Web GUI は自己署名証明書の HTTPS を使用しています（exporter が自動的に処理します）
- Web 認証情報（`ARUBA_WEB_USERNAME` / `ARUBA_WEB_PASSWORD`）を確認
- `ARUBA_WEB_PORT`（デフォルト `4343`）を確認

### メトリクスが空・No Data になる

- exporter のログを確認: `docker compose logs -f`
- ヘルスメトリクスで状態を確認:
  ```
  aruba_instant_collector_success
  aruba_instant_collector_duration_seconds
  aruba_instant_collector_last_success_timestamp
  ```

### 5GHz のチャネル品質が取得できない

`show ap arm rf-summary` は Aruba ARM（Adaptive Radio Management）の設計上、2.4GHz (wifi1) のチャネル品質履歴のみを返します。ARM は 5GHz に対してチャネル品質スコアを生成しない仕様であり、代わりに Noise Floor・EIRP・DFS によって 5GHz ラジオを管理します。実際の API レスポンスで確認済みです（チャネル番号 1/6/11 のみ返却）。

---

## ライセンス

MIT License — 詳細は [LICENSE](LICENSE) を参照してください。
