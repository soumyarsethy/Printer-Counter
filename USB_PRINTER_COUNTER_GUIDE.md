# 🖨️ Printer Counter — Complete Software Architecture & User Guide

**Application Name:** Printer Counter  
**Version:** `v2.2.1 (Auto-Discovery Dual Fleet Edition)`  
**Developer:** **Soumya Ranjan Sethy**  
**Release Date:** 2026-10-28  
**Supported Platforms:** Windows 10, Windows 11, Windows Server (32-bit & 64-bit)  
**Portability:** 100% Self-Contained Standalone Executable (Runs from USB Flash Drive or any folder)

---

## 1. What is this Software For?

**Printer Counter** is a dual-fleet printer audit and meter reading application developed by **Soumya Ranjan Sethy**. It provides complete visibility and automated discovery for both **local USB-connected printers** and **remote Network-connected printers**.

### Core Objectives
1. **Interactive In-Section Auto-Discovery**:
   - **USB Auto-Discovery**: Automatically probes local USB ports (`USB001` - `USB020`, `DOT4`), Windows PnP devices, and `USBPRINT` hardware registry to discover all attached desktop printers.
   - **Network Auto-Discovery**: Automatically determines the local subnet range and multithreads across SNMP (UDP 161), PJL (port 9100), and HTTP Embedded Web Servers to discover copiers and printers across the LAN.
2. **Total Print Till Date**:
   - Accurately captures and tracks the lifetime total page impressions across your entire printer fleet till the current moment.
3. **Date Range Consumption Filter**:
   - Allows users to select any customized start and end date (e.g. `2026-10-01` to `2026-10-28`, "Today", "Last 7 Days", "This Month", or custom billing cycles).
   - Dynamically calculates the exact number of pages printed within that specific date range for individual printers and the whole fleet.
4. **USB Printer Meter Reading**:
   - Seamlessly interfaces with local desktop printers plugged via USB (`USB001`, `USB004`, `USB010`, `DOT4`), including the *Canon LBP2900*, *HP LaserJet Pro P1100 / P1102*, *Epson EcoTank*, and *Brother HL* series.
5. **Network Printer Meter Reading**:
   - Automatically polls networked office and enterprise copiers across IP subnets using SNMP v1/v2c (`prtMarkerLifeCount`), PJL over port 9100, and HTTP/HTTPS Embedded Web Servers (Canon Remote UI / RPS, HP EWS, Ricoh, Xerox, Kyocera).
6. **Department Billing & Cost Accounting**:
   - Generates billing-ready reports with cost-per-page calculations for department expense allocation.

---

## 2. Dedicated Sections & Architecture

The software is structured into two dedicated management sections:

