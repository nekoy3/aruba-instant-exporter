"""CGI-based metric collector for Aruba Instant AP.

Collects client, radio, uptime, and channel metrics via HTTPS swarm.cgi.
The Aruba Instant web GUI exposes a CGI endpoint that accepts CLI commands
and returns structured XML responses.

CGIベースの Aruba Instant AP メトリクスコレクター。

HTTPS swarm.cgi 経由でクライアント・Radio・稼働時間・チャネルメトリクスを収集する。
Aruba Instant の Web GUI は CLI コマンドを受け付ける CGI エンドポイントを持ち、
構造化された XML レスポンスを返す。
"""

import re
import ssl
import time
import logging
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen
from urllib.parse import urlencode

from . import metrics as m

logger = logging.getLogger(__name__)


def _parse_xml(xml_string):
    """Parse Aruba CGI XML into tables and key-value data.

    Returns dict with:
      - tables: list of {name, headers, rows}
      - data: dict of key-value pairs
    """
    xml_string = xml_string.strip()
    if not xml_string:
        return {"tables": [], "data": {}}
    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        logger.warning("XML parse error: %s", e)
        return {"tables": [], "data": {}}

    result = {"tables": [], "data": {}}

    for table in root.findall(".//t"):
        name = (table.get("tn") or "").strip()
        headers = [h.text or "" for h in table.findall(".//th/h")]
        rows = []
        for row in table.findall(".//r"):
            cells = [(c.text or "") for c in row.findall("c")]
            rows.append(cells)
        result["tables"].append({"name": name, "headers": headers, "rows": rows})

    for data_el in root.findall(".//data"):
        name = (data_el.get("name") or "").strip()
        value = (data_el.text or "").strip()
        if name:
            result["data"][name] = value

    return result


def _parse_signal(signal_str):
    """Extract numeric signal value from e.g. '63(good)' -> 63.

    '63(good)' のような文字列から数値のシグナル値を抽出する。"""
    match = re.match(r"(-?\d+)", signal_str)
    return int(match.group(1)) if match else None


def _parse_speed(speed_str):
    """Extract numeric speed from e.g. '1134(good)' -> 1134.

    '1134(good)' のような文字列から数値の速度値を抽出する。"""
    match = re.match(r"(\d+)", speed_str)
    return int(match.group(1)) if match else None


def _extract_radio_name(bssid_str):
    """Extract radio name from bssid string like '34:3a:20:2c:82:b0(wifi0)'.

    Returns (bssid, radio_name) tuple.
    """
    match = re.match(r"([0-9a-f:]+)\((\w+)\)", bssid_str, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2)
    return bssid_str, bssid_str


