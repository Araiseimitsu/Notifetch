#!/usr/bin/env python3
"""
リソースファイルパス処理ユーティリティ
PyInstallerビルド時のリソースファイルアクセスを正しく処理
"""

import sys
import os
from pathlib import Path

def get_resource_path(resource_name: str) -> Path:
    """
    リソースファイルの正しいパスを取得
    開発時とPyInstallerビルド時の両方に対応
    
    Args:
        resource_name: リソースファイル名（例: "logo.png", "icon.ico"）
    
    Returns:
        Path: リソースファイルの完全パス
    """
    try:
        # PyInstallerでビルドされた場合、_MEIBUNDLEが存在
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller実行時のテンポラリディレクトリ
            base_path = Path(sys._MEIPASS)
            resource_path = base_path / "assets" / resource_name
        else:
            # 開発時：プロジェクトルートからのパス
            # このファイルはsrc/utils/にあるので、2階層上がプロジェクトルート
            project_root = Path(__file__).parent.parent.parent
            resource_path = project_root / "assets" / resource_name
        
        return resource_path
    
    except Exception as e:
        print(f"リソースパス取得エラー ({resource_name}): {e}")
        # フォールバック：現在のディレクトリから検索
        fallback_path = Path("assets") / resource_name
        return fallback_path

def get_icon_path() -> Path:
    """UIアイコンファイルのパスを取得（PNG形式）"""
    return get_resource_path("logo.png")

def get_app_icon_path() -> Path:
    """アプリケーションアイコンファイルのパスを取得（ICO形式）"""
    return get_resource_path("icon.ico")

def get_taskbar_icon_path() -> Path:
    """タスクバー用アイコンファイルのパスを取得（ICO形式優先）"""
    # Windowsタスクバーには.icoファイルが最適
    ico_path = get_resource_path("icon.ico")
    if ico_path.exists():
        return ico_path
    # フォールバック：PNGファイル
    return get_resource_path("logo.png")

def setup_windows_taskbar_icon(app_instance):
    """
    Windowsタスクバー用のアイコン設定を強化
    
    Args:
        app_instance: QApplication のインスタンス
    """
    if not sys.platform.startswith('win'):
        return False
    
    try:
        import ctypes
        from ctypes import wintypes
        
        # より詳細なWindows設定
        app_id = "NotiFetch.DataAnalysisTool.1.0"
        
        # アプリケーションユーザーモデルIDを設定
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        
        # アイコンファイルのパスを取得
        icon_path = get_taskbar_icon_path()
        
        if icon_path.exists() and str(icon_path).endswith('.ico'):
            try:
                # Windows用のアイコンハンドルを作成
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                
                # LoadImageでアイコンを読み込み
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x0010
                LR_DEFAULTSIZE = 0x0040
                
                hicon = user32.LoadImageW(
                    None,  # hInstance
                    str(icon_path),  # lpszName
                    IMAGE_ICON,  # uType
                    0,  # cxDesired
                    0,  # cyDesired
                    LR_LOADFROMFILE | LR_DEFAULTSIZE  # fuLoad
                )
                
                if hicon:
                    print(f"Windows アイコンハンドルを作成しました: {icon_path}")
                    
                    # QApplicationのネイティブウィンドウハンドルを取得して設定
                    if hasattr(app_instance, 'setProperty'):
                        app_instance.setProperty("windows_icon_handle", hicon)
                    
                    return True
                else:
                    print("Windows アイコンハンドルの作成に失敗しました")
                    
            except Exception as native_e:
                print(f"ネイティブアイコン設定エラー: {native_e}")
        
        print("Windowsタスクバーアイコン設定を適用しました")
        return True
        
    except Exception as e:
        print(f"Windowsタスクバーアイコン設定エラー: {e}")
        return False 