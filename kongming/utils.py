from datetime import datetime, timedelta

def convert_timestamp(timestamp_str):
    """
    将UTC时间戳字符串转换为本地时间戳字符串
    
    Args:
        timestamp_str: UTC时间戳字符串，例如 "2025-08-18T20:06:10.149Z"
    
    Returns:
        本地时间戳字符串，格式为 "年-月-日 时:分:秒.毫秒"，例如 "2025-08-19 04:06:10.149"
    """
    utc_dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    local_dt = utc_dt.astimezone()
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")

def calculate_time_difference(timestamp_str1, timestamp_str2):
    """
    计算两个时间戳字符串之间的时间差

    Args:
        timestamp_str1: 第一个时间戳字符串，例如 "2025-08-18T20:06:10.149Z"
        timestamp_str2: 第二个时间戳字符串，例如 "2025-08-18T21:06:10.249Z"

    Returns:
        时间差，以秒为单位
    """
    dt1 = datetime.fromisoformat(timestamp_str1.replace('Z', '+00:00')).astimezone()
    dt2 = datetime.fromisoformat(timestamp_str2.replace('Z', '+00:00')).astimezone()
    return abs((dt2 - dt1).total_seconds())

def adjust_timestamp(timestamp_str, seconds):
    """
    将一个UTC时间戳字符串向前或向后调整指定的秒数。

    Args:
        timestamp_str (str): UTC时间戳字符串，例如 "2025-08-18T20:06:10.149Z"。
        seconds (float): 需要调整的秒数。正数表示向后调整（未来），
                         负数表示向前调整（过去）。

    Returns:
        str: 调整后的UTC时间戳字符串，格式与输入相同。
    """
    # 为了兼容旧版Python，我们将'Z'替换为'+00:00'
    utc_dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    adjusted_dt = utc_dt + timedelta(seconds=seconds)
    # .isoformat(timespec='milliseconds') 会生成 YYYY-MM-DDTHH:MM:SS.sss+00:00
    # 然后我们将其转换回Z格式
    return adjusted_dt.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
