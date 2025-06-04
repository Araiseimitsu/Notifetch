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
    
    # Windowsでのタスクバーアイコン設定のため
    try:
        import ctypes
        # アプリケーションIDを設定（タスクバーアイコンのため）
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('NotiFetch.DataAnalysisTool.1.0')
    except Exception:
        pass  # Windows以外や設定失敗時は無視
    
# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.ui.main_window import MainWindow
from src.config.settings import Settings
from src.utils.resource_utils import get_taskbar_icon_path, get_app_icon_path, setup_windows_taskbar_icon

def setup_application():
    """アプリケーションのセットアップ"""
    # PySide6アプリケーション作成
    app = QApplication(sys.argv)
    
    # アプリケーション情報
    app.setApplicationName("NotiFetch")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("NotiFetch")
    
    # タスクバーアイコンの設定（最優先で実行）
    try:
        # Windowsタスクバー用には.icoファイルを優先
        taskbar_icon_path = get_taskbar_icon_path()
        
        print(f"タスクバーアイコンパスを確認中: {taskbar_icon_path}")
        print(f"ファイル存在確認: {taskbar_icon_path.exists()}")
        
        if taskbar_icon_path.exists():
            icon = QIcon(str(taskbar_icon_path))
            if not icon.isNull():
                # アプリケーション全体のアイコンを設定（タスクバー用）
                app.setWindowIcon(icon)
                QApplication.setWindowIcon(icon)
                
                print(f"タスクバーアイコンを設定しました: {taskbar_icon_path}")
                
                # Windowsでのタスクバーアイコン強化設定
                if sys.platform.startswith('win'):
                    try:
                        # 新しい強化されたWindows設定を使用
                        setup_success = setup_windows_taskbar_icon(app)
                        if setup_success:
                            print("Windowsタスクバーアイコン設定を強化しました")
                        else:
                            print("Windowsタスクバーアイコン強化設定に失敗しました")
                    except Exception as win_e:
                        print(f"Windows固有の設定でエラー: {win_e}")
                        
            else:
                print("タスクバーアイコンの作成に失敗しました（QIcon.isNull() == True）")
        else:
            print(f"タスクバーアイコンファイルが見つかりません: {taskbar_icon_path}")
            # PyInstaller環境でのデバッグ情報
            if hasattr(sys, '_MEIPASS'):
                print(f"PyInstaller実行中、_MEIPASS: {sys._MEIPASS}")
                # _MEIPASSディレクトリの内容を確認
                try:
                    meipass_path = Path(sys._MEIPASS)
                    print(f"_MEIPASS内容: {list(meipass_path.iterdir())}")
                    assets_path = meipass_path / "assets"
                    if assets_path.exists():
                        print(f"assets内容: {list(assets_path.iterdir())}")
                except Exception as debug_e:
                    print(f"デバッグ情報取得エラー: {debug_e}")
    except Exception as e:
        print(f"タスクバーアイコン設定エラー: {e}")
    
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