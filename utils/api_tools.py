"""
API 工具函数
"""

import os
import requests
import streamlit as st


def get_weather_amap(city: str) -> dict:
    """使用高德地图API查询真实天气"""
    api_key = os.getenv("AMAP_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("AMAP_API_KEY")
        except:
            pass

    if not api_key:
        return {"error": "❌ 高德API Key未配置"}

    try:
        geo_url = "https://restapi.amap.com/v3/geocode/geo"
        geo_params = {"key": api_key, "address": city}
        geo_resp = requests.get(geo_url, params=geo_params, timeout=10)
        geo_data = geo_resp.json()

        if geo_data.get("status") != "1" or not geo_data.get("geocodes"):
            return {"error": f"未找到城市：{city}"}

        adcode = geo_data["geocodes"][0]["adcode"]

        weather_url = "https://restapi.amap.com/v3/weather/weatherInfo"
        weather_params = {"key": api_key, "city": adcode, "extensions": "all"}
        weather_resp = requests.get(weather_url, params=weather_params, timeout=10)
        weather_data = weather_resp.json()

        if weather_data.get("status") != "1":
            return {"error": "天气查询失败"}

        forecast = weather_data["forecasts"][0]
        casts = forecast.get("casts", [])

        if not casts:
            return {"error": "暂无天气数据"}

        today = casts[0]
        tomorrow = casts[1] if len(casts) > 1 else None

        return {
            "city": forecast["city"],
            "today": {
                "date": today.get("date", ""),
                "weather": today.get("dayweather", ""),
                "temperature": f"{today.get('nighttemp', '')}°C ~ {today.get('daytemp', '')}°C",
                "wind": today.get("daywind", ""),
                "dayweather": today.get("dayweather", ""),
                "nightweather": today.get("nightweather", "")
            },
            "tomorrow": {
                "date": tomorrow.get("date", ""),
                "weather": tomorrow.get("dayweather", ""),
                "temperature": f"{tomorrow.get('nighttemp', '')}°C ~ {tomorrow.get('daytemp', '')}°C"
            } if tomorrow else None
        }
    except Exception as e:

        return {"error": f"查询失败：{str(e)}"}


# ==================== 文档解析 ====================

import io
import PyPDF2
import docx


def parse_uploaded_file(uploaded_file) -> str:
    """解析上传的文件内容"""
    filename = uploaded_file.name
    content = ""

    try:
        # TXT文件
        if filename.endswith(".txt"):
            content = uploaded_file.getvalue().decode("utf-8")

        # PDF文件
        elif filename.endswith(".pdf"):
            reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.getvalue()))
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    content += text + "\n"

        # Word文档
        elif filename.endswith(".docx"):
            doc = docx.Document(io.BytesIO(uploaded_file.getvalue()))
            for para in doc.paragraphs:
                if para.text:
                    content += para.text + "\n"

        else:
            return f"不支持的文件格式：{filename}"

        if not content.strip():
            return "文件内容为空"

        return content[:10000]  # 限制长度

    except Exception as e:
        return f"解析失败：{str(e)}"
