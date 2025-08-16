from typing import List
from .elk import NlpRequest
def print_nlp_request_html(nlp_requests: List[NlpRequest], filename: str = "nlp_requests.html"):
    """
    将NlpRequest列表输出到HTML文件中的表格
    
    Args:
        nlp_requests: NlpRequest对象列表
        filename: 输出的HTML文件名
    """
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NLP Requests</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f7fa;
            margin: 0;
            padding: 20px;
        }
        .container {
            width: 100%;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
        }
        table {
            width: 90%;
            border-collapse: collapse;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            background-color: white;
            border-radius: 8px;
            overflow: visible;
            margin: 0 auto;
        }
        th {
            background-color: #3498db;
            color: white;
            text-align: left;
            padding: 12px 15px;
            font-weight: 600;
        }
        tbody {
            font-family: 'Courier New', Courier, monospace;
        }
        tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        tr:hover {
            background-color: #e3f2fd;
        }
        td, th {
            padding: 10px 15px;
            border-bottom: 1px solid #eee;
        }
        .cell-content {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .no-wrap {
            white-space: nowrap;
        }
        .query-cell {
            display: flex;
            align-items: center;
        }
        .header-cell {
            position: sticky;
            top: 0;
        }
        .tooltip {
            position: relative;
            display: inline-block;
            overflow: visible;
        }
        .tooltip .tooltiptext {
            visibility: hidden;
            display: block;
            max-width: 900px;
            background-color: #ffffff;
            color: #222222;
            text-align: left;
            border-radius: 6px;
            padding: 12px;
            position: absolute;
            z-index: 99999;
            bottom: 125%;
            left: 50%;
            transform: translateX(-50%);
            opacity: 0;
            transition: opacity 0.18s ease;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 14px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.08);
            border: 1px solid rgba(0,0,0,0.06);
            outline: 0;
            white-space: pre-wrap;
            word-break: break-word;
        }
        .tooltip .tooltiptext::after {
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: #ffffff transparent transparent transparent;
        }
        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        .tooltip-table {
            width: auto;
            border-collapse: collapse;
            margin: 0;
        }
        .tooltip-table td {
            padding: 4px 8px;
            border: none;
            font-size: 14px;
            background-color: transparent;
            color: #222222;
            white-space: nowrap;
        }
        .tooltip-table tr:nth-child(odd) {
            background-color: transparent;
        }
        .tooltip-table tr:hover {
            background-color: rgba(255, 255, 255, 0.02);
        }
        .property-name {
            font-weight: bold;
            width: auto;
            white-space: nowrap;
        }
        .img-icon {
            display: inline-block;
            position: relative;
            cursor: pointer;
            margin-right: 8px;
            vertical-align: middle;
        }
        .material-icon-svg {
            width: 24px;
            height: 24px;
            fill: #1a73e8; /* A vibrant Google-like blue */
            transition: transform 0.2s ease;
        }
        .img-icon:hover .material-icon-svg {
            transform: scale(1.2);
        }
        .img-icon .imgtooltip {
            visibility: hidden;
            position: absolute;
            bottom: 125%;
            left: 50%;
            transform: translateX(-50%);
            z-index: 100000;
            max-width: 860px;
            max-height: 480px;
            padding: 0;
            background: transparent;
            opacity: 0;
            transition: opacity 0.18s ease;
        }
        .img-icon .imgtooltip img {
            display: block;
            max-width: 860px;
            max-height: 480px;
            width: auto;
            height: auto;
            border-radius: 6px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.08);
        }
        .img-icon:hover .imgtooltip {
            visibility: visible;
            opacity: 1;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>NLP Requests</h1>
        <table>
            <thead>
            <tr>
                    <th class="header-cell">No.</th>
                    <th class="header-cell">Timestamp</th>
                    <th class="header-cell">Trace ID</th>
                    <th class="header-cell">Device ID</th>
                    <th class="header-cell">Glass Device ID</th>
                    <th class="header-cell">Glass Product</th>
                    <th class="header-cell">Location</th>
                    <th class="header-cell">Query</th>
                </tr>
            </thead>
            <tbody>
"""

    for idx, request in enumerate(nlp_requests, 1):
        location_str = ''
        try:
            loc = getattr(request, 'location', None)
            if loc and len(loc) >= 2:
                lon = float(loc[0])
                lat = float(loc[1])
                location_str = f"{lon:.5f},{lat:.5f}"
        except Exception:
            location_str = ''
        
        tooltip_content = f'''
        <table class="tooltip-table">
            <tr><td class="property-name">Timestamp</td><td>{request.timestamp or ''}</td></tr>
            <tr><td class="property-name">Session ID</td><td>{request.session_id or ''}</td></tr>
            <tr><td class="property-name">Trace ID</td><td>{request.trace_id or ''}</td></tr>
            <tr><td class="property-name">Account ID</td><td>{request.account_id or ''}</td></tr>
            <tr><td class="property-name">Device ID</td><td>{request.device_id or ''}</td></tr>
            <tr><td class="property-name">Glass Device ID</td><td>{request.glass_device_id or ''}</td></tr>
            <tr><td class="property-name">IoT Device ID</td><td>{request.iot_device_id or ''}</td></tr>
            <tr><td class="property-name">Glass Product</td><td>{str(request.glass_product)}</td></tr>
            <tr><td class="property-name">Function Type</td><td>{str(request.function_type) if request.function_type is not None else ''}</td></tr>
            <tr><td class="property-name">Origin Type</td><td>{str(request.origin_type) if request.origin_type is not None else ''}</td></tr>
            <tr><td class="property-name">Time Zone</td><td>{request.time_zone or ''}</td></tr>
            <tr><td class="property-name">Location</td><td>{location_str}</td></tr>
            <tr><td class="property-name">Query</td><td>{request.query or ''}</td></tr>
        </table>
        '''

        query_text = request.query or ''
        img_icon_html = ''
        try:
            files_check = getattr(request, 'files', None)
            if files_check and isinstance(files_check, list) and len(files_check) > 0 and isinstance(files_check[0], str) and files_check[0].strip():
                img_url = files_check[0]
                material_icon_svg = '<svg class="material-icon-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg>'
                img_icon_html = (
                    f'<span class="img-icon">{material_icon_svg}'
                    f'<span class="imgtooltip"><img src="{img_url}" alt="attachment"/></span>'
                    f'</span>'
                )
        except Exception:
            pass

        html_content += f'''
                <tr>
                    <td><div class="tooltip"><div class="cell-content">{idx}</div><span class="tooltiptext">{tooltip_content}</span></div></td>
                    <td><div class="tooltip"><div class="cell-content">{request.timestamp or ''}</div><span class="tooltiptext">{tooltip_content}</span></div></td>
                    <td><div class="tooltip"><div class="cell-content">{request.trace_id or ''}</div><span class="tooltiptext">{tooltip_content}</span></div></td>
                    <td><div class="tooltip"><div class="cell-content">{request.device_id or ''}</div><span class="tooltiptext">{tooltip_content}</span></div></td>
                    <td><div class="tooltip"><div class="cell-content">{request.glass_device_id or ''}</div><span class="tooltiptext">{tooltip_content}</span></div></td>
                    <td><div class="tooltip"><div class="cell-content">{str(request.glass_product)}</div><span class="tooltiptext">{tooltip_content}</span></div></td>
                    <td><div class="tooltip"><div class="cell-content">{location_str}</div><span class="tooltiptext">{tooltip_content}</span></div></td>
                    <td class="query-cell">
                        {img_icon_html}
                        <div class="tooltip"><div class="cell-content">{query_text}</div><span class="tooltiptext">{tooltip_content}</span></div>
                    </td>
                </tr>
'''

    html_content += """
            </tbody>
        </table>
    </div>
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        function positionTooltip(container, tooltip) {
            tooltip.style.visibility = 'visible';
            tooltip.style.opacity = '1';

            const rect = tooltip.getBoundingClientRect();

            tooltip.style.bottom = '125%';
            tooltip.style.top = 'auto';
            tooltip.style.transform = 'translateX(-50%)';

            if (rect.top < 0) {
                tooltip.style.bottom = 'auto';
                tooltip.style.top = '125%';
            }

            const finalRect = tooltip.getBoundingClientRect();
            if (finalRect.bottom > window.innerHeight) {
                tooltip.style.top = 'auto';
                tooltip.style.bottom = '100%';
            }
        }

        document.querySelectorAll('.tooltip').forEach(container => {
            const tooltip = container.querySelector('.tooltiptext');
            if (!tooltip) return;

            container.addEventListener('mouseover', () => positionTooltip(container, tooltip));
            container.addEventListener('mouseout', () => {
                tooltip.style.visibility = 'hidden';
                tooltip.style.opacity = '0';
            });
        });

        document.querySelectorAll('.img-icon').forEach(container => {
            const tooltip = container.querySelector('.imgtooltip');
            if (!tooltip) return;

            container.addEventListener('mouseover', () => positionTooltip(container, tooltip));
            container.addEventListener('mouseout', () => {
                tooltip.style.visibility = 'hidden';
                tooltip.style.opacity = '0';
            });
        });
    });
    </script>
</body>
</html>
"""

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)