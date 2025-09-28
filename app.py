import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import folium_static
import io
import json
import zipfile
from datetime import datetime, timedelta
import pytz
import tempfile
import os

# 📌 タイトル
st.title("📍 放射線ヒートマップ作成ツール")

# 📌 使用方法の説明
with st.expander("📖 使用方法"):
    st.markdown("""
    ### 📱 iPhoneでの使用手順
    1. **JSONファイルの準備**: 放射線測定データをJSON形式で準備します
    2. **ZIP圧縮**: JSONファイルが大量の場合は、ZIP形式に圧縮してください
    3. **ファイル選択**: iPhoneのファイルアプリから該当のZIPファイルを選択します
    4. **Pythonista3での読み取り**: アプリがZIPファイルを展開し、JSONデータを自動読み込みします
    
    ### 📊 必要なデータ形式
    JSONファイルには以下のデータが含まれている必要があります：
    - **緯度** (latitude, lat, 緯度など)
    - **経度** (longitude, lon, lng, 経度など)  
    - **線量率** (dose, radiation, 線量, µSv/h, uSv/hなど)
    - **タイムスタンプ** (timestamp, time, date, datetimeなど) ※オプション
    
    ### ✨ 機能
    - 自動カラム検出
    - タイムスタンプによるフィルタリング
    - インタラクティブなヒートマップ表示
    - 処理済みデータのダウンロード
    """)

# 📌 ZIPファイルアップロード（JSONファイル用）
uploaded_file = st.file_uploader("📂 JSONファイルを含むZIPファイルをアップロードしてください", type=["zip"])

def extract_json_from_zip(zip_file):
    """ZIPファイルからJSONファイルを抽出して読み込む"""
    json_data = []
    json_files_found = []
    
    try:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            # ZIPファイル内のファイル一覧を取得
            file_list = zip_ref.namelist()
            
            # JSONファイルを検索
            json_files = [f for f in file_list if f.lower().endswith('.json') and not f.startswith('__MACOSX/')]
            
            if not json_files:
                st.error("❌ ZIPファイル内にJSONファイルが見つかりませんでした。")
                return None, []
            
            st.info(f"📂 見つかったJSONファイル: {len(json_files)}個")
            
            # 各JSONファイルを読み込み
            for json_file in json_files:
                try:
                    with zip_ref.open(json_file) as f:
                        content = f.read().decode('utf-8')
                        json_content = json.loads(content)
                        
                        # JSONの構造に応じて処理
                        if isinstance(json_content, list):
                            json_data.extend(json_content)
                        elif isinstance(json_content, dict):
                            json_data.append(json_content)
                        
                        json_files_found.append(json_file)
                        st.success(f"✅ {json_file} を読み込みました")
                        
                except Exception as e:
                    st.warning(f"⚠️ {json_file} の読み込み中にエラーが発生しました: {str(e)}")
                    continue
            
            return json_data, json_files_found
            
    except Exception as e:
        st.error(f"❌ ZIPファイルの処理中にエラーが発生しました: {str(e)}")
        return None, []

