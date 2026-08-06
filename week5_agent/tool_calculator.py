"""
工具3：数学计算器
"""

import math
import re


# ==================== 工具函数 ====================
def calculate(expression: str) -> dict:
    """
    执行数学计算

    参数:
        expression: 数学表达式，如 "2 + 3 * 4"

    返回:
        计算结果
    """
    # 安全检查：只允许数字和基本运算符
    allowed_chars = r'[\d+\-*/().% ]'
    if not re.match(f'^{allowed_chars}+$', expression):
        return {
            "expression": expression,
            "error": "表达式包含非法字符",
            "result": None
        }

    try:
        # 安全执行计算
        result = eval(expression, {"__builtins__": {}}, {"math": math})
        return {
            "expression": expression,
            "result": result,
            "error": None
        }
    except Exception as e:
        return {
            "expression": expression,
            "result": None,
            "error": str(e)
        }


# ==================== 工具描述 ====================
def get_tool_description():
    return {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算，支持加减乘除、括号、百分比等基本运算",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，如 '2 + 3 * 4' 或 '(10 + 5) / 3'"
                    }
                },
                "required": ["expression"]
            }
        }
    }


# ==================== 测试 ====================
if __name__ == "__main__":
    print("=" * 50)
    print("🧮 计算器工具测试")
    print("=" * 50)

    test_cases = ["2 + 3 * 4", "(10 + 5) / 3", "2 ** 10"]
    for expr in test_cases:
        result = calculate(expr)
        print(f"{expr} = {result['result']}")