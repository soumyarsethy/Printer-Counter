"""
Printer Counter - Windows Portable Application
Developed by Soumya Ranjan Sethy
Version 2.2.0 - Auto-Discovery Dual Fleet Edition (USB & Network Printers)
Features Interactive In-Section Auto-Discovery for both USB and Network Printers,
Date Range Filtering, Total Print Till Date, and Comprehensive Audit Export.
"""

import os
import sys
import json
import queue
import threading
import webbrowser
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Persistent App Directory
def get_app_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_app_dir()
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.version import (
    APP_NAME, APP_VERSION, APP_EDITION, APP_RELEASE_DATE,
    APP_DEVELOPER, CHANGELOG, get_version_string, get_developer_credit
)
from core.db import init_db, Database
from core.usb_scanner import USBPrinterScanner
from core.scanner import PrinterScanner
from core.exporter import FleetReportExporter

# Windows High-DPI Support
try:
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass


class AutoDiscoverUSBDialog(tk.Toplevel):
    """Dedicated interactive Auto-Discovery dialog for USB Printers."""
    def __init__(self, parent, on_imported_callback=None):
        super().__init__(parent)
        self.title("Auto-Discover USB Printers - " + get_developer_credit())
        self.geometry("820x500")
        self.minsize(700, 400)
        self.transient(parent)
        self.grab_set()

        self.on_imported_callback = on_imported_callback
        self.discovered_list = []
        self.setup_ui()
        self.start_usb_scan()

    def setup_ui(self):
        # Header
        hdr = tk.Frame(self, bg="#0f172a", height=50)
        hdr.pack(fill=tk.X, side=tk.TOP)
        tk.Label(hdr, text="🔍 USB PRINTER AUTO-DISCOVERY", font=("Segoe UI", 11, "bold"), bg="#0f172a", fg="white").pack(side=tk.LEFT, padx=14, pady=10)
        tk.Label(hdr, text="Probes USB Ports (USB001-USB020, DOT4) & PnP Hardware", font=("Segoe UI", 8), bg="#0f172a", fg="#94a3b8").pack(side=tk.LEFT, pady=12)

        self.lbl_status = tk.Label(hdr, text="Scanning...", font=("Segoe UI", 9, "bold"), bg="#0f172a", fg="#38bdf8")
        self.lbl_status.pack(side=tk.RIGHT, padx=14, pady=10)

        # Toolbar
        t_bar = ttk.Frame(self, padding="8")
        t_bar.pack(fill=tk.X)

        ttk.Button(t_bar, text="🔄 Re-Scan USB Ports", style="Accent.TButton", command=self.start_usb_scan).pack(side=tk.LEFT, padx=4)
        ttk.Button(t_bar, text="➕ Import Selected to USB Fleet", style="Success.TButton", command=self.import_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(t_bar, text="Select All", command=self.select_all).pack(side=tk.LEFT, padx=4)

        # Table
        tree_frame = ttk.Frame(self, padding="8")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("status", "port", "name", "mfg", "driver", "fleet_state", "serial")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="extended")
        self.tree.heading("status", text="Connection")
        self.tree.heading("port", text="USB Port")
        self.tree.heading("name", text="Discovered Printer Name")
        self.tree.heading("mfg", text="Manufacturer")
        self.tree.heading("driver", text="Driver Model")
        self.tree.heading("fleet_state", text="Fleet Status")
        self.tree.heading("serial", text="Hardware Serial / Instance")

        self.tree.column("status", width=90, anchor=tk.CENTER)
        self.tree.column("port", width=80, anchor=tk.CENTER)
        self.tree.column("name", width=190)
        self.tree.column("mfg", width=95, anchor=tk.CENTER)
        self.tree.column("driver", width=160)
        self.tree.column("fleet_state", width=110, anchor=tk.CENTER)
        self.tree.column("serial", width=160)

        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.tag_configure("ONLINE", foreground="#15803d")
        self.tree.tag_configure("OFFLINE", foreground="#b91c1c")
        self.tree.tag_configure("IN_FLEET", foreground="#0369a1")

        # Bottom Bar
        b_bar = ttk.Frame(self, padding="10")
        b_bar.pack(fill=tk.X)
        self.lbl_info = ttk.Label(b_bar, text="Scanning for connected USB printers...")
        self.lbl_info.pack(side=tk.LEFT)
        ttk.Button(b_bar, text="Close", command=self.destroy).pack(side=tk.RIGHT)

    def start_usb_scan(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.lbl_status.config(text="Scanning USB Ports...", fg="#38bdf8")
        self.lbl_info.config(text="Probing Win32 print subsystem and USBPRINT registry devices...")

        def _worker():
            existing = {p["identifier"].upper() for p in Database.get_printers(printer_type="USB")}
            discovered = USBPrinterScanner.get_discovered_usb_printers_with_fleet_status(existing)
            self.discovered_list = discovered
            self.after(0, lambda: self.render_results(discovered))

        threading.Thread(target=_worker, daemon=True).start()

    def render_results(self, discovered):
        for idx, p in enumerate(discovered):
            status = p.get("status", "ONLINE")
            status_lbl = "🟢 READY" if status == "ONLINE" else "🔴 OFFLINE"
            in_fleet = p.get("already_in_fleet", False)
            fleet_lbl = "✅ In Fleet" if in_fleet else "🆕 New Device"
            tag = "IN_FLEET" if in_fleet else status

            self.tree.insert("", tk.END, iid=str(idx), values=(
                status_lbl,
                p.get("port", ""),
                p.get("name", ""),
                p.get("mfg", ""),
                p.get("driver", ""),
                fleet_lbl,
                p.get("serial_number", "-") or "-"
            ), tags=(tag,))

        self.lbl_status.config(text=f"Found {len(discovered)} USB Devices", fg="#4ade80")
        self.lbl_info.config(text=f"Detected {len(discovered)} local USB printers. Select devices and click 'Import Selected to USB Fleet'.")

    def select_all(self):
        self.tree.selection_set(self.tree.get_children())

    def import_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select at least one USB printer to import.", parent=self)
            return

        to_add = [self.discovered_list[int(i)] for i in sel]
        added = Database.sync_detected_usb_printers(to_add)

        if self.on_imported_callback:
            self.on_imported_callback()

        messagebox.showinfo("Success", f"Imported/Synchronized {len(to_add)} USB printers into active fleet!", parent=self)
        self.destroy()


class AutoDiscoverNetworkDialog(tk.Toplevel):
    """Dedicated interactive Auto-Discovery dialog for Network Printers."""
    def __init__(self, parent, on_imported_callback=None):
        super().__init__(parent)
        self.title("Auto-Discover Network Printers - " + get_developer_credit())
        self.geometry("860x540")
        self.minsize(740, 420)
        self.transient(parent)
        self.grab_set()

        self.on_imported_callback = on_imported_callback
        self.discovered_list = []
        self.setup_ui()

    def setup_ui(self):
        # Header
        hdr = tk.Frame(self, bg="#0f172a", height=50)
        hdr.pack(fill=tk.X, side=tk.TOP)
        tk.Label(hdr, text="🔍 NETWORK PRINTER AUTO-DISCOVERY", font=("Segoe UI", 11, "bold"), bg="#0f172a", fg="white").pack(side=tk.LEFT, padx=14, pady=10)
        tk.Label(hdr, text="Multithreaded Subnet Scanner (SNMP v1/v2c, PJL, HTTP)", font=("Segoe UI", 8), bg="#0f172a", fg="#94a3b8").pack(side=tk.LEFT, pady=12)

        self.lbl_status = tk.Label(hdr, text="Ready", font=("Segoe UI", 9, "bold"), bg="#0f172a", fg="#38bdf8")
        self.lbl_status.pack(side=tk.RIGHT, padx=14, pady=10)

        # Control Box
        ctrl = ttk.LabelFrame(self, text="Subnet Configuration", padding="10")
        ctrl.pack(fill=tk.X, padx=10, pady=8)

        # Auto-detect local subnet
        suggested_subnet = PrinterScanner.get_local_subnet()

        ttk.Label(ctrl, text="IP Range / Subnet:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, padx=6)
        self.ent_range = ttk.Entry(ctrl, width=24)
        self.ent_range.grid(row=0, column=1, padx=6)
        self.ent_range.insert(0, suggested_subnet)

        ttk.Label(ctrl, text="SNMP Community:").grid(row=0, column=2, sticky=tk.W, padx=6)
        self.ent_comm = ttk.Entry(ctrl, width=12)
        self.ent_comm.grid(row=0, column=3, padx=6)
        self.ent_comm.insert(0, "public")

        ttk.Label(ctrl, text="Threads:").grid(row=0, column=4, sticky=tk.W, padx=6)
        self.ent_threads = ttk.Spinbox(ctrl, from_=1, to=50, width=5)
        self.ent_threads.grid(row=0, column=5, padx=6)
        self.ent_threads.set("15")

        self.btn_start = ttk.Button(ctrl, text="🔍 Start Discovery", style="Accent.TButton", command=self.start_network_scan)
        self.btn_start.grid(row=0, column=6, padx=12)

        # Progress bar
        self.prog_bar = ttk.Progressbar(self, orient=tk.HORIZONTAL, mode='determinate')
        self.prog_bar.pack(fill=tk.X, padx=12, pady=(0, 6))

        # Toolbar
        t_bar = ttk.Frame(self, padding="4")
        t_bar.pack(fill=tk.X, padx=8)
        ttk.Button(t_bar, text="➕ Import Selected to Network Fleet", style="Success.TButton", command=self.import_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(t_bar, text="Select All", command=self.select_all).pack(side=tk.LEFT, padx=4)

        # Results Table
        tree_frame = ttk.Frame(self, padding="8")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("status", "ip", "counter", "model", "serial", "method", "fleet_state")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="extended")
        self.tree.heading("status", text="Status")
        self.tree.heading("ip", text="IP Address")
        self.tree.heading("counter", text="Total Counter Till Date")
        self.tree.heading("model", text="Detected Model")
        self.tree.heading("serial", text="Serial Number")
        self.tree.heading("method", text="Detected Protocol")
        self.tree.heading("fleet_state", text="Fleet Status")

        self.tree.column("status", width=85, anchor=tk.CENTER)
        self.tree.column("ip", width=115, anchor=tk.CENTER)
        self.tree.column("counter", width=140, anchor=tk.E)
        self.tree.column("model", width=200)
        self.tree.column("serial", width=110, anchor=tk.CENTER)
        self.tree.column("method", width=160)
        self.tree.column("fleet_state", width=105, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.tag_configure("ONLINE", foreground="#15803d")
        self.tree.tag_configure("IN_FLEET", foreground="#0369a1")

        # Bottom Bar
        b_bar = ttk.Frame(self, padding="10")
        b_bar.pack(fill=tk.X)
        self.lbl_info = ttk.Label(b_bar, text="Click 'Start Discovery' to scan your local network for printers.")
        self.lbl_info.pack(side=tk.LEFT)
        ttk.Button(b_bar, text="Close", command=self.destroy).pack(side=tk.RIGHT)

    def start_network_scan(self):
        rng = self.ent_range.get().strip()
        comm = self.ent_comm.get().strip() or "public"
        threads = int(self.ent_threads.get() or "15")

        if not rng:
            messagebox.showerror("Error", "Please specify an IP range or subnet.", parent=self)
            return

        self.btn_start.config(state=tk.DISABLED)
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.lbl_status.config(text="Scanning Subnet...", fg="#38bdf8")
        self.lbl_info.config(text=f"Scanning {rng} across SNMP & port 9100...")

        def _progress(done, total):
            pct = int((done / total) * 100) if total > 0 else 0
            self.after(0, lambda: self.prog_bar.config(value=pct))

        def _worker():
            existing_ips = {p["identifier"].strip() for p in Database.get_printers(printer_type="NETWORK")}
            results = PrinterScanner.scan_ip_range(rng, community=comm, max_threads=threads, progress_callback=_progress)
            self.discovered_list = results
            self.after(0, lambda: self.render_results(results, existing_ips))

        threading.Thread(target=_worker, daemon=True).start()

    def render_results(self, results, existing_ips):
        self.prog_bar["value"] = 100
        self.btn_start.config(state=tk.NORMAL)
        self.lbl_status.config(text=f"Found {len(results)} Printers", fg="#4ade80")
        self.lbl_info.config(text=f"Scan complete! Discovered {len(results)} network printers. Select devices and click 'Import Selected to Network Fleet'.")

        for idx, r in enumerate(results):
            ip = r["ip"]
            in_fleet = ip in existing_ips
            fleet_lbl = "✅ In Fleet" if in_fleet else "🆕 New Device"
            cnt_str = f"{r['counter']:,}" if r['counter'] > 0 else "-"
            tag = "IN_FLEET" if in_fleet else "ONLINE"

            self.tree.insert("", tk.END, iid=str(idx), values=(
                "🟢 ONLINE",
                ip,
                cnt_str,
                r.get("model") or "Network Printer",
                r.get("serial") or "-",
                r.get("method") or "-",
                fleet_lbl
            ), tags=(tag,))

    def select_all(self):
        self.tree.selection_set(self.tree.get_children())

    def import_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select network printers to import.", parent=self)
            return

        added = 0
        comm = self.ent_comm.get().strip() or "public"
        for i in sel:
            r = self.discovered_list[int(i)]
            ip = r["ip"]
            model = r.get("model") or "Network Printer"
            Database.save_network_printer({
                "name": f"{model} ({ip.split('.')[-1]})",
                "identifier": ip,
                "model": model,
                "serial_number": r.get("serial", ""),
                "community": comm
            })
            if r.get("counter", 0) > 0:
                p_obj = Database.get_printers(printer_type="NETWORK")
                cur = next((p for p in p_obj if p["identifier"] == ip), None)
                if cur:
                    Database.update_network_reading(cur["id"], r["counter"], model=model, serial=r.get("serial", ""), method=r.get("method", ""))
            added += 1

        if self.on_imported_callback:
            self.on_imported_callback()

        messagebox.showinfo("Success", f"Imported {added} network printers into your active fleet!", parent=self)
        self.destroy()


class AddNetworkPrinterDialog(tk.Toplevel):
    """Modal dialog to add or edit a Network printer manually."""
    def __init__(self, parent, printer_data=None, on_save_callback=None):
        super().__init__(parent)
        self.title("Edit Network Printer" if printer_data else "Add New Network Printer")
        self.geometry("480x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.printer_data = printer_data or {}
        self.on_save_callback = on_save_callback
        self.setup_ui()

    def setup_ui(self):
        pad_opts = {'padx': 12, 'pady': 6}
        frame = ttk.Frame(self, padding="16")
        frame.pack(fill=tk.BOTH, expand=True)

        r = 0
        ttk.Label(frame, text="Printer Name *:", font=("Segoe UI", 9, "bold")).grid(row=r, column=0, sticky=tk.W, **pad_opts)
        self.ent_name = ttk.Entry(frame, width=32)
        self.ent_name.grid(row=r, column=1, sticky=tk.W, **pad_opts)
        self.ent_name.insert(0, self.printer_data.get("name", ""))

        r += 1
        ttk.Label(frame, text="IP Address / Host *:", font=("Segoe UI", 9, "bold")).grid(row=r, column=0, sticky=tk.W, **pad_opts)
        self.ent_ip = ttk.Entry(frame, width=32)
        self.ent_ip.grid(row=r, column=1, sticky=tk.W, **pad_opts)
        self.ent_ip.insert(0, self.printer_data.get("identifier", ""))

        r += 1
        ttk.Label(frame, text="Department:").grid(row=r, column=0, sticky=tk.W, **pad_opts)
        self.ent_dept = ttk.Entry(frame, width=32)
        self.ent_dept.grid(row=r, column=1, sticky=tk.W, **pad_opts)
        self.ent_dept.insert(0, self.printer_data.get("department", "Accounts / Office"))

        r += 1
        ttk.Label(frame, text="Location / Desk:").grid(row=r, column=0, sticky=tk.W, **pad_opts)
        self.ent_loc = ttk.Entry(frame, width=32)
        self.ent_loc.grid(row=r, column=1, sticky=tk.W, **pad_opts)
        self.ent_loc.insert(0, self.printer_data.get("location", "Floor 1"))

        r += 1
        ttk.Label(frame, text="Model / Series:").grid(row=r, column=0, sticky=tk.W, **pad_opts)
        self.ent_model = ttk.Entry(frame, width=32)
        self.ent_model.grid(row=r, column=1, sticky=tk.W, **pad_opts)
        self.ent_model.insert(0, self.printer_data.get("model", ""))

        r += 1
        ttk.Label(frame, text="Protocol Preference:").grid(row=r, column=0, sticky=tk.W, **pad_opts)
        self.cmb_proto = ttk.Combobox(frame, values=["AUTO", "SNMP", "PJL", "HTTP"], state="readonly", width=30)
        self.cmb_proto.grid(row=r, column=1, sticky=tk.W, **pad_opts)
        self.cmb_proto.set(self.printer_data.get("protocol_pref", "AUTO"))

        r += 1
        ttk.Label(frame, text="SNMP Community:").grid(row=r, column=0, sticky=tk.W, **pad_opts)
        self.ent_comm = ttk.Entry(frame, width=32)
        self.ent_comm.grid(row=r, column=1, sticky=tk.W, **pad_opts)
        self.ent_comm.insert(0, self.printer_data.get("community", "public"))

        r += 1
        ttk.Label(frame, text="Canon Web PIN / Pwd:").grid(row=r, column=0, sticky=tk.W, **pad_opts)
        self.ent_pin = ttk.Entry(frame, width=32, show="*")
        self.ent_pin.grid(row=r, column=1, sticky=tk.W, **pad_opts)
        self.ent_pin.insert(0, self.printer_data.get("password", "1234"))

        r += 1
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=r, column=0, columnspan=2, pady=16)

        ttk.Button(btn_frame, text="Save Network Printer", style="Accent.TButton", command=self.save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

    def save(self):
        name = self.ent_name.get().strip()
        ip = self.ent_ip.get().strip()
        if not name or not ip:
            messagebox.showerror("Error", "Printer Name and IP Address are required!", parent=self)
            return

        data = {
            "id": self.printer_data.get("id"),
            "name": name,
            "identifier": ip,
            "department": self.ent_dept.get().strip(),
            "location": self.ent_loc.get().strip(),
            "model": self.ent_model.get().strip(),
            "protocol_pref": self.cmb_proto.get(),
            "community": self.ent_comm.get().strip() or "public",
            "password": self.ent_pin.get().strip()
        }

        Database.save_network_printer(data)
        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()


class UpdateUSBMeterDialog(tk.Toplevel):
    """Modal dialog to set baseline meter reading for USB printers."""
    def __init__(self, parent, printer_data, on_save_callback=None):
        super().__init__(parent)
        self.title(f"Update USB Meter - {printer_data['name']}")
        self.geometry("450x360")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.printer_data = printer_data
        self.on_save_callback = on_save_callback
        self.setup_ui()

    def setup_ui(self):
        frame = ttk.Frame(self, padding="16")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=self.printer_data['name'], font=("Segoe UI", 11, "bold")).pack(anchor=tk.W, pady=(0, 2))
        ttk.Label(frame, text=f"Port: {self.printer_data['identifier']} | Driver: {self.printer_data['driver']}", font=("Segoe UI", 9), foreground="#64748b").pack(anchor=tk.W, pady=(0, 12))

        lbl_frame = ttk.LabelFrame(frame, text="Meter Configuration", padding="12")
        lbl_frame.pack(fill=tk.X, pady=6)

        ttk.Label(lbl_frame, text="Physical Baseline Counter:").grid(row=0, column=0, sticky=tk.W, pady=6)
        self.ent_base = ttk.Entry(lbl_frame, width=20)
        self.ent_base.grid(row=0, column=1, sticky=tk.W, padx=8, pady=6)
        self.ent_base.insert(0, str(self.printer_data.get("baseline_counter", 0)))

        ttk.Label(lbl_frame, text="Accumulated Pages Printed:").grid(row=1, column=0, sticky=tk.W, pady=6)
        self.ent_accum = ttk.Entry(lbl_frame, width=20)
        self.ent_accum.grid(row=1, column=1, sticky=tk.W, padx=8, pady=6)
        self.ent_accum.insert(0, str(self.printer_data.get("accumulated_pages", 0)))

        ttk.Label(lbl_frame, text="Department:").grid(row=2, column=0, sticky=tk.W, pady=6)
        self.ent_dept = ttk.Entry(lbl_frame, width=20)
        self.ent_dept.grid(row=2, column=1, sticky=tk.W, padx=8, pady=6)
        self.ent_dept.insert(0, self.printer_data.get("department", "General Office"))

        ttk.Label(lbl_frame, text="Desk / Location:").grid(row=3, column=0, sticky=tk.W, pady=6)
        self.ent_loc = ttk.Entry(lbl_frame, width=20)
        self.ent_loc.grid(row=3, column=1, sticky=tk.W, padx=8, pady=6)
        self.ent_loc.insert(0, self.printer_data.get("location", "Local Desk"))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=16)

        ttk.Button(btn_frame, text="💾 Save Meter", style="Accent.TButton", command=self.save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=6)

    def save(self):
        try:
            base = int(self.ent_base.get().strip() or "0")
            accum = int(self.ent_accum.get().strip() or "0")
        except ValueError:
            messagebox.showerror("Error", "Counters must be valid numbers!", parent=self)
            return

        Database.update_usb_meter(
            self.printer_data["id"],
            base,
            accum,
            dept=self.ent_dept.get().strip(),
            loc=self.ent_loc.get().strip()
        )
        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()


class PrinterCounterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION} - {get_developer_credit()}")
        self.root.geometry("1150x700")
        self.root.minsize(1000, 620)

        self.queue = queue.Queue()

        today = datetime.now()
        first_of_month = today.replace(day=1)
        self.default_start = first_of_month.strftime("%Y-%m-%d")
        self.default_end = today.strftime("%Y-%m-%d")

        init_db()
        self.setup_styles()
        self.build_ui()

        # Initial background sync
        self.auto_sync_usb(silent=True)
        self.load_usb_table()
        self.load_network_table()

        self.root.after(100, self.process_queue)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#0f172a", foreground="white", relief="flat")
        style.map("Treeview.Heading", background=[('active', '#1e293b')])
        style.configure("Treeview", rowheight=26, font=("Segoe UI", 9), relief="flat")

        style.configure("Accent.TButton", font=("Segoe UI", 9, "bold"), background="#2563eb", foreground="white")
        style.map("Accent.TButton", background=[('active', '#1d4ed8')])

        style.configure("Success.TButton", font=("Segoe UI", 9, "bold"), background="#16a34a", foreground="white")
        style.map("Success.TButton", background=[('active', '#15803d')])

        style.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=[14, 6])

    def build_ui(self):
        # Top Header Bar
        hdr_frame = tk.Frame(self.root, bg="#0f172a", height=54)
        hdr_frame.pack(fill=tk.X, side=tk.TOP)

        lbl_icon = tk.Label(hdr_frame, text="🖨️", font=("Segoe UI", 16), bg="#0f172a")
        lbl_icon.pack(side=tk.LEFT, padx=(16, 4), pady=8)

        lbl_title = tk.Label(hdr_frame, text=APP_NAME.upper(), font=("Segoe UI", 12, "bold"), bg="#0f172a", fg="white")
        lbl_title.pack(side=tk.LEFT, pady=10)

        # Version Badge
        lbl_ver = tk.Label(hdr_frame, text=f"v{APP_VERSION}", font=("Segoe UI", 9, "bold"), bg="#2563eb", fg="white", padx=6, pady=1)
        lbl_ver.pack(side=tk.LEFT, padx=6, pady=12)

        # Developer Attribution Badge
        lbl_dev = tk.Label(hdr_frame, text=f"👨‍💻 {get_developer_credit()}", font=("Segoe UI", 9, "bold"), bg="#1e293b", fg="#38bdf8", padx=8, pady=2, relief="solid", bd=1)
        lbl_dev.pack(side=tk.LEFT, padx=10, pady=11)

        self.lbl_status = tk.Label(hdr_frame, text="Ready", font=("Segoe UI", 9, "bold"), bg="#0f172a", fg="#4ade80")
        self.lbl_status.pack(side=tk.RIGHT, padx=16, pady=10)

        # Notebook Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.tab_usb = ttk.Frame(self.notebook)
        self.tab_network = ttk.Frame(self.notebook)
        self.tab_discovery = ttk.Frame(self.notebook)
        self.tab_history = ttk.Frame(self.notebook)
        self.tab_about = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_usb, text="  🔌 USB Printers  ")
        self.notebook.add(self.tab_network, text="  🌐 Network Printers  ")
        self.notebook.add(self.tab_discovery, text="  🔍 Subnet Discovery  ")
        self.notebook.add(self.tab_history, text="  📜 Audit History  ")
        self.notebook.add(self.tab_about, text="  ℹ️ Version & Developer  ")

        self.build_usb_section()
        self.build_network_section()
        self.build_discovery_section()
        self.build_history_section()
        self.build_about_section()

    # =========================================================================
    # SECTION 1: USB PRINTERS
    # =========================================================================
    def build_usb_section(self):
        # Date Range Filter Bar
        df_frame = ttk.LabelFrame(self.tab_usb, text="📅 Date Range Filter (Calculates Range Print Count)", padding="8")
        df_frame.pack(fill=tk.X, padx=10, pady=(6, 4))

        ttk.Label(df_frame, text="From Date (YYYY-MM-DD):", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=4)
        self.ent_usb_start = ttk.Entry(df_frame, width=12)
        self.ent_usb_start.pack(side=tk.LEFT, padx=4)
        self.ent_usb_start.insert(0, self.default_start)

        ttk.Label(df_frame, text="To Date (YYYY-MM-DD):", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(12, 4))
        self.ent_usb_end = ttk.Entry(df_frame, width=12)
        self.ent_usb_end.pack(side=tk.LEFT, padx=4)
        self.ent_usb_end.insert(0, self.default_end)

        ttk.Button(df_frame, text="🔍 Apply Filter", style="Accent.TButton", command=self.load_usb_table).pack(side=tk.LEFT, padx=10)

        # Quick Range Presets
        ttk.Button(df_frame, text="Today", command=lambda: self.set_quick_date("USB", 0)).pack(side=tk.LEFT, padx=2)
        ttk.Button(df_frame, text="Last 7 Days", command=lambda: self.set_quick_date("USB", 7)).pack(side=tk.LEFT, padx=2)
        ttk.Button(df_frame, text="This Month", command=lambda: self.set_quick_date("USB", "month")).pack(side=tk.LEFT, padx=2)
        ttk.Button(df_frame, text="All Time", command=lambda: self.set_quick_date("USB", "all")).pack(side=tk.LEFT, padx=2)

        # KPI Stats Cards
        card_frame = ttk.Frame(self.tab_usb)
        card_frame.pack(fill=tk.X, padx=10, pady=(4, 6))

        self.card_usb_total = self.create_card(card_frame, "USB Printers", "0", "#0f172a", 0)
        self.card_usb_online = self.create_card(card_frame, "Connected / Ready", "0", "#16a34a", 1)
        self.card_usb_range = self.create_card(card_frame, "Date Range Prints", "+0", "#0284c7", 2)
        self.card_usb_lifetime = self.create_card(card_frame, "Total Print Till Date", "0", "#2563eb", 3)

        # Toolbar
        t_bar = ttk.Frame(self.tab_usb)
        t_bar.pack(fill=tk.X, padx=10, pady=4)

        # AUTO-DISCOVERY OPTION FOR USB
        ttk.Button(t_bar, text="🔍 Auto-Discover USB Printers", style="Accent.TButton", command=self.open_auto_discover_usb).pack(side=tk.LEFT, padx=3)
        ttk.Button(t_bar, text="🔄 Quick Sync", command=lambda: self.auto_sync_usb(silent=False)).pack(side=tk.LEFT, padx=3)
        ttk.Separator(t_bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        ttk.Button(t_bar, text="🔢 Set / Update Meter", command=self.open_usb_meter_dialog).pack(side=tk.LEFT, padx=3)
        ttk.Button(t_bar, text="⚡ Query USB Hardware", command=self.query_usb_hardware).pack(side=tk.LEFT, padx=3)

        # Export Button
        export_btn = ttk.Menubutton(t_bar, text="📥 Export USB Report")
        export_menu = tk.Menu(export_btn, tearoff=0)
        export_menu.add_command(label="Export to Excel (.xls XML)", command=lambda: self.export_fleet_report("USB", "excel"))
        export_menu.add_command(label="Export to CSV (.csv)", command=lambda: self.export_fleet_report("USB", "csv"))
        export_menu.add_command(label="View HTML Audit Report (Printable)", command=lambda: self.export_fleet_report("USB", "html"))
        export_btn["menu"] = export_menu
        export_btn.pack(side=tk.RIGHT, padx=3)

        # Treeview Table
        tree_frame = ttk.Frame(self.tab_usb)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        cols = ("status", "name", "port", "dept", "driver", "mfg", "range_count", "lifetime", "last_checked")
        self.tree_usb = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")

        self.tree_usb.heading("status", text="USB Status")
        self.tree_usb.heading("name", text="Printer Name")
        self.tree_usb.heading("port", text="USB Port")
        self.tree_usb.heading("dept", text="Department / Location")
        self.tree_usb.heading("driver", text="Driver Model")
        self.tree_usb.heading("mfg", text="Manufacturer")
        self.tree_usb.heading("range_count", text="Date Range Prints")
        self.tree_usb.heading("lifetime", text="Total Print Till Date")
        self.tree_usb.heading("last_checked", text="Last Checked")

        self.tree_usb.column("status", width=95, anchor=tk.CENTER)
        self.tree_usb.column("name", width=190)
        self.tree_usb.column("port", width=85, anchor=tk.CENTER)
        self.tree_usb.column("dept", width=140)
        self.tree_usb.column("driver", width=180)
        self.tree_usb.column("mfg", width=100, anchor=tk.CENTER)
        self.tree_usb.column("range_count", width=130, anchor=tk.E)
        self.tree_usb.column("lifetime", width=140, anchor=tk.E)
        self.tree_usb.column("last_checked", width=130, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_usb.yview)
        scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree_usb.xview)
        self.tree_usb.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree_usb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree_usb.tag_configure("ONLINE", foreground="#15803d")
        self.tree_usb.tag_configure("OFFLINE", foreground="#b91c1c")
        self.tree_usb.bind("<Double-1>", lambda e: self.open_usb_meter_dialog())

    # =========================================================================
    # SECTION 2: NETWORK PRINTERS
    # =========================================================================
    def build_network_section(self):
        # Date Range Filter Bar
        df_frame = ttk.LabelFrame(self.tab_network, text="📅 Date Range Filter (Calculates Range Print Count)", padding="8")
        df_frame.pack(fill=tk.X, padx=10, pady=(6, 4))

        ttk.Label(df_frame, text="From Date (YYYY-MM-DD):", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=4)
        self.ent_net_start = ttk.Entry(df_frame, width=12)
        self.ent_net_start.pack(side=tk.LEFT, padx=4)
        self.ent_net_start.insert(0, self.default_start)

        ttk.Label(df_frame, text="To Date (YYYY-MM-DD):", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(12, 4))
        self.ent_net_end = ttk.Entry(df_frame, width=12)
        self.ent_net_end.pack(side=tk.LEFT, padx=4)
        self.ent_net_end.insert(0, self.default_end)

        ttk.Button(df_frame, text="🔍 Apply Filter", style="Accent.TButton", command=self.load_network_table).pack(side=tk.LEFT, padx=10)

        # Quick Range Presets
        ttk.Button(df_frame, text="Today", command=lambda: self.set_quick_date("NET", 0)).pack(side=tk.LEFT, padx=2)
        ttk.Button(df_frame, text="Last 7 Days", command=lambda: self.set_quick_date("NET", 7)).pack(side=tk.LEFT, padx=2)
        ttk.Button(df_frame, text="This Month", command=lambda: self.set_quick_date("NET", "month")).pack(side=tk.LEFT, padx=2)
        ttk.Button(df_frame, text="All Time", command=lambda: self.set_quick_date("NET", "all")).pack(side=tk.LEFT, padx=2)

        # KPI Stats Cards
        card_frame = ttk.Frame(self.tab_network)
        card_frame.pack(fill=tk.X, padx=10, pady=(4, 6))

        self.card_net_total = self.create_card(card_frame, "Network Printers", "0", "#0f172a", 0)
        self.card_net_online = self.create_card(card_frame, "Online / Responding", "0", "#16a34a", 1)
        self.card_net_range = self.create_card(card_frame, "Date Range Prints", "+0", "#0284c7", 2)
        self.card_net_lifetime = self.create_card(card_frame, "Total Print Till Date", "0", "#2563eb", 3)

        # Toolbar
        t_bar = ttk.Frame(self.tab_network)
        t_bar.pack(fill=tk.X, padx=10, pady=4)

        # AUTO-DISCOVERY OPTION FOR NETWORK
        ttk.Button(t_bar, text="🔍 Auto-Discover Network Printers", style="Accent.TButton", command=self.open_auto_discover_network).pack(side=tk.LEFT, padx=3)
        ttk.Button(t_bar, text="🔄 Poll All Network", command=self.poll_all_network).pack(side=tk.LEFT, padx=3)
        ttk.Button(t_bar, text="⚡ Poll Selected IP", command=self.poll_selected_network).pack(side=tk.LEFT, padx=3)
        ttk.Separator(t_bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        ttk.Button(t_bar, text="➕ Add IP Printer", command=self.open_add_network_dialog).pack(side=tk.LEFT, padx=3)
        ttk.Button(t_bar, text="✏️ Edit", command=self.open_edit_network_dialog).pack(side=tk.LEFT, padx=3)
        ttk.Button(t_bar, text="🗑️ Delete", command=self.delete_selected_network).pack(side=tk.LEFT, padx=3)

        # Export Button
        export_btn = ttk.Menubutton(t_bar, text="📥 Export Network Report")
        export_menu = tk.Menu(export_btn, tearoff=0)
        export_menu.add_command(label="Export to Excel (.xls XML)", command=lambda: self.export_fleet_report("NETWORK", "excel"))
        export_menu.add_command(label="Export to CSV (.csv)", command=lambda: self.export_fleet_report("NETWORK", "csv"))
        export_menu.add_command(label="View HTML Audit Report (Printable)", command=lambda: self.export_fleet_report("NETWORK", "html"))
        export_btn["menu"] = export_menu
        export_btn.pack(side=tk.RIGHT, padx=3)

        # Treeview Table
        tree_frame = ttk.Frame(self.tab_network)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        cols = ("status", "name", "ip", "dept", "model", "range_count", "lifetime", "toner", "last_checked")
        self.tree_net = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")

        self.tree_net.heading("status", text="Network Status")
        self.tree_net.heading("name", text="Printer Name")
        self.tree_net.heading("ip", text="IP Address")
        self.tree_net.heading("dept", text="Department / Location")
        self.tree_net.heading("model", text="Model / Series")
        self.tree_net.heading("range_count", text="Date Range Prints")
        self.tree_net.heading("lifetime", text="Total Print Till Date")
        self.tree_net.heading("toner", text="Toner Levels")
        self.tree_net.heading("last_checked", text="Last Polled")

        self.tree_net.column("status", width=95, anchor=tk.CENTER)
        self.tree_net.column("name", width=180)
        self.tree_net.column("ip", width=110, anchor=tk.CENTER)
        self.tree_net.column("dept", width=140)
        self.tree_net.column("model", width=160)
        self.tree_net.column("range_count", width=130, anchor=tk.E)
        self.tree_net.column("lifetime", width=140, anchor=tk.E)
        self.tree_net.column("toner", width=100, anchor=tk.CENTER)
        self.tree_net.column("last_checked", width=130, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_net.yview)
        scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree_net.xview)
        self.tree_net.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree_net.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree_net.tag_configure("ONLINE", foreground="#15803d")
        self.tree_net.tag_configure("OFFLINE", foreground="#b91c1c")
        self.tree_net.bind("<Double-1>", lambda e: self.poll_selected_network())

    # =========================================================================
    # SECTION 3: SUBNET AUTO-DISCOVERY (TAB)
    # =========================================================================
    def build_discovery_section(self):
        ctrl = ttk.LabelFrame(self.tab_discovery, text="Scan Subnet for Network Printers", padding="12")
        ctrl.pack(fill=tk.X, padx=12, pady=10)

        suggested_subnet = PrinterScanner.get_local_subnet()

        ttk.Label(ctrl, text="IP Range (e.g. 192.168.1.1-254 or 192.168.1.0/24):", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, padx=6, pady=4)
        self.ent_scan_range = ttk.Entry(ctrl, width=28)
        self.ent_scan_range.grid(row=0, column=1, padx=6, pady=4)
        self.ent_scan_range.insert(0, suggested_subnet)

        ttk.Label(ctrl, text="SNMP Community:").grid(row=0, column=2, sticky=tk.W, padx=6, pady=4)
        self.ent_scan_comm = ttk.Entry(ctrl, width=12)
        self.ent_scan_comm.grid(row=0, column=3, padx=6, pady=4)
        self.ent_scan_comm.insert(0, "public")

        self.btn_scan = ttk.Button(ctrl, text="🔍 Start Scan", style="Accent.TButton", command=self.start_subnet_scan)
        self.btn_scan.grid(row=0, column=4, padx=12, pady=4)

        self.scan_prog = ttk.Progressbar(self.tab_discovery, orient=tk.HORIZONTAL, mode='determinate')
        self.scan_prog.pack(fill=tk.X, padx=12, pady=(0, 6))

        self.lbl_scan_info = ttk.Label(self.tab_discovery, text="Scan your LAN to auto-discover network printers and import them.")
        self.lbl_scan_info.pack(anchor=tk.W, padx=14, pady=2)

        d_frame = ttk.Frame(self.tab_discovery)
        d_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        d_cols = ("ip", "status", "counter", "model", "serial", "method")
        self.disc_tree = ttk.Treeview(d_frame, columns=d_cols, show="headings", selectmode="extended")
        self.disc_tree.heading("ip", text="IP Address")
        self.disc_tree.heading("status", text="Status")
        self.disc_tree.heading("counter", text="Total Counter Till Date")
        self.disc_tree.heading("model", text="Detected Model")
        self.disc_tree.heading("serial", text="Serial Number")
        self.disc_tree.heading("method", text="Protocol")

        self.disc_tree.column("ip", width=120, anchor=tk.CENTER)
        self.disc_tree.column("status", width=90, anchor=tk.CENTER)
        self.disc_tree.column("counter", width=140, anchor=tk.E)
        self.disc_tree.column("model", width=220)
        self.disc_tree.column("serial", width=110, anchor=tk.CENTER)
        self.disc_tree.column("method", width=180)

        d_scroll = ttk.Scrollbar(d_frame, orient=tk.VERTICAL, command=self.disc_tree.yview)
        self.disc_tree.configure(yscrollcommand=d_scroll.set)
        self.disc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        d_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        b_bar = ttk.Frame(self.tab_discovery)
        b_bar.pack(fill=tk.X, padx=12, pady=8)
        ttk.Button(b_bar, text="➕ Add Selected to Network Fleet", style="Success.TButton", command=self.add_discovered_printers).pack(side=tk.LEFT, padx=4)

    # =========================================================================
    # SECTION 4: AUDIT HISTORY
    # =========================================================================
    def build_history_section(self):
        h_frame = ttk.Frame(self.tab_history, padding="10")
        h_frame.pack(fill=tk.BOTH, expand=True)

        top_bar = ttk.Frame(h_frame)
        top_bar.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(top_bar, text="🔄 Refresh History", command=self.load_history_table).pack(side=tk.LEFT, padx=4)
        ttk.Button(top_bar, text="📥 Export History to CSV", command=self.export_history_csv).pack(side=tk.LEFT, padx=4)

        cols = ("time", "type", "printer", "identifier", "meter", "prev", "delta", "method", "status")
        self.hist_tree = ttk.Treeview(h_frame, columns=cols, show="headings", selectmode="browse")
        self.hist_tree.heading("time", text="Timestamp")
        self.hist_tree.heading("type", text="Type")
        self.hist_tree.heading("printer", text="Printer Name")
        self.hist_tree.heading("identifier", text="Port / IP")
        self.hist_tree.heading("meter", text="Counter Value")
        self.hist_tree.heading("prev", text="Previous")
        self.hist_tree.heading("delta", text="Delta (+Pages)")
        self.hist_tree.heading("method", text="Audit Method")
        self.hist_tree.heading("status", text="Status")

        self.hist_tree.column("time", width=140, anchor=tk.CENTER)
        self.hist_tree.column("type", width=70, anchor=tk.CENTER)
        self.hist_tree.column("printer", width=180)
        self.hist_tree.column("identifier", width=110, anchor=tk.CENTER)
        self.hist_tree.column("meter", width=100, anchor=tk.E)
        self.hist_tree.column("prev", width=100, anchor=tk.E)
        self.hist_tree.column("delta", width=95, anchor=tk.E)
        self.hist_tree.column("method", width=160)
        self.hist_tree.column("status", width=90, anchor=tk.CENTER)

        h_scroll = ttk.Scrollbar(h_frame, orient=tk.VERTICAL, command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=h_scroll.set)
        self.hist_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        h_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    # =========================================================================
    # SECTION 5: ABOUT & DEVELOPER INFO
    # =========================================================================
    def build_about_section(self):
        about_frame = ttk.Frame(self.tab_about, padding="16")
        about_frame.pack(fill=tk.BOTH, expand=True)

        card = tk.Frame(about_frame, bg="white", relief="solid", bd=1, padx=22, pady=18)
        card.pack(fill=tk.X, pady=(0, 16))

        tk.Label(card, text=f"🖨️ {APP_NAME} v{APP_VERSION}", font=("Segoe UI", 16, "bold"), fg="#0f172a", bg="white").pack(anchor=tk.W)
        tk.Label(card, text=f"Edition: {APP_EDITION} &bull; Released: {APP_RELEASE_DATE}", font=("Segoe UI", 9), fg="#64748b", bg="white").pack(anchor=tk.W, pady=(2, 6))

        dev_box = tk.Frame(card, bg="#f0f9ff", relief="solid", bd=1, padx=12, pady=8)
        dev_box.pack(anchor=tk.W, pady=6)
        tk.Label(dev_box, text=f"👨‍💻 {get_developer_credit()}", font=("Segoe UI", 11, "bold"), fg="#0369a1", bg="#f0f9ff").pack(anchor=tk.W)
        tk.Label(dev_box, text="Crafted for enterprise and office fleet printer meter auditing, cost allocation, and consumption tracking.", font=("Segoe UI", 9), fg="#334155", bg="#f0f9ff").pack(anchor=tk.W)

        btn_box = ttk.Frame(card)
        btn_box.pack(anchor=tk.W, pady=(12, 0))
        doc_path = os.path.join(BASE_DIR, "USB_PRINTER_COUNTER_GUIDE.md")
        data_dir = os.path.join(BASE_DIR, "data")
        ttk.Button(btn_box, text="📖 Open Full Software Guide (MD)", style="Accent.TButton", command=lambda: os.startfile(doc_path) if os.path.exists(doc_path) else None).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_box, text="📂 Open Data Folder", command=lambda: os.startfile(data_dir)).pack(side=tk.LEFT, padx=4)

        ttk.Label(about_frame, text="Version History & Release Changelog:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(6, 4))
        txt_ch = tk.Text(about_frame, wrap=tk.WORD, font=("Consolas", 9), bg="#f8fafc", fg="#1e293b", relief="solid", bd=1)
        txt_ch.pack(fill=tk.BOTH, expand=True)

        for entry in CHANGELOG:
            txt_ch.insert(tk.END, f"=== Version {entry['version']} ({entry['date']}) - {entry['title']} ===\n")
            for c in entry['changes']:
                txt_ch.insert(tk.END, f"  • {c}\n")
            txt_ch.insert(tk.END, "\n")
        txt_ch.config(state=tk.DISABLED)

    # =========================================================================
    # CORE ACTIONS & CONTROLLERS
    # =========================================================================
    def open_auto_discover_usb(self):
        """Opens dedicated interactive USB auto-discovery dialog."""
        AutoDiscoverUSBDialog(self.root, on_imported_callback=self.load_usb_table)

    def open_auto_discover_network(self):
        """Opens dedicated interactive Network auto-discovery dialog."""
        AutoDiscoverNetworkDialog(self.root, on_imported_callback=self.load_network_table)

    def create_card(self, parent, title, val, color, col):
        card = tk.Frame(parent, bg="white", relief="solid", bd=1, padx=14, pady=8)
        card.grid(row=0, column=col, padx=4, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)

        tk.Label(card, text=title.upper(), font=("Segoe UI", 8, "bold"), fg="#64748b", bg="white").pack(anchor=tk.W)
        lbl_val = tk.Label(card, text=val, font=("Segoe UI", 15, "bold"), fg=color, bg="white")
        lbl_val.pack(anchor=tk.W, pady=(2, 0))
        return lbl_val

    def set_quick_date(self, section: str, mode):
        today = datetime.now()
        if mode == 0:
            start_str = today.strftime("%Y-%m-%d")
        elif mode == "month":
            start_str = today.replace(day=1).strftime("%Y-%m-%d")
        elif mode == "all":
            start_str = "2000-01-01"
        else:
            start_str = (today - timedelta(days=mode)).strftime("%Y-%m-%d")

        end_str = today.strftime("%Y-%m-%d")

        if section == "USB":
            self.ent_usb_start.delete(0, tk.END)
            self.ent_usb_start.insert(0, start_str)
            self.ent_usb_end.delete(0, tk.END)
            self.ent_usb_end.insert(0, end_str)
            self.load_usb_table()
        else:
            self.ent_net_start.delete(0, tk.END)
            self.ent_net_start.insert(0, start_str)
            self.ent_net_end.delete(0, tk.END)
            self.ent_net_end.insert(0, end_str)
            self.load_network_table()

    def auto_sync_usb(self, silent=True):
        def _worker():
            detected = USBPrinterScanner.enumerate_usb_printers()
            Database.sync_detected_usb_printers(detected)
            self.queue.put(("USB_SYNC_DONE", (len(detected), silent)))

        threading.Thread(target=_worker, daemon=True).start()

    def load_usb_table(self):
        for item in self.tree_usb.get_children():
            self.tree_usb.delete(item)

        start_d = self.ent_usb_start.get().strip() or self.default_start
        end_d = self.ent_usb_end.get().strip() or self.default_end

        printers = Database.get_printers_with_date_range("USB", start_d, end_d)
        total_p = len(printers)
        online_p = 0
        total_range = 0
        total_lifetime = 0

        for p in printers:
            r_cnt = p.get("range_print_count", 0) or 0
            l_cnt = p.get("total_till_date", 0) or 0
            status = p.get("status", "ONLINE")

            if status == "ONLINE":
                online_p += 1
                status_icon = "🟢 ONLINE"
                tag = "ONLINE"
            else:
                status_icon = "🔴 OFFLINE"
                tag = "OFFLINE"

            total_range += r_cnt
            total_lifetime += l_cnt

            chk = p.get("last_checked") or "Never"
            if len(chk) > 16:
                chk = chk[5:16]

            self.tree_usb.insert("", tk.END, iid=str(p["id"]), values=(
                status_icon,
                p.get("name", ""),
                p.get("identifier", ""),
                f"{p.get('department', '')} ({p.get('location', '')})".strip(" ()") or "-",
                p.get("driver", "-") or "-",
                p.get("mfg", "-") or "-",
                f"+{r_cnt:,}",
                f"{l_cnt:,}",
                chk
            ), tags=(tag,))

        self.card_usb_total.config(text=str(total_p))
        self.card_usb_online.config(text=f"{online_p} / {total_p}")
        self.card_usb_range.config(text=f"+{total_range:,}")
        self.card_usb_lifetime.config(text=f"{total_lifetime:,}")

    def load_network_table(self):
        for item in self.tree_net.get_children():
            self.tree_net.delete(item)

        start_d = self.ent_net_start.get().strip() or self.default_start
        end_d = self.ent_net_end.get().strip() or self.default_end

        printers = Database.get_printers_with_date_range("NETWORK", start_d, end_d)
        total_p = len(printers)
        online_p = 0
        total_range = 0
        total_lifetime = 0

        for p in printers:
            r_cnt = p.get("range_print_count", 0) or 0
            l_cnt = p.get("total_till_date", 0) or 0
            status = p.get("status", "ONLINE")

            if status == "ONLINE":
                online_p += 1
                status_icon = "🟢 ONLINE"
                tag = "ONLINE"
            else:
                status_icon = "🔴 OFFLINE"
                tag = "OFFLINE"

            total_range += r_cnt
            total_lifetime += l_cnt

            toner = {}
            try:
                toner_raw = p.get("toner_json") or "{}"
                toner = json.loads(toner_raw) if isinstance(toner_raw, str) else toner_raw
            except Exception:
                pass
            toner_str = f"K:{toner['black']}%" if "black" in toner else "-"

            chk = p.get("last_checked") or "Never"
            if len(chk) > 16:
                chk = chk[5:16]

            self.tree_net.insert("", tk.END, iid=str(p["id"]), values=(
                status_icon,
                p.get("name", ""),
                p.get("identifier", ""),
                f"{p.get('department', '')} ({p.get('location', '')})".strip(" ()") or "-",
                p.get("model", "-") or "-",
                f"+{r_cnt:,}",
                f"{l_cnt:,}",
                toner_str,
                chk
            ), tags=(tag,))

        self.card_net_total.config(text=str(total_p))
        self.card_net_online.config(text=f"{online_p} / {total_p}")
        self.card_net_range.config(text=f"+{total_range:,}")
        self.card_net_lifetime.config(text=f"{total_lifetime:,}")

    def open_usb_meter_dialog(self):
        sel = self.tree_usb.selection()
        if not sel:
            messagebox.showinfo("Select Printer", "Please select a USB printer to update.", parent=self.root)
            return
        p_id = int(sel[0])
        printers = Database.get_printers(printer_type="USB")
        target = next((p for p in printers if p["id"] == p_id), None)
        if target:
            UpdateUSBMeterDialog(self.root, target, on_save_callback=self.load_usb_table)

    def query_usb_hardware(self):
        sel = self.tree_usb.selection()
        if not sel:
            messagebox.showinfo("Select Printer", "Please select a USB printer to query.", parent=self.root)
            return
        p_id = int(sel[0])
        printers = Database.get_printers(printer_type="USB")
        target = next((p for p in printers if p["id"] == p_id), None)
        if not target:
            return

        self.lbl_status.config(text=f"Querying USB hardware for {target['name']}...", fg="#38bdf8")

        def _worker():
            cnt, meth = USBPrinterScanner.query_usb_hardware_counter(target["name"])
            self.queue.put(("USB_HW_QUERY_RESULT", (target, cnt, meth)))

        threading.Thread(target=_worker, daemon=True).start()

    def poll_all_network(self):
        printers = Database.get_printers(printer_type="NETWORK")
        if not printers:
            messagebox.showinfo("No Printers", "Please add network printers or run Auto-Discovery.", parent=self.root)
            return

        self.lbl_status.config(text=f"Polling {len(printers)} network printers...", fg="#38bdf8")

        def _worker():
            for p in printers:
                res = PrinterScanner.poll_printer(
                    ip=p["identifier"],
                    community=p.get("community") or "public",
                    pin=p.get("password") or "1234",
                    username=p.get("username") or "",
                    protocol_pref=p.get("protocol_pref") or "AUTO",
                    timeout=2.5
                )
                Database.update_network_reading(
                    printer_id=p["id"],
                    counter_value=res["counter"],
                    model=res["model"],
                    serial=res["serial"],
                    method=res["method"],
                    status=res["status"],
                    toner=res["toner"]
                )
            self.queue.put(("NET_POLL_COMPLETE", None))

        threading.Thread(target=_worker, daemon=True).start()

    def poll_selected_network(self):
        sel = self.tree_net.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select a network printer from the list.", parent=self.root)
            return
        p_id = int(sel[0])
        printers = Database.get_printers(printer_type="NETWORK")
        target = next((p for p in printers if p["id"] == p_id), None)
        if not target:
            return

        self.lbl_status.config(text=f"Polling {target['name']} ({target['identifier']})...", fg="#38bdf8")

        def _worker():
            res = PrinterScanner.poll_printer(
                ip=target["identifier"],
                community=target.get("community") or "public",
                pin=target.get("password") or "1234",
                username=target.get("username") or "",
                protocol_pref=target.get("protocol_pref") or "AUTO",
                timeout=3.0
            )
            Database.update_network_reading(
                printer_id=target["id"],
                counter_value=res["counter"],
                model=res["model"],
                serial=res["serial"],
                method=res["method"],
                status=res["status"],
                toner=res["toner"]
            )
            self.queue.put(("SINGLE_NET_COMPLETE", (target["name"], res)))

        threading.Thread(target=_worker, daemon=True).start()

    def open_add_network_dialog(self):
        AddNetworkPrinterDialog(self.root, on_save_callback=self.load_network_table)

    def open_edit_network_dialog(self):
        sel = self.tree_net.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select a network printer to edit.", parent=self.root)
            return
        p_id = int(sel[0])
        printers = Database.get_printers(printer_type="NETWORK")
        target = next((p for p in printers if p["id"] == p_id), None)
        if target:
            AddNetworkPrinterDialog(self.root, printer_data=target, on_save_callback=self.load_network_table)

    def delete_selected_network(self):
        sel = self.tree_net.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select a printer to delete.", parent=self.root)
            return
        p_id = int(sel[0])
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this network printer and its meter logs?"):
            Database.delete_printer(p_id)
            self.load_network_table()

    def start_subnet_scan(self):
        rng = self.ent_scan_range.get().strip()
        comm = self.ent_scan_comm.get().strip() or "public"
        self.btn_scan.config(state=tk.DISABLED)
        for item in self.disc_tree.get_children():
            self.disc_tree.delete(item)
        self.lbl_scan_info.config(text=f"Scanning subnet {rng}...")

        def _progress(done, total):
            pct = int((done / total) * 100) if total > 0 else 0
            self.queue.put(("SCAN_PROG", pct))

        def _worker():
            results = PrinterScanner.scan_ip_range(rng, community=comm, progress_callback=_progress)
            self.queue.put(("SCAN_DONE", results))

        threading.Thread(target=_worker, daemon=True).start()

    def add_discovered_printers(self):
        sel = self.disc_tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select discovered printers to add.", parent=self.root)
            return

        added = 0
        for item_id in sel:
            vals = self.disc_tree.item(item_id, "values")
            ip = vals[0]
            model = vals[3] if vals[3] != "-" else "Network Printer"
            serial = vals[4] if vals[4] != "-" else ""

            Database.save_network_printer({
                "name": f"{model} ({ip.split('.')[-1]})",
                "identifier": ip,
                "model": model,
                "serial_number": serial,
                "community": self.ent_scan_comm.get().strip() or "public"
            })
            added += 1

        self.load_network_table()
        messagebox.showinfo("Added", f"Added {added} printers to Network Fleet!", parent=self.root)

    def load_history_table(self):
        for item in self.hist_tree.get_children():
            self.hist_tree.delete(item)
        records = Database.get_readings_history(limit=300)
        for r in records:
            d_str = f"+{r.get('delta', 0):,}" if (r.get('delta', 0) or 0) > 0 else "-"
            self.hist_tree.insert("", tk.END, values=(
                r.get("timestamp", ""),
                r.get("printer_type", ""),
                r.get("printer_name", ""),
                r.get("identifier", ""),
                f"{r.get('counter_value', 0):,}",
                f"{r.get('previous_value', 0):,}",
                d_str,
                r.get("method", ""),
                r.get("status", "")
            ))

    def export_history_csv(self):
        records = Database.get_readings_history(limit=2000)
        if not records:
            messagebox.showinfo("No History", "No history to export.", parent=self.root)
            return
        filepath = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile=f"Fleet_Audit_History_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        if filepath:
            import csv
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([f"# {get_developer_credit()} - Fleet Meter Audit History"])
                writer.writerow(["Timestamp", "Type", "Printer Name", "Port / IP", "Department", "Counter Value", "Previous Value", "Delta", "Method", "Status"])
                for r in records:
                    writer.writerow([
                        r.get("timestamp"), r.get("printer_type"), r.get("printer_name"),
                        r.get("identifier"), r.get("department"), r.get("counter_value"),
                        r.get("previous_value"), r.get("delta"), r.get("method"), r.get("status")
                    ])
            messagebox.showinfo("Exported", f"History saved to:\n{filepath}", parent=self.root)

    def export_fleet_report(self, printer_type: str, fmt: str):
        if printer_type == "USB":
            start_d = self.ent_usb_start.get().strip() or self.default_start
            end_d = self.ent_usb_end.get().strip() or self.default_end
            section_name = "USB"
        else:
            start_d = self.ent_net_start.get().strip() or self.default_start
            end_d = self.ent_net_end.get().strip() or self.default_end
            section_name = "Network"

        printers = Database.get_printers_with_date_range(printer_type, start_d, end_d)
        if not printers:
            messagebox.showinfo("No Printers", f"No {section_name} printer data to export.", parent=self.root)
            return

        tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        if fmt == "excel":
            filepath = filedialog.asksaveasfilename(
                parent=self.root,
                defaultextension=".xls",
                filetypes=[("Excel Spreadsheet (*.xls)", "*.xls")],
                initialfile=f"{section_name}_Printer_Report_{tag}.xls"
            )
            if filepath:
                FleetReportExporter.export_excel_xml(printers, filepath, section_name=section_name, start_date=start_d, end_date=end_d)
                if messagebox.askyesno("Open File", "Excel report generated! Open it now?"):
                    os.startfile(filepath)

        elif fmt == "csv":
            filepath = filedialog.asksaveasfilename(
                parent=self.root,
                defaultextension=".csv",
                filetypes=[("CSV File (*.csv)", "*.csv")],
                initialfile=f"{section_name}_Printer_Report_{tag}.csv"
            )
            if filepath:
                FleetReportExporter.export_csv(printers, filepath, section_name=section_name, start_date=start_d, end_date=end_d)
                if messagebox.askyesno("Open File", "CSV report generated! Open it now?"):
                    os.startfile(filepath)

        elif fmt == "html":
            filepath = os.path.join(BASE_DIR, "data", f"{section_name}_Printer_Report_{tag}.html")
            FleetReportExporter.export_html_report(printers, filepath, section_name=section_name, start_date=start_d, end_date=end_d)
            webbrowser.open(filepath)

    def process_queue(self):
        try:
            while True:
                msg_type, data = self.queue.get_nowait()
                if msg_type == "USB_SYNC_DONE":
                    cnt, silent = data
                    self.load_usb_table()
                    self.lbl_status.config(text=f"USB Fleet synchronized ({cnt} detected).", fg="#4ade80")
                    if not silent:
                        messagebox.showinfo("USB Scan", f"Detected {cnt} local USB printers!", parent=self.root)

                elif msg_type == "NET_POLL_COMPLETE":
                    self.load_network_table()
                    self.lbl_status.config(text="Network polling complete. Fleet counters updated.", fg="#4ade80")

                elif msg_type == "SINGLE_NET_COMPLETE":
                    name, res = data
                    self.load_network_table()
                    if res["status"] == "ONLINE":
                        self.lbl_status.config(text=f"{name}: Lifetime Counter is {res['counter']:,}!", fg="#4ade80")
                    else:
                        self.lbl_status.config(text=f"{name}: {res['status']}", fg="#f87171")

                elif msg_type == "USB_HW_QUERY_RESULT":
                    target, cnt, meth = data
                    if cnt:
                        Database.update_usb_meter(target["id"], cnt, 0)
                        self.load_usb_table()
                        messagebox.showinfo("Hardware Response", f"{target['name']}\nHardware Counter: {cnt:,} pages\nMethod: {meth}", parent=self.root)
                    else:
                        messagebox.showinfo("Hardware Query", f"{target['name']}\nStatus: {meth}\n\nTip: You can use 'Set / Update Meter' to define baseline reading.", parent=self.root)

                elif msg_type == "SCAN_PROG":
                    self.scan_prog["value"] = data

                elif msg_type == "SCAN_DONE":
                    results = data
                    self.scan_prog["value"] = 100
                    self.btn_scan.config(state=tk.NORMAL)
                    self.lbl_scan_info.config(text=f"Scan complete! Discovered {len(results)} active network printers.")
                    for r in results:
                        cnt_str = f"{r['counter']:,}" if r['counter'] > 0 else "-"
                        self.disc_tree.insert("", tk.END, values=(
                            r["ip"], r["status"], cnt_str, r["model"] or "Network Printer", r["serial"] or "-", r["method"] or "-"
                        ))

        except queue.Empty:
            pass

        self.root.after(100, self.process_queue)


def main():
    root = tk.Tk()
    app = PrinterCounterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
