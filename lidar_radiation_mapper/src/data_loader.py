"""
データローダーモジュール
Polycamから出力されたPLY/JSONファイルとAccuRad PRDのCSVファイルを読み込む
"""
import json
import pandas as pd
import numpy as np
from plyfile import PlyData
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional


class PolycamDataLoader:
    """PolycamのLiDARデータを読み込むクラス"""
    
    def __init__(self, ply_path: str, json_path: str):
        """
        Args:
            ply_path: PLYファイルのパス
            json_path: JSONファイル（SLAMデータ）のパス
        """
        self.ply_path = ply_path
        self.json_path = json_path
        self.point_cloud = None
        self.slam_data = None
        
    def load_ply(self) -> np.ndarray:
        """PLYファイルから点群データを読み込む"""
        plydata = PlyData.read(self.ply_path)
        
        # 頂点データを取得
        vertex = plydata['vertex']
        
        # XYZ座標を取得
        x = vertex['x']
        y = vertex['y']
        z = vertex['z']
        
        # RGB色情報があれば取得
        colors = None
        vertex_dtype_names = vertex.data.dtype.names if hasattr(vertex.data, 'dtype') else []
        if 'red' in vertex_dtype_names:
            r = vertex['red']
            g = vertex['green']
            b = vertex['blue']
            colors = np.column_stack((r, g, b))
        
        points = np.column_stack((x, y, z))
        
        self.point_cloud = {
            'points': points,
            'colors': colors
        }
        
        return points
    
    def load_slam_trajectory(self) -> Dict:
        """JSONファイルからSLAMの軌跡データを読み込む"""
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.slam_data = data
        
        # Polycamの出力形式に応じて調整が必要
        # 以下は想定される形式の例
        trajectory = []
        
        # カメラポーズデータを抽出（形式は要確認）
        if 'frames' in data:
            for frame in data['frames']:
                timestamp = frame.get('timestamp', 0)
                
                # 位置情報
                position = frame.get('position', {})
                x = position.get('x', 0)
                y = position.get('y', 0)
                z = position.get('z', 0)
                
                # 姿勢情報（クォータニオンまたは回転行列）
                orientation = frame.get('orientation', {})
                
                trajectory.append({
                    'timestamp': timestamp,
                    'position': np.array([x, y, z]),
                    'orientation': orientation
                })
        
        elif 'trajectory' in data:
            # 別の形式の場合
            for point in data['trajectory']:
                trajectory.append({
                    'timestamp': point.get('timestamp', 0),
                    'position': np.array([
                        point.get('x', 0),
                        point.get('y', 0),
                        point.get('z', 0)
                    ])
                })
        
        return trajectory


class RadiationDataLoader:
    """AccuRad PRDの放射線測定データを読み込むクラス"""
    
    def __init__(self, csv_path: str):
        """
        Args:
            csv_path: CSVファイルのパス
        """
        self.csv_path = csv_path
        self.radiation_data = None
        
    def load_csv(self) -> pd.DataFrame:
        """CSVファイルから放射線データを読み込む"""
        # AccuRad PRDの出力形式に応じて調整が必要
        # 以下は想定される形式の例
        
        try:
            # 一般的なCSV形式を試す
            df = pd.read_csv(self.csv_path)
            
            # カラム名を確認して適切に処理
            # 想定されるカラム: timestamp, dose_rate, unit など
            required_columns = []
            
            if 'timestamp' in df.columns:
                required_columns.append('timestamp')
            elif 'time' in df.columns:
                df['timestamp'] = df['time']
                required_columns.append('timestamp')
            elif 'datetime' in df.columns:
                df['timestamp'] = df['datetime']
                required_columns.append('timestamp')
            
            # 線量率のカラムを探す
            dose_columns = ['dose_rate', 'dose', 'rate', 'value', 'measurement']
            for col in dose_columns:
                if col in df.columns:
                    df['dose_rate_uSv_h'] = df[col]
                    required_columns.append('dose_rate_uSv_h')
                    break
            
            # タイムスタンプを datetime 型に変換
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            self.radiation_data = df
            
        except Exception as e:
            print(f"CSVの読み込みエラー: {e}")
            print("カスタム形式での読み込みを試みます...")
            
            # カスタム形式での読み込み
            df = pd.read_csv(self.csv_path, header=None)
            
            # 仮のカラム名を設定
            if df.shape[1] >= 2:
                df.columns = ['timestamp', 'dose_rate_uSv_h'] + [f'col_{i}' for i in range(2, df.shape[1])]
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                self.radiation_data = df
            
        return self.radiation_data
    
    def get_interpolated_dose_rate(self, timestamp: float) -> float:
        """
        指定されたタイムスタンプの線量率を補間して取得
        
        Args:
            timestamp: Unix timestamp (seconds)
            
        Returns:
            補間された線量率 (μSv/h)
        """
        if self.radiation_data is None:
            return 0.0
        
        # タイムスタンプをdatetimeに変換
        target_time = datetime.fromtimestamp(timestamp)
        
        # 最も近い2つのデータポイントを見つけて線形補間
        df = self.radiation_data.copy()
        df['time_diff'] = abs((df['timestamp'] - target_time).dt.total_seconds())
        
        # 最も近いポイントを取得
        closest_idx = df['time_diff'].idxmin()
        
        # 単純に最も近い値を返す（より高度な補間も可能）
        return df.loc[closest_idx, 'dose_rate_uSv_h']


def synchronize_data(trajectory: List[Dict], radiation_loader: RadiationDataLoader) -> List[Dict]:
    """
    軌跡データと放射線データをタイムスタンプで同期
    
    Args:
        trajectory: SLAM軌跡データ
        radiation_loader: 放射線データローダー
        
    Returns:
        線量率が付加された軌跡データ
    """
    synchronized_data = []
    
    for point in trajectory:
        timestamp = point['timestamp']
        dose_rate = radiation_loader.get_interpolated_dose_rate(timestamp)
        
        synchronized_data.append({
            'timestamp': timestamp,
            'position': point['position'],
            'orientation': point.get('orientation', None),
            'dose_rate_uSv_h': dose_rate
        })
    
    return synchronized_data