if uploaded_file is not None:
    # 📌 ZIPファイルからJSONデータを抽出
    json_data, json_files = extract_json_from_zip(uploaded_file)
    
    if json_data is None:
        st.stop()
    
    # 📌 JSONデータをDataFrameに変換
    try:
        df = pd.json_normalize(json_data)
        st.success(f"✅ {len(json_data)}件のJSONレコードをDataFrameに変換しました")
    except Exception as e:
        st.error(f"❌ JSONデータの変換中にエラーが発生しました: {str(e)}")
        st.stop()

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
    
    # 📌 放射線データに必要なカラムを自動検出
    def detect_columns(df):
        """DataFrameから放射線データに必要なカラムを自動検出"""
        lat_col = None
        lon_col = None
        dose_col = None
        
        # 緯度カラムを検出
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['lat', '緯度', 'latitude']):
                lat_col = col
                break
        
        # 経度カラムを検出
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['lon', 'lng', '経度', 'longitude']):
                lon_col = col
                break
        
        # 線量率カラムを検出
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['dose', 'radiation', '線量', 'µsv', 'usv', 'sv/h']):
                dose_col = col
                break
        
        return lat_col, lon_col, dose_col
    
    lat_col, lon_col, dose_col = detect_columns(df)
    
    # 📌 検出されたカラムの表示
    st.subheader("🔍 自動検出されたカラム")
    col1, col2, col3 = st.columns(3)
    with col1:
        if lat_col:
            st.success(f"✅ 緯度: {lat_col}")
        else:
            st.error("❌ 緯度カラムが見つかりません")
    with col2:
        if lon_col:
            st.success(f"✅ 経度: {lon_col}")
        else:
            st.error("❌ 経度カラムが見つかりません")
    with col3:
        if dose_col:
            st.success(f"✅ 線量率: {dose_col}")
        else:
            st.error("❌ 線量率カラムが見つかりません")
    
    # 📌 手動でカラムを選択するオプション
    if not all([lat_col, lon_col, dose_col]):
        st.subheader("🔧 手動カラム選択")
        st.info("自動検出できなかったカラムを手動で選択してください")
        
        available_columns = list(df.columns)
        
        if not lat_col:
            lat_col = st.selectbox("緯度カラムを選択:", available_columns, key="lat_select")
        if not lon_col:
            lon_col = st.selectbox("経度カラムを選択:", available_columns, key="lon_select")
        if not dose_col:
            dose_col = st.selectbox("線量率カラムを選択:", available_columns, key="dose_select")
    
    # 📌 必要なカラムが全て揃っているかチェック
    if not all([lat_col, lon_col, dose_col]):
        st.error("❌ 必要なカラムが全て選択されていません。")
        st.stop()
    
    # 📌 選択されたカラムでデータを処理
    required_columns = [lat_col, lon_col, dose_col]
    
    # 📌 数値データの変換とエラーハンドリング
    st.subheader("🔧 データ変換")
    
    # 緯度・経度・線量率を数値型に変換
    conversion_errors = []
    
    for col in [lat_col, lon_col, dose_col]:
        try:
            # 元の型を確認
            original_type = df[col].dtype
            
            # 数値型でない場合は変換を試行
            if not pd.api.types.is_numeric_dtype(df[col]):
                df[col] = pd.to_numeric(df[col], errors='coerce')
                st.info(f"✅ {col}: {original_type} → 数値型に変換")
            else:
                st.success(f"✅ {col}: 既に数値型 ({original_type})")
                
        except Exception as e:
            conversion_errors.append(f"{col}: {str(e)}")
            st.error(f"❌ {col} の数値変換に失敗しました")
    
    if conversion_errors:
        st.error("数値変換エラーが発生しました:")
        for error in conversion_errors:
            st.write(f"- {error}")
    
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
    
    # 📌 データ品質チェック
    st.subheader("🔍 データ品質チェック")
    
    # NaNの数をチェック
    nan_counts = df_to_use[required_columns].isnull().sum()
    total_rows = len(df_to_use)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(f"🌍 {lat_col} 欠損値", f"{nan_counts[lat_col]} / {total_rows}")
    with col2:
        st.metric(f"🌏 {lon_col} 欠損値", f"{nan_counts[lon_col]} / {total_rows}")
    with col3:
        st.metric(f"☢️ {dose_col} 欠損値", f"{nan_counts[dose_col]} / {total_rows}")
    
    # 📌 NaNを除外
    df_filtered = df_to_use[required_columns].dropna()
    
    # データ範囲のチェック
    if len(df_filtered) > 0:
        lat_range = (df_filtered[lat_col].min(), df_filtered[lat_col].max())
        lon_range = (df_filtered[lon_col].min(), df_filtered[lon_col].max())
        dose_range = (df_filtered[dose_col].min(), df_filtered[dose_col].max())
        
        # 異常値の警告
        if not (-90 <= lat_range[0] <= 90 and -90 <= lat_range[1] <= 90):
            st.warning(f"⚠️ 緯度の値が異常です: {lat_range[0]:.3f} ～ {lat_range[1]:.3f}")
        if not (-180 <= lon_range[0] <= 180 and -180 <= lon_range[1] <= 180):
            st.warning(f"⚠️ 経度の値が異常です: {lon_range[0]:.3f} ～ {lon_range[1]:.3f}")
        if dose_range[0] < 0:
            st.warning(f"⚠️ 線量率に負の値があります: {dose_range[0]:.3f}")
    
    if len(df_filtered) == 0:
        st.error("❌ 有効なデータがありません。データを確認してください。")
        st.stop()
    elif len(df_filtered) < len(df_to_use):
        st.warning(f"⚠️ {len(df_to_use) - len(df_filtered)}行のデータが欠損値により除外されました。")
    else:
        # 📌 データ統計情報の表示
        st.subheader("📊 データ統計")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("データポイント数", len(df_filtered))
        with col2:
            st.metric("平均線量率 (µSv/h)", f"{df_filtered[dose_col].mean():.3f}")
        with col3:
            st.metric("最大線量率 (µSv/h)", f"{df_filtered[dose_col].max():.3f}")

        # 📌 ヒートマップデータ作成
        heat_data = df_filtered[[lat_col, lon_col, dose_col]].values.tolist()

        # 📌 地図の中心を計算
        center_lat = df_filtered[lat_col].mean()
        center_lon = df_filtered[lon_col].mean()

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
        
        # 📌 フィルタリングされたJSONのダウンロード
        with col2:
            # 処理済みデータをJSONとして出力
            json_data = df_to_use.to_json(orient='records', force_ascii=False, indent=2)
            
            st.download_button(
                label="📥 処理済みJSONをダウンロード",
                data=json_data,
                file_name="processed_radiation_data.json",
                mime="application/json"
            )
