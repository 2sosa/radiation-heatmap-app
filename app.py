import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import folium_static
import io

# 📌 タイトル
st.title("📍 放射線ヒートマップ作成ツール")

# 📌 CSVファイルアップロード
uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type=["csv"])

if uploaded_file is not None:
    # 📌 CSVをデータフレームとして読み込み
    df = pd.read_csv(uploaded_file, delimiter=";")  # 必要に応じてカンマ区切りに変更

    # 📌 カラム名の前後のスペースを削除
    df.columns = df.columns.str.strip()

    # 📌 必要なカラムがあるかチェック
    required_columns = ['Latitude (°)', 'Longitude (°)', 'Dose rate (gamma) (µSv/h)']
    if not all(col in df.columns for col in required_columns):
        st.error("❌ 必要なカラムが見つかりません。CSVを確認してください。")
    else:
        # 📌 NaNを除外
        df_filtered = df[required_columns].dropna()

        # 📌 ヒートマップデータ作成
        heat_data = df_filtered[['Latitude (°)', 'Longitude (°)', 'Dose rate (gamma) (µSv/h)']].values.tolist()

        # 📌 地図の中心を計算
        center_lat = df_filtered['Latitude (°)'].mean()
        center_lon = df_filtered['Longitude (°)'].mean()

        # 📌 地図を作成
        m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

        # 📌 ヒートマップを追加
        HeatMap(heat_data, radius=10, blur=15, max_zoom=13).add_to(m)

        # 📌 地図を表示
        folium_static(m)

        # 📌 ヒートマップをHTMLとして保存
        heatmap_html = io.BytesIO()
        m.save(heatmap_html, close_file=False)

        # 📌 ダウンロードボタン
        st.download_button(
            label="📥 ヒートマップをダウンロード",
            data=heatmap_html.getvalue(),
            file_name="radiation_heatmap.html",
            mime="text/html"
        )
