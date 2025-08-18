from typing import List
from .elk import NlpRequest

def print_nlp_request_table(nlp_requests: List[NlpRequest]):
    """
    使用rich库打印NlpRequest表格
    
    Args:
        nlp_requests: NlpRequest对象列表
    """
    from rich.table import Table
    from rich.console import Console

    console = Console()
    
    # 创建表格
    table = Table(title="NLP Requests", show_header=True, header_style="bold magenta")
    
    # 添加列
    table.add_column("No.", style="dim", no_wrap=True)  # 序号列
    table.add_column("Timestamp", style="dim", no_wrap=True)  # 不换行
    # table.add_column("Session ID", width=36)
    table.add_column("Trace ID", no_wrap=True)
    # table.add_column("Account ID", width=15)
    table.add_column("Device ID", no_wrap=True)
    table.add_column("Query", width=30)
    table.add_column("Intent", no_wrap=True)
    
    # 添加行数据
    for idx, request in enumerate(nlp_requests, 1):  # 序号从1开始
        table.add_row(
            str(idx),  # 序号
            request.timestamp or "",
            # request.session_id or "",
            request.trace_id or "",
            # request.account_id or "",
            request.device_id or "",
            request.query or "",
            '::'.join(request.intent) if request.intent else ""
        )
    
    # 打印表格
    console.print(table)
