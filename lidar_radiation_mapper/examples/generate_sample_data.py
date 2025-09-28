#!/usr/bin/env python3
"""
サンプルデータ生成スクリプト
テスト用のダミーデータを生成します
"""
import json
import csv
import numpy as np
from datetime import datetime, timedelta
import random


def generate_sample_trajectory_json(output_path="sample_trajectory.json", num_points=100):
    """サンプルの軌跡JSONファイルを生成"""
    
    # スパイラル状の軌跡を生成
    trajectory_data = {
        "version": "1.0",
        "capture_date": datetime.now().isoformat(),
        "device": "iPhone16Pro",
        "app": "Polycam",
        "frames": []
    }
    
    base_time = datetime.now().timestamp()
    
    for i in range(num_points):
        t = i / num_points * 4 * np.pi
        
        # スパイラル軌跡
        x = 5 * np.cos(t) * (1 - i/num_points)
        y = 5 * np.sin(t) * (1 - i/num_points)
        z = i / num_points * 3  # 0から3メートルまで上昇
        
        frame = {
            "frame_id": i,
            "timestamp": base_time + i * 0.5,  # 0.5秒間隔
            "position": {
                "x": float(x),
                "y": float(y),
                "z": float(z)
            },
            "orientation": {
                "w": 1.0,
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
            }
        }
        
        trajectory_data["frames"].append(frame)
    
    with open(output_path, 'w') as f:
        json.dump(trajectory_data, f, indent=2)
    
    print(f"サンプル軌跡データ生成: {output_path}")
    print(f"  ポイント数: {num_points}")
    return trajectory_data


def generate_sample_radiation_csv(output_path="sample_radiation.csv", 
                                 duration_seconds=50, 
                                 interval_seconds=0.1):
    """サンプルの放射線測定CSVファイルを生成"""
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # ヘッダー
        writer.writerow(['timestamp', 'dose_rate_uSv_h', 'unit', 'device'])
        
        base_time = datetime.now()
        num_measurements = int(duration_seconds / interval_seconds)
        
        for i in range(num_measurements):
            current_time = base_time + timedelta(seconds=i * interval_seconds)
            
            # 線量率を生成（位置に応じて変化）
            # 中心部で高く、外側で低い + ランダムノイズ
            progress = i / num_measurements
            
            # ホットスポットをシミュレート
            if 0.3 < progress < 0.4:
                base_dose = 8.0  # ホットスポット1
            elif 0.6 < progress < 0.65:
                base_dose = 9.5  # ホットスポット2
            else:
                base_dose = 1.0 + progress * 2.0  # 徐々に上昇
            
            # ランダムノイズを追加
            dose_rate = max(0, base_dose + random.gauss(0, 0.5))
            dose_rate = min(10, dose_rate)  # 0-10μSv/hの範囲に制限
            
            writer.writerow([
                current_time.timestamp(),
                f"{dose_rate:.3f}",
                "uSv/h",
                "AccuRad_PRD"
            ])
    
    print(f"サンプル放射線データ生成: {output_path}")
    print(f"  測定数: {num_measurements}")
    print(f"  期間: {duration_seconds}秒")
    return output_path


def generate_sample_ply_pointcloud(output_path="sample_pointcloud.ply", 
                                  num_points=10000,
                                  area_size=10):
    """サンプルの点群PLYファイルを生成"""
    
    vertices = []
    colors = []
    
    # ランダムな点群を生成（床と壁をシミュレート）
    for i in range(num_points):
        if i < num_points // 2:
            # 床
            x = random.uniform(-area_size/2, area_size/2)
            y = random.uniform(-area_size/2, area_size/2)
            z = random.gauss(0, 0.1)  # 床の高さにノイズ
            color = (128, 128, 128)  # グレー
        else:
            # 壁（4面）
            wall = random.choice(['north', 'south', 'east', 'west'])
            if wall == 'north':
                x = random.uniform(-area_size/2, area_size/2)
                y = area_size/2 + random.gauss(0, 0.1)
                z = random.uniform(0, 3)
            elif wall == 'south':
                x = random.uniform(-area_size/2, area_size/2)
                y = -area_size/2 + random.gauss(0, 0.1)
                z = random.uniform(0, 3)
            elif wall == 'east':
                x = area_size/2 + random.gauss(0, 0.1)
                y = random.uniform(-area_size/2, area_size/2)
                z = random.uniform(0, 3)
            else:  # west
                x = -area_size/2 + random.gauss(0, 0.1)
                y = random.uniform(-area_size/2, area_size/2)
                z = random.uniform(0, 3)
            
            color = (200, 200, 200)  # 明るいグレー
        
        vertices.append((x, y, z))
        colors.append(color)
    
    # PLYファイルとして保存
    with open(output_path, 'w') as f:
        # ヘッダー
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(vertices)}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("property uchar red\n")
        f.write("property uchar green\n")
        f.write("property uchar blue\n")
        f.write("end_header\n")
        
        # 頂点データ
        for vertex, color in zip(vertices, colors):
            f.write(f"{vertex[0]} {vertex[1]} {vertex[2]} ")
            f.write(f"{color[0]} {color[1]} {color[2]}\n")
    
    print(f"サンプル点群データ生成: {output_path}")
    print(f"  点数: {num_points}")
    return output_path


def main():
    """メイン処理"""
    print("=" * 60)
    print("サンプルデータ生成スクリプト")
    print("=" * 60)
    
    # 出力ディレクトリ
    import os
    output_dir = "sample_data"
    os.makedirs(output_dir, exist_ok=True)
    
    # 各種サンプルデータを生成
    print("\n[1/3] 軌跡データ生成中...")
    trajectory_path = os.path.join(output_dir, "sample_trajectory.json")
    generate_sample_trajectory_json(trajectory_path, num_points=100)
    
    print("\n[2/3] 放射線データ生成中...")
    radiation_path = os.path.join(output_dir, "sample_radiation.csv")
    generate_sample_radiation_csv(radiation_path, duration_seconds=50)
    
    print("\n[3/3] 点群データ生成中...")
    pointcloud_path = os.path.join(output_dir, "sample_pointcloud.ply")
    generate_sample_ply_pointcloud(pointcloud_path, num_points=5000)
    
    print("\n" + "=" * 60)
    print("サンプルデータ生成完了！")
    print("=" * 60)
    print("\n生成されたファイル:")
    print(f"  - {trajectory_path}")
    print(f"  - {radiation_path}")
    print(f"  - {pointcloud_path}")
    
    print("\n使用例:")
    print("python ../main.py \\")
    print(f"  --lidar-ply {pointcloud_path} \\")
    print(f"  --lidar-json {trajectory_path} \\")
    print(f"  --radiation-csv {radiation_path} \\")
    print("  --output output_with_heatline.ply \\")
    print("  --include-pointcloud \\")
    print("  --add-markers \\")
    print("  --export-legend")


if __name__ == "__main__":
    main()