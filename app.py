import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import folium_static
import io
from datetime import datetime, timezone, timedelta

# 📌 タイトル
st.title("📍 放射線ヒートマップ作成ツール")

# 📌 タイムゾーン設定
st.sidebar.header("🕐 タイムゾーン設定")
timezone_mode = st.sidebar.selectbox(
    "タイムゾーン変換モード",
    ["UTC→JST (UTC+9) 変換", "JST→UTC 変換", "変換なし"],
    help="accurad本体はUTC+9で表示、CSVはUTCで出力される場合に使用"
)

# 📌 CSVファイルアップロード
uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type=["csv"])

if uploaded_file is not None:
    # 📌 CSVをデータフレームとして読み込み
    df = pd.read_csv(uploaded_file, delimiter=";")  # 必要に応じてカンマ区切りに変更

    # 📌 カラム名の前後のスペースを削除
    df.columns = df.columns.str.strip()
    
    # 📌 タイムスタンプカラムを検索
    timestamp_columns = [col for col in df.columns if any(keyword in col.lower() for keyword in ['time', 'date', 'timestamp', '時刻', '日時'])]
    
    if timestamp_columns:
        st.sidebar.subheader("🕐 タイムスタンプ設定")
        selected_timestamp_col = st.sidebar.selectbox(
            "タイムスタンプカラムを選択",
            timestamp_columns,
            help="変換対象のタイムスタンプカラムを選択してください"
        )
        
        # 📌 タイムゾーン変換処理
        if timezone_mode != "変換なし":
            try:
                # タイムスタンプカラムをdatetime型に変換
                df[selected_timestamp_col] = pd.to_datetime(df[selected_timestamp_col])
                
                if timezone_mode == "UTC→JST (UTC+9) 変換":
                    # UTCからJST（UTC+9）に変換
                    df[selected_timestamp_col] = df[selected_timestamp_col].dt.tz_localize('UTC') + timedelta(hours=9)
                    st.sidebar.success("✅ UTC→JST変換を適用しました")
                elif timezone_mode == "JST→UTC 変換":
                    # JST（UTC+9）からUTCに変換
                    df[selected_timestamp_col] = df[selected_timestamp_col] - timedelta(hours=9)
                    st.sidebar.success("✅ JST→UTC変換を適用しました")
                
                # 変換後のタイムスタンプを表示
                st.sidebar.write("**変換後のタイムスタンプ例:**")
                st.sidebar.write(f"最初のレコード: {df[selected_timestamp_col].iloc[0]}")
                st.sidebar.write(f"最後のレコード: {df[selected_timestamp_col].iloc[-1]}")
                
            except Exception as e:
                st.sidebar.error(f"❌ タイムゾーン変換エラー: {str(e)}")
                st.sidebar.info("💡 タイムスタンプの形式を確認してください")
    else:
        st.sidebar.info("ℹ️ タイムスタンプカラムが見つかりませんでした")

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
        
        # 📌 タイムスタンプ情報の表示
        if timestamp_columns and selected_timestamp_col in df.columns:
            st.subheader("🕐 タイムスタンプ情報")
            
            # タイムスタンプの統計情報
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("データ数", len(df))
            with col2:
                st.metric("開始時刻", df[selected_timestamp_col].min().strftime("%Y-%m-%d %H:%M:%S"))
            with col3:
                st.metric("終了時刻", df[selected_timestamp_col].max().strftime("%Y-%m-%d %H:%M:%S"))
            
            # タイムスタンプの分布
            st.write("**タイムスタンプ分布:**")
            timestamp_counts = df[selected_timestamp_col].dt.date.value_counts().sort_index()
            st.bar_chart(timestamp_counts)
            
            # 変換されたCSVのダウンロード
            if timezone_mode != "変換なし":
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False, sep=';')
                st.download_button(
                    label="📥 変換済みCSVをダウンロード",
                    data=csv_buffer.getvalue(),
                    file_name=f"converted_{uploaded_file.name}",
                    mime="text/csv"
                )
