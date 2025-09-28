#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pythonista3 JSON ZIP Processor
iPhoneのファイルアプリから手動でZIPファイルを選択し、
中のJSONファイルを読み取るためのスクリプト
"""

import sys
import os
import json
import zipfile
import tempfile
import shutil
from pathlib import Path

# Pythonista3特有のモジュール
try:
    import console
    import dialogs
    PYTHONISTA = True
except ImportError:
    # デバッグ用（通常のPython環境）
    PYTHONISTA = False
    print("Warning: Running outside Pythonista3 environment")


class JSONZipProcessor:
    """ZIPファイル内のJSONファイルを処理するクラス"""
    
    def __init__(self):
        self.temp_dir = None
        self.json_data = {}
        self.file_count = 0
        
    def select_zip_file(self):
        """
        iPhoneのファイルアプリからZIPファイルを選択
        
        Returns:
            str: 選択されたファイルのパス（キャンセルの場合はNone）
        """
        if PYTHONISTA:
            try:
                console.alert(
                    'ファイル選択',
                    'ファイルアプリからZIPファイルを選択してください',
                    'OK',
                    hide_cancel_button=True
                )
                
                # Pythonista3のファイル選択ダイアログ
                file_path = dialogs.pick_document(types=['public.zip-archive'])
                
                if file_path:
                    console.hud_alert(f'選択: {os.path.basename(file_path)}', 'success', 1.5)
                    return file_path
                else:
                    console.hud_alert('キャンセルされました', 'error', 1.5)
                    return None
                    
            except Exception as e:
                console.alert('エラー', f'ファイル選択中にエラーが発生しました:\n{str(e)}', 'OK')
                return None
        else:
            # デバッグ用（通常のPython環境）
            file_path = input("ZIPファイルのパスを入力してください: ")
            if os.path.exists(file_path) and file_path.endswith('.zip'):
                return file_path
            else:
                print("有効なZIPファイルが見つかりません")
                return None
    
    def extract_zip(self, zip_path):
        """
        ZIPファイルを一時ディレクトリに展開
        
        Args:
            zip_path (str): ZIPファイルのパス
            
        Returns:
            bool: 成功した場合True
        """
        try:
            # 一時ディレクトリを作成
            self.temp_dir = tempfile.mkdtemp(prefix='json_zip_')
            
            if PYTHONISTA:
                console.show_activity('ZIPファイルを展開中...')
            
            # ZIPファイルを展開
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            
            if PYTHONISTA:
                console.hide_activity()
                console.hud_alert('展開完了', 'success', 1.0)
            else:
                print(f"ZIPファイルを展開しました: {self.temp_dir}")
            
            return True
            
        except zipfile.BadZipFile:
            error_msg = "無効なZIPファイルです"
            if PYTHONISTA:
                console.hide_activity()
                console.alert('エラー', error_msg, 'OK')
            else:
                print(f"Error: {error_msg}")
            return False
            
        except Exception as e:
            error_msg = f"展開中にエラーが発生しました: {str(e)}"
            if PYTHONISTA:
                console.hide_activity()
                console.alert('エラー', error_msg, 'OK')
            else:
                print(f"Error: {error_msg}")
            return False
    
    def process_json_files(self):
        """
        展開されたディレクトリからJSONファイルを読み取り処理
        
        Returns:
            dict: 読み取ったJSONデータ（ファイル名をキーとする辞書）
        """
        if not self.temp_dir:
            return {}
        
        json_files = []
        
        # JSONファイルを再帰的に検索
        for root, dirs, files in os.walk(self.temp_dir):
            for file in files:
                if file.lower().endswith('.json'):
                    json_files.append(os.path.join(root, file))
        
        if not json_files:
            if PYTHONISTA:
                console.alert('警告', 'ZIPファイル内にJSONファイルが見つかりません', 'OK')
            else:
                print("Warning: No JSON files found in ZIP")
            return {}
        
        if PYTHONISTA:
            console.show_activity(f'{len(json_files)}個のJSONファイルを処理中...')
        else:
            print(f"Processing {len(json_files)} JSON files...")
        
        # 各JSONファイルを読み取り
        for json_path in json_files:
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    # ファイル名（相対パス）を取得
                    relative_path = os.path.relpath(json_path, self.temp_dir)
                    
                    # JSONデータを読み取り
                    data = json.load(f)
                    self.json_data[relative_path] = data
                    self.file_count += 1
                    
            except json.JSONDecodeError as e:
                error_msg = f"JSONパースエラー ({os.path.basename(json_path)}): {str(e)}"
                if PYTHONISTA:
                    console.hud_alert(error_msg, 'error', 2.0)
                else:
                    print(f"Error: {error_msg}")
                continue
                
            except Exception as e:
                error_msg = f"ファイル読み取りエラー ({os.path.basename(json_path)}): {str(e)}"
                if PYTHONISTA:
                    console.hud_alert(error_msg, 'error', 2.0)
                else:
                    print(f"Error: {error_msg}")
                continue
        
        if PYTHONISTA:
            console.hide_activity()
            console.hud_alert(f'{self.file_count}個のJSONファイルを読み取りました', 'success', 2.0)
        else:
            print(f"Successfully processed {self.file_count} JSON files")
        
        return self.json_data
    
    def display_summary(self):
        """処理結果のサマリーを表示"""
        if not self.json_data:
            if PYTHONISTA:
                console.alert('結果', '処理されたJSONデータがありません', 'OK')
            else:
                print("No JSON data processed")
            return
        
        summary = []
        summary.append(f"📊 処理結果サマリー")
        summary.append(f"{'='*40}")
        summary.append(f"✅ 読み取り成功: {self.file_count}個のファイル")
        summary.append(f"\n📁 ファイル一覧:")
        
        for i, (filename, data) in enumerate(self.json_data.items(), 1):
            # データの概要を取得
            if isinstance(data, dict):
                data_info = f"オブジェクト (キー数: {len(data)})"
            elif isinstance(data, list):
                data_info = f"配列 (要素数: {len(data)})"
            else:
                data_info = f"その他 (型: {type(data).__name__})"
            
            summary.append(f"  {i}. {filename}")
            summary.append(f"     → {data_info}")
        
        summary_text = '\n'.join(summary)
        
        if PYTHONISTA:
            console.clear()
            print(summary_text)
            
            # 詳細表示のオプション
            if dialogs.alert('詳細表示', 'JSONデータの詳細を表示しますか？', 'はい', 'いいえ') == 1:
                self.display_detailed_data()
        else:
            print(summary_text)
    
    def display_detailed_data(self):
        """JSONデータの詳細を表示"""
        if PYTHONISTA:
            # ファイル選択
            files = list(self.json_data.keys())
            selected = dialogs.list_dialog('ファイル選択', files)
            
            if selected:
                data = self.json_data[selected]
                formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
                
                console.clear()
                print(f"📄 {selected}")
                print("="*40)
                print(formatted_json)
                
                # データをクリップボードにコピーするオプション
                if dialogs.alert('クリップボード', 'JSONデータをクリップボードにコピーしますか？', 'はい', 'いいえ') == 1:
                    import clipboard
                    clipboard.set(formatted_json)
                    console.hud_alert('コピーしました', 'success', 1.5)
        else:
            # 通常のPython環境での表示
            for filename, data in self.json_data.items():
                print(f"\n📄 {filename}")
                print("="*40)
                print(json.dumps(data, indent=2, ensure_ascii=False))
    
    def save_processed_data(self, output_format='json'):
        """
        処理したデータを保存
        
        Args:
            output_format (str): 出力形式 ('json', 'txt', 'csv')
        """
        if not self.json_data:
            return
        
        if PYTHONISTA:
            # 保存オプションを選択
            formats = ['JSON (統合)', 'テキスト (サマリー)', 'キャンセル']
            choice = dialogs.list_dialog('保存形式', formats)
            
            if choice == 'JSON (統合)':
                # すべてのJSONを1つのファイルに統合
                output_data = {
                    'file_count': self.file_count,
                    'files': self.json_data
                }
                
                output_path = 'processed_json_data.json'
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                
                console.hud_alert(f'保存完了: {output_path}', 'success', 2.0)
                
            elif choice == 'テキスト (サマリー)':
                # サマリーをテキストファイルに保存
                output_path = 'json_summary.txt'
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"JSON処理結果サマリー\n")
                    f.write(f"{'='*40}\n")
                    f.write(f"処理日時: {self._get_timestamp()}\n")
                    f.write(f"ファイル数: {self.file_count}\n\n")
                    
                    for filename, data in self.json_data.items():
                        f.write(f"ファイル: {filename}\n")
                        f.write(f"  データ型: {type(data).__name__}\n")
                        if isinstance(data, (dict, list)):
                            f.write(f"  要素数: {len(data)}\n")
                        f.write("\n")
                
                console.hud_alert(f'保存完了: {output_path}', 'success', 2.0)
    
    def _get_timestamp(self):
        """現在のタイムスタンプを取得"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def cleanup(self):
        """一時ファイルのクリーンアップ"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                if PYTHONISTA:
                    console.hud_alert('一時ファイルを削除しました', 'success', 1.0)
                else:
                    print("Temporary files cleaned up")
            except Exception as e:
                if PYTHONISTA:
                    console.hud_alert(f'クリーンアップエラー: {str(e)}', 'error', 2.0)
                else:
                    print(f"Cleanup error: {str(e)}")
    
    def process(self):
        """メイン処理フロー"""
        try:
            # 1. ZIPファイルを選択
            zip_path = self.select_zip_file()
            if not zip_path:
                return False
            
            # 2. ZIPファイルを展開
            if not self.extract_zip(zip_path):
                return False
            
            # 3. JSONファイルを処理
            self.process_json_files()
            
            # 4. 結果を表示
            self.display_summary()
            
            # 5. 保存オプション
            if self.json_data and PYTHONISTA:
                if dialogs.alert('保存', '処理結果を保存しますか？', 'はい', 'いいえ') == 1:
                    self.save_processed_data()
            
            return True
            
        finally:
            # 6. クリーンアップ
            self.cleanup()


def main():
    """メイン関数"""
    if PYTHONISTA:
        console.clear()
        console.set_font('Menlo', 12)
        print("🚀 JSON ZIP Processor for Pythonista3")
        print("="*40)
    else:
        print("JSON ZIP Processor")
        print("="*40)
    
    processor = JSONZipProcessor()
    
    if processor.process():
        if PYTHONISTA:
            console.hud_alert('✅ 処理完了', 'success', 2.0)
        else:
            print("\n✅ Processing completed successfully")
    else:
        if PYTHONISTA:
            console.hud_alert('❌ 処理中断', 'error', 2.0)
        else:
            print("\n❌ Processing interrupted")
    
    # 追加の処理オプション
    if PYTHONISTA and processor.json_data:
        while True:
            options = ['JSONデータを再表示', '別のZIPファイルを処理', '終了']
            choice = dialogs.list_dialog('次の操作', options)
            
            if choice == 'JSONデータを再表示':
                processor.display_detailed_data()
            elif choice == '別のZIPファイルを処理':
                # 新しいプロセッサーインスタンスで再処理
                new_processor = JSONZipProcessor()
                new_processor.process()
                break
            else:
                break
    
    if PYTHONISTA:
        print("\n👋 処理を終了しました")


if __name__ == '__main__':
    main()