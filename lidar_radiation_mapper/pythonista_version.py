#!/usr/bin/env python3
"""
Pythonista3用の簡易版スクリプト
iPhone上で直接実行可能なバージョン

注意: Pythonista3では一部のライブラリが利用できない可能性があるため、
      必要に応じて代替実装を使用しています。
"""
import json
import csv
import math
from datetime import datetime


class SimpleLiDARRadiationMapper:
    """Pythonista3用の簡易マッパークラス"""
    
    def __init__(self):
        self.trajectory_data = []
        self.radiation_data = []
        self.synchronized_data = []
        
    def load_polycam_json(self, json_path):
        """PolycamのJSONファイルを読み込む"""
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # 軌跡データを抽出（Polycamの形式に応じて調整が必要）
        self.trajectory_data = []
        
        if 'frames' in data:
            for frame in data['frames']:
                self.trajectory_data.append({
                    'timestamp': frame.get('timestamp', 0),
                    'x': frame.get('position', {}).get('x', 0),
                    'y': frame.get('position', {}).get('y', 0),
                    'z': frame.get('position', {}).get('z', 0)
                })
        elif 'trajectory' in data:
            for point in data['trajectory']:
                self.trajectory_data.append({
                    'timestamp': point.get('timestamp', 0),
                    'x': point.get('x', 0),
                    'y': point.get('y', 0),
                    'z': point.get('z', 0)
                })
        
        print(f"軌跡データ読み込み: {len(self.trajectory_data)} ポイント")
        return self.trajectory_data
    
    def load_radiation_csv(self, csv_path):
        """AccuRadのCSVファイルを読み込む"""
        self.radiation_data = []
        
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            
            for row in reader:
                try:
                    # CSVの形式に応じて調整が必要
                    self.radiation_data.append({
                        'timestamp': float(row[0]) if row[0] else 0,
                        'dose_rate': float(row[1]) if row[1] else 0
                    })
                except (ValueError, IndexError):
                    continue
        
        print(f"放射線データ読み込み: {len(self.radiation_data)} レコード")
        return self.radiation_data
    
    def synchronize_data(self):
        """軌跡データと放射線データを同期"""
        self.synchronized_data = []
        
        for traj_point in self.trajectory_data:
            # 最も近い放射線データを見つける
            closest_dose = self._find_closest_dose_rate(traj_point['timestamp'])
            
            self.synchronized_data.append({
                'timestamp': traj_point['timestamp'],
                'x': traj_point['x'],
                'y': traj_point['y'],
                'z': traj_point['z'],
                'dose_rate': closest_dose
            })
        
        print(f"データ同期完了: {len(self.synchronized_data)} ポイント")
        return self.synchronized_data
    
    def _find_closest_dose_rate(self, timestamp):
        """指定タイムスタンプに最も近い線量率を取得"""
        if not self.radiation_data:
            return 0.0
        
        closest = min(self.radiation_data, 
                     key=lambda x: abs(x['timestamp'] - timestamp))
        return closest['dose_rate']
    
    def dose_to_rgb(self, dose_rate, min_dose=0, max_dose=10):
        """線量率をRGB色に変換（青→赤のグラデーション）"""
        # 0-1に正規化
        normalized = max(0, min(1, (dose_rate - min_dose) / (max_dose - min_dose)))
        
        # 青(0,0,255) → シアン(0,255,255) → 緑(0,255,0) → 黄(255,255,0) → 赤(255,0,0)
        if normalized < 0.25:
            # 青→シアン
            t = normalized * 4
            r, g, b = 0, int(255 * t), 255
        elif normalized < 0.5:
            # シアン→緑
            t = (normalized - 0.25) * 4
            r, g, b = 0, 255, int(255 * (1 - t))
        elif normalized < 0.75:
            # 緑→黄
            t = (normalized - 0.5) * 4
            r, g, b = int(255 * t), 255, 0
        else:
            # 黄→赤
            t = (normalized - 0.75) * 4
            r, g, b = 255, int(255 * (1 - t)), 0
        
        return (r, g, b)
    
    def generate_simple_ply(self, output_path, tube_radius=0.05):
        """簡易的なPLYファイルを生成"""
        if not self.synchronized_data:
            print("エラー: 同期データがありません")
            return False
        
        vertices = []
        colors = []
        faces = []
        
        # 各セグメントごとにチューブを生成
        for i in range(len(self.synchronized_data) - 1):
            current = self.synchronized_data[i]
            next_point = self.synchronized_data[i + 1]
            
            # 現在の点と次の点の色を計算
            color_current = self.dose_to_rgb(current['dose_rate'])
            color_next = self.dose_to_rgb(next_point['dose_rate'])
            
            # 簡易的な線分として頂点を追加
            vertex_index = len(vertices)
            
            # 始点
            vertices.append([current['x'], current['y'], current['z']])
            colors.append(color_current)
            
            # 終点
            vertices.append([next_point['x'], next_point['y'], next_point['z']])
            colors.append(color_next)
        
        # PLYファイルとして出力
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
        
        print(f"PLYファイル出力完了: {output_path}")
        return True
    
    def generate_full_tube_ply(self, output_path, tube_radius=0.05, segments=8):
        """完全なチューブ形状のPLYファイルを生成"""
        if not self.synchronized_data:
            print("エラー: 同期データがありません")
            return False
        
        vertices = []
        colors = []
        faces = []
        
        for i in range(len(self.synchronized_data) - 1):
            current = self.synchronized_data[i]
            next_point = self.synchronized_data[i + 1]
            
            # 方向ベクトルを計算
            dx = next_point['x'] - current['x']
            dy = next_point['y'] - current['y']
            dz = next_point['z'] - current['z']
            length = math.sqrt(dx*dx + dy*dy + dz*dz)
            
            if length < 1e-6:
                continue
            
            # 正規化
            dx, dy, dz = dx/length, dy/length, dz/length
            
            # 垂直ベクトルを生成
            if abs(dz) < 0.9:
                ux, uy, uz = 0, 0, 1
            else:
                ux, uy, uz = 1, 0, 0
            
            # 外積で右ベクトルを計算
            rx = uy * dz - uz * dy
            ry = uz * dx - ux * dz
            rz = ux * dy - uy * dx
            rl = math.sqrt(rx*rx + ry*ry + rz*rz)
            rx, ry, rz = rx/rl, ry/rl, rz/rl
            
            # 上ベクトルを計算
            ux = dy * rz - dz * ry
            uy = dz * rx - dx * rz
            uz = dx * ry - dy * rx
            
            # 色を計算
            color_current = self.dose_to_rgb(current['dose_rate'])
            color_next = self.dose_to_rgb(next_point['dose_rate'])
            
            # 円周上の頂点を生成
            vertex_start = len(vertices)
            
            for j in range(2):  # 始点と終点
                if j == 0:
                    cx, cy, cz = current['x'], current['y'], current['z']
                    color = color_current
                else:
                    cx, cy, cz = next_point['x'], next_point['y'], next_point['z']
                    color = color_next
                
                for k in range(segments):
                    angle = 2 * math.pi * k / segments
                    cos_a = math.cos(angle)
                    sin_a = math.sin(angle)
                    
                    # オフセットを計算
                    ox = tube_radius * (cos_a * rx + sin_a * ux)
                    oy = tube_radius * (cos_a * ry + sin_a * uy)
                    oz = tube_radius * (cos_a * rz + sin_a * uz)
                    
                    vertices.append([cx + ox, cy + oy, cz + oz])
                    colors.append(color)
            
            # 面を生成
            for k in range(segments):
                k_next = (k + 1) % segments
                
                # 三角形1
                v1 = vertex_start + k
                v2 = vertex_start + k_next
                v3 = vertex_start + k + segments
                faces.append([v1, v2, v3])
                
                # 三角形2
                v1 = vertex_start + k_next
                v2 = vertex_start + k_next + segments
                v3 = vertex_start + k + segments
                faces.append([v1, v2, v3])
        
        # PLYファイルとして出力
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
            f.write(f"element face {len(faces)}\n")
            f.write("property list uchar int vertex_indices\n")
            f.write("end_header\n")
            
            # 頂点データ
            for vertex, color in zip(vertices, colors):
                f.write(f"{vertex[0]} {vertex[1]} {vertex[2]} ")
                f.write(f"{color[0]} {color[1]} {color[2]}\n")
            
            # 面データ
            for face in faces:
                f.write(f"3 {face[0]} {face[1]} {face[2]}\n")
        
        print(f"完全なPLYファイル出力完了: {output_path}")
        print(f"  頂点数: {len(vertices)}")
        print(f"  面数: {len(faces)}")
        return True


