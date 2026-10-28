"""
Network & Local Printer Counter Engine
Pure Python standard library implementation - Zero external dependencies!
Supports:
1. SNMP v1 and SNMP v2c (Standard Printer-MIB, HP, Xerox, Canon, Ricoh, Lexmark, Brother)
2. PJL (Printer Job Language) over RAW TCP Port 9100
3. Canon Remote UI / RPS Port 8000 / HTTP EWS with PIN / General User Mode login
4. Generic Printer Web EWS (HP, Ricoh, Xerox, Kyocera, Brother) with SSL override
5. Windows Local Spooler / USB printers via PowerShell CIM/WMI
6. Fast Multi-Threaded Subnet Auto-Discovery
"""

import os
import re
import ssl
import json
import socket
import base64
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import subprocess
import concurrent.futures
from typing import Optional, Dict, Any, List, Tuple


# Standard Printer MIB OIDs for Lifetime Page Count
PRINTER_MIB_OIDS = [
    # Standard Printer MIB: prtMarkerLifeCount (index 1.1)
    "1.3.6.1.2.1.43.10.2.1.4.1.1",
    # Standard Printer MIB: prtMarkerLifeCount (index 1)
    "1.3.6.1.2.1.43.10.2.1.4.1",
    # Alternative marker count
    "1.3.6.1.2.1.43.10.2.1.4.1.2",
    # HP Printer MIB: Total Page Count
    "1.3.6.1.4.1.11.2.3.9.4.2.1.4.1.2.5.0",
    # Xerox / Lexmark Printer MIB: Total Impressions
    "1.3.6.1.4.1.2699.1.2.1.2.1.1.3.1",
    "1.3.6.1.4.1.253.8.53.13.2.1.6.1.20.1",
    # Kyocera / Brother / Ricoh alternate
    "1.3.6.1.4.1.1347.43.10.1.1.12.1.1",
    "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.5.10.1.0"
]

OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"
OID_DEVICE_DESCR = "1.3.6.1.2.1.25.3.2.1.3.1"
OID_SERIAL_NUM = "1.3.6.1.2.1.43.5.1.1.17.1"


# --- SNMP ASN.1 DER Low-Level Helpers (Zero External Dependency) ---

def _encode_asn1_len(length: int) -> bytes:
    if length < 128:
        return bytes([length])
    b = []
    while length > 0:
        b.insert(0, length & 0xFF)
        length >>= 8
    return bytes([0x80 | len(b)]) + bytes(b)


def _encode_oid(oid_str: str) -> bytes:
    parts = [int(p) for p in oid_str.strip('.').split('.')]
    res = bytes([parts[0] * 40 + parts[1]])
    for p in parts[2:]:
        vb = [p & 0x7F]
        p >>= 7
        while p > 0:
            vb.insert(0, 0x80 | (p & 0x7F))
            p >>= 7
        res += bytes(vb)
    return b'\x06' + _encode_asn1_len(len(res)) + res


def _build_snmp_get(community: str, oid_str: str, req_id: int = 1, snmp_version: int = 1) -> bytes:
    oid_bytes = _encode_oid(oid_str)
    varbind = b'\x30' + _encode_asn1_len(len(oid_bytes) + 2) + oid_bytes + b'\x05\x00'
    varbind_list = b'\x30' + _encode_asn1_len(len(varbind)) + varbind
    pdu_payload = bytes([0x02, 0x01, req_id & 0x7F, 0x02, 0x01, 0x00, 0x02, 0x01, 0x00]) + varbind_list
    pdu = b'\xa0' + _encode_asn1_len(len(pdu_payload)) + pdu_payload
    comm_bytes = community.encode('utf-8')
    comm_tlv = b'\x04' + _encode_asn1_len(len(comm_bytes)) + comm_bytes
    version_tlv = bytes([0x02, 0x01, snmp_version])  # 0 for SNMP v1, 1 for SNMP v2c
    snmp_payload = version_tlv + comm_tlv + pdu
    return b'\x30' + _encode_asn1_len(len(snmp_payload)) + snmp_payload


def _read_tlv(b: bytes, offset: int):
    if offset >= len(b):
        return None, b'', offset
    tag = b[offset]
    offset += 1
    if offset >= len(b):
        return None, b'', offset
    length = b[offset]
    offset += 1
    if length & 0x80:
        num_octets = length & 0x7F
        if offset + num_octets > len(b):
            return None, b'', offset
        length = int.from_bytes(b[offset:offset + num_octets], 'big')
        offset += num_octets
    if offset + length > len(b):
        val = b[offset:]
        return tag, val, len(b)
    val = b[offset:offset + length]
    return tag, val, offset + length


