#!/usr/bin/env python3
"""
3D放射線ヒートマップ生成ツール - 使用例

このスクリプトは、ツールの基本的な使用方法を示すサンプルコードです。
"""

import numpy as np
import json
import pandas as pd
import os
from datetime import datetime, timedelta

# 自作モジュールをインポート
from data_loader import PolycamDataLoader, AccuRadDataLoader
from trajectory_processor import TrajectoryProcessor
from heat_tube_generator import HeatTubeGenerator
from ply_exporter import PLYExporter


def create_sample_data():
    """
    サンプルデータを生成する関数
    実際のデータが無い場合のテスト用
    """
    print("サンプルデータを生成中...")
    
    # サンプル軌跡データの生成（螺旋状の軌跡）
    t = np.linspace(0, 4*np.pi, 100)
    trajectory = np.column_stack([
        np.cos(t) * 2,  # X座標
        np.sin(t) * 2,  # Y座標  
        t * 0.1         # Z座標（上昇）
    ])
    
    # サンプルタイムスタンプ（1秒間隔）
    base_time = datetime.now()
    timestamps = [base_time + timedelta(seconds=i) for i in range(len(trajectory))]
    
    # サンプルJSONファイルを生成
    frames = []
    for i, (pos, ts) in enumerate(zip(trajectory, timestamps)):
        # 4x4変換行列を生成（位置のみ設定、回転は単位行列）
        transform_matrix = [
            [1.0, 0.0, 0.0, float(pos[0])],
            [0.0, 1.0, 0.0, float(pos[1])],
            [0.0, 0.0, 1.0, float(pos[2])],
            [0.0, 0.0, 0.0, 1.0]
        ]
        
        frame = {
            "transform_matrix": transform_matrix,
            "timestamp": ts.timestamp(),
            "time": ts.isoformat()
        }
        frames.append(frame)
    
    slam_data = {
        "camera_model": "PINHOLE",
        "frames": frames
    }
    
    # JSONファイルを保存
    with open("sample_slam.json", "w") as f:
        json.dump(slam_data, f, indent=2)
    
    # サンプル線量率データの生成
    dose_data = []
    for i, ts in enumerate(timestamps):
        # 軌跡に沿って変化する線量率（0-10μSv/hの範囲）
        dose_rate = 2.0 + 3.0 * np.sin(i * 0.1) + np.random.normal(0, 0.5)
        dose_rate = max(0, min(10, dose_rate))  # 0-10の範囲にクリップ
        
        dose_data.append({
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "dose_rate": dose_rate,
            "x": trajectory[i][0],
            "y": trajectory[i][1], 
            "z": trajectory[i][2]
        })
    
    # CSVファイルを保存
    df = pd.DataFrame(dose_data)
    df.to_csv("sample_dose_rates.csv", index=False)
    
    # サンプル点群データの生成（ランダム点群）
    n_points = 10000
    point_cloud = np.random.randn(n_points, 3) * 5  # 5m範囲のランダム点群
    
    # 簡単なPLYファイルを生成
    with open("sample_pointcloud.ply", "w") as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {n_points}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("property uchar red\n")
        f.write("property uchar green\n")
        f.write("property uchar blue\n")
        f.write("end_header\n")
        
        for point in point_cloud:
            # グレーの点群
            f.write(f"{point[0]:.6f} {point[1]:.6f} {point[2]:.6f} 128 128 128\n")
    
    print("サンプルデータを生成しました:")
    print("  - sample_slam.json")
    print("  - sample_dose_rates.csv")
    print("  - sample_pointcloud.ply")
    
    return "sample_pointcloud.ply", "sample_slam.json", "sample_dose_rates.csv"


