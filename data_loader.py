"""
データローダーモジュール
Polycam PLY/JSONファイルとAccuRad CSVファイルを読み込む機能を提供
"""

import json
import pandas as pd
import numpy as np
from plyfile import PlyData, PlyElement
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import open3d as o3d


class PolycamDataLoader:
    """Polycamから取得したPLYとJSONデータを読み込むクラス"""
    
    def __init__(self, ply_path: str, json_path: str):
        self.ply_path = ply_path
        self.json_path = json_path
        self.point_cloud = None
        self.camera_poses = None
        self.timestamps = None
    
    def load_ply(self) -> np.ndarray:
        """PLYファイルから点群データを読み込む"""
        try:
            # Open3Dを使用してPLYファイルを読み込み
            pcd = o3d.io.read_point_cloud(self.ply_path)
            self.point_cloud = np.asarray(pcd.points)
            print(f"PLY点群データを読み込みました: {self.point_cloud.shape[0]}点")
            return self.point_cloud
        except Exception as e:
            print(f"PLYファイル読み込みエラー: {e}")
            return None
    
    def load_json(self) -> Dict:
        """JSONファイルからSLAMデータを読み込む"""
        try:
            with open(self.json_path, 'r') as f:
                data = json.load(f)
            
            # 一般的なPolycam JSONフォーマットを想定
            # 実際のフォーマットに応じて調整が必要
            if 'frames' in data:
                self.camera_poses = []
                self.timestamps = []
                
                for frame in data['frames']:
                    # カメラポーズ（4x4変換行列）
                    if 'transform_matrix' in frame:
                        pose = np.array(frame['transform_matrix'])
                        self.camera_poses.append(pose)
                    
                    # タイムスタンプ
                    if 'timestamp' in frame:
                        self.timestamps.append(frame['timestamp'])
                    elif 'time' in frame:
                        self.timestamps.append(frame['time'])
                
                self.camera_poses = np.array(self.camera_poses)
                self.timestamps = np.array(self.timestamps)
                
                print(f"カメラポーズデータを読み込みました: {len(self.camera_poses)}フレーム")
                return data
            
        except Exception as e:
            print(f"JSONファイル読み込みエラー: {e}")
            return None
    
    def get_trajectory(self) -> np.ndarray:
        """カメラポーズから軌跡（位置のみ）を抽出"""
        if self.camera_poses is not None:
            # 4x4変換行列の平行移動成分（最後の列の最初の3要素）を抽出
            trajectory = self.camera_poses[:, :3, 3]
            return trajectory
        return None


class AccuRadDataLoader:
    """AccuRad PRDから取得したCSVデータを読み込むクラス"""
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.data = None
        self.timestamps = None
        self.dose_rates = None
        self.positions = None
    
    def load_csv(self) -> pd.DataFrame:
        """CSVファイルから線量率データを読み込む"""
        try:
            # 一般的なCSVフォーマットを想定（実際の形式に応じて調整が必要）
            self.data = pd.read_csv(self.csv_path)
            
            # タイムスタンプ列を検出・変換
            timestamp_columns = ['timestamp', 'time', 'datetime', 'Time', 'Timestamp']
            timestamp_col = None
            
            for col in timestamp_columns:
                if col in self.data.columns:
                    timestamp_col = col
                    break
            
            if timestamp_col:
                self.timestamps = pd.to_datetime(self.data[timestamp_col])
            
            # 線量率列を検出
            dose_columns = ['dose_rate', 'doserate', 'dose', 'radiation', 'uSv/h', 'μSv/h']
            dose_col = None
            
            for col in dose_columns:
                if col in self.data.columns:
                    dose_col = col
                    break
            
            if dose_col:
                self.dose_rates = self.data[dose_col].values
            
            # 位置情報があれば読み込み（オプション）
            if 'x' in self.data.columns and 'y' in self.data.columns and 'z' in self.data.columns:
                self.positions = self.data[['x', 'y', 'z']].values
            
            print(f"線量率データを読み込みました: {len(self.data)}レコード")
            return self.data
            
        except Exception as e:
            print(f"CSVファイル読み込みエラー: {e}")
            return None
    
    def get_dose_rate_range(self) -> Tuple[float, float]:
        """線量率の最小値と最大値を取得"""
        if self.dose_rates is not None:
            return np.min(self.dose_rates), np.max(self.dose_rates)
        return 0.0, 10.0  # デフォルト値


def synchronize_data(polycam_timestamps: np.ndarray, 
                    accuRad_timestamps: np.ndarray,
                    trajectory: np.ndarray,
                    dose_rates: np.ndarray,
                    time_tolerance: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    タイムスタンプに基づいて軌跡データと線量率データを同期
    
    Args:
        polycam_timestamps: Polycamのタイムスタンプ
        accuRad_timestamps: AccuRadのタイムスタンプ
        trajectory: 軌跡データ
        dose_rates: 線量率データ
        time_tolerance: 時間許容誤差（秒）
    
    Returns:
        同期された軌跡データと線量率データのタプル
    """
    synchronized_trajectory = []
    synchronized_dose_rates = []
    
    # Polycamの各タイムスタンプに対して最も近いAccuRadデータを見つける
    for i, poly_time in enumerate(polycam_timestamps):
        # 時間差を計算
        time_diffs = np.abs(accuRad_timestamps - poly_time)
        min_diff_idx = np.argmin(time_diffs)
        min_diff = time_diffs[min_diff_idx]
        
        # 許容誤差内であれば同期データとして採用
        if min_diff <= time_tolerance:
            synchronized_trajectory.append(trajectory[i])
            synchronized_dose_rates.append(dose_rates[min_diff_idx])
    
    return np.array(synchronized_trajectory), np.array(synchronized_dose_rates)