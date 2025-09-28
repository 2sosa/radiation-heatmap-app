import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import folium_static
import io
from datetime import datetime, timedelta
import pytz

# 📌 タイトル
st.title("📍 放射線ヒートマップ作成ツール")

# 📌 CSVファイルアップロード
uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type=["csv"])

if uploaded_file is not None:
    # 📌 CSVをデータフレームとして読み込み
    df = pd.read_csv(uploaded_file, delimiter=";")  # 必要に応じてカンマ区切りに変更

    # 📌 カラム名の前後のスペースを削除
    df.columns = df.columns.str.strip()

    # 📌 タイムスタンプカラムを検出（一般的な名前パターン）
    timestamp_columns = []
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ['timestamp', 'time', 'date', 'datetime', '時刻', '日時']):
            timestamp_columns.append(col)
    
    # 📌 タイムスタンプ変換処理
    if timestamp_columns:
        st.info(f"⏰ タイムスタンプカラムを検出しました: {', '.join(timestamp_columns)}")
        
        # UTC+9（日本標準時）のタイムゾーン設定
        jst = pytz.timezone('Asia/Tokyo')
        utc = pytz.UTC
        
        for col in timestamp_columns:
            try:
                # タイムスタンプをdatetimeに変換
                df[f'{col}_UTC'] = pd.to_datetime(df[col])
                
                # UTCとして解釈し、JSTに変換
                df[f'{col}_JST'] = df[f'{col}_UTC'].dt.tz_localize(utc).dt.tz_convert(jst)
                
                # 表示用に文字列形式も追加
                df[f'{col}_JST_str'] = df[f'{col}_JST'].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                st.success(f"✅ {col} をUTCからJST（UTC+9）に変換しました")
            except Exception as e:
                st.warning(f"⚠️ {col} の変換中にエラーが発生しました: {str(e)}")
    
    # 📌 データプレビュー表示（タイムスタンプ変換後）
    with st.expander("📊 データプレビュー（最初の10行）"):
        st.dataframe(df.head(10))
    
    # 📌 必要なカラムがあるかチェック
    required_columns = ['Latitude (°)', 'Longitude (°)', 'Dose rate (gamma) (µSv/h)']
    if not all(col in df.columns for col in required_columns):
        st.error("❌ 必要なカラムが見つかりません。CSVを確認してください。")
    else:
        # 📌 タイムスタンプフィルタリング機能
        df_to_use = df.copy()
        
        # JSTタイムスタンプカラムが存在する場合、フィルタリングオプションを提供
        jst_columns = [col for col in df.columns if col.endswith('_JST')]
        if jst_columns:
            st.subheader("⏱️ タイムスタンプフィルタリング")
            
            # 使用するタイムスタンプカラムを選択
            selected_timestamp_col = st.selectbox(
                "フィルタリングに使用するタイムスタンプカラムを選択:",
                jst_columns,
                format_func=lambda x: x.replace('_JST', ' (JST変換済み)')
            )
            
            # 日付範囲選択
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "開始日（JST）",
                    value=df[selected_timestamp_col].min().date() if pd.notna(df[selected_timestamp_col].min()) else None
                )
                start_time = st.time_input("開始時刻（JST）", value=datetime.min.time())
            
            with col2:
                end_date = st.date_input(
                    "終了日（JST）",
                    value=df[selected_timestamp_col].max().date() if pd.notna(df[selected_timestamp_col].max()) else None
                )
                end_time = st.time_input("終了時刻（JST）", value=datetime.max.time())
            
            # フィルタリング実行
            if st.button("🔍 タイムスタンプでフィルタリング"):
                jst = pytz.timezone('Asia/Tokyo')
                start_datetime = jst.localize(datetime.combine(start_date, start_time))
                end_datetime = jst.localize(datetime.combine(end_date, end_time))
                
                # フィルタリング
                mask = (df[selected_timestamp_col] >= start_datetime) & (df[selected_timestamp_col] <= end_datetime)
                df_to_use = df[mask].copy()
                
                st.info(f"📊 フィルタリング結果: {len(df_to_use)} / {len(df)} 行")
                
                # フィルタリング後のデータプレビュー
                with st.expander("フィルタリング後のデータプレビュー"):
                    st.dataframe(df_to_use.head(10))
        
        # 📌 NaNを除外
        df_filtered = df_to_use[required_columns].dropna()
        
        if len(df_filtered) == 0:
            st.warning("⚠️ フィルタリング後のデータが空です。条件を調整してください。")
        else:
            # 📌 データ統計情報の表示
            st.subheader("📊 データ統計")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("データポイント数", len(df_filtered))
            with col2:
                st.metric("平均線量率 (µSv/h)", f"{df_filtered['Dose rate (gamma) (µSv/h)'].mean():.3f}")
            with col3:
                st.metric("最大線量率 (µSv/h)", f"{df_filtered['Dose rate (gamma) (µSv/h)'].max():.3f}")

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
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📥 ヒートマップをダウンロード",
                    data=heatmap_html.getvalue(),
                    file_name="radiation_heatmap.html",
                    mime="text/html"
                )
            
            # 📌 フィルタリングされたCSVのダウンロード
            with col2:
                # タイムスタンプ変換情報を含むCSVを作成
                csv_buffer = io.StringIO()
                df_to_use.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()
                
                st.download_button(
                    label="📥 処理済みCSVをダウンロード",
                    data=csv_data,
                    file_name="processed_radiation_data.csv",
                    mime="text/csv"
                )
