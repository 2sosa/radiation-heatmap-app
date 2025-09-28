#!/usr/bin/env python3
"""
LiDAR + 放射線測定データ統合可視化システム
メインスクリプト

使用方法:
    python main.py --lidar-ply path/to/scan.ply \
                   --lidar-json path/to/trajectory.json \
                   --radiation-csv path/to/radiation.csv \
                   --output path/to/output.ply
"""
import argparse
import os
import sys
from pathlib import Path

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data_loader import PolycamDataLoader, RadiationDataLoader, synchronize_data
from trajectory_visualizer import TrajectoryVisualizer
from ply_exporter import PLYExporter


def main():
    """メイン処理"""
    
    # コマンドライン引数のパーサーを設定
    parser = argparse.ArgumentParser(
        description='LiDARスキャンデータと放射線測定データを統合して3D可視化'
    )
    
    # 入力ファイル
    parser.add_argument('--lidar-ply', type=str, required=True,
                       help='PolycamのPLYファイルパス')
    parser.add_argument('--lidar-json', type=str, required=True,
                       help='PolycamのJSON（軌跡）ファイルパス')
    parser.add_argument('--radiation-csv', type=str, required=True,
                       help='AccuRad PRDのCSVファイルパス')
    
    # 出力ファイル
    parser.add_argument('--output', type=str, default='output.ply',
                       help='出力PLYファイルパス（デフォルト: output.ply）')
    
    # オプション設定
    parser.add_argument('--tube-diameter', type=float, default=0.1,
                       help='軌跡チューブの直径（メートル、デフォルト: 0.1）')
    parser.add_argument('--dose-min', type=float, default=0.0,
                       help='線量率の最小値（μSv/h、デフォルト: 0.0）')
    parser.add_argument('--dose-max', type=float, default=10.0,
                       help='線量率の最大値（μSv/h、デフォルト: 10.0）')
    parser.add_argument('--include-pointcloud', action='store_true',
                       help='元の点群データも含める')
    parser.add_argument('--add-markers', action='store_true',
                       help='軌跡上にマーカーを追加')
    parser.add_argument('--marker-interval', type=int, default=10,
                       help='マーカーの配置間隔（デフォルト: 10）')
    parser.add_argument('--export-legend', action='store_true',
                       help='カラーレジェンドを別ファイルとして出力')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("LiDAR + 放射線測定データ統合可視化システム")
    print("=" * 60)
    
    # ファイルの存在確認
    for file_path, file_type in [(args.lidar_ply, 'PLY'),
                                  (args.lidar_json, 'JSON'),
                                  (args.radiation_csv, 'CSV')]:
        if not os.path.exists(file_path):
            print(f"エラー: {file_type}ファイルが見つかりません: {file_path}")
            sys.exit(1)
    
    try:
        # 1. データの読み込み
        print("\n[1/5] データを読み込み中...")
        
        # Polycamデータの読み込み
        print("  - LiDARデータを読み込み中...")
        polycam_loader = PolycamDataLoader(args.lidar_ply, args.lidar_json)
        point_cloud_data = None
        if args.include_pointcloud:
            polycam_loader.load_ply()
            point_cloud_data = polycam_loader.point_cloud
            print(f"    点群データ: {len(point_cloud_data['points'])} 点")
        
        trajectory_data = polycam_loader.load_slam_trajectory()
        print(f"    軌跡データ: {len(trajectory_data)} ポイント")
        
        # 放射線データの読み込み
        print("  - 放射線測定データを読み込み中...")
        radiation_loader = RadiationDataLoader(args.radiation_csv)
        radiation_data = radiation_loader.load_csv()
        print(f"    測定データ: {len(radiation_data)} レコード")
        
        # 2. データの同期
        print("\n[2/5] タイムスタンプでデータを同期中...")
        synchronized_data = synchronize_data(trajectory_data, radiation_loader)
        print(f"  同期完了: {len(synchronized_data)} ポイント")
        
        # 線量率の統計を表示
        dose_rates = [point['dose_rate_uSv_h'] for point in synchronized_data]
        if dose_rates:
            print(f"  線量率統計:")
            print(f"    最小: {min(dose_rates):.2f} μSv/h")
            print(f"    最大: {max(dose_rates):.2f} μSv/h")
            print(f"    平均: {sum(dose_rates)/len(dose_rates):.2f} μSv/h")
        
        # 3. 軌跡の可視化
        print("\n[3/5] 3D軌跡を生成中...")
        visualizer = TrajectoryVisualizer(
            tube_radius=args.tube_diameter / 2,
            dose_rate_range=(args.dose_min, args.dose_max)
        )
        
        trajectory_mesh = visualizer.create_trajectory_mesh(synchronized_data)
        
        if trajectory_mesh is None:
            print("エラー: 軌跡メッシュの生成に失敗しました")
            sys.exit(1)
        
        print(f"  軌跡メッシュ生成完了:")
        print(f"    頂点数: {len(trajectory_mesh.vertices)}")
        print(f"    面数: {len(trajectory_mesh.faces)}")
        
        # マーカーの追加（オプション）
        markers = None
        if args.add_markers:
            print(f"  マーカーを追加中（間隔: {args.marker_interval}）...")
            markers = visualizer.add_sphere_markers(synchronized_data, args.marker_interval)
            print(f"    {len(markers)} 個のマーカーを追加")
        
        # 4. メッシュの結合
        print("\n[4/5] メッシュを結合中...")
        exporter = PLYExporter()
        
        combined_mesh = exporter.combine_meshes(
            point_cloud_data if args.include_pointcloud else None,
            trajectory_mesh,
            markers
        )
        
        # 5. PLYファイルとして出力
        print("\n[5/5] PLYファイルを出力中...")
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        success = exporter.export_to_ply(combined_mesh, str(output_path))
        
        if success:
            print(f"\n✓ 出力完了: {output_path}")
            print(f"  ファイルサイズ: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
            
            # カラーレジェンドの出力（オプション）
            if args.export_legend:
                legend_path = output_path.with_suffix('.png')
                print(f"\nカラーレジェンドを生成中...")
                import matplotlib.pyplot as plt
                legend_image = visualizer.create_color_legend()
                plt.imsave(str(legend_path), legend_image)
                print(f"✓ カラーレジェンド出力: {legend_path}")
        else:
            print("\n✗ PLYファイルの出力に失敗しました")
            sys.exit(1)
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("処理完了")
    print("=" * 60)


if __name__ == '__main__':
    main()