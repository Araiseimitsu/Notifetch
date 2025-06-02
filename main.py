#!/usr/bin/env python3
"""
NotiFetch - Notion データ取得・分析ツール
メインエントリーポイント
"""

import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.ui.main_window import MainWindow
from src.config.settings import Settings

def setup_application():
    """アプリケーションのセットアップ"""
    app = QApplication(sys.argv)
    
    # アプリケーション情報
    app.setApplicationName("NotiFetch")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("NotiFetch")
    
    # 高DPI対応
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    return app

def main():
    """メイン関数"""
    try:
        # 設定初期化（ログ設定含む）
        settings = Settings()
        logger = logging.getLogger(__name__)
        logger.info("NotiFetch アプリケーションを開始します")
        
        # PySide6アプリケーション作成
        app = setup_application()
        
        # メインウィンドウ作成・表示
        window = MainWindow()
        window.show()
        
        logger.info("メインウィンドウを表示しました")
        
        # アプリケーション実行
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"アプリケーション起動エラー: {e}", exc_info=True)
        
        # エラー発生時にメッセージボックスを表示
        try:
            app = QApplication.instance()
            if not app:
                app = QApplication(sys.argv)
            
            QMessageBox.critical(
                None, 
                "起動エラー", 
                f"アプリケーションの起動に失敗しました。\n\nエラー詳細:\n{e}"
            )
        except:
            # メッセージボックスも表示できない場合はコンソールに出力
            print(f"Fatal error: {e}")
        
        sys.exit(1)

if __name__ == "__main__":
    main() 