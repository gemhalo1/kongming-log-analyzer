from typing import List
from .model import DialogRound

from .utils import convert_timestamp

def print_dialog_round_table(rounds: List[DialogRound]):
    """
    使用rich库打印DialogRound表格
    
    Args:
        rounds: DialogRound对象列表
    """
    from rich.table import Table
    from rich.console import Console
    from rich.style import Style

    console = Console()
    
    # 创建表格
    table = Table(title="对话记录", show_header=True, header_style="bold magenta")
    
    # 添加列
    table.add_column("No.", style="dim", width=5, no_wrap=True)  # 序号列
    table.add_column("Timestamp", style="dim", no_wrap=True)  # 不换行
    # table.add_column("Session ID", width=36)
    table.add_column("Trace ID", no_wrap=True)
    # table.add_column("Account ID", width=15)
    table.add_column("Device ID", no_wrap=True)
    table.add_column("Glass Device ID", no_wrap=True)
    table.add_column("眼镜类型", no_wrap=True)
    table.add_column("Query", width=30)
    table.add_column("Intent", no_wrap=True)
    table.add_column("LLM Query", width=30)
    
    # 添加行数据
    for idx, round in enumerate(rounds, 1):  # 序号从1开始
        table.add_row(
            str(idx),  # 序号
            convert_timestamp(round.nlp_round.request_timestamp) if round.nlp_round.request_timestamp else "",
            # round.sessionId or "",
            round.traceId or "",
            round.deviceId or "",
            round.glassDeviceId or "",
            round.glassProduct or "",
            round.nlp_round.query or "",
            str(round.nlp_round.intent or ""),
            (round.llm_round.query or "") if round.llm_round else "",
            style=Style(bgcolor='light_sea_green') if round.llm_round else None
        )
    
    # 打印表格
    console.print(table)
