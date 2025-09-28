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

    # 📌 タイムスタンプ（UTC）→ローカル（UTC+オフセット）変換＆突合用フィルタ
    #    - CSV のタイムスタンプは UTC とみなす
    #    - Accurad 本体は UTC+9（既定）なので、オフセットを設定可能にする
    time_col_candidates = [
        c for c in df.columns
        if any(k in c.lower() for k in ["time", "timestamp", "date", "datetime", "日時", "時間"])
    ]
    selected_time_col = None
    if len(time_col_candidates) > 0:
        selected_time_col = st.sidebar.selectbox(
            "CSVのタイムスタンプ列 (UTC として解釈)", time_col_candidates, index=0
        )
        tz_offset_hours = st.sidebar.number_input(
            "デバイスのタイムゾーン (UTCからの時差・時間)", min_value=-12, max_value=14, value=9, step=1
        )

        # 文字列/数値/混在を許容して日時へ変換（UTCとして扱う）
        df["__timestamp_utc__"] = pd.to_datetime(df[selected_time_col], errors="coerce", utc=True)
        # ローカル相当（UTC+オフセット）を作成
        df["__timestamp_local__"] = df["__timestamp_utc__"] + pd.to_timedelta(tz_offset_hours, unit="h")

        valid_time_mask = df["__timestamp_local__"].notna()
        if valid_time_mask.any():
            min_time = df.loc[valid_time_mask, "__timestamp_local__"].min()
            max_time = df.loc[valid_time_mask, "__timestamp_local__"].max()
            # 範囲スライダーでローカル時刻のフィルタ（突合）
            if pd.notna(min_time) and pd.notna(max_time) and min_time != max_time:
                time_range = st.sidebar.slider(
                    "表示するローカル時刻の範囲",
                    min_value=min_time.to_pydatetime(),
                    max_value=max_time.to_pydatetime(),
                    value=(min_time.to_pydatetime(), max_time.to_pydatetime()),
                )
                time_mask = (
                    (df["__timestamp_local__"] >= pd.Timestamp(time_range[0])) &
                    (df["__timestamp_local__"] <= pd.Timestamp(time_range[1]))
                )
            else:
                time_mask = valid_time_mask

            df = df[time_mask]
            sign = "+" if tz_offset_hours >= 0 else ""
            st.info(f"タイムスタンプを UTC{sign}{tz_offset_hours} 相当に調整して突合しています。")

    # 📌 必要なカラムがあるかチェック
    required_columns = ['Latitude (°)', 'Longitude (°)', 'Dose rate (gamma) (µSv/h)']
    if not all(col in df.columns for col in required_columns):
        st.error("❌ 必要なカラムが見つかりません。CSVを確認してください。")
    else:
        # 📌 NaNを除外（時刻フィルタがあれば適用済の df に対して実施）
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
