#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iPhoneファイルアプリからzipファイルを選択し、JSONファイルを読み取るスクリプト
Pythonista3用
"""

import zipfile
import json
import os
import tempfile
from pathlib import Path
import console

def select_zip_file():
    """
    iPhoneのファイルアプリからzipファイルを選択する
    """
    try:
        # Pythonista3のファイル選択機能を使用
        import ui
        
        # ファイル選択ダイアログを表示
        file_path = console.input_alert(
            'Zipファイル選択',
            'ファイルアプリからzipファイルのパスを入力してください:',
            'ファイルを選択'
        )
        
        if not file_path:
            return None
            
        # ファイルが存在するかチェック
        if not os.path.exists(file_path):
            console.alert('エラー', f'ファイルが見つかりません: {file_path}')
            return None
            
        return file_path
        
    except Exception as e:
        console.alert('エラー', f'ファイル選択中にエラーが発生しました: {str(e)}')
        return None

def extract_and_read_json(zip_path):
    """
    zipファイルを解凍してJSONファイルを読み取る
    """
    try:
        json_files = []
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # zipファイル内のファイル一覧を取得
            file_list = zip_ref.namelist()
            console.alert('情報', f'zipファイル内に{len(file_list)}個のファイルが見つかりました')
            
            # JSONファイルのみをフィルタリング
            json_file_names = [f for f in file_list if f.lower().endswith('.json')]
            
            if not json_file_names:
                console.alert('警告', 'zipファイル内にJSONファイルが見つかりません')
                return []
            
            console.alert('情報', f'{len(json_file_names)}個のJSONファイルが見つかりました')
            
            # 各JSONファイルを読み取り
            for json_file_name in json_file_names:
                try:
                    # zipファイルからJSONファイルを読み取り
                    with zip_ref.open(json_file_name) as json_file:
                        json_content = json_file.read().decode('utf-8')
                        json_data = json.loads(json_content)
                        
                        json_files.append({
                            'filename': json_file_name,
                            'data': json_data,
                            'size': len(json_content)
                        })
                        
                        print(f"✓ {json_file_name} を読み取りました ({len(json_content)} bytes)")
                        
                except json.JSONDecodeError as e:
                    print(f"✗ {json_file_name} のJSON解析に失敗: {str(e)}")
                except Exception as e:
                    print(f"✗ {json_file_name} の読み取りに失敗: {str(e)}")
        
        return json_files
        
    except zipfile.BadZipFile:
        console.alert('エラー', '無効なzipファイルです')
        return []
    except Exception as e:
        console.alert('エラー', f'zipファイルの処理中にエラーが発生しました: {str(e)}')
        return []

def display_json_summary(json_files):
    """
    JSONファイルの概要を表示
    """
    if not json_files:
        console.alert('情報', '表示するJSONファイルがありません')
        return
    
    summary = f"読み取り完了: {len(json_files)}個のJSONファイル\n\n"
    
    for i, json_file in enumerate(json_files, 1):
        filename = json_file['filename']
        size = json_file['size']
        data = json_file['data']
        
        # データの型を判定
        if isinstance(data, dict):
            data_type = f"辞書 (キー数: {len(data)})"
        elif isinstance(data, list):
            data_type = f"リスト (要素数: {len(data)})"
        else:
            data_type = type(data).__name__
        
        summary += f"{i}. {filename}\n"
        summary += f"   サイズ: {size} bytes\n"
        summary += f"   データ型: {data_type}\n\n"
    
    console.alert('JSONファイル概要', summary)

def main():
    """
    メイン処理
    """
    console.clear()
    print("=== Zip JSON Reader ===")
    print("iPhoneファイルアプリからzipファイルを選択し、JSONファイルを読み取ります\n")
    
    # 1. zipファイルを選択
    zip_path = select_zip_file()
    if not zip_path:
        print("ファイル選択がキャンセルされました")
        return
    
    print(f"選択されたファイル: {zip_path}")
    
    # 2. zipファイルを解凍してJSONファイルを読み取り
    print("\nzipファイルを処理中...")
    json_files = extract_and_read_json(zip_path)
    
    if not json_files:
        print("JSONファイルの読み取りに失敗しました")
        return
    
    # 3. 結果を表示
    print(f"\n✓ {len(json_files)}個のJSONファイルを正常に読み取りました")
    display_json_summary(json_files)
    
    # 4. 詳細表示のオプション
    if console.alert('詳細表示', 'JSONファイルの詳細内容を表示しますか？', 'はい', 'いいえ') == 'はい':
        for json_file in json_files:
            filename = json_file['filename']
            data = json_file['data']
            
            print(f"\n=== {filename} ===")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print("\n" + "="*50)

if __name__ == '__main__':
    main()