import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import folium_static
import io
import datetime
from datetime import timezone, timedelta
import pytz

# 📌 タイトル
st.title("📍 放射線ヒートマップ作成ツール")

# 📌 タイムスタンプ変換関数
def convert_accurad_timestamp_to_utc(timestamp_str, source_timezone='Asia/Tokyo'):
    """
    AccuradのタイムスタンプをUTC+9（日本時間）からUTCに変換する
    
    Args:
        timestamp_str: タイムスタンプ文字列（例: "2023-12-01 12:00:00"）
        source_timezone: ソースタイムゾーン（デフォルト: Asia/Tokyo）
    
    Returns:
        UTC時刻の文字列
    """
    try:
        # 様々な日時フォーマットに対応
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S", 
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S.%f"
        ]
        
        parsed_dt = None
        for fmt in formats:
            try:
                parsed_dt = datetime.datetime.strptime(timestamp_str, fmt)
                break
            except ValueError:
                continue
        
        if parsed_dt is None:
            raise ValueError(f"タイムスタンプフォーマットが認識できません: {timestamp_str}")
        
        # タイムゾーン情報を設定
        source_tz = pytz.timezone(source_timezone)
        localized_dt = source_tz.localize(parsed_dt)
        
        # UTCに変換
        utc_dt = localized_dt.astimezone(pytz.UTC)
        
        return utc_dt.strftime("%Y-%m-%d %H:%M:%S")
        
    except Exception as e:
        st.error(f"タイムスタンプ変換エラー: {e}")
        return timestamp_str

def convert_utc_to_local_timezone(timestamp_str, target_timezone='Asia/Tokyo'):
    """
    UTCタイムスタンプを指定のタイムゾーンに変換する
    
    Args:
        timestamp_str: UTCタイムスタンプ文字列
        target_timezone: ターゲットタイムゾーン（デフォルト: Asia/Tokyo）
    
    Returns:
        ローカル時刻の文字列
    """
    try:
        # UTCタイムスタンプをパース
        utc_dt = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        utc_dt = pytz.UTC.localize(utc_dt)
        
        # ターゲットタイムゾーンに変換
        target_tz = pytz.timezone(target_timezone)
        local_dt = utc_dt.astimezone(target_tz)
        
        return local_dt.strftime("%Y-%m-%d %H:%M:%S")
        
    except Exception as e:
        st.error(f"タイムゾーン変換エラー: {e}")
        return timestamp_str

def match_timestamps_with_tolerance(df1, df2, time_col1, time_col2, tolerance_minutes=5):
    """
    2つのデータフレーム間でタイムスタンプを突合する
    
    Args:
        df1, df2: 比較するデータフレーム
        time_col1, time_col2: それぞれのタイムスタンプカラム名
        tolerance_minutes: 許容誤差（分）
    
    Returns:
        突合結果のデータフレーム
    """
    try:
        # タイムスタンプを datetime に変換
        df1[time_col1] = pd.to_datetime(df1[time_col1])
        df2[time_col2] = pd.to_datetime(df2[time_col2])
        
        matches = []
        tolerance = pd.Timedelta(minutes=tolerance_minutes)
        
        for idx1, row1 in df1.iterrows():
            timestamp1 = row1[time_col1]
            
            # 許容範囲内のタイムスタンプを検索
            time_diff = abs(df2[time_col2] - timestamp1)
            matching_indices = df2[time_diff <= tolerance].index
            
            if len(matching_indices) > 0:
                # 最も近い時刻を選択
                closest_idx = df2.loc[matching_indices, time_col2].sub(timestamp1).abs().idxmin()
                closest_row = df2.loc[closest_idx]
                time_difference = abs(closest_row[time_col2] - timestamp1).total_seconds() / 60
                
                matches.append({
                    'データ1_インデックス': idx1,
                    'データ2_インデックス': closest_idx,
                    'データ1_タイムスタンプ': timestamp1,
                    'データ2_タイムスタンプ': closest_row[time_col2],
                    '時刻差_分': round(time_difference, 2)
                })
        
        return pd.DataFrame(matches)
        
    except Exception as e:
        st.error(f"タイムスタンプ突合エラー: {e}")
        return pd.DataFrame()

# 📌 タイムゾーン設定
st.sidebar.header("⚙️ 設定")

# タイムゾーン選択
timezone_options = {
    'Asia/Tokyo': 'UTC+9 (日本標準時)',
    'UTC': 'UTC (協定世界時)',
    'Asia/Seoul': 'UTC+9 (韓国標準時)',
    'America/New_York': 'UTC-5/-4 (東部標準時)',
    'Europe/London': 'UTC+0/+1 (グリニッジ標準時)',
    'Asia/Shanghai': 'UTC+8 (中国標準時)'
}

