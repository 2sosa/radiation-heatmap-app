#!/usr/bin/env python3
"""
3D放射線ヒートマップ生成メインスクリプト

iPhone16 ProのLiDARスキャナーで収集した3次元データ及びSLAM(自己位置推定)データと、
放射線測定機で得た線量率データをタイムスタンプで結びつけて、
3次元空間内にSLAMに基づいた軌跡を再現し、
その軌跡に線量率由来の色付けをしたヒートラインを生成する。

使用方法:
python main.py --ply_file path/to/scan.ply --json_file path/to/slam.json --csv_file path/to/dose_rates.csv --output output.ply

作成者: AI Assistant
日付: 2025年
"""

import argparse
import sys
import os
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

# 自作モジュールをインポート
from data_loader import PolycamDataLoader, AccuRadDataLoader, synchronize_data
from trajectory_processor import TrajectoryProcessor, synchronize_trajectory_with_dose_rates
from heat_tube_generator import HeatTubeGenerator, combine_with_point_cloud
from ply_exporter import PLYExporter


def parse_arguments():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(
        description="3D放射線ヒートマップ生成ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main.py --ply_file scan.ply --json_file slam.json --csv_file dose_rates.csv --output heatmap.ply
  
  python main.py --ply_file scan.ply --json_file slam.json --csv_file dose_rates.csv \\
                 --output heatmap.ply --tube_radius 0.06 --dose_range 0 15 \\
                 --smooth_trajectory --preview
        """
    )
    
    # 必須引数
    parser.add_argument('--ply_file', required=True, 
                       help='Polycamで取得したPLYファイルのパス')
    parser.add_argument('--json_file', required=True,
                       help='PolycamのSLAMデータJSONファイルのパス')
    parser.add_argument('--csv_file', required=True,
                       help='AccuRadの線量率CSVファイルのパス')
    parser.add_argument('--output', required=True,
                       help='出力PLYファイルのパス')
    
    # オプション引数
    parser.add_argument('--tube_radius', type=float, default=0.05,
                       help='ヒートチューブの半径（メートル）。デフォルト: 0.05 (直径10cm)')
    parser.add_argument('--dose_range', nargs=2, type=float, default=[0.0, 10.0],
                       help='線量率の範囲 [最小値 最大値] (μSv/h)。デフォルト: 0.0 10.0')
    parser.add_argument('--radial_segments', type=int, default=16,
                       help='チューブの円周分割数。デフォルト: 16')
    parser.add_argument('--time_tolerance', type=float, default=1.0,
                       help='データ同期の時間許容誤差（秒）。デフォルト: 1.0')
    
    # 処理オプション
    parser.add_argument('--smooth_trajectory', action='store_true',
                       help='軌跡データをスムージングする')
    parser.add_argument('--smooth_sigma', type=float, default=1.0,
                       help='スムージングの強度（ガウシアンフィルタのσ）。デフォルト: 1.0')
    parser.add_argument('--remove_outliers', action='store_true',
                       help='軌跡データから外れ値を除去する')
    parser.add_argument('--interpolate_points', type=int, default=None,
                       help='軌跡を指定した点数に補間する')
    
    # 出力オプション
    parser.add_argument('--include_point_cloud', action='store_true',
                       help='LiDAR点群データもPLYファイルに含める')
    parser.add_argument('--separate_components', action='store_true',
                       help='コンポーネントを個別のPLYファイルとして出力する')
    parser.add_argument('--preview', action='store_true',
                       help='プレビュー画像を生成する')
    parser.add_argument('--color_scale', action='store_true',
                       help='カラースケールバーを生成する')
    parser.add_argument('--visualize', action='store_true',
                       help='3Dビューアーで結果を表示する')
    
    # デバッグオプション
    parser.add_argument('--verbose', action='store_true',
                       help='詳細な処理情報を表示する')
    parser.add_argument('--save_intermediate', action='store_true',
                       help='中間結果を保存する')
    
    return parser.parse_args()


def load_data(args, verbose=False):
    """すべてのデータを読み込み"""
    if verbose:
        print("=== データ読み込み開始 ===")
    
    # Polycamデータの読み込み
    if verbose:
        print(f"Polycamデータを読み込み中...")
    polycam_loader = PolycamDataLoader(args.ply_file, args.json_file)
    
    point_cloud = polycam_loader.load_ply()
    if point_cloud is None:
        raise ValueError(f"PLYファイルの読み込みに失敗しました: {args.ply_file}")
    
    slam_data = polycam_loader.load_json()
    if slam_data is None:
        raise ValueError(f"JSONファイルの読み込みに失敗しました: {args.json_file}")
    
    trajectory = polycam_loader.get_trajectory()
    if trajectory is None:
        raise ValueError("軌跡データの取得に失敗しました")
    
    polycam_timestamps = polycam_loader.timestamps
    if polycam_timestamps is None:
        print("警告: Polycamタイムスタンプが見つかりません。等間隔のタイムスタンプを生成します。")
        polycam_timestamps = np.arange(len(trajectory))
    
    # AccuRadデータの読み込み
    if verbose:
        print(f"AccuRadデータを読み込み中...")
    accuRad_loader = AccuRadDataLoader(args.csv_file)
    
    dose_data = accuRad_loader.load_csv()
    if dose_data is None:
        raise ValueError(f"CSVファイルの読み込みに失敗しました: {args.csv_file}")
    
    dose_rates = accuRad_loader.dose_rates
    dose_timestamps = accuRad_loader.timestamps
    
    if dose_rates is None:
        raise ValueError("線量率データの取得に失敗しました")
    if dose_timestamps is None:
        print("警告: AccuRadタイムスタンプが見つかりません。等間隔のタイムスタンプを生成します。")
        dose_timestamps = np.arange(len(dose_rates))
    
    if verbose:
        print(f"データ読み込み完了:")
        print(f"  点群データ: {len(point_cloud):,}点")
        print(f"  軌跡データ: {len(trajectory)}点")
        print(f"  線量率データ: {len(dose_rates)}点")
    
    return {
        'point_cloud': point_cloud,
        'trajectory': trajectory,
        'polycam_timestamps': polycam_timestamps,
        'dose_rates': dose_rates,
        'dose_timestamps': dose_timestamps,
        'polycam_loader': polycam_loader,
        'accuRad_loader': accuRad_loader
    }


def process_trajectory(data, args, verbose=False):
    """軌跡データの処理"""
    if verbose:
        print("\n=== 軌跡データ処理開始 ===")
    
    processor = TrajectoryProcessor()
    processor.set_trajectory(data['trajectory'], data['polycam_timestamps'])
    
    # 統計情報を計算
    metrics = processor.calculate_trajectory_metrics()
    if verbose:
        print(f"軌跡統計:")
        print(f"  総距離: {metrics['total_distance']:.2f}m")
        print(f"  点数: {metrics['num_points']}")
        print(f"  範囲: X={metrics['bounding_box_size'][0]:.2f}m, "
              f"Y={metrics['bounding_box_size'][1]:.2f}m, "
              f"Z={metrics['bounding_box_size'][2]:.2f}m")
        if metrics['average_speed'] is not None:
            print(f"  平均速度: {metrics['average_speed']:.2f}m/s")
    
    processed_trajectory = data['trajectory'].copy()
    processed_timestamps = data['polycam_timestamps'].copy()
    
    # 外れ値除去
    if args.remove_outliers:
        if verbose:
            print("外れ値除去を実行中...")
        processed_trajectory, processed_timestamps = processor.remove_outliers()
        processor.set_trajectory(processed_trajectory, processed_timestamps)
    
    # スムージング
    if args.smooth_trajectory:
        if verbose:
            print(f"軌跡スムージングを実行中（σ={args.smooth_sigma}）...")
        processed_trajectory = processor.smooth_trajectory(sigma=args.smooth_sigma)
    
    # 補間
    if args.interpolate_points:
        if verbose:
            print(f"軌跡補間を実行中（{args.interpolate_points}点）...")
        processed_trajectory, processed_timestamps = processor.interpolate_trajectory(args.interpolate_points)
    
    # 中間結果の保存
    if args.save_intermediate:
        processor.visualize_trajectory(save_path="trajectory_visualization.png")
        if verbose:
            print("軌跡可視化画像を保存しました: trajectory_visualization.png")
    
    return processed_trajectory, processed_timestamps, metrics


def synchronize_and_generate_heat_tube(trajectory, trajectory_timestamps, 
                                      dose_rates, dose_timestamps, args, verbose=False):
    """データ同期とヒートチューブ生成"""
    if verbose:
        print("\n=== データ同期とヒートチューブ生成 ===")
    
    # データ同期
    if verbose:
        print("タイムスタンプベースでデータを同期中...")
    
    synchronized_trajectory, synchronized_dose_rates = synchronize_trajectory_with_dose_rates(
        trajectory, trajectory_timestamps, dose_rates, dose_timestamps
    )
    
    if len(synchronized_trajectory) == 0:
        raise ValueError("同期されたデータが存在しません。タイムスタンプの範囲を確認してください。")
    
    if verbose:
        print(f"同期完了: {len(synchronized_trajectory)}点")
        print(f"線量率範囲: {np.min(synchronized_dose_rates):.3f} - {np.max(synchronized_dose_rates):.3f} μSv/h")
    
    # ヒートチューブ生成
    if verbose:
        print("ヒートチューブを生成中...")
    
    tube_generator = HeatTubeGenerator(tube_radius=args.tube_radius)
    heat_tube_mesh = tube_generator.create_tube_mesh(
        synchronized_trajectory,
        synchronized_dose_rates,
        radial_segments=args.radial_segments,
        dose_range=args.dose_range
    )
    
    if verbose:
        vertices = np.asarray(heat_tube_mesh.vertices)
        triangles = np.asarray(heat_tube_mesh.triangles)
        print(f"ヒートチューブ生成完了:")
        print(f"  頂点数: {len(vertices):,}")
        print(f"  面数: {len(triangles):,}")
    
    # カラースケールバーの生成
    if args.color_scale:
        tube_generator.create_color_scale_bar(
            args.dose_range, 
            save_path="color_scale_bar.png"
        )
        if verbose:
            print("カラースケールバーを保存しました: color_scale_bar.png")
    
    return heat_tube_mesh, synchronized_trajectory, synchronized_dose_rates


def export_results(heat_tube_mesh, point_cloud, args, metadata, verbose=False):
    """結果の出力"""
    if verbose:
        print("\n=== 結果出力 ===")
    
    exporter = PLYExporter()
    exporter.add_metadata(metadata)
    
    # ジオメトリの統合
    if args.include_point_cloud:
        if verbose:
            print("点群データを統合中...")
        combined_mesh = exporter.combine_geometries(
            heat_tube_mesh, 
            point_cloud=point_cloud
        )
    else:
        combined_mesh = exporter.combine_geometries(heat_tube_mesh)
    
    # メインPLYファイルの出力
    success = exporter.export_to_ply(args.output, include_metadata=True, binary=True)
    if not success:
        raise RuntimeError(f"PLYファイル出力に失敗しました: {args.output}")
    
    # コンポーネント個別出力
    if args.separate_components:
        base_name = os.path.splitext(args.output)[0]
        point_cloud_mesh = None
        if args.include_point_cloud:
            point_cloud_mesh = exporter._convert_points_to_mesh(point_cloud)
        exporter.export_separate_components(base_name, heat_tube_mesh, point_cloud_mesh)
    
    # プレビュー画像生成
    if args.preview:
        preview_path = args.output.replace('.ply', '_preview.png')
        exporter.create_preview_image(preview_path)
        if verbose:
            print(f"プレビュー画像を生成しました: {preview_path}")
    
    # 出力ファイルの検証
    if not exporter.validate_output(args.output):
        print("警告: 出力ファイルの検証に失敗しました")
    
    # 3Dビューアーで表示
    if args.visualize:
        if verbose:
            print("3Dビューアーを起動中...")
        tube_generator = HeatTubeGenerator()
        tube_generator.tube_mesh = combined_mesh
        tube_generator.visualize_tube()


def main():
    """メイン処理"""
    # コマンドライン引数の解析
    args = parse_arguments()
    
    print("3D放射線ヒートマップ生成ツール")
    print("=" * 50)
    
    start_time = datetime.now()
    
    try:
        # 1. データ読み込み
        data = load_data(args, verbose=args.verbose)
        
        # 2. 軌跡データ処理
        processed_trajectory, processed_timestamps, trajectory_metrics = process_trajectory(
            data, args, verbose=args.verbose
        )
        
        # 3. データ同期とヒートチューブ生成
        heat_tube_mesh, synchronized_trajectory, synchronized_dose_rates = synchronize_and_generate_heat_tube(
            processed_trajectory, processed_timestamps,
            data['dose_rates'], data['dose_timestamps'],
            args, verbose=args.verbose
        )
        
        # 4. メタデータの準備
        metadata = {
            'generation_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'input_ply_file': args.ply_file,
            'input_json_file': args.json_file,
            'input_csv_file': args.csv_file,
            'tube_radius_m': args.tube_radius,
            'tube_diameter_m': args.tube_radius * 2,
            'dose_range_min_uSv_h': args.dose_range[0],
            'dose_range_max_uSv_h': args.dose_range[1],
            'radial_segments': args.radial_segments,
            'original_trajectory_points': len(data['trajectory']),
            'processed_trajectory_points': len(processed_trajectory),
            'synchronized_points': len(synchronized_trajectory),
            'total_trajectory_distance_m': trajectory_metrics['total_distance'],
            'point_cloud_points': len(data['point_cloud']) if args.include_point_cloud else 0,
            'smooth_trajectory': args.smooth_trajectory,
            'remove_outliers': args.remove_outliers
        }
        
        # 5. 結果出力
        export_results(
            heat_tube_mesh, 
            data['point_cloud'] if args.include_point_cloud else None,
            args, metadata, verbose=args.verbose
        )
        
        # 処理完了
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"\n処理完了!")
        print(f"処理時間: {processing_time:.1f}秒")
        print(f"出力ファイル: {args.output}")
        
        if args.verbose:
            print("\n=== 処理サマリー ===")
            print(f"元軌跡点数: {len(data['trajectory'])}")
            print(f"同期後点数: {len(synchronized_trajectory)}")
            print(f"線量率範囲: {np.min(synchronized_dose_rates):.3f} - {np.max(synchronized_dose_rates):.3f} μSv/h")
            print(f"チューブ半径: {args.tube_radius}m (直径: {args.tube_radius*2}m)")
        
    except KeyboardInterrupt:
        print("\n処理が中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()