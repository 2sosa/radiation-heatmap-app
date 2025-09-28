"""
軌跡の3D可視化モジュール
チューブ状の軌跡を生成し、線量率に基づいて色付けを行う
"""
import numpy as np
import trimesh
from typing import List, Dict, Tuple
import matplotlib.pyplot as plt
import matplotlib.cm as cm


class TrajectoryVisualizer:
    """軌跡を3Dチューブとして可視化するクラス"""
    
    def __init__(self, tube_radius: float = 0.05, dose_rate_range: Tuple[float, float] = (0, 10)):
        """
        Args:
            tube_radius: チューブの半径（メートル単位、デフォルト5cm）
            dose_rate_range: 線量率の範囲 (min, max) μSv/h
        """
        self.tube_radius = tube_radius
        self.dose_rate_min, self.dose_rate_max = dose_rate_range
        self.colormap = cm.get_cmap('jet')  # 青から赤へのカラーマップ
        
    def dose_rate_to_color(self, dose_rate: float) -> Tuple[float, float, float]:
        """
        線量率をRGB色に変換
        
        Args:
            dose_rate: 線量率 (μSv/h)
            
        Returns:
            RGB色 (0-255の範囲)
        """
        # 線量率を0-1の範囲に正規化
        normalized = np.clip(
            (dose_rate - self.dose_rate_min) / (self.dose_rate_max - self.dose_rate_min),
            0, 1
        )
        
        # カラーマップから色を取得
        rgba = self.colormap(normalized)
        rgb = (int(rgba[0] * 255), int(rgba[1] * 255), int(rgba[2] * 255))
        
        return rgb
    
    def create_tube_segment(self, start_point: np.ndarray, end_point: np.ndarray, 
                           start_color: Tuple, end_color: Tuple, 
                           num_segments: int = 8) -> trimesh.Trimesh:
        """
        2点間にチューブセグメントを作成
        
        Args:
            start_point: 始点の3D座標
            end_point: 終点の3D座標
            start_color: 始点の色
            end_color: 終点の色
            num_segments: 円周方向の分割数
            
        Returns:
            チューブセグメントのメッシュ
        """
        # 方向ベクトルを計算
        direction = end_point - start_point
        length = np.linalg.norm(direction)
        
        if length < 1e-6:
            return None
        
        direction = direction / length
        
        # 垂直なベクトルを生成
        if abs(direction[2]) < 0.9:
            up = np.array([0, 0, 1])
        else:
            up = np.array([1, 0, 0])
        
        right = np.cross(direction, up)
        right = right / np.linalg.norm(right)
        up = np.cross(right, direction)
        
        # 円周上の点を生成
        vertices = []
        faces = []
        vertex_colors = []
        
        for i in range(2):  # 始点と終点
            center = start_point if i == 0 else end_point
            color = start_color if i == 0 else end_color
            
            for j in range(num_segments):
                angle = 2 * np.pi * j / num_segments
                offset = self.tube_radius * (np.cos(angle) * right + np.sin(angle) * up)
                vertices.append(center + offset)
                vertex_colors.append(color)
        
        vertices = np.array(vertices)
        vertex_colors = np.array(vertex_colors)
        
        # 面を生成
        for j in range(num_segments):
            j_next = (j + 1) % num_segments
            
            # 三角形1
            faces.append([j, j_next, j + num_segments])
            # 三角形2
            faces.append([j_next, j_next + num_segments, j + num_segments])
        
        faces = np.array(faces)
        
        # メッシュを作成
        mesh = trimesh.Trimesh(
            vertices=vertices,
            faces=faces,
            vertex_colors=vertex_colors
        )
        
        return mesh
    
    def create_trajectory_mesh(self, synchronized_data: List[Dict]) -> trimesh.Trimesh:
        """
        同期されたデータから軌跡メッシュを作成
        
        Args:
            synchronized_data: 位置と線量率が同期されたデータ
            
        Returns:
            軌跡全体のメッシュ
        """
        meshes = []
        
        for i in range(len(synchronized_data) - 1):
            current_point = synchronized_data[i]
            next_point = synchronized_data[i + 1]
            
            start_pos = current_point['position']
            end_pos = next_point['position']
            
            start_color = self.dose_rate_to_color(current_point['dose_rate_uSv_h'])
            end_color = self.dose_rate_to_color(next_point['dose_rate_uSv_h'])
            
            segment = self.create_tube_segment(start_pos, end_pos, start_color, end_color)
            
            if segment is not None:
                meshes.append(segment)
        
        # すべてのセグメントを結合
        if meshes:
            combined_mesh = trimesh.util.concatenate(meshes)
            return combined_mesh
        else:
            return None
    
    def add_sphere_markers(self, synchronized_data: List[Dict], interval: int = 10) -> List[trimesh.Trimesh]:
        """
        軌跡上に球体マーカーを追加（オプション）
        
        Args:
            synchronized_data: 同期されたデータ
            interval: マーカーを配置する間隔
            
        Returns:
            球体マーカーのリスト
        """
        markers = []
        
        for i in range(0, len(synchronized_data), interval):
            point = synchronized_data[i]
            position = point['position']
            color = self.dose_rate_to_color(point['dose_rate_uSv_h'])
            
            # 球体を作成
            sphere = trimesh.creation.icosphere(subdivisions=2, radius=self.tube_radius * 1.5)
            sphere.vertices += position
            
            # 色を設定
            sphere.visual.vertex_colors = np.tile(color + (255,), (len(sphere.vertices), 1))
            
            markers.append(sphere)
        
        return markers
    
    def create_color_legend(self) -> np.ndarray:
        """
        カラーレジェンドを作成
        
        Returns:
            カラーバーの画像配列
        """
        fig, ax = plt.subplots(figsize=(1, 6))
        
        # カラーバーを作成
        gradient = np.linspace(0, 1, 256).reshape(256, 1)
        ax.imshow(gradient, aspect='auto', cmap=self.colormap, origin='lower')
        
        # ラベルを設定
        ax.set_ylabel('線量率 (μSv/h)', fontsize=12)
        ax.set_xticks([])
        ax.set_yticks([0, 64, 128, 192, 255])
        ax.set_yticklabels([
            f'{self.dose_rate_min:.1f}',
            f'{self.dose_rate_min + (self.dose_rate_max - self.dose_rate_min) * 0.25:.1f}',
            f'{self.dose_rate_min + (self.dose_rate_max - self.dose_rate_min) * 0.5:.1f}',
            f'{self.dose_rate_min + (self.dose_rate_max - self.dose_rate_min) * 0.75:.1f}',
            f'{self.dose_rate_max:.1f}'
        ])
        
        plt.tight_layout()
        
        # 画像として保存
        fig.canvas.draw()
        # matplotlib 3.8以降の互換性対応
        if hasattr(fig.canvas, 'tostring_rgb'):
            image = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        else:
            # 新しいバージョンのmatplotlibではbuffer_rgbaを使用
            image = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
            # RGBAからRGBに変換
            image = image.reshape(fig.canvas.get_width_height()[::-1] + (4,))
            image = image[:, :, :3]
            return image
        image = image.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        
        plt.close()
        
        return image