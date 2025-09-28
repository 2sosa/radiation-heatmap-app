#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト用のサンプルZIPファイルを作成するスクリプト
JSONファイルを含むZIPファイルを生成します
"""

import json
import zipfile
import os
from datetime import datetime

def create_sample_zip():
    """サンプルのJSONファイルを含むZIPファイルを作成"""
    
    # サンプルデータの定義
    sample_data = {
        "users.json": {
            "users": [
                {"id": 1, "name": "田中太郎", "email": "tanaka@example.com"},
                {"id": 2, "name": "山田花子", "email": "yamada@example.com"},
                {"id": 3, "name": "佐藤次郎", "email": "sato@example.com"}
            ],
            "total": 3,
            "timestamp": datetime.now().isoformat()
        },
        
        "products.json": {
            "products": [
                {"id": 101, "name": "ノートPC", "price": 98000, "stock": 5},
                {"id": 102, "name": "マウス", "price": 2500, "stock": 50},
                {"id": 103, "name": "キーボード", "price": 8900, "stock": 20}
            ],
            "currency": "JPY"
        },
        
        "settings.json": {
            "app_name": "Sample App",
            "version": "1.0.0",
            "settings": {
                "theme": "dark",
                "language": "ja",
                "notifications": True,
                "auto_save": True
            }
        },
        
        "data/analytics.json": {
            "daily_stats": [
                {"date": "2025-09-26", "views": 1250, "clicks": 89},
                {"date": "2025-09-27", "views": 1380, "clicks": 102},
                {"date": "2025-09-28", "views": 1567, "clicks": 134}
            ],
            "summary": {
                "total_views": 4197,
                "total_clicks": 325,
                "conversion_rate": 7.74
            }
        },
        
        "data/inventory.json": {
            "warehouse": "Tokyo-01",
            "items": [
                {"sku": "A001", "quantity": 150, "location": "A-1-1"},
                {"sku": "A002", "quantity": 89, "location": "A-1-2"},
                {"sku": "B001", "quantity": 234, "location": "B-2-1"}
            ],
            "last_updated": datetime.now().isoformat()
        }
    }
    
    # ZIPファイルを作成
    zip_filename = "sample_json_data.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filename, data in sample_data.items():
            # JSONデータを文字列に変換
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            
            # ZIPファイルに追加
            zipf.writestr(filename, json_str.encode('utf-8'))
    
    print(f"✅ サンプルZIPファイルを作成しました: {zip_filename}")
    print(f"📦 含まれるファイル:")
    
    # 作成したZIPファイルの内容を確認
    with zipfile.ZipFile(zip_filename, 'r') as zipf:
        for info in zipf.filelist:
            print(f"  - {info.filename} ({info.file_size} bytes)")
    
    return zip_filename

def create_large_sample_zip():
    """大量のJSONファイルを含むZIPファイルを作成（テスト用）"""
    
    zip_filename = "large_sample_json_data.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 100個のJSONファイルを作成
        for i in range(100):
            data = {
                "file_id": i,
                "filename": f"data_{i:03d}.json",
                "content": {
                    "index": i,
                    "value": f"Value {i}",
                    "timestamp": datetime.now().isoformat(),
                    "data": [j for j in range(10)]
                }
            }
            
            filename = f"batch_{i//10}/data_{i:03d}.json"
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            zipf.writestr(filename, json_str.encode('utf-8'))
    
    print(f"✅ 大量サンプルZIPファイルを作成しました: {zip_filename}")
    print(f"📦 100個のJSONファイルを含んでいます")
    
    return zip_filename

def main():
    """メイン処理"""
    print("📝 サンプルZIPファイル作成ツール")
    print("="*40)
    
    # 通常のサンプルを作成
    create_sample_zip()
    
    print("\n" + "="*40)
    
    # オプション：大量ファイルのサンプルも作成
    response = input("\n大量のJSONファイル（100個）を含むサンプルも作成しますか？ (y/n): ")
    if response.lower() == 'y':
        create_large_sample_zip()
    
    print("\n✨ 完了しました！")
    print("これらのZIPファイルをiPhoneに転送して、Pythonista3でテストできます。")

if __name__ == "__main__":
    main()