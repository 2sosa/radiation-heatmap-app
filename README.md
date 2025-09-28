# 放射線ヒートマップ作成ツール

AccuradのCSVデータを処理し、タイムスタンプの時差問題を解決する放射線データ分析アプリケーション。

## 主な機能

### 1. タイムスタンプ時差変換
- **問題**: AccuradはUTC+9で表示されるが、CSVではUTCで出力される
- **解決策**: 自動的にUTC+9からUTCへの変換を実行
- **例**: Accurad表示 12:00 → CSV出力 03:00（9時間の時差を考慮）

### 2. 単一ファイル処理
- CSVファイルから放射線ヒートマップを作成
- タイムスタンプ自動検出・変換
- インタラクティブな地図表示
- 変換済みCSVのダウンロード

### 3. 複数ファイル比較
- 2つのCSVファイル間でタイムスタンプ突合
- 許容誤差設定（1-60分）
- 突合統計の表示
- 突合結果のエクスポート

### 4. 対応タイムゾーン
- Asia/Tokyo (UTC+9) - 日本標準時
- UTC (協定世界時)
- Asia/Seoul (UTC+9) - 韓国標準時
- America/New_York (UTC-5/-4) - 東部標準時
- Europe/London (UTC+0/+1) - グリニッジ標準時
- Asia/Shanghai (UTC+8) - 中国標準時

## 使用方法

### インストール
```bash
pip install -r requirements.txt
```

### 実行
```bash
streamlit run app.py
```

### 操作手順
1. サイドバーでタイムゾーンを選択（デフォルト: Asia/Tokyo）
2. 動作モードを選択
   - **単一ファイル処理**: ヒートマップ作成
   - **複数ファイル比較**: タイムスタンプ突合
3. CSVファイルをアップロード
4. 結果を確認・ダウンロード

## タイムスタンプ形式対応
- `YYYY-MM-DD HH:MM:SS`
- `YYYY/MM/DD HH:MM:SS`
- `YYYY-MM-DD HH:MM`
- `YYYY/MM/DD HH:MM`
- `YYYY-MM-DDTHH:MM:SS`
- `YYYY-MM-DDTHH:MM:SSZ`
- `YYYY-MM-DD HH:MM:SS.ffffff`

## 技術仕様
- Python 3.7+
- Streamlit
- Pandas
- Folium
- PyTZ

## Accurad時差問題の解決
本アプリケーションは、Accuradの以下の問題を解決します：
- Accurad本体での表示時刻とCSV出力時刻の9時間の時差
- 複数データセット間での時刻突合の困難
- タイムゾーン変換の手動作業の煩雑さ