class CGICollector:
    """Collects metrics from Aruba Instant AP via HTTPS CGI.

    HTTPS CGI 経由で Aruba Instant AP のメトリクスを収集するクラス。"""

    def __init__(self, config):
        self.config = config
        self._sid = None
        self._base_url = (
            f"https://{config.aruba_host}:{config.web_port}/swarm.cgi"
        )
        self._ssl_ctx = ssl.create_default_context()
        if not config.ssl_verify:
            # Disable SSL verification for self-signed certificates (common on APs)
            # 自己署名証明書に対応するため SSL 検証を無効化（AP では一般的）
            self._ssl_ctx.check_hostname = False
            self._ssl_ctx.verify_mode = ssl.CERT_NONE
        else:
            logger.debug("SSL verification enabled")

    def _request(self, data_dict):
        """Send a POST request to swarm.cgi.

        swarm.cgi に POST リクエストを送信する。"""
        data = urlencode(data_dict).encode()
        req = Request(self._base_url, data=data, method="POST")
        resp = urlopen(req, timeout=self.config.cgi_timeout, context=self._ssl_ctx)
        return resp.read().decode(errors="replace")

    def _login(self):
        """Authenticate and obtain a session ID.

        認証を行いセッション ID を取得する。"""
        logger.debug("Logging in to CGI on %s", self.config.aruba_host)
        raw = self._request({
            "opcode": "login",
            "user": self.config.web_username,
            "passwd": self.config.web_password,
        })
        parsed = _parse_xml(raw)
        sid = parsed["data"].get("sid", "")
        if not sid:
            raise RuntimeError(f"CGI login failed: no session ID in response")
        self._sid = sid
        logger.info("CGI login successful, sid=%s...", sid[:8])

    def _execute(self, command):
        """Execute a show command via CGI and return parsed XML.

        CGI 経由で show コマンドを実行し、解析済み XML データを返す。"""
        if not self._sid:
            self._login()
        raw = self._request({
            "opcode": "show",
            "cmd": command,
            "sid": self._sid,
        })
        # Check for session expiry (empty response)
        # セッション切れを確認（空のレスポンスで判定）
        if raw.strip() == "<?xml version='1.0'?>" or "<re/>" in raw:
            logger.debug("Session expired, re-authenticating")
            self._login()
            raw = self._request({
                "opcode": "show",
                "cmd": command,
                "sid": self._sid,
            })
        return _parse_xml(raw)

    def collect(self):
        """Run all CGI collections and update Prometheus metrics.

        全 CGI 収集を実行し、Prometheus メトリクスを更新する。"""
        t0 = time.time()
        try:
            self._login()
            self._collect_clients()
            self._collect_monitor_status()
            self._collect_radio_stats()
            self._collect_rf_summary()
            m.collector_success.labels(collector="cgi").set(1)
            logger.debug("CGI collection completed in %.2fs", time.time() - t0)
        except Exception:
            m.collector_success.labels(collector="cgi").set(0)
            logger.exception("CGI collection failed")
        finally:
            m.collector_duration_seconds.labels(collector="cgi").set(time.time() - t0)
            m.collector_last_scrape_timestamp.labels(collector="cgi").set(time.time())
            self._logout()

    def _collect_clients(self):
        """Parse 'show clients' and update client metrics.

        'show clients' を解析してクライアントメトリクスを更新する。"""
        parsed = self._execute("show clients")

        # Client count from data field
        # dataフィールドからクライアント接続数を取得
        count_str = parsed["data"].get("Number of Clients", "0")
        try:
            count = int(count_str)
        except ValueError:
            count = 0
        m.clients.set(count)

        # Per-client metrics from table
        # テーブルから各クライアントのメトリクスを取得
        for table in parsed["tables"]:
            if "Client" not in table["name"]:
                continue
            headers = [h.lower() for h in table["headers"]]
            for row in table["rows"]:
                if len(row) != len(headers):
                    continue
                data = dict(zip(headers, row))
                name = data.get("name", "") or "unknown"
                mac = data.get("mac address", "")
                ip = data.get("ip address", "")
                essid = data.get("essid", "")
                channel = data.get("channel", "")
                wtype = data.get("type", "")

                labels = dict(
                    name=name, mac=mac, ip=ip,
                    essid=essid, channel=channel, type=wtype,
                )

                signal = _parse_signal(data.get("signal", ""))
                if signal is not None:
                    m.client_signal_dbm.labels(**labels).set(signal)

                speed = _parse_speed(data.get("speed (mbps)", ""))
                if speed is not None:
                    m.client_speed_mbps.labels(**labels).set(speed)

        logger.debug("Client metrics updated: %d clients", count)

    def _collect_monitor_status(self):
        """Parse 'show ap monitor status' and update radio/wired metrics.

        'show ap monitor status' を解析して Radio・有線メトリクスを更新する。"""
        parsed = self._execute("show ap monitor status")

        for table in parsed["tables"]:
            tn = table["name"].strip()
            headers = [h.strip() for h in table["headers"]]

            if "AP Info" in tn:
                self._parse_ap_info(table)
            elif tn == "Wired packet counters":
                self._parse_wired_counters(table, headers)
            elif tn == "WLAN Interface":
                self._parse_wlan_interface(table, headers)
            elif tn == "WLAN packet counters" and "DATA" not in tn and "MGMT" not in tn and "CTRL" not in tn:
                self._parse_wlan_packet_counters(table, headers)
            elif "counters for DATA" in tn:
                self._parse_wlan_type_counters(table, headers, "data")
            elif "counters for MGMT" in tn:
                self._parse_wlan_type_counters(table, headers, "mgmt")
            elif "counters for CTRL" in tn:
                self._parse_wlan_type_counters(table, headers, "ctrl")

    def _parse_ap_info(self, table):
        """Parse AP Info key-value table.

        AP 情報のキーバリューテーブルを解析する。"""
        info = {}
        for row in table["rows"]:
            if len(row) >= 2:
                info[row[0].strip()] = row[1].strip()

        uptime_str = info.get("Uptime", "0")
        try:
            m.uptime_seconds.set(int(uptime_str))
        except ValueError:
            pass

        m.ap_info.info({
            "ap_name": info.get("AP Name", ""),
            "ap_type": info.get("AP Type", ""),
            "country_code": info.get("Country Code", ""),
        })

    def _parse_wired_counters(self, table, headers):
        """Parse wired packet counters.

        有線インターフェースのパケットカウンターを解析する。"""
        for row in table["rows"]:
            if len(row) < 2:
                continue
            iface_raw = row[0]
            _, iface = _extract_radio_name(iface_raw) if "(" in iface_raw else (iface_raw, iface_raw)
            # Normalize header keys to lowercase to handle "Pkts"/"PKTS"/"pkts" variations
            # ヘッダーキーを小文字に正規化（"Pkts"/"PKTS"/"pkts" 等のバリエーションに対応）
            data = {str(k).strip().lower(): v for k, v in zip(headers, row)}
            try:
                m.wired_packets_total.labels(interface=iface).set(
                    int(data.get("pkts", 0))
                )
            except (ValueError, TypeError):
                pass

    def _parse_wlan_interface(self, table, headers):
        """Parse WLAN interface table for channel and phy-type.

        WLAN インターフェーステーブルからチャネルと物理タイプを解析する。"""
        for row in table["rows"]:
            if len(row) < len(headers):
                continue
            data = dict(zip(headers, row))
            bssid = data.get("bssid", "")
            _, radio = _extract_radio_name(bssid) if "(" in bssid else (bssid, bssid)

            # Channel (strip band suffix like "E")
            # チャネル番号を取得（"E"などのバンドサフィックスを除去）
            ch_str = data.get("channel", "0")
            ch_num = re.sub(r"[^0-9]", "", ch_str)
            phy = data.get("phy-type", "")
            try:
                m.radio_channel.labels(radio=radio, phy_type=phy).set(int(ch_num or 0))
            except ValueError:
                pass

    def _parse_wlan_packet_counters(self, table, headers):
        """Parse main WLAN packet counters (not DATA/MGMT/CTRL).

        メインの WLAN パケットカウンター（DATA/MGMT/CTRL 以外）を解析する。"""
        for row in table["rows"]:
            if len(row) < len(headers):
                continue
            data = dict(zip(headers, row))
            iface_raw = data.get("Interface", row[0])
            _, radio = _extract_radio_name(iface_raw)

            self._safe_set(m.radio_packets_read_total, radio, data.get("Packets Read"))
            self._safe_set(m.radio_bytes_read_total, radio, data.get("Bytes Read"))
            self._safe_set(m.radio_buffer_overflows_total, radio, data.get("Buffer Overflows"))
            self._safe_set(m.radio_max_pps, radio, data.get("Max PPS"))
            self._safe_set(m.radio_cur_pps, radio, data.get("Cur PPS"))

    def _parse_wlan_type_counters(self, table, headers, pkt_type):
        """Parse DATA/MGMT/CTRL packet counters.

        DATA・MGMT・CTRL フレームのパケットカウンターを解析する。"""
        # DATA headers use title case ("Data Pkts"), MGMT/CTRL use all-caps
        # DATAはタイトルケース（"Data Pkts"）、MGMT/CTRLは大文字のヘッダーを使用
        prefix = "Data" if pkt_type == "data" else pkt_type.upper()
        metrics_map = {
            "data": {
                f"{prefix} Pkts": m.radio_data_packets_total,
                f"{prefix} Bytes": m.radio_data_bytes_total,
                f"{prefix} Cur PPS": m.radio_data_cur_pps,
                f"{prefix} Cur BPS": m.radio_data_cur_bps,
            },
            "mgmt": {
                f"{prefix} Pkts": m.radio_mgmt_packets_total,
                f"{prefix} Bytes": m.radio_mgmt_bytes_total,
            },
            "ctrl": {
                f"{prefix} Pkts": m.radio_ctrl_packets_total,
                f"{prefix} Bytes": m.radio_ctrl_bytes_total,
            },
        }
        mapping = metrics_map.get(pkt_type, {})

        for row in table["rows"]:
            if len(row) < len(headers):
                continue
            data = dict(zip(headers, row))
            iface_raw = data.get("Interface", row[0])
            _, radio = _extract_radio_name(iface_raw)

            for col_name, gauge in mapping.items():
                self._safe_set(gauge, radio, data.get(col_name))

    def _collect_radio_stats(self):
        """Parse 'show ap debug radio-stats' for noise floor, EIRP, etc.

        Queries both radio 0 (wifi0/5GHz) and radio 1 (wifi1/2.4GHz).
        """
        for idx, radio in [(0, "wifi0"), (1, "wifi1")]:
            try:
                parsed = self._execute(f"show ap debug radio-stats {idx}")
            except Exception:
                logger.debug("Failed to get radio-stats for %s", radio)
                continue

            kv = {}
            for table in parsed["tables"]:
                for row in table["rows"]:
                    if len(row) >= 2 and "---" not in row[0]:
                        kv[row[0].strip()] = row[1].strip()

            if not kv:
                continue

            self._safe_set_kv(m.radio_noise_floor_dbm, radio, kv, "Current Noise Floor", negate=True)
            self._safe_set_kv(m.radio_eirp_dbm, radio, kv, "EIRP", is_float=True)
            self._safe_set_kv(m.radio_max_eirp_dbm, radio, kv, "MAX EIRP", is_float=True)
            self._safe_set_kv(m.radio_resets_total, radio, kv, "Total Radio Resets")
            self._safe_set_kv(m.radio_channel_changes_total, radio, kv, "Channel Changes")
            self._safe_set_kv(m.radio_tx_power_changes_total, radio, kv, "TX Power Changes")
            self._safe_set_kv(m.radio_tx_frames_total, radio, kv, "Tx Frames Transmitted")
            self._safe_set_kv(m.radio_tx_retries_total, radio, kv, "Tx Success With Retry")
            self._safe_set_kv(m.radio_rx_crc_errors_total, radio, kv, "Rx CRC Errors")

            logger.debug("Radio stats updated for %s", radio)

    def _collect_rf_summary(self):
        """Parse 'show ap arm rf-summary' for channel quality.

        'show ap arm rf-summary' からチャネル品質を解析する。"""
        parsed = self._execute("show ap arm rf-summary")

        # The rf-summary output is a series of <data> elements
        # rf-summaryの出力は<data>要素の連続で構成されている
        # "Channel quality history" -> radio name (e.g. "wifi1")
        # "Channel quality history" キーの値がRadio名（例: "wifi1"）
        # Then channel blocks: name=" 1" -> "Q: 90 90 ..."
        # その後チャネルブロックが続く: name=" 1" -> "Q: 90 90 ..."
        current_radio = None
        current_channel = None

        data_items = list(parsed["data"].items())
        for key, value in data_items:
            if "Channel quality history" in key:
                current_radio = value.strip()
                current_channel = None
                continue

            if current_radio is None:
                continue

            # Channel number line (non-empty name with digits)
            # チャネル番号行（数字を含む空でない名前）
            ch_match = re.match(r"\s*(\d+)\s*$", key)
            if ch_match:
                current_channel = ch_match.group(1)
                # This line has the Q values
                # このチャネル番号行にQuality値が含まれている
                q_match = re.match(r"Q:\s*([\d\s*]+)", value)
                if q_match and current_channel:
                    vals = q_match.group(1).strip().split()
                    if vals:
                        latest = int(re.sub(r"[^0-9]", "", vals[0]))
                        m.channel_quality.labels(
                            radio=current_radio, channel=current_channel
                        ).set(latest)
                continue

            if current_channel is None:
                continue

            # Noise line: "N: *82 *82 ..."
            # ノイズ行: "N: *82 *82 ..." 形式
            if value.startswith("N:"):
                vals = value[2:].strip().split()
                if vals:
                    raw = re.sub(r"[^0-9]", "", vals[0])
                    if raw:
                        m.channel_noise_dbm.labels(
                            radio=current_radio, channel=current_channel
                        ).set(-int(raw))

            # Utilization line: "U: 11 11 ..."
            # チャネル使用率行: "U: 11 11 ..." 形式
            elif value.startswith("U:"):
                vals = value[2:].strip().split()
                if vals:
                    raw = re.sub(r"[^0-9]", "", vals[0])
                    if raw:
                        m.channel_utilization_percent.labels(
                            radio=current_radio, channel=current_channel
                        ).set(int(raw))

        logger.debug("RF summary metrics updated")

    @staticmethod
    def _safe_set(gauge, radio, value_str):
        """Safely set a gauge value for a radio label.

        Radio ラベルに対してゲージ値を安全に設定する。"""
        if value_str is None:
            return
        try:
            gauge.labels(radio=radio).set(int(value_str))
        except (ValueError, TypeError):
            pass

    @staticmethod
    def _safe_set_kv(gauge, radio, kv, key, negate=False, is_float=False):
        """Safely set a gauge from a key-value dict.

        キーバリュー辞書からゲージ値を安全に設定する。"""
        val_str = kv.get(key)
        if val_str is None:
            return
        try:
            val = float(val_str) if is_float else int(val_str)
            if negate:
                val = -val
            gauge.labels(radio=radio).set(val)
        except (ValueError, TypeError):
            pass

    def _logout(self):
        """Logout from CGI session.

        CGI セッションからログアウトする。"""
        if self._sid:
            try:
                self._request({"opcode": "logout", "sid": self._sid})
            except Exception:
                pass
            self._sid = None