selected_timezone = st.sidebar.selectbox(
    "Accuradデータのタイムゾーン",
    options=list(timezone_options.keys()),
    format_func=lambda x: timezone_options[x],
    index=0  # デフォルトは日本時間
)

# タイムスタンプ変換オプション
convert_timestamps = st.sidebar.checkbox(
    "タイムスタンプをUTCに変換",
    value=True,
    help="Accuradの表示時刻（UTC+9）からCSV出力時刻（UTC）への変換を行います"
)

# 時差表示
if selected_timezone != 'UTC':
    tz = pytz.timezone(selected_timezone)
    now = datetime.datetime.now(tz)
    utc_offset = now.utcoffset().total_seconds() / 3600
    st.sidebar.info(f"選択されたタイムゾーンのUTC時差: {utc_offset:+.0f}時間")

# 📌 タイムスタンプ変換テスト
st.sidebar.subheader("🧪 変換テスト")
test_timestamp = st.sidebar.text_input(
    "テスト用タイムスタンプ", 
    "2023-12-01 12:00:00",
    help="例: 2023-12-01 12:00:00"
)

if st.sidebar.button("変換テスト実行"):
    if test_timestamp:
        converted = convert_accurad_timestamp_to_utc(test_timestamp, selected_timezone)
        back_converted = convert_utc_to_local_timezone(converted, selected_timezone)
        
        st.sidebar.write("**変換結果:**")
        st.sidebar.write(f"元の時刻: {test_timestamp}")
        st.sidebar.write(f"UTC変換後: {converted}")
        st.sidebar.write(f"逆変換: {back_converted}")
        
        # 変換例の表示
        st.sidebar.success("✅ 変換テスト完了")
        
        # 実際の例（Accuradの問題例）
        st.sidebar.write("**Accurad問題例:**")
        st.sidebar.write("- Accurad表示: 12:00 (UTC+9)")
        st.sidebar.write("- CSV出力: 03:00 (UTC)")
        st.sidebar.write("- 時差: 9時間")

# 📌 動作モード選択
mode = st.radio(
    "動作モード選択",
    ["単一ファイル処理", "複数ファイル比較"],
    help="単一ファイル: ヒートマップ作成、複数ファイル: タイムスタンプ突合"
)

if mode == "単一ファイル処理":
    # 📌 CSVファイルアップロード
    uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type=["csv"])