def _parse_snmp_value(data: bytes) -> Optional[Any]:
    try:
        tag, val, _ = _read_tlv(data, 0)
        _, _, off = _read_tlv(val, 0)
        _, _, off = _read_tlv(val, off)
        pdu_tag, pdu_val, _ = _read_tlv(val, off)
        _, _, pdu_off = _read_tlv(pdu_val, 0)
        _, err_status, pdu_off = _read_tlv(pdu_val, pdu_off)
        if int.from_bytes(err_status, 'big') != 0:
            return None
        _, _, pdu_off = _read_tlv(pdu_val, pdu_off)
        _, vbl_val, _ = _read_tlv(pdu_val, pdu_off)
        _, vb_val, _ = _read_tlv(vbl_val, 0)
        _, _, vb_off = _read_tlv(vb_val, 0)
        val_tag, value_bytes, _ = _read_tlv(vb_val, vb_off)
        if val_tag in (0x02, 0x41, 0x42, 0x46):  # Integer, Counter32, Gauge32, Counter64
            return int.from_bytes(value_bytes, 'big')
        elif val_tag == 0x04:  # Octet String
            return value_bytes.decode('utf-8', errors='ignore').strip()
    except Exception:
        pass
    return None


def _create_unverified_ssl_context() -> ssl.SSLContext:
    try:
        ctx = ssl._create_unverified_context()
    except Exception:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    if hasattr(ssl, "TLSVersion") and hasattr(ssl.TLSVersion, "MINIMUM_SUPPORTED"):
        try:
            ctx.minimum_version = ssl.TLSVersion.MINIMUM_SUPPORTED
        except Exception:
            pass
    if hasattr(ssl, "OP_LEGACY_SERVER_CONNECT"):
        ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
    try:
        ctx.set_ciphers("DEFAULT:@SECLEVEL=0:ALL:!aNULL:!eNULL")
    except Exception:
        pass
    return ctx