def example_basic_usage():
    """基本的な使用例"""
    print("\n=== 基本的な使用例 ===")
    
    # サンプルデータを生成
    ply_file, json_file, csv_file = create_sample_data()
    
    try:
        # 1. データ読み込み
        print("1. データを読み込み中...")
        polycam_loader = PolycamDataLoader(ply_file, json_file)
        accuRad_loader = AccuRadDataLoader(csv_file)
        
        # PLYファイルから点群を読み込み
        point_cloud = polycam_loader.load_ply()
        
        # JSONファイルからSLAMデータを読み込み
        slam_data = polycam_loader.load_json()
        trajectory = polycam_loader.get_trajectory()
        polycam_timestamps = polycam_loader.timestamps
        
        # CSVファイルから線量率データを読み込み
        dose_data = accuRad_loader.load_csv()
        dose_rates = accuRad_loader.dose_rates
        dose_timestamps = accuRad_loader.timestamps
        
        print(f"   点群: {len(point_cloud):,}点")
        print(f"   軌跡: {len(trajectory)}点")
        print(f"   線量率: {len(dose_rates)}点")
        
        # 2. 軌跡処理
        print("2. 軌跡を処理中...")
        processor = TrajectoryProcessor()
        processor.set_trajectory(trajectory, polycam_timestamps)
        
        # 軌跡をスムージング
        smoothed_trajectory = processor.smooth_trajectory(sigma=1.0)
        
        # 統計情報を表示
        metrics = processor.calculate_trajectory_metrics()
        print(f"   総距離: {metrics['total_distance']:.2f}m")
        
        # 3. データ同期
        print("3. データを同期中...")
        # タイムスタンプをUnix時刻に変換
        if isinstance(dose_timestamps[0], str):
            dose_timestamps = pd.to_datetime(dose_timestamps).astype(int) / 10**9
        
        # 簡単な同期（最近傍マッチング）
        synchronized_trajectory = []
        synchronized_dose_rates = []
        
        for i, poly_time in enumerate(polycam_timestamps):
            # 最も近い線量率データを見つける
            time_diffs = np.abs(dose_timestamps - poly_time)
            min_idx = np.argmin(time_diffs)
            
            if time_diffs[min_idx] <= 2.0:  # 2秒以内
                synchronized_trajectory.append(smoothed_trajectory[i])
                synchronized_dose_rates.append(dose_rates[min_idx])
        
        synchronized_trajectory = np.array(synchronized_trajectory)
        synchronized_dose_rates = np.array(synchronized_dose_rates)
        
        print(f"   同期後: {len(synchronized_trajectory)}点")
        
        # 4. ヒートチューブ生成
        print("4. ヒートチューブを生成中...")
        tube_generator = HeatTubeGenerator(tube_radius=0.05)  # 直径10cm
        heat_tube_mesh = tube_generator.create_tube_mesh(
            synchronized_trajectory,
            synchronized_dose_rates,
            radial_segments=16,
            dose_range=(0.0, 10.0)
        )
        
        vertices = np.asarray(heat_tube_mesh.vertices)
        triangles = np.asarray(heat_tube_mesh.triangles)
        print(f"   頂点: {len(vertices):,}, 面: {len(triangles):,}")
        
        # 5. PLY出力
        print("5. PLYファイルを出力中...")
        exporter = PLYExporter()
        
        # メタデータを追加
        metadata = {
            "generation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "trajectory_points": len(synchronized_trajectory),
            "dose_range": "0.0-10.0 μSv/h",
            "tube_diameter": "10cm"
        }
        exporter.add_metadata(metadata)
        
        # ヒートチューブと点群を統合
        combined_mesh = exporter.combine_geometries(
            heat_tube_mesh,
            point_cloud=point_cloud[:1000]  # 点群を1000点に制限
        )
        
        # PLYファイルとして出力
        output_file = "example_heatmap.ply"
        success = exporter.export_to_ply(output_file)
        
        if success:
            print(f"   出力完了: {output_file}")
            
            # プレビュー画像を生成
            exporter.create_preview_image("example_preview.png")
            print("   プレビュー画像: example_preview.png")
            
            # カラースケールバーを生成
            tube_generator.create_color_scale_bar(
                (0.0, 10.0), 
                save_path="example_colorbar.png"
            )
            print("   カラーバー: example_colorbar.png")
            
        # 6. 結果の可視化（オプション）
        if input("3Dビューアーで表示しますか？ (y/n): ").lower() == 'y':
            tube_generator.tube_mesh = combined_mesh
            tube_generator.visualize_tube()
        
        print("\n基本使用例完了!")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