# 使用例
def main():
    """メイン処理（Pythonista3用）"""
    print("=" * 50)
    print("LiDAR + 放射線データマッピングツール")
    print("Pythonista3版")
    print("=" * 50)
    
    # ファイルパスを設定（Pythonista3の環境に応じて調整）
    json_path = "sample_trajectory.json"  # Polycamの軌跡データ
    csv_path = "sample_radiation.csv"     # AccuRadの測定データ
    output_path = "pythonista_output.ply"     # 出力ファイル
    
    # マッパーを初期化
    mapper = SimpleLiDARRadiationMapper()
    
    try:
        # データを読み込み
        print("\n[1/3] データ読み込み中...")
        mapper.load_polycam_json(json_path)
        mapper.load_radiation_csv(csv_path)
        
        # データを同期
        print("\n[2/3] データ同期中...")
        mapper.synchronize_data()
        
        # PLYファイルを生成
        print("\n[3/3] PLYファイル生成中...")
        # 簡易版（線のみ）
        # mapper.generate_simple_ply(output_path)
        
        # 完全版（チューブ形状）
        mapper.generate_full_tube_ply(output_path, tube_radius=0.05)
        
        print("\n✓ 処理完了！")
        
    except Exception as e:
        print(f"\nエラー: {e}")
        return False
    
    return True


if __name__ == '__main__':
    main()