"""
USB Printer Interrogation Engine
Dedicated strictly to local USB-connected printers (USB001, USB004, USB010, DOT4, etc.).
Uses native Windows winspool.drv, Win32 Spooler APIs, and Windows Registry via standard ctypes & winreg.
Zero external dependencies!
"""

import os
import re
import sys
import ctypes
from ctypes import wintypes
import winreg
from typing import List, Dict, Any, Optional, Tuple


# --- Win32 Spooler Structures ---

class PRINTER_INFO_2(ctypes.Structure):
    _fields_ = [
        ('pServerName', wintypes.LPWSTR),
        ('pPrinterName', wintypes.LPWSTR),
        ('pShareName', wintypes.LPWSTR),
        ('pPortName', wintypes.LPWSTR),
        ('pDriverName', wintypes.LPWSTR),
        ('pComment', wintypes.LPWSTR),
        ('pLocation', wintypes.LPWSTR),
        ('pDevMode', ctypes.c_void_p),
        ('pSepFile', wintypes.LPWSTR),
        ('pPrintProcessor', wintypes.LPWSTR),
        ('pDatatype', wintypes.LPWSTR),
        ('pParameters', wintypes.LPWSTR),
        ('pSecurityDescriptor', ctypes.c_void_p),
        ('Attributes', wintypes.DWORD),
        ('Priority', wintypes.DWORD),
        ('DefaultPriority', wintypes.DWORD),
        ('StartTime', wintypes.DWORD),
        ('UntilTime', wintypes.DWORD),
        ('Status', wintypes.DWORD),
        ('cJobs', wintypes.DWORD),
        ('AveragePPM', wintypes.DWORD),
    ]


class DOC_INFO_1(ctypes.Structure):
    _fields_ = [
        ('pDocName', wintypes.LPWSTR),
        ('pOutputFile', wintypes.LPWSTR),
        ('pDatatype', wintypes.LPWSTR),
    ]


class JOB_INFO_1(ctypes.Structure):
    _fields_ = [
        ('JobId', wintypes.DWORD),
        ('pPrinterName', wintypes.LPWSTR),
        ('pMachineName', wintypes.LPWSTR),
        ('pUserName', wintypes.LPWSTR),
        ('pDocument', wintypes.LPWSTR),
        ('pDatatype', wintypes.LPWSTR),
        ('pStatus', wintypes.LPWSTR),
        ('Status', wintypes.DWORD),
        ('Priority', wintypes.DWORD),
        ('Position', wintypes.DWORD),
        ('TotalPages', wintypes.DWORD),
        ('PagesPrinted', wintypes.DWORD),
        ('Submitted', wintypes.FILETIME),
    ]


# Win32 Printer Status Codes
STATUS_FLAGS = {
    0x00000001: "PAUSED",
    0x00000002: "ERROR",
    0x00000004: "PENDING_DELETION",
    0x00000008: "PAPER_JAM",
    0x00000010: "PAPER_OUT",
    0x00000020: "MANUAL_FEED",
    0x00000040: "PAPER_PROBLEM",
    0x00000080: "OFFLINE",
    0x00000100: "IO_ACTIVE",
    0x00000200: "BUSY",
    0x00000400: "PRINTING",
    0x00000800: "OUTPUT_BIN_FULL",
    0x00001000: "NOT_AVAILABLE",
    0x00002000: "WAITING",
    0x00004000: "PROCESSING",
    0x00008000: "INITIALIZING",
    0x00010000: "WARMING_UP",
    0x00020000: "TONER_LOW",
    0x00040000: "NO_TONER",
    0x00080000: "PAGE_PUNT",
    0x00100000: "USER_INTERVENTION",
    0x00200000: "OUT_OF_MEMORY",
    0x00400000: "DOOR_OPEN",
    0x01000000: "POWER_SAVE",
}