def example_advanced_usage():
    """高度な使用例"""
    print("\n=== 高度な使用例 ===")
    
    # より複雑な軌跡データの生成
    print("複雑な軌跡データを生成中...")
    
    # 建物内を移動するような軌跡
    trajectory_parts = []
    
    # 廊下を直進
    t1 = np.linspace(0, 10, 50)
    part1 = np.column_stack([t1, np.zeros(50), np.ones(50) * 1.5])
    
    # 右に曲がる
    t2 = np.linspace(0, np.pi/2, 25)
    part2 = np.column_stack([
        10 + 2*np.sin(t2),
        2*(1-np.cos(t2)),
        np.ones(25) * 1.5
    ])
    
    # また直進
    t3 = np.linspace(0, 8, 40)
    part3 = np.column_stack([
        12 + np.zeros(40),
        2 + t3,
        np.ones(40) * 1.5
    ])
    
    complex_trajectory = np.vstack([part1, part2, part3])
    
    # 線量率データ（部屋によって異なる）
    dose_rates = np.concatenate([
        np.random.normal(1.0, 0.2, 50),  # 低線量エリア
        np.random.normal(5.0, 1.0, 25),  # 中線量エリア（曲がり角）
        np.random.normal(8.0, 1.5, 40)   # 高線量エリア
    ])
    dose_rates = np.clip(dose_rates, 0, 10)
    
    print(f"複雑な軌跡: {len(complex_trajectory)}点")
    print(f"線量率範囲: {np.min(dose_rates):.2f} - {np.max(dose_rates):.2f} μSv/h")
    
    # ヒートチューブ生成（より高解像度）
    tube_generator = HeatTubeGenerator(tube_radius=0.03)  # 直径6cm
    heat_tube_mesh = tube_generator.create_tube_mesh(
        complex_trajectory,
        dose_rates,
        radial_segments=24,  # より滑らかな円
        dose_range=(0.0, 10.0)
    )
    
    # 個別コンポーネントとして出力
    exporter = PLYExporter()
    exporter.export_separate_components(
        "advanced_example",
        heat_tube_mesh
    )
    
    # カラースケールバーを生成
    tube_generator.create_color_scale_bar(
        (0.0, 10.0),
        save_path="advanced_colorbar.png"
    )
    
    print("高度な使用例完了!")
    print("出力ファイル:")
    print("  - advanced_example_heat_tube.ply")
    print("  - advanced_colorbar.png")


def cleanup_sample_files():
    """サンプルファイルをクリーンアップ"""
    sample_files = [
        "sample_slam.json",
        "sample_dose_rates.csv", 
        "sample_pointcloud.ply",
        "example_heatmap.ply",
        "example_preview.png",
        "example_colorbar.png",
        "example_heatmap_metadata.txt",
        "advanced_example_heat_tube.ply",
        "advanced_colorbar.png"
    ]
    
    print("\nサンプルファイルをクリーンアップ中...")
    for file in sample_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"  削除: {file}")


def main():
    """メイン関数"""
    print("3D放射線ヒートマップ生成ツール - 使用例")
    print("=" * 50)
    
    try:
        # 基本使用例
        example_basic_usage()
        
        # 高度な使用例
        if input("\n高度な使用例も実行しますか？ (y/n): ").lower() == 'y':
            example_advanced_usage()
        
        # クリーンアップ
        if input("\nサンプルファイルを削除しますか？ (y/n): ").lower() == 'y':
            cleanup_sample_files()
        
        print("\n使用例の実行完了!")
        
    except KeyboardInterrupt:
        print("\n処理が中断されました")
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()