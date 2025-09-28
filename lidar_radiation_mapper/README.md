# LiDAR + 放射線測定データ統合可視化システム

iPhone LiDARスキャナーで収集した3次元データと放射線測定機のデータを統合し、3D空間内に線量率で色付けされた軌跡（ヒートライン）を生成するPythonツールです。

## 特徴

- **データ統合**: PolycamのLiDARデータとAccuRad PRDの放射線データをタイムスタンプで同期
- **3D可視化**: SLAM軌跡を直径10cmのチューブ状で表現
- **ヒートマップ**: 線量率（0-10μSv/h）を青から赤のグラデーションで可視化
- **PLY出力**: 汎用的な3Dファイル形式での出力
- **Pythonista3対応**: iPhone上で直接実行可能な簡易版も提供

## 必要環境

### PC版（フル機能）
```bash
pip install -r requirements.txt
```

必要なパッケージ:
- numpy >= 1.21.0
- trimesh >= 3.15.0
- scipy >= 1.7.0
- matplotlib >= 3.5.0
- plyfile >= 0.7.4
- pandas >= 1.3.0

### Pythonista3版（iPhone用）
標準ライブラリのみで動作する簡易版を提供

## 使用方法

### 1. サンプルデータの生成（テスト用）

```bash
cd examples
python generate_sample_data.py
```

### 2. メインスクリプトの実行

```bash
python main.py \
  --lidar-ply data/lidar/scan.ply \
  --lidar-json data/lidar/trajectory.json \
  --radiation-csv data/radiation/measurements.csv \
  --output data/output/result.ply
```

#### コマンドラインオプション

**必須引数:**
- `--lidar-ply`: PolycamのPLYファイルパス
- `--lidar-json`: Polycamの軌跡データ（JSON）パス
- `--radiation-csv`: AccuRad PRDのCSVファイルパス

**オプション引数:**
- `--output`: 出力PLYファイルパス（デフォルト: output.ply）
- `--tube-diameter`: 軌跡チューブの直径[m]（デフォルト: 0.1）
- `--dose-min`: 線量率の最小値[μSv/h]（デフォルト: 0.0）
- `--dose-max`: 線量率の最大値[μSv/h]（デフォルト: 10.0）
- `--include-pointcloud`: 元の点群データも含める
- `--add-markers`: 軌跡上にマーカーを追加
- `--marker-interval`: マーカーの配置間隔（デフォルト: 10）
- `--export-legend`: カラーレジェンドを別ファイルとして出力

### 3. Pythonista3での使用（iPhone）

```python
# pythonista_version.pyをPythonista3で開いて実行
# ファイルパスは環境に応じて調整してください
```

## データ形式

### Polycam JSON形式（軌跡データ）

```json
{
  "frames": [
    {
      "timestamp": 1234567890.123,
      "position": {
        "x": 0.0,
        "y": 0.0,
        "z": 0.0
      },
      "orientation": {
        "w": 1.0,
        "x": 0.0,
        "y": 0.0,
        "z": 0.0
      }
    }
  ]
}
```

### AccuRad CSV形式（放射線データ）

```csv
timestamp,dose_rate_uSv_h,unit,device
1234567890.123,1.234,uSv/h,AccuRad_PRD
```

## プロジェクト構造

```
lidar_radiation_mapper/
├── src/
│   ├── data_loader.py         # データ読み込みモジュール
│   ├── trajectory_visualizer.py # 3D軌跡生成モジュール
│   └── ply_exporter.py        # PLY出力モジュール
├── examples/
│   └── generate_sample_data.py # サンプルデータ生成
├── data/
│   ├── lidar/                 # LiDARデータ格納
│   ├── radiation/             # 放射線データ格納
│   └── output/                # 出力ファイル格納
├── main.py                    # メインスクリプト
├── pythonista_version.py      # Pythonista3用簡易版
├── requirements.txt           # 必要パッケージ
└── README.md                  # このファイル
```

## カスタマイズ

### データ形式の調整

実際のPolycamやAccuRadの出力形式に合わせて、以下のファイルを編集してください：

1. `src/data_loader.py`:
   - `PolycamDataLoader.load_slam_trajectory()`: JSON形式の調整
   - `RadiationDataLoader.load_csv()`: CSV形式の調整

2. タイムスタンプ形式の変更が必要な場合:
   - `RadiationDataLoader.get_interpolated_dose_rate()`: 補間方法の調整

### 可視化パラメータの調整

`src/trajectory_visualizer.py`で以下をカスタマイズ可能：
- カラーマップの変更（現在: jet - 青→赤）
- チューブの形状（分割数、半径など）
- マーカーのスタイル

## トラブルシューティング

### よくある問題と解決方法

1. **データが同期されない**
   - タイムスタンプの形式を確認
   - タイムゾーンの設定を確認

2. **メモリ不足エラー**
   - 点群データのサイズを削減
   - `--include-pointcloud`オプションを外す

3. **Pythonista3でライブラリエラー**
   - `pythonista_version.py`を使用（外部ライブラリ不要）

## ライセンスと注意事項

- 本ツールは研究・教育目的での使用を想定しています
- 放射線測定データの取り扱いには十分注意してください
- 生成された可視化結果の解釈には専門知識が必要です

## 今後の改善点

- [ ] リアルタイム処理対応
- [ ] GUI版の開発
- [ ] より高度な補間アルゴリズムの実装
- [ ] 複数の測定セッションの統合機能
- [ ] VR/AR表示対応

## お問い合わせ

技術的な質問や改善提案がある場合は、Issueを作成してください。