else:
    # 📌 複数ファイル比較モード
    st.subheader("📊 複数ファイル比較（タイムスタンプ突合）")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**ファイル1**")
        file1 = st.file_uploader("1つ目のCSVファイル", type=["csv"], key="file1")
    with col2:
        st.write("**ファイル2**")  
        file2 = st.file_uploader("2つ目のCSVファイル", type=["csv"], key="file2")
    
    # 許容誤差設定
    tolerance = st.slider("タイムスタンプ突合の許容誤差（分）", 1, 60, 5)
    
    if file1 is not None and file2 is not None:
        # ファイル読み込み
        df1 = pd.read_csv(file1, delimiter=";")
        df2 = pd.read_csv(file2, delimiter=";")
        
        df1.columns = df1.columns.str.strip()
        df2.columns = df2.columns.str.strip()
        
        # タイムスタンプカラム選択
        timestamp_cols1 = [col for col in df1.columns if any(keyword in col.lower() for keyword in ['time', 'date', 'timestamp', '時刻', '日時'])]
        timestamp_cols2 = [col for col in df2.columns if any(keyword in col.lower() for keyword in ['time', 'date', 'timestamp', '時刻', '日時'])]
        
        if timestamp_cols1 and timestamp_cols2:
            col1, col2 = st.columns(2)
            with col1:
                selected_time_col1 = st.selectbox("ファイル1のタイムスタンプカラム", timestamp_cols1)
            with col2:
                selected_time_col2 = st.selectbox("ファイル2のタイムスタンプカラム", timestamp_cols2)
            
            if st.button("タイムスタンプ突合を実行"):
                # タイムスタンプ変換（必要な場合）
                if convert_timestamps and selected_timezone != 'UTC':
                    df1[f"{selected_time_col1}_UTC"] = df1[selected_time_col1].apply(
                        lambda x: convert_accurad_timestamp_to_utc(str(x), selected_timezone) if pd.notna(x) else x
                    )
                    df2[f"{selected_time_col2}_UTC"] = df2[selected_time_col2].apply(
                        lambda x: convert_accurad_timestamp_to_utc(str(x), selected_timezone) if pd.notna(x) else x
                    )
                    use_col1 = f"{selected_time_col1}_UTC"
                    use_col2 = f"{selected_time_col2}_UTC"
                else:
                    use_col1 = selected_time_col1
                    use_col2 = selected_time_col2
                
                # 突合実行
                matches = match_timestamps_with_tolerance(df1, df2, use_col1, use_col2, tolerance)
                
                if not matches.empty:
                    st.success(f"✅ {len(matches)}件のタイムスタンプが突合されました")
                    
                    # 統計情報表示
                    st.subheader("📈 突合統計")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("突合件数", len(matches))
                    with col2:
                        st.metric("平均時刻差", f"{matches['時刻差_分'].mean():.2f}分")
                    with col3:
                        st.metric("最大時刻差", f"{matches['時刻差_分'].max():.2f}分")
                    
                    # 突合結果表示
                    st.subheader("📋 突合結果")
                    st.dataframe(matches)
                    
                    # 突合結果ダウンロード
                    csv_buffer = io.StringIO()
                    matches.to_csv(csv_buffer, index=False)
                    st.download_button(
                        label="📥 突合結果をダウンロード",
                        data=csv_buffer.getvalue(),
                        file_name="timestamp_matching_results.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("⚠️ 指定された許容誤差内で突合できるタイムスタンプが見つかりませんでした")
        else:
            st.error("❌ タイムスタンプカラムが見つかりません")
    
    uploaded_file = None  # 単一ファイル処理を無効化

if uploaded_file is not None:
    # 📌 CSVをデータフレームとして読み込み
    df = pd.read_csv(uploaded_file, delimiter=";")  # 必要に応じてカンマ区切りに変更

    # 📌 カラム名の前後のスペースを削除
    df.columns = df.columns.str.strip()
    
    # 📌 データ概要を表示
    st.subheader("📊 データ概要")
    st.write(f"総レコード数: {len(df)}")
    st.write("カラム一覧:")
    for col in df.columns:
        st.write(f"  - {col}")

    # 📌 タイムスタンプカラムを検出
    timestamp_columns = []
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ['time', 'date', 'timestamp', '時刻', '日時']):
            timestamp_columns.append(col)
    
    if timestamp_columns:
        st.write(f"検出されたタイムスタンプカラム: {timestamp_columns}")
        
        # 📌 タイムスタンプ変換処理
        if convert_timestamps and selected_timezone != 'UTC':
            st.subheader("🕒 タイムスタンプ変換")
            conversion_results = []
            
            for col in timestamp_columns:
                if col in df.columns:
                    st.write(f"変換中: {col}")
                    
                    # サンプルデータを表示
                    sample_original = df[col].dropna().iloc[0] if not df[col].dropna().empty else "N/A"
                    
                    if sample_original != "N/A":
                        # 変換例を表示
                        sample_converted = convert_accurad_timestamp_to_utc(str(sample_original), selected_timezone)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**変換前** ({timezone_options[selected_timezone]})")
                            st.code(sample_original)
                        with col2:
                            st.write("**変換後** (UTC)")
                            st.code(sample_converted)
                        
                        # データフレーム全体を変換
                        df[f"{col}_UTC"] = df[col].apply(
                            lambda x: convert_accurad_timestamp_to_utc(str(x), selected_timezone) if pd.notna(x) else x
                        )
                        
                        conversion_results.append({
                            'カラム': col,
                            '変換前サンプル': sample_original,
                            '変換後サンプル': sample_converted,
                            '時差': f"{pytz.timezone(selected_timezone).localize(datetime.datetime.now()).utcoffset().total_seconds() / 3600:+.0f}時間"
                        })
            
            if conversion_results:
                st.write("### 変換結果サマリー")
                st.dataframe(pd.DataFrame(conversion_results))

    # 📌 必要なカラムがあるかチェック
    required_columns = ['Latitude (°)', 'Longitude (°)', 'Dose rate (gamma) (µSv/h)']
    if not all(col in df.columns for col in required_columns):
        st.error("❌ 必要なカラムが見つかりません。CSVを確認してください。")
        st.write("利用可能なカラム:")
        for col in df.columns:
            st.write(f"  - {col}")
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
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📥 ヒートマップをダウンロード",
                data=heatmap_html.getvalue(),
                file_name="radiation_heatmap.html",
                mime="text/html"
            )
        
        with col2:
            # 📌 変換済みCSVのダウンロード
            if convert_timestamps and timestamp_columns:
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False, sep=";")
                
                st.download_button(
                    label="📥 変換済みCSVをダウンロード",
                    data=csv_buffer.getvalue(),
                    file_name="converted_radiation_data.csv",
                    mime="text/csv",
                    help="タイムスタンプがUTCに変換されたCSVファイル"
                )