```
┌────────────────────────────────────────────────────────────────────────┐
│             PRINTER COUNTER v2.1.0 (Dual Fleet Edition)                │
│                 Developed by Soumya Ranjan Sethy                       │
├──────────────────────────────────┬─────────────────────────────────────┤
│      🔌 SECTION 1: USB FLEET     │     🌐 SECTION 2: NETWORK FLEET     │
│  - Native Windows winspool.drv   │  - SNMP v1/v2c (UDP 161)            │
│  - USBPRINT Hardware Registry    │  - PJL Port 9100 Socket             │
│  - Direct USB PJL Queries        │  - Canon Remote UI / HTTP EWS       │
│  - Baseline + Accumulated Delta  │  - Subnet Auto-Scanner              │
├──────────────────────────────────┴─────────────────────────────────────┤
│              📅 INTERACTIVE DATE RANGE FILTER (BOTH SECTIONS)          │
│       [From: YYYY-MM-DD]  [To: YYYY-MM-DD]  [Quick: Month/Today]       │
│  Outputs: 1. Date Range Print Count   2. Total Print Till Date         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. How Date Range & Total Counter Accounting Works

### 1. Total Print Till Date (Lifetime Counter)
- **Network Printers**: Queried directly from the printer's internal hardware marker counter (Printer-MIB OID `1.3.6.1.2.1.43.10.2.1.4.1.1` or PJL `@PJL INFO PAGECOUNT`).
- **USB Printers**: Computed as `Baseline Hardware Reading + Accumulated Printed Pages`.

### 2. Date Range Print Count
- The user sets a **From Date** and **To Date** (e.g. `2026-10-01` to `2026-10-28`).
- The database queries the audit snapshots within the specified time window:
  $$\text{Date Range Count} = \sum_{\text{timestamp} \in [\text{start}, \text{end}]} \text{delta}$$
- Displays the consumption badge (`+X pages`) dynamically for each printer and aggregates it in the top summary card.

---

## 4. Features & Interface Breakdown

### 🔌 Section 1: USB Printers
- **Auto-Detection**: Scans Windows print subsystem and detects all USB-connected printers (`USB001`, `USB004`, `USB010`, etc.).
- **Live Connection Status**: 🟢 Online, 🔴 Offline, 🟡 Attention (Paper jam, door open).
- **Date Range Filter**: Filter USB prints by Today, This Month, or custom date ranges.
- **Controls**:
  - `Auto-Detect USB Printers`: Re-scans USB ports for newly attached devices.
  - `Set / Update Meter`: Enter physical baseline meter from the printer test page.
  - `Query USB Hardware`: Sends raw PJL commands over USB port to extract hardware counters.
  - `Export USB Report`: Generates formatted Excel XML, CSV, or HTML reports.

### 🌐 Section 2: Network Printers
- **IP Meter Reading**: Queries network printers concurrently in the background.
- **Date Range Filter**: Computes pages printed between specified dates.
- **Toner Monitoring**: Displays remaining toner levels (Black %, Cyan %, Magenta %, Yellow %).
- **Controls**:
  - `Poll All Network Printers`: Concurrently polls all IP printers.
  - `Poll Selected IP`: Instant diagnostic refresh on a single machine.
  - `Add IP Printer`: Register a new network IP or hostname.
  - `Export Network Report`: Generates billing and audit reports.

### 🔍 Section 3: Subnet Auto-Discovery
- Scans entire IP subnets (e.g., `192.168.1.0/24` or `192.168.1.1-254`).
- Automatically detects active printers, identifies models/serials, and adds them to your Network Fleet.

### 📜 Section 4: Audit History
- Maintains historical snapshots of every meter reading with timestamps, protocol used, and delta.
- Exportable to standard CSV format.

### ℹ️ Section 5: Version & Developer Info
- Displays **`Printer Counter v2.1.0`**, developer signature **`Developed by Soumya Ranjan Sethy`**, and full release changelog.

---

## 5. Report Generation & Exports

All exported reports automatically include:
- **Developer Attribution:** `Developed by Soumya Ranjan Sethy`
- **Filtered Date Range:** `From [Date] to [Date]`
- **Date Range Prints (+X)** and **Total Print Till Date**
- Formats supported:
  1. **Excel XML (`.xls`)**: Native formatted workbook with color-coded headers and auto-sum formula totals.
  2. **CSV (`.csv`)**: Standard UTF-8 BOM CSV.
  3. **HTML Audit Report**: Printable executive audit sheet with KPI summary cards.

---

## 6. How to Run the Software

1. [**`PrinterCounter.exe`**](file:///E:/Backup/Printer%20Counter/PrinterCounter.exe) *(In the main folder)*:
   - Native Windows executable launcher.
2. [**`dist\PrinterCounterApp\PrinterCounterApp.exe`**](file:///E:/Backup/Printer%20Counter/dist/PrinterCounterApp/PrinterCounterApp.exe):
   - Complete standalone distribution bundle (runs on any PC without Python installed).
3. [**`PrinterCounter.vbs`**](file:///E:/Backup/Printer%20Counter/PrinterCounter.vbs):
   - Silent background script launcher.
4. [**`PrinterCounter.bat`**](file:///E:/Backup/Printer%20Counter/PrinterCounter.bat):
   - Standard Windows batch script launcher.

---

## 7. Version History & Changelog

### Version 2.2.0 (2026-10-28) — Auto-Discovery Dual Fleet Edition
- **Developer:** Soumya Ranjan Sethy.
- Added dedicated **Auto-Discover USB Printers** dialog in the USB section (scans USB001-USB020, DOT4, and PnP USBPRINT devices).
- Added dedicated **Auto-Discover Network Printers** dialog in the Network section (multithreaded subnet scan across SNMP and port 9100).
- Instant preview and one-click import of newly discovered devices.
- Retained Date Range consumption accounting and Total Print Till Date tracking.

### Version 2.1.0 (2026-10-28) — Dual Fleet Edition
- Added dedicated **USB Printers** section and **Network Printers** section.
- Added interactive **Date Range Filtering** (From/To date inputs with quick presets).
- Added **Total Print Till Date** and **Date Range Print Count** calculations.
- Embedded developer attribution throughout the application and exported reports.

### Version 2.0.0 (2026-10-28)
- Added native `winspool.drv` USB printer integration and hardware PnP registry mapping.

### Version 1.0.0 (2026-10-28)
- Initial release.