class PrinterScanner:
    """Core network and local printer interrogation engine."""

    @staticmethod
    def get_local_subnet() -> str:
        """Detects current workstation local IP and returns suggested /24 subnet range."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            parts = ip.split(".")
            return f"{parts[0]}.{parts[1]}.{parts[2]}.1-254"
        except Exception:
            return "192.168.1.1-254"

    @staticmethod
    def is_tcp_port_open(ip: str, port: int, timeout: float = 0.5) -> bool:
        """Quick non-blocking probe to check if a TCP port is open."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                return s.connect_ex((ip, port)) == 0
        except Exception:
            return False

    @staticmethod
    def query_snmp(
        ip: str,
        community: str = "public",
        timeout: float = 0.8
    ) -> Tuple[Optional[int], str, Optional[str], Optional[str]]:
        """
        Polls printer via SNMP (v2c, then v1).
        Returns: (counter_val, method_string, model_name, serial_number)
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        found_counter = None
        method_str = ""
        model_name = None
        serial_num = None

        try:
            # Query sysDescr / Model
            for ver in [1, 0]:
                try:
                    p = _build_snmp_get(community, OID_SYS_DESCR, req_id=10, snmp_version=ver)
                    sock.sendto(p, (ip, 161))
                    resp, _ = sock.recvfrom(4096)
                    val = _parse_snmp_value(resp)
                    if val and isinstance(val, str) and len(val) > 2:
                        model_name = val.split("\r")[0].split("\n")[0].strip()
                        break
                except Exception:
                    pass

            # Query Serial Number
            for ver in [1, 0]:
                try:
                    p = _build_snmp_get(community, OID_SERIAL_NUM, req_id=11, snmp_version=ver)
                    sock.sendto(p, (ip, 161))
                    resp, _ = sock.recvfrom(4096)
                    val = _parse_snmp_value(resp)
                    if val and isinstance(val, str) and len(val) > 1:
                        serial_num = val
                        break
                except Exception:
                    pass

            # Query Page Counter OIDs
            req_id = 20
            for ver in [1, 0]:
                ver_name = "v2c" if ver == 1 else "v1"
                for oid in PRINTER_MIB_OIDS:
                    try:
                        req_id += 1
                        pkt = _build_snmp_get(community, oid, req_id=req_id, snmp_version=ver)
                        sock.sendto(pkt, (ip, 161))
                        resp, _ = sock.recvfrom(4096)
                        val = _parse_snmp_value(resp)
                        if val is not None:
                            int_val = int(val) if isinstance(val, (int, str)) and str(val).isdigit() else 0
                            if int_val > 0:
                                found_counter = int_val
                                method_str = f"SNMP {ver_name} ({oid})"
                                break
                    except socket.timeout:
                        continue
                    except Exception:
                        continue
                if found_counter is not None:
                    break
        finally:
            sock.close()

        return found_counter, method_str, model_name, serial_num

    @staticmethod
    def query_snmp_toner(ip: str, community: str = "public", timeout: float = 0.8) -> Optional[Dict[str, int]]:
        """Queries standard SNMP Printer-MIB supply levels (Cyan, Magenta, Yellow, Black)."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        toner = {}
        colors = [(1, "black"), (2, "cyan"), (3, "magenta"), (4, "yellow")]
        try:
            for idx, col in colors:
                # Level
                p_cur = _build_snmp_get(community, f"1.3.6.1.2.1.43.11.1.1.9.1.{idx}", req_id=100 + idx, snmp_version=1)
                sock.sendto(p_cur, (ip, 161))
                resp, _ = sock.recvfrom(4096)
                cur_val = _parse_snmp_value(resp)
                if cur_val is not None and isinstance(cur_val, int) and cur_val >= 0:
                    # Max Capacity
                    p_max = _build_snmp_get(community, f"1.3.6.1.2.1.43.11.1.1.8.1.{idx}", req_id=110 + idx, snmp_version=1)
                    sock.sendto(p_max, (ip, 161))
                    resp_m, _ = sock.recvfrom(4096)
                    max_val = _parse_snmp_value(resp_m)
                    if max_val and isinstance(max_val, int) and max_val > 0:
                        pct = max(0, min(100, round((cur_val / max_val) * 100)))
                        toner[col] = pct
        except Exception:
            pass
        finally:
            sock.close()
        return toner if toner else None

    @staticmethod
    def query_pjl(ip: str, timeout: float = 1.2) -> Tuple[Optional[int], str, Optional[str]]:
        """Queries PJL (Printer Job Language) over TCP Port 9100."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        found_counter = None
        method_str = ""
        model_name = None

        try:
            sock.connect((ip, 9100))
            # Send PJL commands for pagecount and ID
            cmd = (
                b"\x1b%-12345X@PJL\r\n"
                b"@PJL INFO ID\r\n"
                b"@PJL INFO PAGECOUNT\r\n"
                b"\x1b%-12345X\r\n"
            )
            sock.sendall(cmd)
            data = sock.recv(4096)
            text = data.decode("utf-8", errors="ignore")

            m_id = re.search(r'@PJL\s+INFO\s+ID\s*\r?\n\s*"?([^"\r\n]+)"?', text, re.IGNORECASE)
            if m_id:
                model_name = m_id.group(1).strip()

            m_pc = re.search(r'(?i)pagecount\s*\r?\n\s*(\d+)', text)
            if m_pc:
                found_counter = int(m_pc.group(1))
                method_str = "PJL (Port 9100)"
            else:
                for line in text.splitlines():
                    line = line.strip()
                    if line.isdigit() and int(line) > 0:
                        found_counter = int(line)
                        method_str = "PJL (Port 9100)"
                        break
        except Exception:
            pass
        finally:
            sock.close()

        return found_counter, method_str, model_name

    @staticmethod
    def query_http_ews(
        ip: str,
        pin: str = "1234",
        username: str = "",
        timeout: float = 3.0
    ) -> Tuple[Optional[int], str, Optional[str], Optional[Dict[str, int]]]:
        """
        Polls printer via Embedded Web Server (HTTP/HTTPS).
        Includes Canon Remote UI / MF / RPS & generic HP/Ricoh/Brother/Xerox/Kyocera parsers.
        """
        clean_ip = ip.strip()
        ssl_ctx = _create_unverified_ssl_context()
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl_ctx),
            urllib.request.HTTPCookieProcessor(cookie_jar)
        )

        counter_val = None
        method_str = ""
        model_name = None
        toner = {}

        # 1. Canon Remote UI Check
        for proto in ["http", "https"]:
            base = f"{proto}://{clean_ip}"
            try:
                # Login attempt if PIN exists
                if pin:
                    login_url = f"{base}/checkLogin.cgi"
                    post_data = urllib.parse.urlencode({
                        "i0017": "2",
                        "i0019": username or "",
                        "i2101": pin
                    }).encode("utf-8")
                    req = urllib.request.Request(login_url, data=post_data, headers={
                        "User-Agent": "Mozilla/5.0",
                        "Referer": f"{base}/login.html"
                    })
                    try:
                        opener.open(req, timeout=timeout)
                    except Exception:
                        pass

                # Try counter endpoints
                for path in ["/d_counter.html", "/counter.html", "/m_counter.html", "/portal_top.html"]:
                    try:
                        req = urllib.request.Request(f"{base}{path}", headers={"User-Agent": "Mozilla/5.0"})
                        with opener.open(req, timeout=timeout) as resp:
                            html = resp.read().decode("utf-8", errors="ignore")

                            # Look for Total counter
                            m1 = re.search(r'101:\s*Total\s*1\s*</th>\s*<td[^>]*>\s*(\d+)\s*</td>', html, re.IGNORECASE) or \
                                 re.search(r'Total(?:\s*1)?\s*</th>\s*<td[^>]*>\s*(\d+)\s*</td>', html, re.IGNORECASE) or \
                                 re.search(r'(?:total\s*impressions|total\s*pages|total\s*page\s*count|total\s*counter)[^\d<]{1,30}(\d{1,9})', html, re.IGNORECASE)
                            if m1:
                                val = int(m1.group(1))
                                if val > 0:
                                    counter_val = val
                                    method_str = f"Web EWS ({proto.upper()}:{path})"

                            # Look for Toner in Canon MF HTML
                            m_blk = re.search(r'id=["\']black["\'][^>]*></div></div></td>\s*<td[^>]*>\s*(\d+)\s*%', html, re.IGNORECASE)
                            if m_blk:
                                toner["black"] = int(m_blk.group(1))

                            m_mod = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
                            if m_mod and "login" not in m_mod.group(1).lower():
                                clean_t = m_mod.group(1).replace("Remote UI", "").replace("Portal", "").strip(" :-\t")
                                if clean_t and len(clean_t) > 2:
                                    model_name = clean_t

                            if counter_val is not None:
                                break
                    except Exception:
                        continue
                if counter_val is not None:
                    break
            except Exception:
                continue

        # 2. Generic HTTP Endpoints (HP, Xerox, Brother, Ricoh)
        if counter_val is None:
            generic_paths = [
                "/hp/device/this.cntPage",
                "/devicestatus.html",
                "/status.html",
                "/info_configuration.html",
                "/general/status.html"
            ]
            for proto in ["http", "https"]:
                for path in generic_paths:
                    try:
                        req = urllib.request.Request(f"{proto}://{clean_ip}{path}", headers={"User-Agent": "Mozilla/5.0"})
                        with opener.open(req, timeout=timeout) as resp:
                            html = resp.read().decode("utf-8", errors="ignore")
                            m = re.search(r'(?:total\s*impressions|total\s*pages|total\s*page\s*count|total\s*counter|total\s*count)[^\d<]{1,30}(\d{1,9})', html, re.IGNORECASE)
                            if m:
                                val = int(m.group(1))
                                if val > 0:
                                    counter_val = val
                                    method_str = f"Printer Web EWS ({proto.upper()}:{path})"
                                    break
                    except Exception:
                        continue
                if counter_val is not None:
                    break

        return counter_val, method_str, model_name, (toner if toner else None)

    @classmethod
    def poll_printer(
        cls,
        ip: str,
        community: str = "public",
        pin: str = "1234",
        username: str = "",
        protocol_pref: str = "AUTO",
        timeout: float = 2.5
    ) -> Dict[str, Any]:
        """
        Unified multi-protocol polling for a single printer.
        Tries SNMP -> PJL -> HTTP based on preference or AUTO.
        """
        clean_ip = ip.strip()
        result = {
            "ip": clean_ip,
            "status": "OFFLINE",
            "counter": 0,
            "method": "",
            "model": "",
            "serial": "",
            "toner": {},
            "error": ""
        }

        # Check if host responds to common ports first
        has_9100 = cls.is_tcp_port_open(clean_ip, 9100, timeout=0.4)
        has_80 = cls.is_tcp_port_open(clean_ip, 80, timeout=0.4)
        has_443 = cls.is_tcp_port_open(clean_ip, 443, timeout=0.4)
        has_8000 = cls.is_tcp_port_open(clean_ip, 8000, timeout=0.4)

        counter = None
        method = ""
        model = None
        serial = None
        toner = {}

        # 1. SNMP Query (UDP port 161)
        if protocol_pref in ("AUTO", "SNMP"):
            c, m, mod, ser = cls.query_snmp(clean_ip, community=community, timeout=min(timeout, 1.2))
            if c:
                counter = c
                method = m
            if mod:
                model = mod
            if ser:
                serial = ser

            # Get Toner via SNMP
            snmp_toner = cls.query_snmp_toner(clean_ip, community=community, timeout=0.8)
            if snmp_toner:
                toner.update(snmp_toner)

        # 2. PJL Query (Port 9100)
        if counter is None and (protocol_pref in ("AUTO", "PJL")) and has_9100:
            c, m, mod = cls.query_pjl(clean_ip, timeout=min(timeout, 1.5))
            if c:
                counter = c
                method = m
            if mod and not model:
                model = mod

        # 3. HTTP / Canon Remote UI Query
        if counter is None and (protocol_pref in ("AUTO", "HTTP")) and (has_80 or has_443 or has_8000):
            c, m, mod, t = cls.query_http_ews(clean_ip, pin=pin, username=username, timeout=timeout)
            if c:
                counter = c
                method = m
            if mod and not model:
                model = mod
            if t:
                toner.update(t)

        if counter is not None and counter > 0:
            result["status"] = "ONLINE"
            result["counter"] = counter
            result["method"] = method
            result["model"] = model or ""
            result["serial"] = serial or ""
            result["toner"] = toner
        elif has_9100 or has_80 or has_443 or has_8000:
            result["status"] = "REACHABLE_NO_COUNTER"
            result["model"] = model or ""
            result["serial"] = serial or ""
            result["error"] = "Printer reachable on network, but page count counter protocol was not enabled or protected."
        else:
            result["status"] = "OFFLINE"
            result["error"] = "Printer offline or unreachable on IP."

        return result

    @classmethod
    def get_local_windows_printers(cls) -> List[Dict[str, Any]]:
        """Queries local Windows installed printers & queues via PowerShell CIM."""
        printers = []
        try:
            ps_cmd = (
                "Get-CimInstance -ClassName Win32_Printer | "
                "Select-Object Name, PortName, DriverName, PrinterStatus, DeviceID, Shared, Local | "
                "ConvertTo-Json -Compress"
            )
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=5
            )
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for p in data:
                    printers.append({
                        "name": p.get("Name", "Unknown"),
                        "port": p.get("PortName", ""),
                        "driver": p.get("DriverName", ""),
                        "device_id": p.get("DeviceID", ""),
                        "is_local": p.get("Local", True)
                    })
        except Exception:
            pass
        return printers

    @classmethod
    def scan_ip_range(
        cls,
        ip_range_str: str,
        community: str = "public",
        pin: str = "1234",
        max_threads: int = 15,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        Scans a range of IP addresses (e.g. 192.168.1.1-192.168.1.254 or 192.168.1.0/24).
        Discovers printers and queries counters.
        """
        ips = cls._parse_ip_range(ip_range_str)
        if not ips:
            return []

        results = []
        total = len(ips)
        completed = 0

        def _worker(ip):
            res = cls.poll_printer(ip, community=community, pin=pin, timeout=1.8)
            return res

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            future_to_ip = {executor.submit(_worker, ip): ip for ip in ips}
            for future in concurrent.futures.as_completed(future_to_ip):
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
                try:
                    res = future.result()
                    if res["status"] in ("ONLINE", "REACHABLE_NO_COUNTER"):
                        results.append(res)
                except Exception:
                    pass

        return results

    @staticmethod
    def _parse_ip_range(range_str: str) -> List[str]:
        """Parses CIDR (192.168.1.0/24), Range (192.168.1.10-50), or comma-separated list."""
        s = range_str.strip()
        ips = []

        # Comma-separated list
        if "," in s:
            for part in s.split(","):
                ips.extend(PrinterScanner._parse_ip_range(part.strip()))
            return list(dict.fromkeys(ips))

        # CIDR format: 192.168.1.0/24
        if "/" in s:
            try:
                import ipaddress
                net = ipaddress.ip_network(s, strict=False)
                return [str(ip) for ip in net.hosts()]
            except Exception:
                return []

        # Hyphen range: 192.168.1.1-192.168.1.50 or 192.168.1.1-50
        if "-" in s:
            parts = s.split("-")
            start_ip = parts[0].strip()
            end_part = parts[1].strip()

            start_octets = start_ip.split(".")
            if len(start_octets) == 4:
                prefix = ".".join(start_octets[:3])
                start_num = int(start_octets[3])
                if "." in end_part:
                    end_num = int(end_part.split(".")[3])
                else:
                    end_num = int(end_part)
                start_num, end_num = min(start_num, end_num), max(start_num, end_num)
                return [f"{prefix}.{i}" for i in range(start_num, end_num + 1)]

        # Single IP
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', s):
            return [s]

        return []

