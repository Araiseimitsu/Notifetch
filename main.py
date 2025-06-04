#!/usr/bin/env python3
"""
NotiFetch - Notion データ取得・分析ツール
メインエントリーポイント
"""

import sys
import os
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

# Windows環境でのDIBエラー対策
if sys.platform.startswith('win'):
    # Qt関連の環境変数設定
    os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '1')
    os.environ.setdefault('QT_SCALE_FACTOR', '1')
    
# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.ui.main_window import MainWindow
from src.config.settings import Settings

def setup_application():
    """アプリケーションのセットアップ"""
    # PySide6アプリケーション作成
    app = QApplication(sys.argv)
    
    # アプリケーション情報
    app.setApplicationName("NotiFetch")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("NotiFetch")
    
    # 現代的なPySide6では高DPI対応は自動的に有効
    # 古いバージョンとの互換性のため、安全に設定を試行
    try:
        # PySide6 6.5以降では通常不要だが、互換性のため
        if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
            app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
            app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    except (AttributeError, Exception):
        # 新しいバージョンでは自動的に有効、または属性が存在しない
        pass
    
    # Windows環境でのグラフィックス最適化
    if sys.platform.startswith('win'):
        try:
            # 利用可能な場合のみ設定
            if hasattr(Qt.ApplicationAttribute, 'AA_DisableWindowContextHelpButton'):
                app.setAttribute(Qt.ApplicationAttribute.AA_DisableWindowContextHelpButton, True)
        except (AttributeError, Exception):
            pass
    
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