# 🖨️ Printer Counter (Portable Windows Edition)

**Dual Fleet Edition (USB & Network Printers)**  
**Developer:** **Soumya Ranjan Sethy**  
**Current Version:** `v2.2.1`  
**Full Documentation:** See [`USB_PRINTER_COUNTER_GUIDE.md`](file:///E:/Backup/Printer%20Counter/USB_PRINTER_COUNTER_GUIDE.md)

---

## 🌟 Key Features

- **Two Dedicated Sections**:
  - **🔌 USB Printers**: Tracks locally connected USB desktop printers (`USB001`, `USB004`, `USB010`, etc.), including Canon LBP2900, HP LaserJet, Epson EcoTank, and Brother.
  - **🌐 Network Printers**: Concurrently monitors networked copiers and office printers over SNMP v1/v2c, PJL, and HTTP/HTTPS Web EWS.
- **Date Range Consumption Filter**:
  - Select any custom date range (`From Date` to `To Date`) or use quick presets ("Today", "Last 7 Days", "This Month", "All Time").
  - Dynamically calculates the **Date Range Print Count** alongside the **Total Print Till Date** (lifetime impressions).
- **Developer Attribution**:
  - Prominently developed by **Soumya Ranjan Sethy**.
  - Included across all UI headers, status dialogs, and exported Excel, CSV, and HTML reports.
- **Subnet Auto-Discovery**:
  - Scans CIDR subnets (e.g., `192.168.1.0/24`) and IP ranges to detect and import printers with one click.
- **100% Portable Executable**:
  - Runs directly from any folder or USB flash drive with zero installation.

---

## 🚀 How to Run

1. [**`PrinterCounter.exe`**](file:///E:/Backup/Printer%20Counter/PrinterCounter.exe) *(In the root folder)*: Double-click to launch immediately.
2. [**`dist\PrinterCounterApp\PrinterCounterApp.exe`**](file:///E:/Backup/Printer%20Counter/dist/PrinterCounterApp/PrinterCounterApp.exe): Self-contained portable binary distribution (runs on any PC without Python installed).
3. [**`PrinterCounter.vbs`**](file:///E:/Backup/Printer%20Counter/PrinterCounter.vbs): Silent background script launcher (no cmd window).
4. [**`PrinterCounter.bat`**](file:///E:/Backup/Printer%20Counter/PrinterCounter.bat): Standard Windows batch script.

---

## 📁 Directory Structure

```text
E:\Backup\Printer Counter\
│
├── printer_counter.py        # Main Tkinter Desktop Application
├── PrinterCounter.bat        # Windows Batch Launcher
├── PrinterCounter.vbs        # Silent VBScript Launcher (no cmd window)
│
├── core/
│   ├── __init__.py
│   ├── db.py                 # SQLite storage layer (printers, readings, settings)
│   ├── scanner.py            # SNMP, PJL, HTTP/EWS, WMI printer interrogation engine
│   └── exporter.py           # Excel XML, CSV, and HTML report generator
│
├── data/
│   └── printer_counter.db    # Embedded portable SQLite database
│
└── README.md                 # User Guide and Documentation
```

---

## 🛠️ Protocols & Ports Used

| Protocol | Port | Used For |
|---|---|---|
| **SNMP v1/v2c** | UDP 161 | Standard Printer-MIB `prtMarkerLifeCount`, Toner levels, Serial number |
| **PJL / RAW** | TCP 9100 | Direct page counter polling for HP, Lexmark, Samsung, Brother |
| **HTTP / HTTPS** | TCP 80 / 443 | Canon Remote UI, HP EWS, Ricoh Web Image Monitor |
| **Canon RPS** | TCP 8000 / 8443 | Canon imageRUNNER ADVANCE portal challenge-response |
| **Windows CIM/WMI** | Local Spooler | Local USB and client-shared printers |

---

## 💡 Quick Tips

1. **First-Time Discovery**: Go to the **"Subnet Discovery"** tab, verify your local IP range, and click **"Start Scan"**. Select discovered printers and click **"Add Selected to Monitored List"**.
2. **Taking Meter Readings**: In the **"Fleet Dashboard"**, click **"Poll All Printers"**. The app polls all machines concurrently in the background and computes the delta consumption.
3. **Monthly Reporting**: Click **"Export Report"** -> **"Export to Excel"** or **"View HTML Audit Report"** to generate audit sheets for billing or department paper cost allocation.

