import re


############################################################################################################
def extract_json_from_codeblock(text: str) -> str:
    """从Markdown代码块中提取JSON内容"""
    pattern = r"```json\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return ""
