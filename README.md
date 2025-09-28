# 3D放射線ヒートマップ生成ツール

iPhone16 ProのLiDARスキャナーで収集した3次元データ及びSLAM(自己位置推定)データと、放射線測定機で得た線量率データをタイムスタンプで結びつけて、3次元空間内にSLAMに基づいた軌跡を再現し、その軌跡に線量率由来の色付けをしたヒートラインを生成するツールです。

## 概要

このツールは以下の機能を提供します：

- PolycamアプリのPLY・JSONファイルからLiDAR点群とSLAM軌跡データを読み込み
- AccuRad PRDのCSVファイルから放射線線量率データを読み込み
- タイムスタンプに基づくデータ同期
- 軌跡に沿った直径10cmのチューブ状ヒートマップ生成
- 線量率に応じた青→緑→赤のグラデーション色付け
- 統合された3DモデルのPLY形式での出力

## 必要な機器・ソフトウェア

### ハードウェア
- iPhone16 Pro（LiDARスキャナー搭載）
- AccuRad PRD（放射線測定器）

### ソフトウェア
- Polycam（LiDARスキャナーアプリ）
- Python 3.7以上

## インストール

1. リポジトリをクローン：
```bash
git clone <repository_url>
cd 3d-radiation-heatmap
```

2. 必要なパッケージをインストール：
```bash
pip install -r requirements.txt
```

## 使用方法

### 基本的な使用方法

```bash
python main.py --ply_file scan.ply --json_file slam.json --csv_file dose_rates.csv --output heatmap.ply
```

### 詳細オプション付きの使用例

```bash
python main.py --ply_file scan.ply --json_file slam.json --csv_file dose_rates.csv \
               --output heatmap.ply --tube_radius 0.06 --dose_range 0 15 \
               --smooth_trajectory --preview --include_point_cloud
```

### コマンドラインオプション

#### 必須引数
- `--ply_file`: Polycamで取得したPLYファイルのパス
- `--json_file`: PolycamのSLAMデータJSONファイルのパス  
- `--csv_file`: AccuRadの線量率CSVファイルのパス
- `--output`: 出力PLYファイルのパス

#### オプション引数
- `--tube_radius`: ヒートチューブの半径（メートル）[デフォルト: 0.05]
- `--dose_range`: 線量率の範囲 [最小値 最大値] (μSv/h) [デフォルト: 0.0 10.0]
- `--radial_segments`: チューブの円周分割数 [デフォルト: 16]
- `--time_tolerance`: データ同期の時間許容誤差（秒）[デフォルト: 1.0]

#### 処理オプション
- `--smooth_trajectory`: 軌跡データをスムージング
- `--smooth_sigma`: スムージングの強度 [デフォルト: 1.0]
- `--remove_outliers`: 軌跡データから外れ値を除去
- `--interpolate_points`: 軌跡を指定した点数に補間

#### 出力オプション
- `--include_point_cloud`: LiDAR点群データもPLYファイルに含める
- `--separate_components`: コンポーネントを個別のPLYファイルとして出力
- `--preview`: プレビュー画像を生成
- `--color_scale`: カラースケールバーを生成
- `--visualize`: 3Dビューアーで結果を表示

#### デバッグオプション
- `--verbose`: 詳細な処理情報を表示
- `--save_intermediate`: 中間結果を保存

## データ形式

### Polycam JSONファイル形式（例）

```json
{
  "frames": [
    {
      "transform_matrix": [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0], 
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]
      ],
      "timestamp": 1234567890.123
    }
  ]
}
```

### AccuRad CSVファイル形式（例）

```csv
timestamp,dose_rate,x,y,z
2023-01-01 10:00:00,0.12,1.0,2.0,0.5
2023-01-01 10:00:01,0.15,1.1,2.1,0.5
2023-01-01 10:00:02,0.18,1.2,2.2,0.5
```

サポートされる列名：
- タイムスタンプ: `timestamp`, `time`, `datetime`, `Time`, `Timestamp`
- 線量率: `dose_rate`, `doserate`, `dose`, `radiation`, `uSv/h`, `μSv/h`
- 位置情報（オプション）: `x`, `y`, `z`

## 出力ファイル

### メインPLYファイル
- 統合された3Dモデル（ヒートチューブ + オプションで点群）
- 頂点色情報を含む
- 各種3Dソフトウェアで読み込み可能

### 追加出力ファイル（オプション）
- `*_heat_tube.ply`: ヒートチューブのみ
- `*_point_cloud.ply`: 点群データのみ
- `*_preview.png`: プレビュー画像
- `*_metadata.txt`: メタデータ情報
- `color_scale_bar.png`: カラースケールバー
- `trajectory_visualization.png`: 軌跡可視化画像

## 色の意味

ヒートチューブの色は線量率を表します：

- **青色**: 低線量率（0 μSv/h付近）
- **緑色**: 中間線量率（5 μSv/h付近）  
- **赤色**: 高線量率（10 μSv/h付近）

線量率の範囲は `--dose_range` オプションで調整可能です。

## トラブルシューティング

### よくある問題

1. **「軌跡データの取得に失敗しました」エラー**
   - JSONファイルの形式を確認してください
   - `frames` キーと `transform_matrix` が正しく含まれているか確認

2. **「線量率データの取得に失敗しました」エラー**
   - CSVファイルの列名を確認してください
   - サポートされている列名を使用しているか確認

3. **「同期されたデータが存在しません」エラー**
   - タイムスタンプの形式と範囲を確認してください
   - `--time_tolerance` オプションを大きくしてみてください

4. **メモリ不足エラー**
   - 点群データが大きすぎる場合があります
   - `--include_point_cloud` を外してみてください

### デバッグのヒント

- `--verbose` オプションで詳細な処理情報を表示
- `--save_intermediate` で中間結果を確認
- 小さなデータセットで動作確認してから本格的なデータを処理

## パフォーマンス

### 推奨システム要件
- RAM: 8GB以上
- CPU: マルチコア推奨
- ストレージ: 十分な空き容量

### 処理時間の目安
- 軌跡点数1000点、点群10万点: 約30秒〜1分
- 軌跡点数5000点、点群50万点: 約2〜5分

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

バグ報告、機能要望、プルリクエストを歓迎します。

## 更新履歴

### Version 1.0.0
- 初回リリース
- 基本的なヒートマップ生成機能
- PLY出力機能
- コマンドラインインターフェース