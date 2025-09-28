"""
軌跡処理モジュール
SLAMデータから3次元軌跡を再構築し、スムージングや補間を行う
"""

import numpy as np
from scipy import interpolate
from scipy.ndimage import gaussian_filter1d
from typing import Tuple, Optional
import matplotlib.pyplot as plt


class TrajectoryProcessor:
    """軌跡データの処理クラス"""
    
    def __init__(self):
        self.trajectory = None
        self.smoothed_trajectory = None
        self.timestamps = None
    
    def set_trajectory(self, trajectory: np.ndarray, timestamps: Optional[np.ndarray] = None):
        """軌跡データを設定"""
        self.trajectory = trajectory
        self.timestamps = timestamps
        if timestamps is None:
            # タイムスタンプが無い場合は等間隔で生成
            self.timestamps = np.arange(len(trajectory))
    
    def smooth_trajectory(self, sigma: float = 1.0) -> np.ndarray:
        """
        軌跡をガウシアンフィルタでスムージング
        
        Args:
            sigma: ガウシアンフィルタの標準偏差
        
        Returns:
            スムージングされた軌跡
        """
        if self.trajectory is None:
            raise ValueError("軌跡データが設定されていません")
        
        smoothed = np.zeros_like(self.trajectory)
        for i in range(3):  # x, y, z成分それぞれにフィルタを適用
            smoothed[:, i] = gaussian_filter1d(self.trajectory[:, i], sigma=sigma)
        
        self.smoothed_trajectory = smoothed
        return smoothed
    
    def interpolate_trajectory(self, num_points: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        軌跡を指定した点数に補間
        
        Args:
            num_points: 補間後の点数
        
        Returns:
            補間された軌跡とタイムスタンプのタプル
        """
        if self.trajectory is None:
            raise ValueError("軌跡データが設定されていません")
        
        # 元の軌跡の累積距離を計算
        distances = np.cumsum(np.concatenate([[0], 
                                            np.linalg.norm(np.diff(self.trajectory, axis=0), axis=1)]))
        
        # 新しい等間隔の距離点を生成
        new_distances = np.linspace(0, distances[-1], num_points)
        
        # 各軸について補間
        interpolated = np.zeros((num_points, 3))
        for i in range(3):
            f = interpolate.interp1d(distances, self.trajectory[:, i], 
                                   kind='cubic', bounds_error=False, fill_value='extrapolate')
            interpolated[:, i] = f(new_distances)
        
        # タイムスタンプも補間
        f_time = interpolate.interp1d(distances, self.timestamps, 
                                    kind='linear', bounds_error=False, fill_value='extrapolate')
        new_timestamps = f_time(new_distances)
        
        return interpolated, new_timestamps
    
    def remove_outliers(self, threshold: float = 3.0) -> np.ndarray:
        """
        軌跡から外れ値を除去
        
        Args:
            threshold: 外れ値判定の閾値（標準偏差の倍数）
        
        Returns:
            外れ値を除去した軌跡
        """
        if self.trajectory is None:
            raise ValueError("軌跡データが設定されていません")
        
        # 各点間の距離を計算
        distances = np.linalg.norm(np.diff(self.trajectory, axis=0), axis=1)
        
        # 距離の統計値を計算
        mean_dist = np.mean(distances)
        std_dist = np.std(distances)
        
        # 外れ値のインデックスを特定
        outlier_indices = np.where(distances > mean_dist + threshold * std_dist)[0]
        
        # 外れ値の次の点も除去対象とする
        outlier_indices = np.concatenate([outlier_indices, outlier_indices + 1])
        outlier_indices = np.unique(outlier_indices)
        outlier_indices = outlier_indices[outlier_indices < len(self.trajectory)]
        
        # 外れ値を除去
        mask = np.ones(len(self.trajectory), dtype=bool)
        mask[outlier_indices] = False
        
        filtered_trajectory = self.trajectory[mask]
        filtered_timestamps = self.timestamps[mask] if self.timestamps is not None else None
        
        print(f"外れ値除去: {len(outlier_indices)}点を除去しました")
        
        return filtered_trajectory, filtered_timestamps
    
    def calculate_trajectory_metrics(self) -> dict:
        """軌跡の統計情報を計算"""
        if self.trajectory is None:
            raise ValueError("軌跡データが設定されていません")
        
        # 総距離
        distances = np.linalg.norm(np.diff(self.trajectory, axis=0), axis=1)
        total_distance = np.sum(distances)
        
        # 軌跡の範囲
        min_coords = np.min(self.trajectory, axis=0)
        max_coords = np.max(self.trajectory, axis=0)
        
        # 平均移動速度（タイムスタンプがある場合）
        avg_speed = None
        if self.timestamps is not None and len(self.timestamps) > 1:
            time_diffs = np.diff(self.timestamps)
            if np.all(time_diffs > 0):
                speeds = distances / time_diffs
                avg_speed = np.mean(speeds)
        
        metrics = {
            'total_distance': total_distance,
            'num_points': len(self.trajectory),
            'min_coordinates': min_coords,
            'max_coordinates': max_coords,
            'bounding_box_size': max_coords - min_coords,
            'average_speed': avg_speed
        }
        
        return metrics
    
    def visualize_trajectory(self, save_path: Optional[str] = None):
        """軌跡を3Dプロットで可視化"""
        if self.trajectory is None:
            raise ValueError("軌跡データが設定されていません")
        
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        # 元の軌跡
        ax.plot(self.trajectory[:, 0], self.trajectory[:, 1], self.trajectory[:, 2], 
                'b-', alpha=0.7, linewidth=2, label='Original Trajectory')
        
        # スムージングされた軌跡があれば表示
        if self.smoothed_trajectory is not None:
            ax.plot(self.smoothed_trajectory[:, 0], 
                   self.smoothed_trajectory[:, 1], 
                   self.smoothed_trajectory[:, 2], 
                   'r-', alpha=0.7, linewidth=2, label='Smoothed Trajectory')
        
        # 開始点と終了点をマーク
        ax.scatter(self.trajectory[0, 0], self.trajectory[0, 1], self.trajectory[0, 2], 
                  c='green', s=100, marker='o', label='Start')
        ax.scatter(self.trajectory[-1, 0], self.trajectory[-1, 1], self.trajectory[-1, 2], 
                  c='red', s=100, marker='s', label='End')
        
        ax.set_xlabel('X [m]')
        ax.set_ylabel('Y [m]')
        ax.set_zlabel('Z [m]')
        ax.set_title('3D Trajectory Visualization')
        ax.legend()
        
        # 軸のスケールを等しくする
        max_range = np.array([self.trajectory[:, 0].max() - self.trajectory[:, 0].min(),
                             self.trajectory[:, 1].max() - self.trajectory[:, 1].min(),
                             self.trajectory[:, 2].max() - self.trajectory[:, 2].min()]).max() / 2.0
        
        mid_x = (self.trajectory[:, 0].max() + self.trajectory[:, 0].min()) * 0.5
        mid_y = (self.trajectory[:, 1].max() + self.trajectory[:, 1].min()) * 0.5
        mid_z = (self.trajectory[:, 2].max() + self.trajectory[:, 2].min()) * 0.5
        
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"軌跡プロットを保存しました: {save_path}")
        
        plt.show()


def synchronize_trajectory_with_dose_rates(trajectory: np.ndarray,
                                         trajectory_timestamps: np.ndarray,
                                         dose_rates: np.ndarray,
                                         dose_timestamps: np.ndarray,
                                         interpolation_method: str = 'linear') -> Tuple[np.ndarray, np.ndarray]:
    """
    軌跡データと線量率データをタイムスタンプベースで同期・補間
    
    Args:
        trajectory: 軌跡データ
        trajectory_timestamps: 軌跡のタイムスタンプ
        dose_rates: 線量率データ
        dose_timestamps: 線量率のタイムスタンプ
        interpolation_method: 補間方法
    
    Returns:
        同期された軌跡と線量率のタプル
    """
    # 共通のタイムスタンプ範囲を決定
    start_time = max(trajectory_timestamps[0], dose_timestamps[0])
    end_time = min(trajectory_timestamps[-1], dose_timestamps[-1])
    
    # 共通範囲内の軌跡データを抽出
    traj_mask = (trajectory_timestamps >= start_time) & (trajectory_timestamps <= end_time)
    common_traj_times = trajectory_timestamps[traj_mask]
    common_trajectory = trajectory[traj_mask]
    
    # 線量率データを軌跡のタイムスタンプに補間
    f_dose = interpolate.interp1d(dose_timestamps, dose_rates, 
                                 kind=interpolation_method, 
                                 bounds_error=False, 
                                 fill_value='extrapolate')
    
    interpolated_dose_rates = f_dose(common_traj_times)
    
    return common_trajectory, interpolated_dose_rates