class USBPrinterScanner:
    """Specialized USB Printer Interrogation Engine."""

    @classmethod
    def get_usbprint_hardware_map(cls) -> Dict[str, Dict[str, str]]:
        """
        Scans HKLM\\SYSTEM\\CurrentControlSet\\Enum\\USBPRINT to get hardware
        vendor, device ID, and unique instance serial strings for USB printers.
        """
        hw_map = {}
        try:
            key_path = r"SYSTEM\CurrentControlSet\Enum\USBPRINT"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
                num_subkeys = winreg.QueryInfoKey(k)[0]
                for i in range(num_subkeys):
                    dev_id = winreg.EnumKey(k, i)
                    with winreg.OpenKey(k, dev_id) as dk:
                        num_inst = winreg.QueryInfoKey(dk)[0]
                        for j in range(num_inst):
                            inst_id = winreg.EnumKey(dk, j)
                            with winreg.OpenKey(dk, inst_id) as ik:
                                try:
                                    mfg, _ = winreg.QueryValueEx(ik, "Mfg")
                                except Exception:
                                    mfg = ""
                                try:
                                    friendly, _ = winreg.QueryValueEx(ik, "FriendlyName")
                                except Exception:
                                    friendly = ""
                                try:
                                    hardware_id, _ = winreg.QueryValueEx(ik, "HardwareID")
                                    if isinstance(hardware_id, list) and hardware_id:
                                        hardware_id = hardware_id[0]
                                except Exception:
                                    hardware_id = ""

                                hw_map[dev_id.upper()] = {
                                    "device_id": dev_id,
                                    "instance_id": inst_id,
                                    "mfg": mfg,
                                    "friendly": friendly,
                                    "hardware_id": str(hardware_id)
                                }
        except Exception:
            pass
        return hw_map

    @classmethod
    def enumerate_usb_printers(cls) -> List[Dict[str, Any]]:
        """
        Enumerates all locally connected USB printers using Windows winspool.drv.
        Filters strictly for printers on USB ports (USB001, USB002, DOT4, etc.).
        """
        usb_printers = []
        hw_map = cls.get_usbprint_hardware_map()

        try:
            winspool = ctypes.WinDLL('winspool.drv')
            PRINTER_ENUM_LOCAL = 0x00000002
            PRINTER_ENUM_CONNECTIONS = 0x00000004
            flags = PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS

            needed = wintypes.DWORD()
            returned = wintypes.DWORD()
            winspool.EnumPrintersW(flags, None, 2, None, 0, ctypes.byref(needed), ctypes.byref(returned))
            if needed.value > 0:
                buf = (ctypes.c_byte * needed.value)()
                if winspool.EnumPrintersW(flags, None, 2, buf, needed.value, ctypes.byref(needed), ctypes.byref(returned)):
                    ptr = ctypes.cast(buf, ctypes.POINTER(PRINTER_INFO_2))
                    for i in range(returned.value):
                        p = ptr[i]
                        port = p.pPortName or ""
                        name = p.pPrinterName or ""
                        driver = p.pDriverName or ""

                        # Check if strictly USB or DOT4 port
                        is_usb = bool(
                            port.upper().startswith("USB") or
                            "USB" in port.upper() or
                            port.upper().startswith("DOT4") or
                            "DOT4" in port.upper()
                        )

                        if is_usb:
                            # Parse status flags
                            status_code = p.Status
                            status_msgs = []
                            for flag_bit, flag_text in STATUS_FLAGS.items():
                                if status_code & flag_bit:
                                    status_msgs.append(flag_text)

                            # Determine friendly status
                            if not status_msgs:
                                friendly_status = "ONLINE"
                            elif "OFFLINE" in status_msgs:
                                friendly_status = "OFFLINE"
                            elif "PAPER_JAM" in status_msgs or "DOOR_OPEN" in status_msgs or "NO_TONER" in status_msgs:
                                friendly_status = "ATTENTION"
                            else:
                                friendly_status = status_msgs[0]

                            # Match hardware info
                            mfg = "Generic / OEM"
                            serial_num = ""
                            dev_key = name.replace(" ", "").upper()
                            for k, v in hw_map.items():
                                if k in dev_key or any(part in k for part in dev_key.split("-")):
                                    mfg = v.get("mfg") or mfg
                                    serial_num = v.get("instance_id") or ""
                                    break

                            usb_printers.append({
                                "name": name,
                                "port": port,
                                "driver": driver,
                                "status": friendly_status,
                                "raw_status": status_code,
                                "status_details": ", ".join(status_msgs) if status_msgs else "Ready",
                                "active_jobs": p.cJobs,
                                "location": p.pLocation or "Local Workstation",
                                "comment": p.pComment or "",
                                "mfg": mfg,
                                "serial_number": serial_num,
                                "is_usb": True
                            })
        except Exception:
            pass

        # Registry fallback if winspool was restricted
        if not usb_printers:
            usb_printers = cls._registry_usb_fallback()

        return usb_printers

    @classmethod
    def get_discovered_usb_printers_with_fleet_status(cls, existing_ports: set) -> List[Dict[str, Any]]:
        """
        Discovers all USB printers and flags whether they are already added to the active fleet.
        """
        printers = cls.enumerate_usb_printers()
        clean_ports = {str(port).strip().upper() for port in existing_ports}
        for p in printers:
            p["already_in_fleet"] = p.get("port", "").strip().upper() in clean_ports
        return printers

    @classmethod
    def _registry_usb_fallback(cls) -> List[Dict[str, Any]]:
        """Fallback to read USB printers from Windows registry if spooler is busy."""
        printers = []
        try:
            key_path = r"SYSTEM\CurrentControlSet\Control\Print\Printers"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
                num_subkeys = winreg.QueryInfoKey(k)[0]
                for i in range(num_subkeys):
                    sub_name = winreg.EnumKey(k, i)
                    with winreg.OpenKey(k, sub_name) as pk:
                        try:
                            port, _ = winreg.QueryValueEx(pk, "Port")
                        except Exception:
                            port = ""
                        try:
                            driver, _ = winreg.QueryValueEx(pk, "Printer Driver")
                        except Exception:
                            driver = ""
                        try:
                            status_val, _ = winreg.QueryValueEx(pk, "Status")
                        except Exception:
                            status_val = 0

                        if "USB" in port.upper() or "DOT4" in port.upper():
                            printers.append({
                                "name": sub_name,
                                "port": port,
                                "driver": driver,
                                "status": "ONLINE" if status_val == 0 else "OFFLINE",
                                "raw_status": status_val,
                                "status_details": "Ready" if status_val == 0 else "Offline / Disconnected",
                                "active_jobs": 0,
                                "location": "Local Workstation",
                                "comment": "",
                                "mfg": "OEM USB",
                                "serial_number": "",
                                "is_usb": True
                            })
        except Exception:
            pass
        return printers

    @classmethod
    def query_usb_hardware_counter(cls, printer_name: str, timeout_sec: float = 1.5) -> Tuple[Optional[int], str]:
        """
        Queries USB printer hardware directly for lifetime page count.
        Sends PJL commands in RAW mode over the active Windows printer spooler handle.
        """
        try:
            winspool = ctypes.WinDLL('winspool.drv')
            hPrinter = wintypes.HANDLE()

            if not winspool.OpenPrinterW(printer_name, ctypes.byref(hPrinter), None):
                return None, "Could not open printer handle"

            try:
                # 1. Try reading standard spooler TotalPagesPrinted from registry/driver data
                pType = wintypes.DWORD()
                dataNeeded = wintypes.DWORD()
                buf = (ctypes.c_byte * 64)()
                if winspool.GetPrinterDataW(hPrinter, "TotalPagesPrinted", ctypes.byref(pType), buf, 64, ctypes.byref(dataNeeded)) == 0:
                    val = int.from_bytes(buf[:dataNeeded.value], 'little')
                    if val > 0:
                        return val, "Spooler TotalPagesPrinted"

                # 2. Try bidirectional PJL INFO PAGECOUNT query
                doc_info = DOC_INFO_1()
                doc_info.pDocName = "CounterQuery"
                doc_info.pOutputFile = None
                doc_info.pDatatype = "RAW"

                job_id = winspool.StartDocPrinterW(hPrinter, 1, ctypes.byref(doc_info))
                if job_id > 0:
                    try:
                        winspool.StartPagePrinter(hPrinter)
                        pjl_cmd = b"\x1b%-12345X@PJL\r\n@PJL INFO PAGECOUNT\r\n\x1b%-12345X\r\n"
                        bytes_written = wintypes.DWORD()
                        winspool.WritePrinter(hPrinter, pjl_cmd, len(pjl_cmd), ctypes.byref(bytes_written))
                        winspool.EndPagePrinter(hPrinter)

                        # Read response
                        read_buf = (ctypes.c_byte * 1024)()
                        bytes_read = wintypes.DWORD()
                        if winspool.ReadPrinter(hPrinter, read_buf, 1024, ctypes.byref(bytes_read)) and bytes_read.value > 0:
                            raw_resp = bytes(read_buf[:bytes_read.value]).decode("utf-8", errors="ignore")
                            m = re.search(r'(?i)pagecount\s*\r?\n\s*(\d+)', raw_resp)
                            if m:
                                return int(m.group(1)), "USB PJL Direct (Port Response)"
                    finally:
                        winspool.EndDocPrinterW(hPrinter)
            finally:
                winspool.ClosePrinter(hPrinter)
        except Exception as e:
            return None, str(e)

        return None, "Not exposed via USB PJL"

    @classmethod
    def get_usb_spooler_jobs(cls, printer_name: str) -> List[Dict[str, Any]]:
        """Retrieves active or queued print jobs on the specified USB printer."""
        jobs = []
        try:
            winspool = ctypes.WinDLL('winspool.drv')
            hPrinter = wintypes.HANDLE()
            if winspool.OpenPrinterW(printer_name, ctypes.byref(hPrinter), None):
                try:
                    needed = wintypes.DWORD()
                    returned = wintypes.DWORD()
                    winspool.EnumJobsW(hPrinter, 0, 100, 1, None, 0, ctypes.byref(needed), ctypes.byref(returned))
                    if needed.value > 0:
                        buf = (ctypes.c_byte * needed.value)()
                        if winspool.EnumJobsW(hPrinter, 0, 100, 1, buf, needed.value, ctypes.byref(needed), ctypes.byref(returned)):
                            ptr = ctypes.cast(buf, ctypes.POINTER(JOB_INFO_1))
                            for i in range(returned.value):
                                j = ptr[i]
                                jobs.append({
                                    "job_id": j.JobId,
                                    "document": j.pDocument or "Untitled Document",
                                    "user": j.pUserName or "Current User",
                                    "status": j.pStatus or "Queued",
                                    "pages": j.TotalPages,
                                    "pages_printed": j.PagesPrinted,
                                    "submitted": str(j.Submitted.dwLowDateTime)
                                })
                finally:
                    winspool.ClosePrinter(hPrinter)
        except Exception:
            pass
        return jobs

