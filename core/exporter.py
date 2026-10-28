"""
Dual Fleet Printer Counter Export Engine
Developed by Soumya Ranjan Sethy
Supports both USB & Network Printers with Date Range print accounting and Total Till Date.
"""

import os
import csv
import json
from datetime import datetime
from typing import List, Dict, Any
from core.version import APP_NAME, APP_VERSION, APP_DEVELOPER, get_developer_credit


class FleetReportExporter:
    @staticmethod
    def export_csv(
        printers: List[Dict[str, Any]],
        filepath: str,
        section_name: str = "Fleet",
        start_date: str = "",
        end_date: str = ""
    ) -> str:
        """Exports printer counter summary to CSV format."""
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([f"# {APP_NAME} v{APP_VERSION} - {section_name} Report"])
            writer.writerow([f"# {get_developer_credit()}"])
            writer.writerow([f"# Filter Date Range: {start_date} to {end_date}"])
            writer.writerow([])
            writer.writerow([
                "Type",
                "Printer Name",
                "Port / IP Address",
                "Department",
                "Location",
                "Model / Driver",
                "Manufacturer",
                f"Date Range Print Count ({start_date} to {end_date})",
                "Total Print Till Date (Lifetime)",
                "Previous Meter",
                "Status",
                "Last Checked"
            ])

            for p in printers:
                writer.writerow([
                    p.get("printer_type", ""),
                    p.get("name", ""),
                    p.get("identifier", ""),
                    p.get("department", ""),
                    p.get("location", ""),
                    p.get("model") or p.get("driver") or "-",
                    p.get("mfg", ""),
                    p.get("range_print_count", 0),
                    p.get("total_till_date", 0),
                    p.get("previous_reading", 0),
                    p.get("status", ""),
                    p.get("last_checked", "")
                ])
        return filepath

    @staticmethod
    def export_excel_xml(
        printers: List[Dict[str, Any]],
        filepath: str,
        section_name: str = "Fleet",
        start_date: str = "",
        end_date: str = ""
    ) -> str:
        """Exports formatted Microsoft Excel SpreadsheetML XML format."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<?mso-application progid="Excel.Sheet"?>',
            '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"',
            ' xmlns:o="urn:schemas-microsoft-com:office:office"',
            ' xmlns:x="urn:schemas-microsoft-com:office:excel"',
            ' xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"',
            ' xmlns:html="http://www.w3.org/TR/REC-html40">',
            ' <Styles>',
            '  <Style ss:ID="Header">',
            '   <Font ss:Bold="1" ss:Color="#FFFFFF" ss:FontName="Calibri" ss:Size="11"/>',
            '   <Interior ss:Color="#0F172A" ss:Pattern="Solid"/>',
            '   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>',
            '   <Borders>',
            '    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#334155"/>',
            '   </Borders>',
            '  </Style>',
            '  <Style ss:ID="Title">',
            '   <Font ss:Bold="1" ss:Color="#0F172A" ss:FontName="Calibri" ss:Size="14"/>',
            '   <Alignment ss:Horizontal="Left" ss:Vertical="Center"/>',
            '  </Style>',
            '  <Style ss:ID="Subtitle">',
            '   <Font ss:Bold="1" ss:Color="#2563EB" ss:FontName="Calibri" ss:Size="11"/>',
            '   <Alignment ss:Horizontal="Left" ss:Vertical="Center"/>',
            '  </Style>',
            '  <Style ss:ID="NumberCell">',
            '   <NumberFormat ss:Format="#,##0"/>',
            '   <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>',
            '  </Style>',
            '  <Style ss:ID="RangeCell">',
            '   <Font ss:Bold="1" ss:Color="#0284C7" ss:FontName="Calibri"/>',
            '   <NumberFormat ss:Format="#,##0"/>',
            '   <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>',
            '  </Style>',
            '  <Style ss:ID="CenterCell">',
            '   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>',
            '  </Style>',
            '  <Style ss:ID="OnlineCell">',
            '   <Font ss:Bold="1" ss:Color="#15803D" ss:FontName="Calibri"/>',
            '   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>',
            '  </Style>',
            '  <Style ss:ID="OfflineCell">',
            '   <Font ss:Bold="1" ss:Color="#B91C1C" ss:FontName="Calibri"/>',
            '   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>',
            '  </Style>',
            ' </Styles>',
            f' <Worksheet ss:Name="{section_name} Printers">',
            '  <Table ss:DefaultRowHeight="20">',
            '   <Column ss:Width="70"/>',   # Type
            '   <Column ss:Width="170"/>',  # Name
            '   <Column ss:Width="120"/>',  # Identifier (Port/IP)
            '   <Column ss:Width="120"/>',  # Dept
            '   <Column ss:Width="110"/>',  # Location
            '   <Column ss:Width="160"/>',  # Model/Driver
            '   <Column ss:Width="140"/>',  # Range Count
            '   <Column ss:Width="140"/>',  # Lifetime Total
            '   <Column ss:Width="90"/>',   # Status
            '   <Column ss:Width="140"/>',  # Last Checked
            f'   <Row ss:Height="26"><Cell ss:StyleID="Title"><Data ss:Type="String">{APP_NAME} v{APP_VERSION} - {section_name} Printer Audit Report</Data></Cell></Row>',
            f'   <Row ss:Height="22"><Cell ss:StyleID="Subtitle"><Data ss:Type="String">{get_developer_credit()} | Date Range: {start_date} to {end_date} | Generated: {now_str}</Data></Cell></Row>',
            '   <Row ss:Height="24">',
            '    <Cell ss:StyleID="Header"><Data ss:Type="String">Type</Data></Cell>',
            '    <Cell ss:StyleID="Header"><Data ss:Type="String">Printer Name</Data></Cell>',
            '    <Cell ss:StyleID="Header"><Data ss:Type="String">Port / IP Address</Data></Cell>',
            '    <Cell ss:StyleID="Header"><Data ss:Type="String">Department</Data></Cell>',
            '    <Cell ss:StyleID="Header"><Data ss:Type="String">Location</Data></Cell>',
            '    <Cell ss:StyleID="Header"><Data ss:Type="String">Model / Driver</Data></Cell>',
            f'    <Cell ss:StyleID="Header"><Data ss:Type="String">Date Range Count ({start_date} to {end_date})</Data></Cell>',
            '    <Cell ss:StyleID="Header"><Data ss:Type="String">Total Print Till Date</Data></Cell>',
            '    <Cell ss:StyleID="Header"><Data ss:Type="String">Status</Data></Cell>',
            '    <Cell ss:StyleID="Header"><Data ss:Type="String">Last Checked</Data></Cell>',
            '   </Row>'
        ]

        total_range = 0
        total_lifetime = 0

        for p in printers:
            range_cnt = p.get("range_print_count", 0) or 0
            lifetime = p.get("total_till_date", 0) or 0
            total_range += range_cnt
            total_lifetime += lifetime

            status = p.get("status", "ONLINE")
            status_style = "OnlineCell" if status == "ONLINE" else "OfflineCell"

            def _clean(val):
                return str(val or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            xml_lines.append('   <Row>')
            xml_lines.append(f'    <Cell ss:StyleID="CenterCell"><Data ss:Type="String">{_clean(p.get("printer_type"))}</Data></Cell>')
            xml_lines.append(f'    <Cell><Data ss:Type="String">{_clean(p.get("name"))}</Data></Cell>')
            xml_lines.append(f'    <Cell ss:StyleID="CenterCell"><Data ss:Type="String">{_clean(p.get("identifier"))}</Data></Cell>')
            xml_lines.append(f'    <Cell><Data ss:Type="String">{_clean(p.get("department"))}</Data></Cell>')
            xml_lines.append(f'    <Cell><Data ss:Type="String">{_clean(p.get("location"))}</Data></Cell>')
            xml_lines.append(f'    <Cell><Data ss:Type="String">{_clean(p.get("model") or p.get("driver") or "-")}</Data></Cell>')
            xml_lines.append(f'    <Cell ss:StyleID="RangeCell"><Data ss:Type="Number">{range_cnt}</Data></Cell>')
            xml_lines.append(f'    <Cell ss:StyleID="NumberCell"><Data ss:Type="Number">{lifetime}</Data></Cell>')
            xml_lines.append(f'    <Cell ss:StyleID="{status_style}"><Data ss:Type="String">{_clean(status)}</Data></Cell>')
            xml_lines.append(f'    <Cell ss:StyleID="CenterCell"><Data ss:Type="String">{_clean(p.get("last_checked"))}</Data></Cell>')
            xml_lines.append('   </Row>')

        # Totals Row
        xml_lines.append('   <Row ss:Height="22">')
        xml_lines.append('    <Cell ss:StyleID="Header"><Data ss:Type="String">TOTALS</Data></Cell>')
        xml_lines.append('    <Cell ss:StyleID="Header"><Data ss:Type="String"></Data></Cell>')
        xml_lines.append('    <Cell ss:StyleID="Header"><Data ss:Type="String"></Data></Cell>')
        xml_lines.append('    <Cell ss:StyleID="Header"><Data ss:Type="String"></Data></Cell>')
        xml_lines.append('    <Cell ss:StyleID="Header"><Data ss:Type="String"></Data></Cell>')
        xml_lines.append('    <Cell ss:StyleID="Header"><Data ss:Type="String"></Data></Cell>')
        xml_lines.append(f'    <Cell ss:StyleID="Header"><Data ss:Type="Number">{total_range}</Data></Cell>')
        xml_lines.append(f'    <Cell ss:StyleID="Header"><Data ss:Type="Number">{total_lifetime}</Data></Cell>')
        xml_lines.append('    <Cell ss:StyleID="Header"><Data ss:Type="String"></Data></Cell>')
        xml_lines.append('    <Cell ss:StyleID="Header"><Data ss:Type="String"></Data></Cell>')
        xml_lines.append('   </Row>')

        xml_lines.extend([
            '  </Table>',
            ' </Worksheet>',
            '</Workbook>'
        ])

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(xml_lines))
        return filepath

    @staticmethod
    def export_html_report(
        printers: List[Dict[str, Any]],
        filepath: str,
        section_name: str = "Fleet",
        start_date: str = "",
        end_date: str = ""
    ) -> str:
        """Generates an HTML report with Date Range and Lifetime prints."""
        now_str = datetime.now().strftime("%d-%b-%Y %I:%M %p")
        total_printers = len(printers)
        online_count = sum(1 for p in printers if p.get("status") == "ONLINE")
        total_lifetime = sum(p.get("total_till_date", 0) or 0 for p in printers)
        total_range = sum(p.get("range_print_count", 0) or 0 for p in printers)

        rows_html = []
        for idx, p in enumerate(printers, 1):
            r_cnt = p.get("range_print_count", 0) or 0
            l_cnt = p.get("total_till_date", 0) or 0
            status = p.get("status", "ONLINE")

            badge_cls = "online" if status == "ONLINE" else "offline"
            badge_html = f'<span class="badge {badge_cls}">{status}</span>'

            rows_html.append(f"""
            <tr>
                <td>{idx}</td>
                <td><span class="type-tag">{p.get('printer_type', '')}</span></td>
                <td><strong>{p.get('name', '')}</strong><br><small class="text-muted">{p.get('mfg', '')}</small></td>
                <td><code>{p.get('identifier', '')}</code></td>
                <td>{p.get('department', '-')}<br><small class="text-muted">{p.get('location', '')}</small></td>
                <td>{p.get('model') or p.get('driver') or '-'}</td>
                <td class="text-right range-val">+{r_cnt:,}</td>
                <td class="text-right"><strong>{l_cnt:,}</strong></td>
                <td>{badge_html}</td>
                <td><small>{p.get('last_checked', '-')}</small></td>
            </tr>
            """)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{APP_NAME} - {section_name} Printer Report</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; margin: 24px; background: #f8fafc; color: #1e293b; }}
    .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #cbd5e1; padding-bottom: 16px; margin-bottom: 24px; }}
    .header h1 {{ margin: 0; font-size: 22px; color: #0f172a; }}
    .dev-badge {{ display: inline-block; background: #2563eb; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-left: 8px; }}
    .header .meta {{ color: #64748b; font-size: 13px; text-align: right; }}
    .cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
    .card {{ background: white; padding: 16px 20px; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
    .card .label {{ font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase; }}
    .card .value {{ font-size: 24px; font-weight: 700; color: #1e293b; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; }}
    th {{ background: #0f172a; color: white; text-align: left; padding: 12px 14px; font-size: 13px; }}
    td {{ padding: 12px 14px; border-bottom: 1px solid #f1f5f9; font-size: 13px; }}
    tr:hover {{ background: #f8fafc; }}
    .text-right {{ text-align: right; }}
    .text-muted {{ color: #64748b; font-size: 12px; }}
    .range-val {{ color: #0284c7; font-weight: 700; }}
    code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 13px; color: #0f172a; }}
    .type-tag {{ background: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 11px; }}
    .badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; }}
    .badge.online {{ background: #dcfce7; color: #15803d; }}
    .badge.offline {{ background: #fee2e2; color: #b91c1c; }}
    .btn-print {{ background: #2563eb; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; }}
    @media print {{
        body {{ background: white; margin: 0; }}
        .btn-print {{ display: none; }}
    }}
</style>
</head>
<body>
    <div class="header">
        <div>
            <h1>{APP_NAME} v{APP_VERSION} &bull; {section_name} Printers <span class="dev-badge">{get_developer_credit()}</span></h1>
            <div style="margin-top: 6px; color: #64748b;">Date Range Window: <strong>{start_date}</strong> to <strong>{end_date}</strong></div>
        </div>
        <div class="meta">
            <button class="btn-print" onclick="window.print()">Print / Save PDF</button><br><br>
            Generated: {now_str}
        </div>
    </div>

    <div class="cards">
        <div class="card">
            <div class="label">Total {section_name} Printers</div>
            <div class="value">{total_printers}</div>
        </div>
        <div class="card">
            <div class="label">Online Status</div>
            <div class="value" style="color: #15803d;">{online_count} / {total_printers}</div>
        </div>
        <div class="card">
            <div class="label">Date Range Prints ({start_date} to {end_date})</div>
            <div class="value" style="color: #0284c7;">+{total_range:,}</div>
        </div>
        <div class="card">
            <div class="label">Total Print Till Date (Lifetime)</div>
            <div class="value">{total_lifetime:,}</div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Type</th>
                <th>Printer Name / Mfg</th>
                <th>Port / IP</th>
                <th>Department / Desk</th>
                <th>Model / Driver</th>
                <th class="text-right">Date Range Prints</th>
                <th class="text-right">Total Print Till Date</th>
                <th>Status</th>
                <th>Last Checked</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows_html)}
        </tbody>
    </table>
</body>
</html>"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        return filepath
