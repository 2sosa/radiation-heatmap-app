"""
PLY出力モジュール
最終的な3Dモデルを統合してPLYファイルとして出力する
"""

import numpy as np
import open3d as o3d
from plyfile import PlyData, PlyElement
from typing import Optional, Dict, Any, List, Tuple
import os
from datetime import datetime


class PLYExporter:
    """PLYファイルの出力を管理するクラス"""
    
    def __init__(self):
        self.combined_mesh = None
        self.metadata = {}
    
    def combine_geometries(self,
                          heat_tube_mesh: o3d.geometry.TriangleMesh,
                          point_cloud: Optional[np.ndarray] = None,
                          point_colors: Optional[np.ndarray] = None,
                          additional_meshes: Optional[List[o3d.geometry.TriangleMesh]] = None) -> o3d.geometry.TriangleMesh:
        """
        各種ジオメトリを統合して単一のメッシュを作成
        
        Args:
            heat_tube_mesh: ヒートチューブメッシュ
            point_cloud: LiDAR点群データ（オプション）
            point_colors: 点群の色（オプション）
            additional_meshes: 追加のメッシュ（オプション）
        
        Returns:
            統合されたメッシュ
        """
        self.combined_mesh = heat_tube_mesh.copy()
        
        # 点群データを球メッシュとして追加
        if point_cloud is not None:
            point_mesh = self._convert_points_to_mesh(point_cloud, point_colors)
            if point_mesh is not None:
                self.combined_mesh += point_mesh
        
        # 追加のメッシュを統合
        if additional_meshes:
            for mesh in additional_meshes:
                self.combined_mesh += mesh
        
        # メッシュを最適化
        self.combined_mesh.remove_duplicated_vertices()
        self.combined_mesh.remove_degenerate_triangles()
        self.combined_mesh.remove_non_manifold_edges()
        
        return self.combined_mesh
    
    def _convert_points_to_mesh(self,
                               points: np.ndarray,
                               colors: Optional[np.ndarray] = None,
                               point_radius: float = 0.002) -> Optional[o3d.geometry.TriangleMesh]:
        """
        点群を小さな球メッシュに変換
        
        Args:
            points: 点群データ
            colors: 点の色
            point_radius: 各点を表現する球の半径
        
        Returns:
            点群メッシュ
        """
        if len(points) == 0:
            return None
        
        # 点数が多すぎる場合はサンプリング
        max_points = 50000  # 最大点数
        if len(points) > max_points:
            indices = np.random.choice(len(points), max_points, replace=False)
            points = points[indices]
            if colors is not None:
                colors = colors[indices]
            print(f"点群を{max_points}点にサンプリングしました")
        
        point_meshes = []
        
        for i, point in enumerate(points):
            sphere = o3d.geometry.TriangleMesh.create_sphere(radius=point_radius, resolution=8)
            sphere.translate(point)
            
            if colors is not None and i < len(colors):
                sphere.paint_uniform_color(colors[i])
            else:
                sphere.paint_uniform_color([0.8, 0.8, 0.8])  # デフォルトの灰色
            
            point_meshes.append(sphere)
        
        # すべての球メッシュを統合
        combined_point_mesh = point_meshes[0]
        for mesh in point_meshes[1:]:
            combined_point_mesh += mesh
        
        return combined_point_mesh
    
    def add_metadata(self, metadata: Dict[str, Any]):
        """メタデータを追加"""
        self.metadata.update(metadata)
    
    def export_to_ply(self,
                     filename: str,
                     include_metadata: bool = True,
                     binary: bool = True) -> bool:
        """
        統合されたメッシュをPLYファイルとして出力
        
        Args:
            filename: 出力ファイル名
            include_metadata: メタデータを含めるかどうか
            binary: バイナリ形式で出力するかどうか
        
        Returns:
            出力の成功/失敗
        """
        if self.combined_mesh is None:
            print("エラー: 出力するメッシュがありません")
            return False
        
        try:
            # Open3Dを使用してPLYファイルを出力
            success = o3d.io.write_triangle_mesh(
                filename,
                self.combined_mesh,
                write_ascii=not binary,
                write_vertex_normals=True,
                write_vertex_colors=True
            )
            
            if success:
                print(f"PLYファイルを出力しました: {filename}")
                
                # メタデータを別ファイルとして出力
                if include_metadata and self.metadata:
                    metadata_filename = filename.replace('.ply', '_metadata.txt')
                    self._write_metadata(metadata_filename)
                
                # 統計情報を出力
                self._print_mesh_statistics()
                
                return True
            else:
                print(f"PLYファイル出力に失敗しました: {filename}")
                return False
                
        except Exception as e:
            print(f"PLYファイル出力中にエラーが発生しました: {e}")
            return False
    
    def _write_metadata(self, filename: str):
        """メタデータをテキストファイルに出力"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("# 3D Radiation Heat Map Metadata\n")
                f.write(f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for key, value in self.metadata.items():
                    f.write(f"{key}: {value}\n")
            
            print(f"メタデータファイルを出力しました: {filename}")
            
        except Exception as e:
            print(f"メタデータファイル出力エラー: {e}")
    
    def _print_mesh_statistics(self):
        """メッシュの統計情報を出力"""
        if self.combined_mesh is None:
            return
        
        vertices = np.asarray(self.combined_mesh.vertices)
        triangles = np.asarray(self.combined_mesh.triangles)
        
        print("\n=== メッシュ統計情報 ===")
        print(f"頂点数: {len(vertices):,}")
        print(f"面数: {len(triangles):,}")
        
        # バウンディングボックス
        min_coords = np.min(vertices, axis=0)
        max_coords = np.max(vertices, axis=0)
        bbox_size = max_coords - min_coords
        
        print(f"バウンディングボックス:")
        print(f"  X: {min_coords[0]:.3f} ~ {max_coords[0]:.3f} (幅: {bbox_size[0]:.3f}m)")
        print(f"  Y: {min_coords[1]:.3f} ~ {max_coords[1]:.3f} (幅: {bbox_size[1]:.3f}m)")
        print(f"  Z: {min_coords[2]:.3f} ~ {max_coords[2]:.3f} (幅: {bbox_size[2]:.3f}m)")
        
        # ファイルサイズの推定
        estimated_size_mb = (len(vertices) * 12 + len(triangles) * 12) / (1024 * 1024)
        print(f"推定ファイルサイズ: {estimated_size_mb:.1f} MB")
    
    def create_preview_image(self,
                           output_path: str,
                           image_size: Tuple[int, int] = (1920, 1080),
                           background_color: Tuple[float, float, float] = (0.1, 0.1, 0.1)):
        """
        3Dモデルのプレビュー画像を生成
        
        Args:
            output_path: 画像の出力パス
            image_size: 画像サイズ (width, height)
            background_color: 背景色 (R, G, B)
        """
        if self.combined_mesh is None:
            print("エラー: プレビュー生成用のメッシュがありません")
            return
        
        try:
            # Open3Dの可視化設定
            vis = o3d.visualization.Visualizer()
            vis.create_window(width=image_size[0], height=image_size[1], visible=False)
            
            # メッシュを追加
            vis.add_geometry(self.combined_mesh)
            
            # 座標軸を追加
            coordinate_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.1)
            vis.add_geometry(coordinate_frame)
            
            # レンダリングオプションを設定
            render_option = vis.get_render_option()
            render_option.background_color = np.array(background_color)
            render_option.mesh_show_back_face = True
            
            # カメラ位置を調整
            ctr = vis.get_view_control()
            ctr.set_zoom(0.8)
            
            # 画像を保存
            vis.capture_screen_image(output_path)
            vis.destroy_window()
            
            print(f"プレビュー画像を生成しました: {output_path}")
            
        except Exception as e:
            print(f"プレビュー画像生成エラー: {e}")
    
    def export_separate_components(self,
                                  base_filename: str,
                                  heat_tube_mesh: o3d.geometry.TriangleMesh,
                                  point_cloud_mesh: Optional[o3d.geometry.TriangleMesh] = None):
        """
        コンポーネントを個別のPLYファイルとして出力
        
        Args:
            base_filename: ベースファイル名（拡張子なし）
            heat_tube_mesh: ヒートチューブメッシュ
            point_cloud_mesh: 点群メッシュ（オプション）
        """
        # ヒートチューブを個別出力
        tube_filename = f"{base_filename}_heat_tube.ply"
        success = o3d.io.write_triangle_mesh(tube_filename, heat_tube_mesh)
        if success:
            print(f"ヒートチューブを出力しました: {tube_filename}")
        
        # 点群を個別出力
        if point_cloud_mesh is not None:
            cloud_filename = f"{base_filename}_point_cloud.ply"
            success = o3d.io.write_triangle_mesh(cloud_filename, point_cloud_mesh)
            if success:
                print(f"点群を出力しました: {cloud_filename}")
    
    def validate_output(self, filename: str) -> bool:
        """
        出力されたPLYファイルの妥当性を検証
        
        Args:
            filename: 検証するPLYファイル名
        
        Returns:
            ファイルが妥当かどうか
        """
        try:
            if not os.path.exists(filename):
                print(f"ファイルが存在しません: {filename}")
                return False
            
            # ファイルサイズをチェック
            file_size = os.path.getsize(filename)
            if file_size == 0:
                print(f"ファイルサイズが0です: {filename}")
                return False
            
            # Open3Dでファイルを読み込んで検証
            mesh = o3d.io.read_triangle_mesh(filename)
            vertices = np.asarray(mesh.vertices)
            triangles = np.asarray(mesh.triangles)
            
            if len(vertices) == 0:
                print(f"頂点データがありません: {filename}")
                return False
            
            if len(triangles) == 0:
                print(f"面データがありません: {filename}")
                return False
            
            print(f"PLYファイル検証成功: {filename}")
            print(f"  ファイルサイズ: {file_size / (1024*1024):.1f} MB")
            print(f"  頂点数: {len(vertices):,}")
            print(f"  面数: {len(triangles):,}")
            
            return True
            
        except Exception as e:
            print(f"PLYファイル検証エラー: {e}")
            return False