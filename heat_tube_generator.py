"""
ヒートチューブ生成モジュール
軌跡に沿った直径10cmのチューブ状ヒートマップを生成する
"""

import numpy as np
import open3d as o3d
from typing import Tuple, List, Optional
from scipy.spatial.transform import Rotation
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap


class HeatTubeGenerator:
    """軌跡に沿ったヒートチューブを生成するクラス"""
    
    def __init__(self, tube_radius: float = 0.05):  # 5cm radius = 10cm diameter
        self.tube_radius = tube_radius
        self.tube_mesh = None
        self.vertices = None
        self.faces = None
        self.colors = None
    
    def create_tube_mesh(self, 
                        trajectory: np.ndarray, 
                        dose_rates: np.ndarray,
                        radial_segments: int = 16,
                        dose_range: Tuple[float, float] = (0.0, 10.0)) -> o3d.geometry.TriangleMesh:
        """
        軌跡に沿ったチューブメッシュを生成
        
        Args:
            trajectory: 軌跡データ (N, 3)
            dose_rates: 各点の線量率 (N,)
            radial_segments: チューブの円周方向分割数
            dose_range: 線量率の範囲 (min, max)
        
        Returns:
            チューブのTriangleMesh
        """
        if len(trajectory) != len(dose_rates):
            raise ValueError("軌跡データと線量率データの長さが一致しません")
        
        vertices = []
        faces = []
        vertex_colors = []
        
        # 各軌跡点でチューブの断面を生成
        for i, (point, dose_rate) in enumerate(zip(trajectory, dose_rates)):
            # 軌跡の方向ベクトルを計算
            if i == 0:
                direction = trajectory[i + 1] - trajectory[i]
            elif i == len(trajectory) - 1:
                direction = trajectory[i] - trajectory[i - 1]
            else:
                direction = trajectory[i + 1] - trajectory[i - 1]
            
            direction = direction / np.linalg.norm(direction)
            
            # チューブの断面を生成
            circle_vertices, color = self._create_circle_vertices(
                point, direction, self.tube_radius, radial_segments, dose_rate, dose_range)
            
            vertices.extend(circle_vertices)
            vertex_colors.extend([color] * len(circle_vertices))
            
            # 面を生成（隣接する断面間）
            if i > 0:
                faces.extend(self._create_tube_faces(i - 1, i, radial_segments))
        
        # Open3Dメッシュを作成
        mesh = o3d.geometry.TriangleMesh()
        mesh.vertices = o3d.utility.Vector3dVector(np.array(vertices))
        mesh.triangles = o3d.utility.Vector3iVector(np.array(faces))
        mesh.vertex_colors = o3d.utility.Vector3dVector(np.array(vertex_colors))
        
        # 法線を計算
        mesh.compute_vertex_normals()
        
        self.tube_mesh = mesh
        self.vertices = np.array(vertices)
        self.faces = np.array(faces)
        self.colors = np.array(vertex_colors)
        
        return mesh
    
    def _create_circle_vertices(self, 
                              center: np.ndarray, 
                              direction: np.ndarray, 
                              radius: float, 
                              segments: int,
                              dose_rate: float,
                              dose_range: Tuple[float, float]) -> Tuple[List[np.ndarray], np.ndarray]:
        """
        指定した中心と方向でチューブの断面円を生成
        
        Args:
            center: 円の中心
            direction: チューブの方向ベクトル
            radius: 円の半径
            segments: 円周分割数
            dose_rate: この断面の線量率
            dose_range: 線量率の範囲
        
        Returns:
            円周上の頂点リストと色のタプル
        """
        # 方向ベクトルに垂直な2つのベクトルを生成
        if abs(direction[2]) < 0.9:
            perpendicular1 = np.cross(direction, np.array([0, 0, 1]))
        else:
            perpendicular1 = np.cross(direction, np.array([1, 0, 0]))
        
        perpendicular1 = perpendicular1 / np.linalg.norm(perpendicular1)
        perpendicular2 = np.cross(direction, perpendicular1)
        perpendicular2 = perpendicular2 / np.linalg.norm(perpendicular2)
        
        # 円周上の点を生成
        vertices = []
        angles = np.linspace(0, 2 * np.pi, segments, endpoint=False)
        
        for angle in angles:
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            vertex = center + x * perpendicular1 + y * perpendicular2
            vertices.append(vertex)
        
        # 線量率に基づく色を計算
        color = self._dose_rate_to_color(dose_rate, dose_range)
        
        return vertices, color
    
    def _create_tube_faces(self, 
                          section1_idx: int, 
                          section2_idx: int, 
                          radial_segments: int) -> List[List[int]]:
        """
        隣接する2つの断面間の面を生成
        
        Args:
            section1_idx: 最初の断面のインデックス
            section2_idx: 次の断面のインデックス
            radial_segments: 円周分割数
        
        Returns:
            面のリスト
        """
        faces = []
        
        for i in range(radial_segments):
            # 現在の断面の頂点インデックス
            curr1 = section1_idx * radial_segments + i
            curr2 = section1_idx * radial_segments + ((i + 1) % radial_segments)
            
            # 次の断面の頂点インデックス
            next1 = section2_idx * radial_segments + i
            next2 = section2_idx * radial_segments + ((i + 1) % radial_segments)
            
            # 2つの三角形で四角形を構成
            faces.append([curr1, next1, curr2])
            faces.append([curr2, next1, next2])
        
        return faces
    
    def _dose_rate_to_color(self, 
                           dose_rate: float, 
                           dose_range: Tuple[float, float]) -> np.ndarray:
        """
        線量率を色（青→赤のグラデーション）に変換
        
        Args:
            dose_rate: 線量率
            dose_range: 線量率の範囲 (min, max)
        
        Returns:
            RGB色配列
        """
        min_dose, max_dose = dose_range
        
        # 線量率を0-1の範囲に正規化
        if max_dose > min_dose:
            normalized = (dose_rate - min_dose) / (max_dose - min_dose)
        else:
            normalized = 0.0
        
        # 0-1の範囲にクリップ
        normalized = np.clip(normalized, 0.0, 1.0)
        
        # 青→緑→赤のグラデーション
        if normalized < 0.5:
            # 青→緑
            t = normalized * 2
            color = np.array([0, t, 1 - t])
        else:
            # 緑→赤
            t = (normalized - 0.5) * 2
            color = np.array([t, 1 - t, 0])
        
        return color
    
    def create_color_scale_bar(self, 
                              dose_range: Tuple[float, float],
                              save_path: Optional[str] = None) -> plt.Figure:
        """
        カラースケールバーを作成
        
        Args:
            dose_range: 線量率の範囲
            save_path: 保存パス（オプション）
        
        Returns:
            Matplotlibのfigure
        """
        fig, ax = plt.subplots(figsize=(8, 2))
        
        # カラーマップを作成
        colors = ['blue', 'green', 'red']
        n_bins = 256
        cmap = LinearSegmentedColormap.from_list('dose_rate', colors, N=n_bins)
        
        # カラーバーを描画
        gradient = np.linspace(0, 1, 256).reshape(1, -1)
        ax.imshow(gradient, aspect='auto', cmap=cmap)
        
        # 軸の設定
        ax.set_xlim(0, 255)
        ax.set_yticks([])
        
        # ラベルの設定
        min_dose, max_dose = dose_range
        tick_positions = [0, 64, 128, 192, 255]
        tick_labels = [f'{min_dose + (max_dose - min_dose) * pos / 255:.1f}' 
                      for pos in tick_positions]
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels)
        ax.set_xlabel('Dose Rate [μSv/h]')
        ax.set_title('Radiation Dose Rate Color Scale')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"カラースケールバーを保存しました: {save_path}")
        
        return fig
    
    def export_to_ply(self, filename: str):
        """
        チューブメッシュをPLYファイルとして出力
        
        Args:
            filename: 出力ファイル名
        """
        if self.tube_mesh is None:
            raise ValueError("チューブメッシュが生成されていません")
        
        # PLYファイルとして保存
        success = o3d.io.write_triangle_mesh(filename, self.tube_mesh)
        
        if success:
            print(f"チューブメッシュをPLYファイルとして保存しました: {filename}")
        else:
            print(f"PLYファイルの保存に失敗しました: {filename}")
        
        return success
    
    def visualize_tube(self, show_wireframe: bool = False):
        """
        チューブメッシュを可視化
        
        Args:
            show_wireframe: ワイヤーフレーム表示するかどうか
        """
        if self.tube_mesh is None:
            raise ValueError("チューブメッシュが生成されていません")
        
        vis = o3d.visualization.Visualizer()
        vis.create_window(window_name="Heat Tube Visualization", width=1024, height=768)
        
        if show_wireframe:
            # ワイヤーフレーム表示
            wireframe = o3d.geometry.LineSet.create_from_triangle_mesh(self.tube_mesh)
            vis.add_geometry(wireframe)
        else:
            # ソリッド表示
            vis.add_geometry(self.tube_mesh)
        
        # 座標軸を追加
        coordinate_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.1)
        vis.add_geometry(coordinate_frame)
        
        vis.run()
        vis.destroy_window()


