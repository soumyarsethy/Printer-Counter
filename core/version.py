"""
Printer Counter - Centralized Version & Developer Information
Developed by Soumya Ranjan Sethy
"""

APP_NAME = "Printer Counter"
APP_VERSION = "2.2.1"
APP_EDITION = "Auto-Discovery Dual Fleet Edition"
APP_RELEASE_DATE = "2026-10-28"
APP_DEVELOPER = "Soumya Ranjan Sethy"

CHANGELOG = [
    {
        "version": "2.2.1",
        "date": "2026-10-28",
        "title": "Tkinter Grid Layout Fix & Rebuilt Standalone Executables",
        "changes": [
            "Fixed _tkinter.TclError: bad option '-fill' in Tkinter layout hierarchy.",
            "Re-compiled clean standalone binaries: dist/PrinterFleet/PrinterFleet.exe and PrinterCounter.exe launcher.",
            "Verified error-free GUI startup and widget rendering across all tabs.",
            "Maintained developer credit: 'Developed by Soumya Ranjan Sethy'."
        ]
    },
    {
        "version": "2.2.0",
        "date": "2026-10-28",
        "title": "USB & Network In-Section Auto-Discovery",
        "changes": [
            "Added dedicated 'Auto-Discover USB Printers' interactive scan dialog directly in the USB section.",
            "Added USB Hardware Plug & Play scanner detecting USB001-USB999, DOT4, and USBPRINT registry instances.",
            "Added dedicated 'Auto-Discover Network Printers' subnet scanner directly in the Network section.",
            "Instant one-click import of discovered USB and Network printers with automatic counter retrieval.",
            "Maintained developer credit: 'Developed by Soumya Ranjan Sethy'.",
            "Updated documentation and compiled standalone executables."
        ]
    },
    {
        "version": "2.1.0",
        "date": "2026-10-28",
        "title": "Dual Fleet (USB & Network) with Date Range Accounting",
        "changes": [
            "Added dedicated USB Printers section and Network Printers section.",
            "Added interactive Date Range Filtering for both USB and Network printers.",
            "Display Lifetime Total Print Till Date alongside Date Range Consumption count.",
            "Added developer attribution: 'Developed by Soumya Ranjan Sethy'."
        ]
    },
    {
        "version": "2.0.0",
        "date": "2026-10-28",
        "title": "USB-Dedicated Edition Release",
        "changes": [
            "Redesigned for local USB-connected printers (USB001, USB004, USB010, DOT4).",
            "Added native winspool.drv Windows print subsystem integration via standard library ctypes."
        ]
    },
    {
        "version": "1.0.0",
        "date": "2026-10-28",
        "title": "Initial Release",
        "changes": [
            "Initial printer counter implementation."
        ]
    }
]


def get_version_string() -> str:
    return f"{APP_NAME} v{APP_VERSION} ({APP_EDITION})"


def get_developer_credit() -> str:
    return f"Developed by {APP_DEVELOPER}"
