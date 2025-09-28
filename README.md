# JSON ZIP Processor for Pythonista3

iPhoneのファイルアプリから手動でZIPファイルを選択し、中に含まれるJSONファイルを読み取るPythonista3用スクリプトです。

## 機能

- 📱 iPhoneのファイルアプリから直接ZIPファイルを選択
- 📦 ZIP形式で圧縮された複数のJSONファイルを一括処理
- 🔍 JSONファイルの自動検出と読み取り
- 📊 処理結果のサマリー表示
- 💾 処理データの保存オプション
- 🧹 自動的な一時ファイルのクリーンアップ

## 使い方

### 1. Pythonista3へのインストール

1. Pythonista3アプリを開く
2. `json_zip_processor.py`ファイルをPythonista3にコピー
   - iCloudドライブやDropbox経由
   - またはPythonista3の「+」ボタンから新規作成してコードを貼り付け

### 2. 実行方法

```python
# Pythonista3で実行
import json_zip_processor
json_zip_processor.main()
```

または、スクリプトを直接実行：
- Pythonista3でファイルを開いて「▶️」ボタンをタップ

### 3. 操作フロー

1. **ファイル選択**
   - スクリプトを実行すると、ファイル選択ダイアログが表示されます
   - iPhoneのファイルアプリからZIPファイルを選択

2. **自動処理**
   - ZIPファイルが自動的に展開されます
   - 含まれるすべてのJSONファイルが読み取られます

3. **結果表示**
   - 処理結果のサマリーが表示されます
   - 各JSONファイルの詳細を確認できます

4. **データ保存（オプション）**
   - JSON形式：すべてのデータを1つのファイルに統合
   - テキスト形式：処理結果のサマリーを保存

## サンプルZIPファイルの構造

```
sample_data.zip
├── data1.json
├── data2.json
├── subfolder/
│   ├── data3.json
│   └── data4.json
└── config.json
```

## 主な機能詳細

### JSONファイルの自動検出
- ZIP内のすべてのディレクトリを再帰的に検索
- `.json`拡張子のファイルを自動的に検出

### エラーハンドリング
- 無効なZIPファイルの検出
- JSONパースエラーの処理
- ファイル読み取りエラーの処理

### データ表示オプション
- **サマリー表示**: ファイル数、各ファイルの概要
- **詳細表示**: 選択したJSONファイルの完全な内容
- **クリップボードコピー**: JSONデータをクリップボードにコピー

### 保存形式
- **JSON統合形式**: すべてのJSONデータを1つのファイルに
- **テキストサマリー**: 処理結果の概要をテキストファイルに

## 使用例

### 基本的な使用

```python
# Pythonista3のコンソールで実行
from json_zip_processor import JSONZipProcessor

processor = JSONZipProcessor()
processor.process()  # これだけで全処理が実行されます
```

### プログラマティックな使用

```python
# カスタム処理を行う場合
processor = JSONZipProcessor()

# ZIPファイルを選択
zip_path = processor.select_zip_file()

if zip_path:
    # ZIPを展開
    processor.extract_zip(zip_path)
    
    # JSONファイルを処理
    json_data = processor.process_json_files()
    
    # データを使用
    for filename, data in json_data.items():
        print(f"File: {filename}")
        print(f"Data: {data}")
    
    # クリーンアップ
    processor.cleanup()
```

## 注意事項

- Pythonista3専用のスクリプトです（`console`、`dialogs`モジュールを使用）
- 大きなZIPファイル（100MB以上）の処理には時間がかかる場合があります
- JSONファイルはUTF-8エンコーディングである必要があります

## トラブルシューティング

### ZIPファイルが選択できない場合
- ファイルアプリでZIPファイルが表示されているか確認
- Pythonista3にファイルアクセス権限があるか確認

### JSONパースエラーが発生する場合
- JSONファイルが正しい形式か確認
- 文字エンコーディングがUTF-8か確認

### メモリエラーが発生する場合
- より小さいZIPファイルに分割して処理
- 不要なアプリを終了してメモリを確保

## ライセンス

MIT License

## 作成者

Created for Pythonista3 on iOS