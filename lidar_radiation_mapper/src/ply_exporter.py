"""
PLYファイル出力モジュール
生成した軌跡メッシュと元の点群データを統合してPLYファイルとして出力
"""
import numpy as np
import trimesh
from plyfile import PlyData, PlyElement
from typing import Optional, Dict


class PLYExporter:
    """PLYファイルエクスポータークラス"""
    
    def __init__(self):
        """初期化"""
        pass
    
    def combine_meshes(self, point_cloud: Optional[Dict], 
                      trajectory_mesh: trimesh.Trimesh,
                      markers: Optional[list] = None) -> trimesh.Trimesh:
        """
        点群データと軌跡メッシュを結合
        
        Args:
            point_cloud: 元の点群データ
            trajectory_mesh: 軌跡のメッシュ
            markers: マーカーのメッシュリスト（オプション）
            
        Returns:
            結合されたメッシュ
        """
        meshes_to_combine = []
        
        # 軌跡メッシュを追加
        if trajectory_mesh is not None:
            meshes_to_combine.append(trajectory_mesh)
        
        # マーカーを追加
        if markers:
            meshes_to_combine.extend(markers)
        
        # 点群データをメッシュとして追加
        if point_cloud is not None and 'points' in point_cloud:
            points = point_cloud['points']
            colors = point_cloud.get('colors', None)
            
            # 点群を頂点のみのメッシュとして作成
            point_mesh = trimesh.Trimesh(vertices=points, faces=[])
            
            if colors is not None:
                # 色情報を追加
                point_mesh.visual.vertex_colors = np.column_stack([
                    colors, 
                    np.full(len(colors), 255, dtype=np.uint8)
                ])
            
            meshes_to_combine.append(point_mesh)
        
        # すべてのメッシュを結合
        if meshes_to_combine:
            combined = trimesh.util.concatenate(meshes_to_combine)
            return combined
        else:
            return None
    
    def export_to_ply(self, mesh: trimesh.Trimesh, output_path: str, 
                     binary: bool = True) -> bool:
        """
        メッシュをPLYファイルとして出力
        
        Args:
            mesh: 出力するメッシュ
            output_path: 出力ファイルパス
            binary: バイナリ形式で出力するか
            
        Returns:
            成功した場合True
        """
        try:
            # Trimeshの標準的なPLYエクスポート
            mesh.export(output_path, file_type='ply', encoding='binary' if binary else 'ascii')
            return True
            
        except Exception as e:
            print(f"PLYエクスポートエラー: {e}")
            return False
    
    def export_with_custom_properties(self, mesh: trimesh.Trimesh, 
                                     synchronized_data: list,
                                     output_path: str) -> bool:
        """
        カスタムプロパティ付きでPLYファイルを出力
        （線量率などの追加情報を含む）
        
        Args:
            mesh: メッシュデータ
            synchronized_data: 同期されたデータ
            output_path: 出力パス
            
        Returns:
            成功した場合True
        """
        try:
            vertices = mesh.vertices
            faces = mesh.faces if len(mesh.faces) > 0 else None
            colors = mesh.visual.vertex_colors if hasattr(mesh.visual, 'vertex_colors') else None
            
            # 頂点データを準備
            vertex_dtype = [
                ('x', 'f4'), ('y', 'f4'), ('z', 'f4')
            ]
            
            vertex_data = np.zeros(len(vertices), dtype=vertex_dtype)
            vertex_data['x'] = vertices[:, 0]
            vertex_data['y'] = vertices[:, 1]
            vertex_data['z'] = vertices[:, 2]
            
            # 色情報があれば追加
            if colors is not None and len(colors) > 0:
                vertex_dtype.extend([
                    ('red', 'u1'), ('green', 'u1'), ('blue', 'u1')
                ])
                vertex_data = np.zeros(len(vertices), dtype=vertex_dtype)
                vertex_data['x'] = vertices[:, 0]
                vertex_data['y'] = vertices[:, 1]
                vertex_data['z'] = vertices[:, 2]
                vertex_data['red'] = colors[:, 0]
                vertex_data['green'] = colors[:, 1]
                vertex_data['blue'] = colors[:, 2]
            
            # PLY要素を作成
            vertex_element = PlyElement.describe(vertex_data, 'vertex')
            
            elements = [vertex_element]
            
            # 面データがあれば追加
            if faces is not None and len(faces) > 0:
                face_dtype = [('vertex_indices', 'i4', (3,))]
                face_data = np.zeros(len(faces), dtype=face_dtype)
                face_data['vertex_indices'] = faces
                
                face_element = PlyElement.describe(face_data, 'face', 
                                                  val_types={'vertex_indices': 'u1'},
                                                  len_types={'vertex_indices': 'i4'})
                elements.append(face_element)
            
            # PLYデータを作成して保存
            ply_data = PlyData(elements)
            ply_data.write(output_path)
            
            return True
            
        except Exception as e:
            print(f"カスタムPLYエクスポートエラー: {e}")
            return False
    
    def export_trajectory_only(self, trajectory_mesh: trimesh.Trimesh,
                              output_path: str) -> bool:
        """
        軌跡メッシュのみをPLYファイルとして出力
        
        Args:
            trajectory_mesh: 軌跡メッシュ
            output_path: 出力パス
            
        Returns:
            成功した場合True
        """
        return self.export_to_ply(trajectory_mesh, output_path)