def combine_with_point_cloud(tube_mesh: o3d.geometry.TriangleMesh,
                           point_cloud: np.ndarray,
                           point_colors: Optional[np.ndarray] = None) -> o3d.geometry.TriangleMesh:
    """
    チューブメッシュと点群データを結合
    
    Args:
        tube_mesh: チューブメッシュ
        point_cloud: 点群データ
        point_colors: 点群の色（オプション）
    
    Returns:
        結合されたメッシュ
    """
    # 点群をOpen3D形式に変換
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(point_cloud)
    
    if point_colors is not None:
        pcd.colors = o3d.utility.Vector3dVector(point_colors)
    else:
        # デフォルトの色（グレー）を設定
        pcd.colors = o3d.utility.Vector3dVector(
            np.full((len(point_cloud), 3), [0.7, 0.7, 0.7]))
    
    # 点群からメッシュを生成（球として表現）
    sphere_radius = 0.005  # 5mm
    point_spheres = []
    
    for i, point in enumerate(point_cloud):
        sphere = o3d.geometry.TriangleMesh.create_sphere(radius=sphere_radius)
        sphere.translate(point)
        
        if point_colors is not None:
            sphere.paint_uniform_color(point_colors[i])
        else:
            sphere.paint_uniform_color([0.7, 0.7, 0.7])
        
        point_spheres.append(sphere)
    
    # すべてのメッシュを結合
    combined_mesh = tube_mesh
    for sphere in point_spheres:
        combined_mesh += sphere
    
    return combined_mesh