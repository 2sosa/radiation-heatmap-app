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

    # 📌 タイムスタンプ（UTC）→ UTC+9(JST) へ自動変換
    def _detect_timestamp_columns(input_df: pd.DataFrame):
        candidates = []
        for col in input_df.columns:
            lower_name = str(col).lower()
            if any(key in lower_name for key in [
                "timestamp", "time", "date", "datetime", "時刻", "日時", "日付"
            ]):
                parsed = pd.to_datetime(input_df[col], errors='coerce', utc=True)
                ratio = parsed.notna().mean()
                if ratio >= 0.5:
                    candidates.append((col, ratio, ("utc" in lower_name) or ("z" in lower_name)))
        # 優先度: 列名にUTC/Zを含む > 解析成功率
        candidates.sort(key=lambda x: (x[2], x[1]), reverse=True)
        return [c[0] for c in candidates]

    def _to_utc_plus_9(series: pd.Series) -> pd.Series:
        parsed = pd.to_datetime(series, errors='coerce', utc=True)
        try:
            # タイムゾーン情報を保持したまま東京時間へ変換し、表示用途にNaiveへ
            return parsed.dt.tz_convert('Asia/Tokyo').dt.tz_localize(None)
        except Exception:
            # フォールバック: UTCとしてNaive化し+9時間加算（JSTは通年UTC+9）
            try:
                return parsed.dt.tz_localize(None) + pd.Timedelta(hours=9)
            except Exception:
                return pd.Series([pd.NaT] * len(series), index=series.index)

    timestamp_cols = _detect_timestamp_columns(df)
    selected_ts_col = timestamp_cols[0] if len(timestamp_cols) > 0 else None
    if selected_ts_col is not None:
        df['Timestamp (UTC+9)'] = _to_utc_plus_9(df[selected_ts_col])
        st.info(
            f"⏱️ タイムスタンプ列 '{selected_ts_col}' をUTCとして解釈し、UTC+9(Asia/Tokyo)に変換して突合します。"
        )
        # 必要に応じサンプル表示（過剰表示を避けるため最初の数行のみ）
        st.dataframe(df[[selected_ts_col, 'Timestamp (UTC+9)']].head(10))
    else:
        st.warning("⏱️ タイムスタンプ列が見つかりませんでした。CSVの日時列名をご確認ください。")

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
