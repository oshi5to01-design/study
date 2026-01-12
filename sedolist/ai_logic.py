import json
import os
import re
from typing import Any

import google_generativeai as genai
import streamlit as st
from dotenv import load_dotenv
from PIL import Image

# .envファイルの読み込み
load_dotenv()

# Google Generative AIの設定
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def analyze_image_with_gemini(uploaded_file: Any) -> dict[str, Any] | None:
    """画像を分析して商品情報を取得する"""
    try:
        # 画像を読み込む
        image = Image.open(uploaded_file)

        # model
        model = genai.GenerativeModel("models/gemini-flash-latest")

        # プロンプト
        prompt = """
        この画像を分析して、以下の情報を抽出してください。
        
        1.商品名(name):パッケージや値札から読み取れる具体的な商品名
        2.価格(price):値札に書かれている価格(数字のみ、円マークやカンマは除く)

        出力は必ず以下のJSON形式のみにしてください。余計な文章は不要です。
        {
            "name":"商品名",
            "price":1000
        }
        """

        # AIに聞く
        with st.spinner("AIが画像を解析中"):
            response = model.generate_content([prompt, image])  # type:ignore
            text = response.text

            match = re.search(r"\{.*\}", text, re.DOTALL)

            if match:
                json_str = match.group()
                result = json.loads(json_str)
                return result
            else:
                st.error("商品情報を抽出できませんでした")
                return None

    except Exception as e:
        st.error(f"商品情報を抽出できませんでした: {e}")
        return None
