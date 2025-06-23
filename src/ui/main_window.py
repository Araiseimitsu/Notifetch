import sys
import logging
import webbrowser
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QLabel, QLineEdit, QPushButton, QTextEdit,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFileDialog, QComboBox, QGroupBox, QFormLayout,
    QSplitter, QScrollArea, QFrame, QApplication, QListWidget,
    QListWidgetItem, QMenu, QInputDialog, QDialog, QStackedWidget,
    QGridLayout, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, QObject, Signal, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QFont, QIcon, QAction, QPixmap, QPainter, QColor, QPen, QBrush, QLinearGradient

from ..config.settings import Settings
from ..core.notion_client import NotionClient
from ..core.gemini_client import GeminiClient
from ..utils.data_converter import DataConverter
from ..utils.resource_utils import get_icon_path, get_taskbar_icon_path

logger = logging.getLogger(__name__)

class InfoCard(QFrame):
    """美しい情報カードウィジェット"""
    
    def __init__(self, icon, title, value, color="#4a90e2"):
        super().__init__()
        self.color = color
        self.icon = icon
        self.title = title
        self.setup_ui(icon, title, value)
    
    def setup_ui(self, icon, title, value):
        self.setFixedSize(200, 140)  # サイズを少し大きく
        self.update_style()
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # アイコン
        self.icon_label = QLabel(icon)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("""
            font-size: 32px; 
            color: white;
            font-weight: bold;
        """)
        
        # 値
        self.value_label = QLabel(value)
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            color: white;
            margin: 4px 0px;
        """)
        
        # タイトル
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            font-size: 13px; 
            color: white;
            font-weight: 500;
        """)
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.title_label)
    
    def update_style(self):
        """スタイルシートを更新"""
        darker_color = self.darken_color(self.color)
        self.setStyleSheet(f"""
            InfoCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                           stop:0 {self.color}, stop:1 {darker_color});
                border: none;
                border-radius: 15px;
                color: white;
            }}
            InfoCard:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                           stop:0 {darker_color}, stop:1 {self.darken_color(darker_color)});
            }}
        """)
    
    def darken_color(self, color):
        """色を暗くする"""
        if color == "#4a90e2":
            return "#357abd"
        elif color == "#5cb85c":
            return "#449d44"
        elif color == "#f0ad4e":
            return "#ec971f"
        elif color == "#d9534f":
            return "#c9302c"
        return color
    
    def update_value(self, value):
        """値を更新"""
        self.value_label.setText(str(value))
    
    def update_color(self, new_color):
        """色を更新"""
        self.color = new_color
        self.update_style()

class NavButton(QPushButton):
    """美しいナビゲーションボタン"""
    
    def __init__(self, icon, text):
        super().__init__()
        self.setText(f"  {icon}   {text}")
        self.setCheckable(True)
        self.setFixedHeight(50)
        self.setStyleSheet("""
            NavButton {
                text-align: left;
                padding: 12px 20px;
                border: none;
                border-radius: 8px;
                background-color: transparent;
                color: #666;
                font-size: 14px;
                font-weight: 500;
            }
            NavButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                           stop:0 #4a90e2, stop:1 #357abd);
                color: white;
                font-weight: 600;
            }
            NavButton:hover:!checked {
                background-color: #f5f5f5;
                color: #333;
            }
        """)

class ModernProgressBar(QProgressBar):
    """モダンなプログレスバー"""
    
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 8px;
                background-color: #f0f0f0;
                height: 16px;
                text-align: center;
                color: #333;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                           stop:0 #4a90e2, stop:0.5 #5cb85c, stop:1 #4a90e2);
                border-radius: 8px;
            }
        """)

class MainWindow(QMainWindow):
    """メインウィンドウクラス - モダンデザイン版"""
    
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.notion_client = None
        self.gemini_client = None
        self.current_data = None
        
        self.init_modern_ui()
        self.load_settings()
        self.apply_theme()
        
        # ウィンドウ設定
        self.setWindowTitle("NotiFetch - Notion データ取得・分析ツール")
        self.setMinimumSize(1200, 800)
        
        # ウィンドウアイコンの設定（タスクバー用）
        try:
            # タスクバーと統一するため.icoファイルを使用
            window_icon_path = get_taskbar_icon_path()
            
            print(f"ウィンドウアイコンパス: {window_icon_path}")
            print(f"ファイル存在確認: {window_icon_path.exists()}")
            
            if window_icon_path.exists():
                # 複数サイズでアイコンを作成
                icon = QIcon(str(window_icon_path))
                if not icon.isNull():
                    # .icoファイルの場合は既に複数サイズが含まれているが、
                    # .pngの場合は手動で複数サイズを追加
                    if str(window_icon_path).endswith('.png'):
                        pixmap = QPixmap(str(window_icon_path))
                        if not pixmap.isNull():
                            # 標準的なアイコンサイズで追加
                            icon.addPixmap(pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                            icon.addPixmap(pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                            icon.addPixmap(pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                            icon.addPixmap(pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                            icon.addPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    
                    # ウィンドウアイコンを設定
                    self.setWindowIcon(icon)
                    
                    # アプリケーションアイコンも再設定（タスクバー統一のため）
                    app = QApplication.instance()
                    if app:
                        app.setWindowIcon(icon)
                        
                    logger.info(f"ウィンドウアイコンを設定しました: {window_icon_path}")
                else:
                    logger.warning(f"アイコンファイルの読み込みに失敗: {window_icon_path}")
            else:
                logger.warning(f"アイコンファイルが見つかりません: {window_icon_path}")
        except Exception as e:
            logger.error(f"ウィンドウアイコン設定エラー: {e}")
        
        # 起動時に画面を最大化
        self.showMaximized()
    
    def center_window(self):
        """ウィンドウを画面中央に配置"""
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def init_modern_ui(self):
        """モダンUI初期化"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト（水平分割）
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # サイドバー作成
        self.create_modern_sidebar()
        main_layout.addWidget(self.sidebar_widget, 0)
        
        # コンテンツエリア作成
        self.create_content_area()
        main_layout.addWidget(self.content_widget, 1)
        
        # 各ページを作成
        self.create_modern_pages()
        
        # ステータスバー
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("🚀 NotiFetchへようこそ！")
    
    def create_modern_sidebar(self):
        """モダンなサイドバーの作成"""
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setFixedWidth(250)
        self.sidebar_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                           stop:0 #f8f9fa, stop:1 #e9ecef);
                border-right: 1px solid #dee2e6;
            }
        """)
        
        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_layout.setSpacing(20)
        sidebar_layout.setContentsMargins(20, 30, 20, 30)
        
        # ロゴエリア
        logo_frame = QFrame()
        logo_layout = QVBoxLayout(logo_frame)
        
        # アイコンファイルからロゴ画像を作成
        try:
            icon_path = get_icon_path()
            print(f"サイドバーアイコンパス: {icon_path}")
            
            if icon_path.exists():
                # QPixmapでアイコンを読み込み、高DPI対応で適切なサイズに調整
                pixmap = QPixmap(str(icon_path))
                if not pixmap.isNull():
                    # 高DPI環境に対応したサイズ計算
                    app = QApplication.instance()
                    device_pixel_ratio = app.devicePixelRatio() if app else 1.0
                    target_size = int(48 * device_pixel_ratio)  # より大きなサイズ
                    
                    # 高品質でスケール
                    scaled_pixmap = pixmap.scaled(
                        target_size, target_size, 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    scaled_pixmap.setDevicePixelRatio(device_pixel_ratio)
                    
                    # ロゴラベルを画像付きで作成
                    logo_label = QLabel()
                    logo_label.setPixmap(scaled_pixmap)
                    logo_label.setAlignment(Qt.AlignCenter)
                    logo_label.setFixedSize(48, 48)  # 固定サイズで表示
                    
                    # テキストラベルを別途作成
                    logo_text = QLabel("NotiFetch")
                    logo_font = QFont()
                    logo_font.setPointSize(20)  # 少し小さく調整
                    logo_font.setBold(True)
                    logo_text.setFont(logo_font)
                    logo_text.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
                    logo_text.setAlignment(Qt.AlignCenter)
                    
                    # 水平レイアウトでアイコンとテキストを並べる
                    logo_container = QWidget()
                    logo_container_layout = QHBoxLayout(logo_container)
                    logo_container_layout.setContentsMargins(0, 0, 0, 0)
                    logo_container_layout.setSpacing(12)
                    logo_container_layout.addStretch()
                    logo_container_layout.addWidget(logo_label)
                    logo_container_layout.addWidget(logo_text)
                    logo_container_layout.addStretch()
                    
                    logo_layout.addWidget(logo_container)
                    logger.info(f"サイドバーロゴを設定しました: {icon_path}")
                else:
                    # フォールバック：絵文字版
                    logger.warning(f"ロゴファイルの読み込みに失敗、絵文字版にフォールバック: {icon_path}")
                    self._create_fallback_logo(logo_layout)
            else:
                # フォールバック：絵文字版
                logger.warning(f"ロゴファイルが見つかりません、絵文字版にフォールバック: {icon_path}")
                self._create_fallback_logo(logo_layout)
        except Exception as e:
            logger.error(f"ロゴアイコン読み込みエラー: {e}")
            # フォールバック：絵文字版
            self._create_fallback_logo(logo_layout)
        
        subtitle_label = QLabel("Notion データ分析ツール")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        
        logo_layout.addWidget(subtitle_label)
        sidebar_layout.addWidget(logo_frame)
        
        # 区切り線
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("color: #dee2e6;")
        sidebar_layout.addWidget(separator)
        
        # ナビゲーションボタン
        nav_data = [
            ("🔗", "接続設定", 0),
            ("📥", "データ取得", 1),
            ("🤖", "AI分析", 2),
            ("⚙️", "設定", 3)
        ]
        
        self.nav_buttons = []
        for icon, text, index in nav_data:
            btn = NavButton(icon, text)
            btn.clicked.connect(lambda checked, idx=index: self.switch_page(idx))
            self.nav_buttons.append(btn)
            sidebar_layout.addWidget(btn)
        
        # スペーサー
        sidebar_layout.addStretch()
        
        # フッター情報
        footer_label = QLabel("Made with 🤩 by A.T")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("color: #6c757d; font-size: 10px;")
        sidebar_layout.addWidget(footer_label)
        
        # 最初のボタンを選択🤩
        self.nav_buttons[0].setChecked(True)
    
    def _create_fallback_logo(self, logo_layout):
        """フォールバック用の絵文字ロゴを作成"""
        logo_label = QLabel("📊 NotiFetch")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_font = QFont()
        logo_font.setPointSize(24)
        logo_font.setBold(True)
        logo_label.setFont(logo_font)
        logo_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        logo_layout.addWidget(logo_label)
    
    def create_content_area(self):
        """コンテンツエリアの作成"""
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        
        # ページタイトルエリア
        self.page_title = QLabel("接続設定")
        self.page_title.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 20px;
        """)
        content_layout.addWidget(self.page_title)
        
        # スタックウィジェット（ページ切り替え用）
        self.content_stack = QStackedWidget()
        content_layout.addWidget(self.content_stack)
    
    def create_modern_pages(self):
        """各ページの作成"""
        self.create_modern_connection_page()
        self.create_modern_data_page()
        self.create_modern_analysis_page()
        self.create_modern_settings_page()
    
    def create_card(self, title):
        """美しい情報カードの作成"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #e9ecef;
                border-radius: 12px;
                margin: 5px;
            }
            QFrame:hover {
                border-color: #4a90e2;
            }
        """)
        
        main_layout = QVBoxLayout(card)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # タイトル
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        """)
        main_layout.addWidget(title_label)
        
        # コンテンツエリア用のウィジェット
        content_widget = QWidget()
        main_layout.addWidget(content_widget)
        
        return card, content_widget
    
    def create_modern_connection_page(self):
        """接続設定ページ"""
        page = QScrollArea()
        page_content = QWidget()
        layout = QVBoxLayout(page_content)
        layout.setSpacing(30)
        
        # Notion API設定カード
        notion_card, notion_content = self.create_card("🔗 Notion API 設定")
        notion_layout = QFormLayout(notion_content)
        
        self.notion_token_input = QLineEdit()
        self.notion_token_input.setEchoMode(QLineEdit.Password)
        self.notion_token_input.setPlaceholderText("secret_...")
        self.notion_token_input.setStyleSheet(self.get_input_style())
        
        self.test_connection_btn = QPushButton("🧪 接続テスト")
        self.test_connection_btn.setStyleSheet(self.get_button_style())
        self.test_connection_btn.clicked.connect(self.test_notion_connection)
        
        notion_layout.addRow("API トークン:", self.notion_token_input)
        notion_layout.addRow("", self.test_connection_btn)
        
        # ページ設定カード
        page_card, page_content_widget = self.create_card("📄 ページ/データベース設定")
        page_layout = QFormLayout(page_content_widget)
        
        # ページID入力エリア
        id_input_widget = QWidget()
        id_input_layout = QHBoxLayout(id_input_widget)
        id_input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.page_id_input = QLineEdit()
        self.page_id_input.setPlaceholderText("ページID または URL")
        self.page_id_input.setStyleSheet(self.get_input_style())
        
        self.history_btn = QPushButton("📚")
        self.history_btn.setFixedSize(40, 40)
        self.history_btn.setStyleSheet(self.get_icon_button_style())
        self.history_btn.clicked.connect(self.show_page_history)
        
        id_input_layout.addWidget(self.page_id_input)
        id_input_layout.addWidget(self.history_btn)
        
        # ボタンエリア
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        self.validate_page_btn = QPushButton("✅ ページ検証")
        self.validate_page_btn.setStyleSheet(self.get_button_style("#5cb85c"))
        self.validate_page_btn.clicked.connect(self.validate_page_id)
        
        self.edit_page_btn = QPushButton("✏️ ページ編集")
        self.edit_page_btn.setStyleSheet(self.get_button_style("#f0ad4e"))
        self.edit_page_btn.clicked.connect(self.edit_current_page)
        self.edit_page_btn.setEnabled(False)
        
        button_layout.addWidget(self.validate_page_btn)
        button_layout.addWidget(self.edit_page_btn)
        button_layout.addStretch()
        
        # ページ情報表示
        self.page_info_text = QTextEdit()
        self.page_info_text.setMaximumHeight(120)
        self.page_info_text.setReadOnly(True)
        self.page_info_text.setStyleSheet(self.get_text_area_style())
        
        page_layout.addRow("ページ/データベース ID:", id_input_widget)
        page_layout.addRow("", button_widget)
        page_layout.addRow("ページ情報:", self.page_info_text)
        
        layout.addWidget(notion_card)
        layout.addWidget(page_card)
        layout.addStretch()
        
        page.setWidget(page_content)
        page.setWidgetResizable(True)
        self.content_stack.addWidget(page)
    
    def create_modern_data_page(self):
        """データ取得ページ"""
        page = QScrollArea()
        page_content = QWidget()
        layout = QVBoxLayout(page_content)
        layout.setSpacing(25)
        
        # 統計カードエリア（グリッドレイアウト）
        stats_container = QFrame()
        stats_container.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
            }
        """)
        stats_main_layout = QVBoxLayout(stats_container)
        stats_main_layout.setContentsMargins(15, 20, 15, 20)
        
        # 統計セクションタイトル
        stats_title = QLabel("📈 データ統計情報")
        stats_title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 15px;
        """)
        stats_main_layout.addWidget(stats_title)
        
        # 統計カードのグリッド
        stats_grid_widget = QWidget()
        stats_grid = QGridLayout(stats_grid_widget)
        stats_grid.setSpacing(20)
        stats_grid.setContentsMargins(0, 0, 0, 0)
        
        # 改良されたカード
        self.rows_card = self.create_enhanced_stat_card("📊", "データ行数", "0", "#4a90e2", "データなし｜待機中")
        self.columns_card = self.create_enhanced_stat_card("📋", "列数", "0", "#5cb85c", "フィールド情報なし")
        self.size_card = self.create_enhanced_stat_card("💾", "データサイズ", "0 KB", "#f0ad4e", "メモリ使用量なし")
        self.status_card = self.create_enhanced_stat_card("🎯", "ステータス", "待機中", "#d9534f", "データ取得を開始してください")
        
        # 2x2グリッドに配置
        stats_grid.addWidget(self.rows_card, 0, 0)
        stats_grid.addWidget(self.columns_card, 0, 1)
        stats_grid.addWidget(self.size_card, 1, 0)
        stats_grid.addWidget(self.status_card, 1, 1)
        
        stats_main_layout.addWidget(stats_grid_widget)
        
        # データ取得コントロールエリア
        control_card, control_content = self.create_card("⚙️ データ取得設定")
        control_card.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #e9ecef;
                border-radius: 20px;
                margin: 5px;
            }
            QFrame:hover {
                border-color: #4a90e2;
            }
        """)
        
        # コントロールパネルのレイアウト
        control_main_layout = QVBoxLayout(control_content)
        control_main_layout.setSpacing(20)
        
        # 取得設定エリア
        settings_widget = QWidget()
        settings_layout = QHBoxLayout(settings_widget)
        settings_layout.setSpacing(25)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        
        # 取得行数設定
        limit_group = QWidget()
        limit_layout = QVBoxLayout(limit_group)
        limit_layout.setSpacing(8)
        
        limit_label = QLabel("📝 取得行数")
        limit_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #2c3e50;
        """)
        
        self.fetch_limit_combo = QComboBox()
        self.fetch_limit_combo.addItems([
            "すべて", "100行", "500行", "1000行", "2000行", "5000行", "カスタム"
        ])
        self.fetch_limit_combo.setStyleSheet(self.get_enhanced_combo_style())
        self.fetch_limit_combo.currentTextChanged.connect(self.on_fetch_limit_changed)
        
        limit_layout.addWidget(limit_label)
        limit_layout.addWidget(self.fetch_limit_combo)
        
        # カスタム行数入力
        custom_group = QWidget()
        custom_layout = QVBoxLayout(custom_group)
        custom_layout.setSpacing(8)
        
        custom_label = QLabel("🔢 カスタム行数")
        custom_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #2c3e50;
        """)
        
        self.custom_limit_input = QLineEdit()
        self.custom_limit_input.setPlaceholderText("例: 10000")
        self.custom_limit_input.setStyleSheet(self.get_enhanced_input_style())
        self.custom_limit_input.setVisible(False)
        
        custom_layout.addWidget(custom_label)
        custom_layout.addWidget(self.custom_limit_input)
        
        # 実行ボタンエリア
        button_group = QWidget()
        button_layout = QVBoxLayout(button_group)
        button_layout.setSpacing(8)
        
        button_label = QLabel("🚀 実行")
        button_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #2c3e50;
        """)
        
        self.fetch_data_btn = QPushButton("データ取得開始")
        self.fetch_data_btn.setFixedHeight(50)
        self.fetch_data_btn.setStyleSheet(self.get_enhanced_primary_button_style())
        self.fetch_data_btn.clicked.connect(self.fetch_data)
        
        button_layout.addWidget(button_label)
        button_layout.addWidget(self.fetch_data_btn)
        
        # レイアウトに追加
        settings_layout.addWidget(limit_group)
        settings_layout.addWidget(custom_group)
        settings_layout.addWidget(button_group)
        settings_layout.addStretch()
        
        control_main_layout.addWidget(settings_widget)
        
        # プログレスバー（改良版）
        self.progress_bar = self.create_enhanced_progress_bar()
        self.progress_bar.setVisible(False)
        
        # データプレビューカード
        preview_card, preview_content = self.create_card("👀 データプレビュー")
        preview_card.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #e9ecef;
                border-radius: 20px;
                margin: 5px;
            }
            QFrame:hover {
                border-color: #4a90e2;
            }
        """)
        
        preview_layout = QVBoxLayout(preview_content)
        
        self.data_table = QTableWidget()
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.data_table.setStyleSheet(self.get_enhanced_table_style())
        self.data_table.setMinimumHeight(450)
        
        # エクスポートボタン（改良版）
        export_widget = QWidget()
        export_layout = QHBoxLayout(export_widget)
        export_layout.setContentsMargins(0, 15, 0, 0)
        export_layout.setSpacing(15)
        
        self.export_csv_btn = QPushButton("📊 CSV エクスポート")
        self.export_csv_btn.setStyleSheet(self.get_enhanced_button_style("#5cb85c"))
        self.export_csv_btn.clicked.connect(self.export_csv)
        self.export_csv_btn.setEnabled(False)
        
        self.export_excel_btn = QPushButton("📈 Excel エクスポート")
        self.export_excel_btn.setStyleSheet(self.get_enhanced_button_style("#f0ad4e"))
        self.export_excel_btn.clicked.connect(self.export_excel)
        self.export_excel_btn.setEnabled(False)
        
        export_layout.addWidget(self.export_csv_btn)
        export_layout.addWidget(self.export_excel_btn)
        export_layout.addStretch()
        
        preview_layout.addWidget(self.data_table)
        preview_layout.addWidget(export_widget)
        
        # データ概要カード
        summary_card, summary_content = self.create_card("📈 データ概要")
        summary_card.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #e9ecef;
                border-radius: 20px;
                margin: 5px;
            }
        """)
        
        summary_layout = QVBoxLayout(summary_content)
        
        self.data_summary_text = QTextEdit()
        self.data_summary_text.setMaximumHeight(200)
        self.data_summary_text.setReadOnly(True)
        self.data_summary_text.setStyleSheet(self.get_enhanced_text_area_style())
        
        summary_layout.addWidget(self.data_summary_text)
        
        # メインレイアウトに追加
        layout.addWidget(stats_container)
        layout.addWidget(control_card)
        layout.addWidget(self.progress_bar)
        layout.addWidget(preview_card)
        layout.addWidget(summary_card)
        layout.addStretch()
        
        page.setWidget(page_content)
        page.setWidgetResizable(True)
        self.content_stack.addWidget(page)
    
    def create_enhanced_stat_card(self, icon, title, value, color, description):
        """改良された統計カード"""
        card = QFrame()
        card.setFixedSize(280, 120)
        
        # カードのスタイル
        darker_color = self.darken_color(color)
        card.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                           stop:0 {color}, stop:1 {darker_color});
                border: none;
                border-radius: 18px;
                color: white;
            }}
            QFrame:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                           stop:0 {darker_color}, stop:1 {self.darken_color(darker_color)});
            }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)
        
        # アイコン部分
        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(50, 50)
        icon_label.setStyleSheet("""
            font-size: 30px;
            color: white;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 25px;
        """)
        
        # テキスト部分
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        # 値
        value_label = QLabel(value)
        value_label.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: white;
        """)
        
        # タイトル
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: white;
        """)
        
        # 説明
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            font-size: 11px;
            color: rgba(255, 255, 255, 0.8);
        """)
        desc_label.setWordWrap(True)
        
        text_layout.addWidget(value_label)
        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)
        
        layout.addWidget(icon_label)
        layout.addWidget(text_widget)
        
        # カスタム属性を追加（desc_labelも追加）
        card.value_label = value_label
        card.title_label = title_label
        card.desc_label = desc_label
        card.color = color
        
        return card
    
    def create_enhanced_progress_bar(self):
        """改良されたプログレスバー"""
        progress = QProgressBar()
        progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 12px;
                background-color: #f0f0f0;
                height: 24px;
                text-align: center;
                color: #2c3e50;
                font-weight: bold;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                           stop:0 #667eea, stop:0.5 #764ba2, stop:1 #667eea);
                border-radius: 12px;
                margin: 2px;
            }
        """)
        return progress
    
    def get_enhanced_combo_style(self):
        """改良されたコンボボックススタイル"""
        return """
            QComboBox {
                border: 2px solid #e9ecef;
                border-radius: 12px;
                padding: 12px 15px;
                background-color: white;
                color: #2c3e50;
                font-size: 14px;
                font-weight: 500;
                min-width: 150px;
                min-height: 20px;
            }
            QComboBox:focus {
                border-color: #4a90e2;
                background-color: #f8f9fa;
                color: #2c3e50;
            }
            QComboBox:hover {
                border-color: #4a90e2;
                background-color: #f8f9fa;
            }
            QComboBox::drop-down {
                border: none;
                background-color: transparent;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 6px solid #2c3e50;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 2px solid #e9ecef;
                border-radius: 12px;
                selection-background-color: #4a90e2;
                selection-color: white;
                color: #2c3e50;
                padding: 5px;
            }
            QComboBox QAbstractItemView::item {
                color: #2c3e50;
                padding: 10px 15px;
                border-radius: 8px;
                margin: 2px;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #4a90e2;
                color: white;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #f8f9fa;
                color: #2c3e50;
            }
        """
    
    def get_enhanced_input_style(self):
        """改良された入力フィールドスタイル"""
        return """
            QLineEdit {
                border: 2px solid #e9ecef;
                border-radius: 12px;
                padding: 12px 15px;
                background-color: white;
                color: #2c3e50;
                font-size: 14px;
                font-weight: 500;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #4a90e2;
                background-color: #f8f9fa;
                color: #2c3e50;
            }
            QLineEdit:hover {
                border-color: #4a90e2;
                background-color: #f8f9fa;
            }
        """
    
    def get_enhanced_primary_button_style(self):
        """改良されたプライマリボタンスタイル"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                           stop:0 #4a90e2, stop:0.5 #5cb85c, stop:1 #4a90e2);
                border: none;
                padding: 15px 25px;
                border-radius: 10px;
                color: white;
                font-size: 16px;
                font-weight: bold;
                min-width: 150px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                           stop:0 #357abd, stop:0.5 #449d44, stop:1 #357abd);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                           stop:0 #2968a3, stop:0.5 #398439, stop:1 #2968a3);
            }
        """
    
    def get_enhanced_button_style(self, color):
        """改良されたボタンスタイル"""
        darker = self.darken_color(color)
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                           stop:0 {color}, stop:1 {darker});
                border: none;
                padding: 12px 20px;
                border-radius: 10px;
                color: white;
                font-size: 14px;
                font-weight: bold;
                min-width: 140px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                           stop:0 {darker}, stop:1 {self.darken_color(darker)});
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                           stop:0 {self.darken_color(darker)}, stop:1 {color});
            }}
            QPushButton:disabled {{
                background: #adb5bd;
                color: #6c757d;
            }}
        """
    
    def get_enhanced_table_style(self):
        """改良されたテーブルスタイル"""
        return """
            QTableWidget {
                background-color: white;
                alternate-background-color: #f8f9fa;
                border: none;
                border-radius: 15px;
                gridline-color: #e9ecef;
                selection-background-color: #4a90e2;
                selection-color: white;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 12px 8px;
                border: none;
                border-bottom: 1px solid #f1f3f4;
            }
            QTableWidget::item:selected {
                background-color: #4a90e2;
                color: white;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                           stop:0 #667eea, stop:1 #764ba2);
                color: white;
                padding: 15px 10px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
            QHeaderView::section:first {
                border-top-left-radius: 15px;
            }
            QHeaderView::section:last {
                border-top-right-radius: 15px;
            }
            QTableWidget QTableCornerButton::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                           stop:0 #667eea, stop:1 #764ba2);
                border: none;
                border-top-left-radius: 15px;
            }
            QScrollBar:vertical {
                background: #f8f9fa;
                width: 12px;
                border-radius: 6px;
                margin: 15px 0;
            }
            QScrollBar::handle:vertical {
                background: #adb5bd;
                border-radius: 6px;
                min-height: 20px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6c757d;
            }
        """
    
    def get_enhanced_text_area_style(self):
        """改良されたテキストエリアスタイル"""
        return """
            QTextEdit {
                border: 2px solid #e9ecef;
                border-radius: 15px;
                padding: 15px;
                background-color: white;
                color: #2c3e50;
                font-size: 13px;
                line-height: 1.6;
                font-family: 'Segoe UI', sans-serif;
            }
            QTextEdit:focus {
                border-color: #4a90e2;
                background-color: #f8f9fa;
                color: #2c3e50;
            }
            QScrollBar:vertical {
                background: #f8f9fa;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #adb5bd;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6c757d;
            }
        """
    
    def create_modern_analysis_page(self):
        """AI分析ページ"""
        page = QScrollArea()
        page_content = QWidget()
        layout = QVBoxLayout(page_content)
        layout.setSpacing(30)
        
        # Gemini API設定カード
        gemini_card, gemini_content = self.create_card("🤖 Gemini API 設定")
        gemini_layout = QFormLayout(gemini_content)
        
        self.gemini_api_key_input = QLineEdit()
        self.gemini_api_key_input.setEchoMode(QLineEdit.Password)
        self.gemini_api_key_input.setPlaceholderText("AIza...")
        self.gemini_api_key_input.setStyleSheet(self.get_input_style())
        
        # モデル選択コンボボックス
        self.gemini_model_combo = QComboBox()
        self.gemini_model_combo.addItem("汎用 (Lite) - 高速・軽量", GeminiClient.LITE_MODEL)
        self.gemini_model_combo.addItem("ハイスペック (Full) - 高精度分析", GeminiClient.FULL_MODEL)
        self.gemini_model_combo.addItem("カスタム - 手入力", "custom")
        self.gemini_model_combo.setStyleSheet(self.get_combo_style())
        self.gemini_model_combo.currentTextChanged.connect(self.on_model_selection_changed)
        
        # カスタムモデル名入力フィールド（初期は非表示）
        self.custom_model_input = QLineEdit()
        self.custom_model_input.setPlaceholderText("カスタムモデル名を入力 (例: gemini-pro)")
        self.custom_model_input.setStyleSheet(self.get_input_style())
        self.custom_model_input.setVisible(False)
        
        self.test_gemini_btn = QPushButton("🧪 Gemini 接続テスト")
        self.test_gemini_btn.setStyleSheet(self.get_button_style())
        self.test_gemini_btn.clicked.connect(self.test_gemini_connection)
        
        gemini_layout.addRow("API キー:", self.gemini_api_key_input)
        gemini_layout.addRow("モデル:", self.gemini_model_combo)
        gemini_layout.addRow("", self.custom_model_input)
        gemini_layout.addRow("", self.test_gemini_btn)
        
        # 分析指示エリア
        analysis_input_card, analysis_input_content = self.create_card("📝 分析指示")
        analysis_input_layout = QVBoxLayout(analysis_input_content)
        
        self.analysis_input = QTextEdit()
        self.analysis_input.setPlaceholderText("データについて分析したい内容を自然言語で入力してください。\n例: このデータの傾向を教えて、売上が最も高い月は？")
        self.analysis_input.setMaximumHeight(120)
        self.analysis_input.setStyleSheet(self.get_text_area_style())
        
        # 分析ボタンエリア
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(15)
        
        self.analyze_btn = QPushButton("🚀 分析実行")
        self.analyze_btn.setStyleSheet(self.get_primary_button_style())
        self.analyze_btn.clicked.connect(self.run_analysis)
        self.analyze_btn.setEnabled(False)
        
        self.auto_insights_btn = QPushButton("🌟 自動洞察生成")
        self.auto_insights_btn.setStyleSheet(self.get_button_style("#5cb85c"))
        self.auto_insights_btn.clicked.connect(self.generate_auto_insights)
        self.auto_insights_btn.setEnabled(False)
        
        self.infographic_btn = QPushButton("📊 インフォグラフィック化")
        self.infographic_btn.setStyleSheet(self.get_button_style("#f0ad4e"))
        self.infographic_btn.clicked.connect(self.create_infographic)
        self.infographic_btn.setEnabled(False)
        
        button_layout.addWidget(self.analyze_btn)
        button_layout.addWidget(self.auto_insights_btn)
        button_layout.addWidget(self.infographic_btn)
        button_layout.addStretch()
        
        analysis_input_layout.addWidget(self.analysis_input)
        analysis_input_layout.addWidget(button_widget)
        
        # 分析用プログレスバー
        self.analysis_progress_bar = ModernProgressBar()
        self.analysis_progress_bar.setVisible(False)
        
        # 分析結果カード
        result_card, result_content = self.create_card("📊 分析結果")
        result_layout = QVBoxLayout(result_content)
        
        self.analysis_result = QTextEdit()
        self.analysis_result.setReadOnly(True)
        self.analysis_result.setStyleSheet(self.get_text_area_style())
        self.analysis_result.setMinimumHeight(300)
        
        # ダウンロードボタンエリア
        download_widget = QWidget()
        download_layout = QHBoxLayout(download_widget)
        download_layout.setContentsMargins(0, 0, 0, 0)
        download_layout.setSpacing(15)
        
        self.download_analysis_btn = QPushButton("📝 分析結果ダウンロード")
        self.download_analysis_btn.setStyleSheet(self.get_button_style("#5cb85c"))
        self.download_analysis_btn.clicked.connect(self.download_analysis_result)
        self.download_analysis_btn.setEnabled(False)
        
        self.download_html_btn = QPushButton("📄 HTMLダウンロード")
        self.download_html_btn.setStyleSheet(self.get_button_style("#f0ad4e"))
        self.download_html_btn.clicked.connect(self.download_html_infographic)
        self.download_html_btn.setEnabled(False)
        
        download_layout.addWidget(self.download_analysis_btn)
        download_layout.addWidget(self.download_html_btn)
        download_layout.addStretch()
        
        result_layout.addWidget(self.analysis_result)
        result_layout.addWidget(download_widget)
        
        layout.addWidget(gemini_card)
        layout.addWidget(analysis_input_card)
        layout.addWidget(self.analysis_progress_bar)
        layout.addWidget(result_card)
        layout.addStretch()
        
        page.setWidget(page_content)
        page.setWidgetResizable(True)
        self.content_stack.addWidget(page)
    
    def create_modern_settings_page(self):
        """設定ページ"""
        page = QScrollArea()
        page_content = QWidget()
        layout = QVBoxLayout(page_content)
        layout.setSpacing(30)
        
        # 一般設定カード
        general_card, general_content = self.create_card("⚙️ 一般設定")
        general_layout = QFormLayout(general_content)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["ja", "en"])
        self.language_combo.setStyleSheet(self.get_combo_style())
        general_layout.addRow("言語:", self.language_combo)
        
        # データ設定カード
        data_card, data_content = self.create_card("💾 データ設定")
        data_layout = QFormLayout(data_content)
        
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["utf-8", "shift_jis", "cp932"])
        self.encoding_combo.setStyleSheet(self.get_combo_style())
        data_layout.addRow("CSV エンコーディング:", self.encoding_combo)
        
        # 保存ボタン
        save_btn_widget = QWidget()
        save_btn_layout = QHBoxLayout(save_btn_widget)
        save_btn_layout.setContentsMargins(0, 0, 0, 0)
        
        self.save_settings_btn = QPushButton("💾 設定保存")
        self.save_settings_btn.setStyleSheet(self.get_primary_button_style())
        self.save_settings_btn.clicked.connect(self.save_settings)
        
        save_btn_layout.addWidget(self.save_settings_btn)
        save_btn_layout.addStretch()
        
        general_layout.addRow("", save_btn_widget)
        
        # アプリ情報カード
        info_card, info_content = self.create_card("ℹ️ アプリケーション情報")
        info_layout = QVBoxLayout(info_content)
        
        info_text = QLabel("""
        <h3 style="color: #2c3e50;">NotiFetch v2.0</h3>
        <p style="color: #6c757d;">Notion データ取得・分析ツール</p>
        <br>
        <p style="color: #6c757d;"><strong>開発者:</strong> A.T</p>
        <p style="color: #6c757d;"><strong>ライセンス:</strong> MIT License</p>
        <p style="color: #6c757d;"><strong>サポート:</strong> takada@araiseimitsu.onmicrosoft.com</p>
        """)
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        layout.addWidget(general_card)
        layout.addWidget(data_card)
        layout.addWidget(info_card)
        layout.addStretch()
        
        page.setWidget(page_content)
        page.setWidgetResizable(True)
        self.content_stack.addWidget(page)
    
    def create_button(self, text, callback):
        """美しいボタンの作成"""
        btn = QPushButton(text)
        btn.setStyleSheet(self.get_button_style("#4a90e2"))
        btn.clicked.connect(callback)
        return btn
    
    def get_input_style(self):
        """入力フィールドのスタイル"""
        return """
            QLineEdit {
                border: 2px solid #e9ecef;
                border-radius: 8px;
                padding: 12px;
                background-color: white;
                color: #2c3e50;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4a90e2;
                background-color: #f8f9fa;
                color: #2c3e50;
            }
        """
    
    def get_combo_style(self):
        """コンボボックスのスタイル"""
        return """
            QComboBox {
                border: 2px solid #e9ecef;
                border-radius: 8px;
                padding: 12px;
                background-color: white;
                color: #2c3e50;
                font-size: 14px;
                min-width: 200px;
            }
            QComboBox:focus {
                border-color: #4a90e2;
                background-color: #f8f9fa;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #2c3e50;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #e9ecef;
                background-color: white;
                color: #2c3e50;
                selection-background-color: #4a90e2;
                selection-color: white;
                outline: none;
            }
        """
    
    def get_button_style(self, color="#4a90e2"):
        """ボタンのスタイル"""
        darker = self.darken_color(color)
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                           stop:0 {color}, stop:1 {darker});
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
                color: white;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                           stop:0 {darker}, stop:1 {self.darken_color(darker)});
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                           stop:0 {self.darken_color(darker)}, stop:1 {color});
            }}
            QPushButton:disabled {{
                background: #adb5bd;
                color: #6c757d;
            }}
        """
    
    def get_combo_style(self):
        """コンボボックスのスタイル"""
        return """
            QComboBox {
                border: 2px solid #e9ecef;
                border-radius: 8px;
                padding: 12px;
                background-color: white;
                color: #2c3e50;
                font-size: 14px;
                min-width: 150px;
            }
            QComboBox:focus {
                border-color: #4a90e2;
                color: #2c3e50;
            }
            QComboBox::drop-down {
                border: none;
                background-color: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #2c3e50;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                selection-background-color: #4a90e2;
                selection-color: white;
                color: #2c3e50;
            }
            QComboBox QAbstractItemView::item {
                color: #2c3e50;
                padding: 8px;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #4a90e2;
                color: white;
            }
        """
    
    def get_text_area_style(self):
        """テキストエリアのスタイル"""
        return """
            QTextEdit {
                border: 2px solid #e9ecef;
                border-radius: 8px;
                padding: 12px;
                background-color: white;
                color: #2c3e50;
                font-size: 14px;
                line-height: 1.6;
            }
            QTextEdit:focus {
                border-color: #4a90e2;
                background-color: #f8f9fa;
                color: #2c3e50;
            }
        """
    
    def get_table_style(self):
        """テーブルのスタイル"""
        return """
            QTableWidget {
                background-color: white;
                alternate-background-color: #f8f9fa;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                gridline-color: #dee2e6;
                selection-background-color: #4a90e2;
                selection-color: white;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #4a90e2;
                color: white;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                           stop:0 #4a90e2, stop:1 #357abd);
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
            QScrollBar:vertical {
                background: #f8f9fa;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #adb5bd;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6c757d;
            }
        """
    
    def get_primary_button_style(self):
        """プライマリボタンのスタイル"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                           stop:0 #4a90e2, stop:0.5 #5cb85c, stop:1 #4a90e2);
                border: none;
                padding: 15px 25px;
                border-radius: 10px;
                color: white;
                font-size: 16px;
                font-weight: bold;
                min-width: 150px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                           stop:0 #357abd, stop:0.5 #449d44, stop:1 #357abd);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                           stop:0 #2968a3, stop:0.5 #398439, stop:1 #2968a3);
            }
        """
    
    def get_icon_button_style(self):
        """アイコンボタンのスタイル"""
        return """
            QPushButton {
                background: #f8f9fa;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                color: #6c757d;
                font-size: 16px;
            }
            QPushButton:hover {
                background: #4a90e2;
                border-color: #4a90e2;
                color: white;
            }
        """
    
    def darken_color(self, color):
        """色を暗くする"""
        color_map = {
            "#4a90e2": "#357abd",
            "#5cb85c": "#449d44", 
            "#f0ad4e": "#ec971f",
            "#d9534f": "#c9302c",
            "#357abd": "#2968a3",
            "#449d44": "#398439",
            "#ec971f": "#d58512",
            "#c9302c": "#ac2925"
        }
        return color_map.get(color, color)
    
    def update_data_stats(self):
        """データ統計を更新"""
        try:
            if self.current_data is not None and not self.current_data.empty:
                rows = len(self.current_data)
                cols = len(self.current_data.columns)
                
                # データサイズを計算（概算）
                try:
                    size_bytes = self.current_data.memory_usage(deep=True).sum()
                    if size_bytes < 1024:
                        size_str = f"{size_bytes} B"
                    elif size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes / 1024:.1f} KB"
                    else:
                        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                except Exception as e:
                    logger.warning(f"メモリ使用量計算エラー: {e}")
                    size_str = "不明"
                
                # カードの存在確認と更新
                if hasattr(self, 'rows_card') and hasattr(self.rows_card, 'value_label'):
                    self.rows_card.value_label.setText(f"{rows:,}")
                    # 3行目：データタイプと範囲情報
                    if hasattr(self.rows_card, 'desc_label'):
                        non_null_percentage = ((self.current_data.count().sum() / (rows * cols)) * 100) if rows > 0 and cols > 0 else 0
                        self.rows_card.desc_label.setText(f"データ完全性: {non_null_percentage:.1f}% | インデックス: 0-{rows-1}")
                
                if hasattr(self, 'columns_card') and hasattr(self.columns_card, 'value_label'):
                    self.columns_card.value_label.setText(str(cols))
                    # 3行目：列のデータタイプ情報
                    if hasattr(self.columns_card, 'desc_label') and cols > 0:
                        dtypes_info = self.current_data.dtypes.value_counts()
                        main_types = []
                        for dtype, count in dtypes_info.head(2).items():
                            dtype_name = str(dtype).replace('object', 'テキスト').replace('int64', '整数').replace('float64', '小数')
                            main_types.append(f"{dtype_name}:{count}")
                        self.columns_card.desc_label.setText(f"主なタイプ: {', '.join(main_types)}")
                
                if hasattr(self, 'size_card') and hasattr(self.size_card, 'value_label'):
                    self.size_card.value_label.setText(size_str)
                    # 3行目：メモリ効率とファイルサイズ推定
                    if hasattr(self.size_card, 'desc_label'):
                        avg_row_size = size_bytes / rows if rows > 0 else 0
                        estimated_csv_size = size_bytes * 1.5  # CSV推定サイズ
                        if estimated_csv_size < 1024 * 1024:
                            csv_size_str = f"{estimated_csv_size / 1024:.0f}KB"
                        else:
                            csv_size_str = f"{estimated_csv_size / (1024 * 1024):.1f}MB"
                        self.size_card.desc_label.setText(f"行平均: {avg_row_size:.0f}B | CSV推定: {csv_size_str}")
                
                if hasattr(self, 'status_card') and hasattr(self.status_card, 'value_label'):
                    self.status_card.value_label.setText("完了")
                    # 3行目：取得時刻と処理時間
                    if hasattr(self.status_card, 'desc_label'):
                        from datetime import datetime
                        current_time = datetime.now().strftime("%H:%M:%S")
                        self.status_card.desc_label.setText(f"取得完了: {current_time} | 最新データ")
                    
                    # ステータスカードの色を緑に変更
                    self.status_card.color = "#5cb85c"
                    darker_color = self.darken_color("#5cb85c")
                    self.status_card.setStyleSheet(f"""
                        QFrame {{
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                       stop:0 #5cb85c, stop:1 {darker_color});
                            border: none;
                            border-radius: 18px;
                            color: white;
                        }}
                        QFrame:hover {{
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                       stop:0 {darker_color}, stop:1 {self.darken_color(darker_color)});
                        }}
                    """)
            else:
                # データがない場合のリセット
                if hasattr(self, 'rows_card') and hasattr(self.rows_card, 'value_label'):
                    self.rows_card.value_label.setText("0")
                    if hasattr(self.rows_card, 'desc_label'):
                        self.rows_card.desc_label.setText("データが取得されていません")
                
                if hasattr(self, 'columns_card') and hasattr(self.columns_card, 'value_label'):
                    self.columns_card.value_label.setText("0")
                    if hasattr(self.columns_card, 'desc_label'):
                        self.columns_card.desc_label.setText("フィールド情報なし")
                
                if hasattr(self, 'size_card') and hasattr(self.size_card, 'value_label'):
                    self.size_card.value_label.setText("0 KB")
                    if hasattr(self.size_card, 'desc_label'):
                        self.size_card.desc_label.setText("メモリ使用量なし")
                
                if hasattr(self, 'status_card') and hasattr(self.status_card, 'value_label'):
                    self.status_card.value_label.setText("待機中")
                    if hasattr(self.status_card, 'desc_label'):
                        self.status_card.desc_label.setText("データ取得を開始してください")
                    
                    # ステータスカードの色を赤に戻す
                    self.status_card.color = "#d9534f"
                    darker_color = self.darken_color("#d9534f")
                    self.status_card.setStyleSheet(f"""
                        QFrame {{
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                       stop:0 #d9534f, stop:1 {darker_color});
                            border: none;
                            border-radius: 18px;
                            color: white;
                        }}
                        QFrame:hover {{
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                       stop:0 {darker_color}, stop:1 {self.darken_color(darker_color)});
                        }}
                    """)
                    
            logger.info("データ統計を更新しました")
        except Exception as e:
            logger.error(f"データ統計更新エラー: {e}")
            # エラー時のフォールバック表示
            if hasattr(self, 'status_card') and hasattr(self.status_card, 'value_label'):
                self.status_card.value_label.setText("エラー")
                if hasattr(self.status_card, 'desc_label'):
                    self.status_card.desc_label.setText(f"統計更新エラー: {str(e)[:30]}...")
    
    def load_settings(self):
        """設定の読み込み"""
        try:
            # API設定の読み込み
            notion_token = self.settings.get_notion_token()
            if notion_token:
                self.notion_token_input.setText(notion_token)
            
            gemini_key = self.settings.get_gemini_api_key()
            if gemini_key:
                self.gemini_api_key_input.setText(gemini_key)
            
            # Geminiモデル設定の読み込み
            saved_model = self.settings.get_gemini_model_name()
            self.set_model_combo_selection(saved_model)
            
            # 最後のページIDの読み込み
            last_page_id = self.settings.get_last_page_id()
            if last_page_id:
                self.page_id_input.setText(last_page_id)
            
            # UI設定の読み込み
            language = self.settings.get_ui_setting("language", "ja")
            self.language_combo.setCurrentText(language)
            
            encoding = self.settings.get_ui_setting("csv_encoding", "utf-8")
            self.encoding_combo.setCurrentText(encoding)
            
            logger.info("設定を読み込みました")
        except Exception as e:
            logger.error(f"設定読み込みエラー: {e}")
    
    def save_settings(self):
        """設定の保存"""
        try:
            # API設定の保存
            self.settings.set_notion_token(self.notion_token_input.text())
            self.settings.set_gemini_api_key(self.gemini_api_key_input.text())
            self.settings.set_gemini_model_name(self.get_selected_model_name())
            self.settings.set_last_page_id(self.page_id_input.text())
            
            # UI設定の保存
            self.settings.set_ui_setting("language", self.language_combo.currentText())
            self.settings.set_ui_setting("csv_encoding", self.encoding_combo.currentText())
            
            QMessageBox.information(self, "設定保存", "設定が正常に保存されました。")
            logger.info("設定を保存しました")
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
            QMessageBox.critical(self, "エラー", f"設定の保存に失敗しました: {e}")
    
    def apply_theme(self):
        """モダンライトテーマの適用"""
        # グローバルスタイルシート
        global_style = """
        /* アプリケーション全体のテーマ */
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                       stop:0 #f8f9fa, stop:1 #e9ecef);
            color: #2c3e50;
        }
        
        /* ラベル */
        QLabel {
            color: #2c3e50;
        }
        
        /* メッセージボックスのスタイル */
        QMessageBox {
            background-color: white;
            color: #2c3e50;
            border-radius: 12px;
        }
        QMessageBox QLabel {
            color: #2c3e50;
            background-color: transparent;
            font-size: 14px;
        }
        QMessageBox QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #4a90e2, stop:1 #357abd);
            border: none;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: bold;
            min-width: 100px;
        }
        QMessageBox QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #357abd, stop:1 #2968a3);
        }
        
        /* ステータスバー */
        QStatusBar {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                       stop:0 white, stop:1 #f8f9fa);
            color: #2c3e50;
            border-top: 1px solid #dee2e6;
            padding: 5px;
            font-size: 12px;
        }
        
        /* スクロールエリア */
        QScrollArea {
            background: transparent;
            border: none;
            color: #2c3e50;
        }
        QScrollArea > QWidget > QWidget {
            background: transparent;
            color: #2c3e50;
        }
        
        /* フォームレイアウト内のラベル */
        QFormLayout QLabel {
            color: #2c3e50;
            font-weight: 500;
            font-size: 14px;
        }
        
        /* ダイアログ */
        QDialog {
            background-color: white;
            border-radius: 12px;
            color: #2c3e50;
        }
        
        QDialog QLabel {
            color: #2c3e50;
            background-color: transparent;
        }
        
        QDialog QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #4a90e2, stop:1 #357abd);
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            font-weight: bold;
            min-width: 80px;
        }
        
        QDialog QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #357abd, stop:1 #2968a3);
        }
        
        /* リストウィジェット */
        QListWidget {
            background-color: white;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            selection-background-color: #4a90e2;
            selection-color: white;
            color: #2c3e50;
        }
        QListWidget::item {
            padding: 8px;
            border-bottom: 1px solid #f1f3f4;
            color: #2c3e50;
        }
        QListWidget::item:hover {
            background-color: #f8f9fa;
            color: #2c3e50;
        }
        QListWidget::item:selected {
            background-color: #4a90e2;
            color: white;
        }
        
        /* メニュー */
        QMenu {
            background-color: white;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 5px;
            color: #2c3e50;
        }
        QMenu::item {
            padding: 8px 20px;
            border-radius: 4px;
            color: #2c3e50;
        }
        QMenu::item:selected {
            background-color: #4a90e2;
            color: white;
        }
        
        /* ファイルダイアログ */
        QFileDialog {
            background-color: white;
            color: #2c3e50;
        }
        
        QFileDialog QLabel {
            color: #2c3e50;
        }
        
        QFileDialog QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                       stop:0 #4a90e2, stop:1 #357abd);
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            font-weight: bold;
        }
        
        QFileDialog QTreeView {
            color: #2c3e50;
            background-color: white;
        }
        
        QFileDialog QTreeView::item {
            color: #2c3e50;
        }
        
        QFileDialog QListView {
            color: #2c3e50;
            background-color: white;
        }
        
        QFileDialog QListView::item {
            color: #2c3e50;
        }
        
        /* 入力ダイアログ */
        QInputDialog {
            background-color: white;
            color: #2c3e50;
        }
        
        QInputDialog QLabel {
            color: #2c3e50;
        }
        
        QInputDialog QLineEdit {
            color: #2c3e50;
            background-color: white;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            padding: 8px;
        }
        
        /* プッシュボタン（一般） */
        QPushButton {
            color: white;
        }
        
        QPushButton:disabled {
            color: #6c757d;
        }
        
        /* グループボックス */
        QGroupBox {
            font-weight: bold;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            margin-top: 1ex;
            background-color: white;
            color: #2c3e50;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #2c3e50;
            background-color: white;
        }
        
        /* フレーム（カード） */
        QFrame {
            background-color: white;
            color: #2c3e50;
        }
        """
        
        self.setStyleSheet(global_style)
        logger.info("モダンライトテーマを適用しました")
    
    def test_notion_connection(self):
        """Notion接続テスト"""
        token = self.notion_token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "APIトークンを入力してください。")
            return
        
        try:
            self.notion_client = NotionClient(token)
            if self.notion_client.test_connection():
                QMessageBox.information(self, "成功", "✅ Notion APIに正常に接続されました。")
                self.status_bar.showMessage("🔗 Notion API 接続成功")
            else:
                QMessageBox.critical(self, "エラー", "❌ Notion APIに接続できませんでした。")
                self.status_bar.showMessage("Notion API 接続失敗")
        except Exception as e:
            logger.error(f"接続テストエラー: {e}")
            QMessageBox.critical(self, "エラー", f"❌ 接続テストに失敗しました:\n{e}")
    
    def on_model_selection_changed(self, text):
        """モデル選択が変更された時の処理"""
        # カスタム選択時はテキスト入力フィールドを表示、それ以外は非表示
        if "カスタム" in text:
            self.custom_model_input.setVisible(True)
        else:
            self.custom_model_input.setVisible(False)
    
    def get_selected_model_name(self):
        """選択されたモデル名を取得"""
        current_data = self.gemini_model_combo.currentData()
        if current_data == "custom":
            # カスタムモデル名を返す
            custom_name = self.custom_model_input.text().strip()
            return custom_name if custom_name else GeminiClient.LITE_MODEL
        else:
            # プリセットモデル名を返す
            return current_data
    
    def set_model_combo_selection(self, model_name):
        """保存されたモデル名に基づいてコンボボックスの選択を設定"""
        # プリセットモデルかどうかをチェック
        if model_name == GeminiClient.LITE_MODEL:
            self.gemini_model_combo.setCurrentIndex(0)
        elif model_name == GeminiClient.FULL_MODEL:
            self.gemini_model_combo.setCurrentIndex(1)
        else:
            # カスタムモデルの場合
            self.gemini_model_combo.setCurrentIndex(2)
            self.custom_model_input.setText(model_name)
            self.custom_model_input.setVisible(True)

    def test_gemini_connection(self):
        """Gemini接続テスト"""
        api_key = self.gemini_api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "警告", "Gemini APIキーを入力してください。")
            return
        
        try:
            # 選択されたモデル名を取得
            model_name = self.get_selected_model_name()
            self.gemini_client = GeminiClient(api_key, model_name)
            if self.gemini_client.test_connection():
                QMessageBox.information(self, "成功", f"✅ Gemini APIに正常に接続されました。\n使用モデル: {model_name}")
                self.status_bar.showMessage(f"🤖 Gemini API 接続成功 ({model_name})")
                # 分析ボタンを有効化
                if self.current_data is not None and not self.current_data.empty:
                    self.analyze_btn.setEnabled(True)
                    self.auto_insights_btn.setEnabled(True)
                    self.infographic_btn.setEnabled(True)
            else:
                QMessageBox.critical(self, "エラー", "❌ Gemini APIに接続できませんでした。")
                self.status_bar.showMessage("Gemini API 接続失敗")
        except Exception as e:
            logger.error(f"Gemini接続テストエラー: {e}")
            QMessageBox.critical(self, "エラー", f"❌ Gemini接続テストに失敗しました:\n{e}")
    
    def validate_page_id(self):
        """ページID検証"""
        page_id = self.page_id_input.text().strip()
        if not page_id:
            QMessageBox.warning(self, "警告", "ページIDを入力してください。")
            return
        
        if not self.notion_client:
            QMessageBox.warning(self, "警告", "まずNotion APIに接続してください。")
            return
        
        try:
            validation_result = self.notion_client.validate_page_id(page_id)
            
            if validation_result["valid"]:
                # 成功：ページまたはデータベースが見つかった
                page_info = self.notion_client.get_page_info(page_id)
                if page_info:
                    # 履歴に追加
                    self.settings.add_page_to_history(page_info)
                    
                    info_text = f"タイプ: {page_info['type'].upper()}\n"
                    info_text += f"タイトル: {page_info['title']}\n"
                    info_text += f"作成日時: {page_info['created_time']}\n"
                    info_text += f"更新日時: {page_info['last_edited_time']}\n"
                    info_text += f"URL: {page_info['url']}"
                    self.page_info_text.setText(info_text)
                    
                    # 編集ボタンを有効化
                    self.edit_page_btn.setEnabled(True)
                
                success_message = f"✅ {validation_result['message']}\n"
                success_message += f"タイプ: {validation_result['type'].upper()}"
                QMessageBox.information(self, "検証成功", success_message)
                self.status_bar.showMessage(f"ページID検証成功 - {validation_result['type']}")
                
            else:
                # 失敗：詳細な理由を表示
                self.page_info_text.clear()
                self.edit_page_btn.setEnabled(False)
                
                if validation_result["error_code"] == "not_found":
                    # ページが存在しない（正常な状況）
                    warning_message = "ℹ️ 指定されたページまたはデータベースが見つかりませんでした。\n\n"
                    warning_message += "確認事項:\n"
                    warning_message += "• ページIDまたはURLが正しいか確認してください\n"
                    warning_message += "• ページが削除されていないか確認してください\n"
                    warning_message += "• URLをコピーした場合は、ページIDのみを入力してみてください"
                    
                    QMessageBox.information(self, "ページが見つかりません", warning_message)
                    self.status_bar.showMessage("ページが見つかりません")
                    
                elif validation_result["error_code"] == "access_denied":
                    # アクセス権限がない
                    warning_message = "🔒 ページまたはデータベースにアクセスする権限がありません。\n\n"
                    warning_message += "確認事項:\n"
                    warning_message += "• Notionインテグレーションがページに招待されているか確認してください\n"
                    warning_message += "• ワークスペースの管理者に権限を確認してください\n"
                    warning_message += "• 正しいAPIトークンを使用しているか確認してください"
                    
                    QMessageBox.warning(self, "アクセス権限エラー", warning_message)
                    self.status_bar.showMessage("アクセス権限がありません")
                    
                elif validation_result["error_code"] == "client_not_ready":
                    # APIクライアントの問題
                    QMessageBox.warning(self, "接続エラー", validation_result["message"])
                    self.status_bar.showMessage("API接続エラー")
                    
                else:
                    # その他のエラー
                    error_message = f"❌ {validation_result['message']}\n\n"
                    if validation_result["error_code"]:
                        error_message += f"エラーコード: {validation_result['error_code']}"
                    
                    QMessageBox.critical(self, "検証エラー", error_message)
                    self.status_bar.showMessage("ページID検証エラー")
                    
        except Exception as e:
            logger.error(f"ページID検証エラー: {e}")
            QMessageBox.critical(self, "エラー", f"ページID検証中に予期しないエラーが発生しました:\n{e}")
            self.page_info_text.clear()
            self.status_bar.showMessage("ページID検証失敗")
            self.edit_page_btn.setEnabled(False)
    
    def show_page_history(self):
        """ページ履歴ダイアログを表示"""
        dialog = QDialog(self)
        dialog.setWindowTitle("ページ履歴")
        dialog.setModal(True)
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # 履歴リスト
        history_list = QListWidget()
        history = self.settings.get_page_history()
        
        if not history:
            item = QListWidgetItem("履歴がありません")
            item.setData(Qt.UserRole, None)
            history_list.addItem(item)
        else:
            for page_info in history:
                title = page_info.get("title", "無題")
                type_str = page_info.get("type", "unknown").upper()
                last_accessed = page_info.get("last_accessed", "")
                
                item_text = f"[{type_str}] {title}\n最終アクセス: {last_accessed}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, page_info)
                history_list.addItem(item)
        
        # 右クリックメニューの設定
        history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        history_list.customContextMenuRequested.connect(
            lambda pos: self.show_history_context_menu(history_list, pos)
        )
        
        layout.addWidget(QLabel("保存された履歴:"))
        layout.addWidget(history_list)
        
        # ボタンレイアウト
        button_layout = QHBoxLayout()
        
        select_btn = QPushButton("選択")
        copy_id_btn = QPushButton("IDをコピー")
        copy_url_btn = QPushButton("URLをコピー")
        clear_btn = QPushButton("履歴クリア")
        close_btn = QPushButton("閉じる")
        
        # ボタンイベント
        def select_item():
            current_item = history_list.currentItem()
            if current_item and current_item.data(Qt.UserRole):
                page_info = current_item.data(Qt.UserRole)
                self.page_id_input.setText(page_info["id"])
                dialog.accept()
        
        def copy_id():
            current_item = history_list.currentItem()
            if current_item and current_item.data(Qt.UserRole):
                page_info = current_item.data(Qt.UserRole)
                clipboard = QApplication.clipboard()
                clipboard.setText(page_info["id"])
                self.status_bar.showMessage("ページIDをクリップボードにコピーしました", 2000)
        
        def copy_url():
            current_item = history_list.currentItem()
            if current_item and current_item.data(Qt.UserRole):
                page_info = current_item.data(Qt.UserRole)
                clipboard = QApplication.clipboard()
                clipboard.setText(page_info["url"])
                self.status_bar.showMessage("URLをクリップボードにコピーしました", 2000)
        
        def clear_history():
            reply = QMessageBox.question(
                dialog, "確認", "履歴をすべて削除しますか？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.settings.clear_page_history()
                dialog.accept()
                self.status_bar.showMessage("履歴をクリアしました", 2000)
        
        select_btn.clicked.connect(select_item)
        copy_id_btn.clicked.connect(copy_id)
        copy_url_btn.clicked.connect(copy_url)
        clear_btn.clicked.connect(clear_history)
        close_btn.clicked.connect(dialog.reject)
        
        # ダブルクリックで選択
        history_list.itemDoubleClicked.connect(lambda: select_item())
        
        button_layout.addWidget(select_btn)
        button_layout.addWidget(copy_id_btn)
        button_layout.addWidget(copy_url_btn)
        button_layout.addStretch()
        button_layout.addWidget(clear_btn)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def show_history_context_menu(self, list_widget, position):
        """履歴リストの右クリックメニュー"""
        item = list_widget.itemAt(position)
        if not item or not item.data(Qt.UserRole):
            return
        
        menu = QMenu(self)
        
        select_action = QAction("選択", self)
        copy_id_action = QAction("IDをコピー", self)
        copy_url_action = QAction("URLをコピー", self)
        edit_action = QAction("編集", self)
        delete_action = QAction("履歴から削除", self)
        
        page_info = item.data(Qt.UserRole)
        
        select_action.triggered.connect(lambda: self.page_id_input.setText(page_info["id"]))
        copy_id_action.triggered.connect(lambda: self.copy_to_clipboard(page_info["id"], "ページID"))
        copy_url_action.triggered.connect(lambda: self.copy_to_clipboard(page_info["url"], "URL"))
        edit_action.triggered.connect(lambda: self.edit_page_from_history(page_info))
        delete_action.triggered.connect(lambda: self.delete_from_history(page_info["id"], list_widget))
        
        menu.addAction(select_action)
        menu.addSeparator()
        menu.addAction(copy_id_action)
        menu.addAction(copy_url_action)
        menu.addSeparator()
        menu.addAction(edit_action)
        menu.addAction(delete_action)
        
        menu.exec(list_widget.mapToGlobal(position))
    
    def copy_to_clipboard(self, text, label):
        """テキストをクリップボードにコピー"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.status_bar.showMessage(f"{label}をクリップボードにコピーしました", 2000)
    
    def delete_from_history(self, page_id, list_widget):
        """履歴から項目を削除"""
        reply = QMessageBox.question(
            self, "確認", "この項目を履歴から削除しますか？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.settings.remove_page_from_history(page_id)
            # リストウィジェットを更新
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item.data(Qt.UserRole) and item.data(Qt.UserRole)["id"] == page_id:
                    list_widget.takeItem(i)
                    break
            self.status_bar.showMessage("履歴から削除しました", 2000)
    
    def edit_page_from_history(self, page_info):
        """履歴からページを編集"""
        self.page_id_input.setText(page_info["id"])
        self.edit_current_page()
    
    def edit_current_page(self):
        """現在のページを編集（NotionのWebページを開く）"""
        page_id = self.page_id_input.text().strip()
        if not page_id:
            QMessageBox.warning(self, "警告", "ページIDを入力してください。")
            return
        
        if not self.notion_client:
            QMessageBox.warning(self, "警告", "まずNotion APIに接続してください。")
            return
        
        try:
            # ページ情報を取得してURLを取得
            page_info = self.notion_client.get_page_info(page_id)
            if page_info and page_info.get("url"):
                webbrowser.open(page_info["url"])
                self.status_bar.showMessage("Notionページを開きました", 2000)
            else:
                QMessageBox.warning(self, "エラー", "ページのURLを取得できませんでした。")
        except Exception as e:
            logger.error(f"ページ編集エラー: {e}")
            QMessageBox.critical(self, "エラー", f"ページを開くことができませんでした: {e}")
    
    def on_fetch_limit_changed(self, text):
        """取得行数選択変更時の処理"""
        if text == "カスタム":
            self.custom_limit_input.setVisible(True)
        else:
            self.custom_limit_input.setVisible(False)
    
    def get_fetch_limit(self):
        """設定された取得行数を取得"""
        limit_text = self.fetch_limit_combo.currentText()
        
        if limit_text == "すべて":
            return None  # 制限なし
        elif limit_text == "カスタム":
            try:
                custom_limit = int(self.custom_limit_input.text().strip())
                return max(1, custom_limit)  # 最低1行
            except (ValueError, AttributeError):
                QMessageBox.warning(self, "警告", "有効な数値を入力してください。")
                return None
        else:
            # "100行" -> 100 のように変換
            return int(limit_text.replace("行", ""))
    
    def fetch_data(self):
        """データ取得"""
        page_id = self.page_id_input.text().strip()
        if not page_id:
            QMessageBox.warning(self, "警告", "ページIDを入力してください。")
            return
        
        if not self.notion_client:
            QMessageBox.warning(self, "警告", "まずNotion APIに接続してください。")
            return
        
        # 取得行数制限を取得
        fetch_limit = self.get_fetch_limit()
        if fetch_limit is None and self.fetch_limit_combo.currentText() == "カスタム":
            return  # カスタムで無効な値の場合は処理を中断
        
        # プログレス管理用の変数
        self.current_progress = 0
        
        def update_progress(message, progress_value=None):
            """プログレス更新用コールバック"""
            if progress_value is not None:
                self.current_progress = progress_value
                self.progress_bar.setValue(self.current_progress)
            
            self.status_bar.showMessage(message)
            QApplication.processEvents()
        
        try:
            # UIを即座に更新
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 100)  # 0-100%のプログレスバー
            self.progress_bar.setValue(0)
            self.fetch_data_btn.setEnabled(False)
            
            update_progress("データ取得準備中...", 5)
            
            # データベースかページかを判定
            update_progress("ページ/データベースの種類を判定中...", 15)
            
            if self.notion_client.is_database(page_id):
                # データベースの場合
                update_progress("データベースからデータを取得中...", 30)
                
                # プログレス更新のカスタムコールバック
                def notion_progress_callback(message):
                    if "データ取得中" in message:
                        # 取得中は30-70%の範囲で更新
                        current_val = min(70, self.current_progress + 5)
                        update_progress(message, current_val)
                    else:
                        update_progress(message)
                
                raw_data = self.notion_client.get_database_data(
                    page_id, 
                    progress_callback=notion_progress_callback,
                    limit=fetch_limit
                )
                
                update_progress("データベースデータを変換中...", 75)
                
                self.current_data = DataConverter.convert_database_to_dataframe(raw_data)
            else:
                # ページの場合
                update_progress("ページからコンテンツを取得中...", 30)
                
                # プログレス更新のカスタムコールバック
                def notion_progress_callback(message):
                    if "ページコンテンツ取得中" in message:
                        current_val = min(70, self.current_progress + 5)
                        update_progress(message, current_val)
                    else:
                        update_progress(message)
                
                raw_data = self.notion_client.get_page_content(
                    page_id,
                    progress_callback=notion_progress_callback
                )
                
                update_progress("ページデータを変換中...", 75)
                
                self.current_data = DataConverter.convert_blocks_to_dataframe(raw_data)
                
                # ページの場合は後で行数制限を適用
                if fetch_limit is not None:
                    self.current_data = self.current_data.head(fetch_limit)
            
            # データ表示処理
            update_progress("データを表示中...", 85)
            
            self.display_data(self.current_data)
            self.display_summary(self.current_data)
            
            # エクスポートボタンを有効化
            self.export_csv_btn.setEnabled(True)
            self.export_excel_btn.setEnabled(True)
            
            # Gemini APIが接続されている場合は分析ボタンも有効化
            if self.gemini_client and self.gemini_client.is_connected:
                self.analyze_btn.setEnabled(True)
                self.auto_insights_btn.setEnabled(True)
                self.infographic_btn.setEnabled(True)
            
            # 完了時のプログレス
            update_progress("データ取得完了", 100)
            
            # 成功メッセージに取得行数情報を追加
            data_count = len(self.current_data)
            limit_info = f" (制限: {fetch_limit}行)" if fetch_limit else ""
            
            # 少し待ってからプログレスバーを非表示にして成功メッセージを表示
            QTimer.singleShot(500, lambda: [
                self.progress_bar.setVisible(False),
                QMessageBox.information(self, "成功", f"{data_count} 件のデータを取得しました。{limit_info}")
            ])
            
        except Exception as e:
            logger.error(f"データ取得エラー: {e}")
            # エラー時もプログレスバーを非表示
            self.progress_bar.setVisible(False)
            QApplication.processEvents()
            
            QMessageBox.critical(self, "エラー", f"データ取得に失敗しました: {e}")
            self.status_bar.showMessage("データ取得失敗")
        finally:
            # 最終的にUIを復元
            self.fetch_data_btn.setEnabled(True)
            QApplication.processEvents()
    
    def display_data(self, dataframe):
        """データテーブルに表示"""
        if dataframe.empty:
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
            return
        
        # テーブルの設定
        self.data_table.setRowCount(min(len(dataframe), 1000))  # 最大1000行まで表示
        self.data_table.setColumnCount(len(dataframe.columns))
        self.data_table.setHorizontalHeaderLabels(dataframe.columns.tolist())
        
        # データの挿入
        for i in range(min(len(dataframe), 1000)):
            for j, column in enumerate(dataframe.columns):
                value = str(dataframe.iloc[i, j])
                item = QTableWidgetItem(value)
                self.data_table.setItem(i, j, item)
        
        # 統計カードの更新
        self.update_data_stats()
    
    def display_summary(self, dataframe):
        """データ概要の表示"""
        summary = DataConverter.generate_summary(dataframe)
        
        summary_text = f"📊 **データ概要**\n"
        summary_text += f"├ 行数: {summary['rows']:,}\n"
        summary_text += f"├ 列数: {summary['columns']}\n"
        summary_text += f"└ メモリ使用量: {summary['memory_usage']}\n\n"
        
        if len(dataframe) > 1000:
            summary_text += "⚠️ **注意**: プレビューでは最初の1,000行のみ表示されています\n\n"
        
        summary_text += "📋 **列情報**:\n"
        for col, info in summary['column_info'].items():
            percentage = (info['non_null_count'] / summary['rows']) * 100
            summary_text += f"├ {col}: {info['non_null_count']}/{summary['rows']} ({percentage:.1f}%)\n"
        
        self.data_summary_text.setText(summary_text)
    
    def export_csv(self):
        """CSV エクスポート"""
        if self.current_data is None or self.current_data.empty:
            QMessageBox.warning(self, "警告", "エクスポートするデータがありません。")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "CSV ファイルを保存", "notion_data.csv", "CSV files (*.csv)"
        )
        
        if file_path:
            encoding = self.encoding_combo.currentText()
            if DataConverter.save_to_csv(self.current_data, Path(file_path), encoding):
                QMessageBox.information(self, "成功", f"✅ CSVファイルを保存しました:\n{file_path}")
            else:
                QMessageBox.critical(self, "エラー", "❌ CSVファイルの保存に失敗しました。")
    
    def export_excel(self):
        """Excel エクスポート"""
        if self.current_data is None or self.current_data.empty:
            QMessageBox.warning(self, "警告", "エクスポートするデータがありません。")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Excel ファイルを保存", "notion_data.xlsx", "Excel files (*.xlsx)"
        )
        
        if file_path:
            if DataConverter.save_to_excel(self.current_data, Path(file_path)):
                QMessageBox.information(self, "成功", f"✅ Excelファイルを保存しました:\n{file_path}")
            else:
                QMessageBox.critical(self, "エラー", "❌ Excelファイルの保存に失敗しました。")
    
    def run_analysis(self):
        """AI分析実行"""
        analysis_text = self.analysis_input.toPlainText().strip()
        
        if not analysis_text:
            QMessageBox.warning(self, "警告", "分析指示を入力してください。")
            return
        
        if not self.gemini_client or not self.gemini_client.is_connected:
            QMessageBox.warning(self, "警告", "まずGemini APIに接続してください。")
            return
        
        if self.current_data is None or self.current_data.empty:
            QMessageBox.warning(self, "警告", "分析するデータがありません。")
            return
        
        # プログレス管理用の変数
        self.current_progress = 0
        
        def update_progress(message, progress_value=None):
            """プログレス更新用コールバック"""
            if progress_value is not None:
                self.current_progress = progress_value
                self.analysis_progress_bar.setValue(self.current_progress)
            
            self.status_bar.showMessage(message)
            self.analysis_result.setText(f"{message}\nしばらくお待ちください...")
            QApplication.processEvents()
        
        try:
            # UIを即座に更新
            self.analysis_progress_bar.setVisible(True)
            self.analysis_progress_bar.setRange(0, 100)  # 0-100%のプログレスバー
            self.analysis_progress_bar.setValue(0)
            self.analyze_btn.setEnabled(False)
            self.auto_insights_btn.setEnabled(False)
            
            update_progress("AI分析を開始中...", 10)
            
            # プログレス更新のカスタムコールバック
            def gemini_progress_callback(message):
                if "データ概要を生成中" in message:
                    update_progress(message, 25)
                elif "サンプルデータを準備中" in message:
                    update_progress(message, 40)
                elif "分析プロンプトを構築中" in message:
                    update_progress(message, 60)
                elif "Gemini AIで分析実行中" in message:
                    update_progress(message, 80)
                else:
                    update_progress(message)
            
            # Gemini APIで分析実行（プログレス更新付き）
            result = self.gemini_client.analyze_data(
                self.current_data, 
                analysis_text,
                progress_callback=gemini_progress_callback
            )
            
            # 完了時のプログレス
            update_progress("分析結果を表示中...", 95)
            
            # プログレスバーを非表示にしてから結果表示
            self.analysis_progress_bar.setValue(100)
            QApplication.processEvents()
            
            if result:
                self.analysis_result.setText(result)
                self.status_bar.showMessage("AI分析完了")
                # 分析結果ダウンロードボタンを有効化
                self.download_analysis_btn.setEnabled(True)
            else:
                self.analysis_result.setText("分析に失敗しました。")
                self.status_bar.showMessage("AI分析失敗")
                self.download_analysis_btn.setEnabled(False)
            
            # 少し待ってからプログレスバーを非表示
            QTimer.singleShot(500, lambda: self.analysis_progress_bar.setVisible(False))
                
        except Exception as e:
            logger.error(f"AI分析エラー: {e}")
            # エラー時もプログレスバーを非表示
            self.analysis_progress_bar.setVisible(False)
            QApplication.processEvents()
            
            self.analysis_result.setText(f"分析中にエラーが発生しました: {e}")
            QMessageBox.critical(self, "エラー", f"AI分析に失敗しました: {e}")
            self.download_analysis_btn.setEnabled(False)
        finally:
            # 最終的にUIを復元
            self.analyze_btn.setEnabled(True)
            self.auto_insights_btn.setEnabled(True)
            QApplication.processEvents()
    
    def generate_auto_insights(self):
        """自動洞察生成"""
        if not self.gemini_client or not self.gemini_client.is_connected:
            QMessageBox.warning(self, "警告", "まずGemini APIに接続してください。")
            return
        
        if self.current_data is None or self.current_data.empty:
            QMessageBox.warning(self, "警告", "分析するデータがありません。")
            return
        
        # プログレス管理用の変数
        self.current_progress = 0
        
        def update_progress(message, progress_value=None):
            """プログレス更新用コールバック"""
            if progress_value is not None:
                self.current_progress = progress_value
                self.analysis_progress_bar.setValue(self.current_progress)
            
            self.status_bar.showMessage(message)
            self.analysis_result.setText(f"{message}\nしばらくお待ちください...")
            QApplication.processEvents()
        
        try:
            # UIを即座に更新
            self.analysis_progress_bar.setVisible(True)
            self.analysis_progress_bar.setRange(0, 100)  # 0-100%のプログレスバー
            self.analysis_progress_bar.setValue(0)
            self.analyze_btn.setEnabled(False)
            self.auto_insights_btn.setEnabled(False)
            
            update_progress("自動洞察生成を開始中...", 10)
            
            # プログレス更新のカスタムコールバック
            def gemini_progress_callback(message):
                if "データ概要を生成中" in message:
                    update_progress(message, 25)
                elif "サンプルデータを準備中" in message:
                    update_progress(message, 40)
                elif "洞察生成プロンプトを構築中" in message:
                    update_progress(message, 60)
                elif "Gemini AIで洞察を生成中" in message:
                    update_progress(message, 80)
                else:
                    update_progress(message)
            
            # Gemini APIで自動洞察生成（プログレス更新付き）
            result = self.gemini_client.generate_insights(
                self.current_data,
                progress_callback=gemini_progress_callback
            )
            
            # 完了時のプログレス
            update_progress("洞察結果を表示中...", 95)
            
            # プログレスバーを非表示にしてから結果表示
            self.analysis_progress_bar.setValue(100)
            QApplication.processEvents()
            
            if result:
                self.analysis_result.setText(result)
                self.status_bar.showMessage("自動洞察生成完了")
                # 分析結果ダウンロードボタンを有効化
                self.download_analysis_btn.setEnabled(True)
            else:
                self.analysis_result.setText("洞察生成に失敗しました。")
                self.status_bar.showMessage("自動洞察生成失敗")
                self.download_analysis_btn.setEnabled(False)
            
            # 少し待ってからプログレスバーを非表示
            QTimer.singleShot(500, lambda: self.analysis_progress_bar.setVisible(False))
                
        except Exception as e:
            logger.error(f"自動洞察生成エラー: {e}")
            # エラー時もプログレスバーを非表示
            self.analysis_progress_bar.setVisible(False)
            QApplication.processEvents()
            
            self.analysis_result.setText(f"洞察生成中にエラーが発生しました: {e}")
            QMessageBox.critical(self, "エラー", f"自動洞察生成に失敗しました: {e}")
            self.download_analysis_btn.setEnabled(False)
        finally:
            # 最終的にUIを復元
            self.analyze_btn.setEnabled(True)
            self.auto_insights_btn.setEnabled(True)
            QApplication.processEvents()
    
    def create_infographic(self):
        """インフォグラフィック化"""
        if not self.gemini_client or not self.gemini_client.is_connected:
            QMessageBox.warning(self, "警告", "まずGemini APIに接続してください。")
            return
        
        if self.current_data is None or self.current_data.empty:
            QMessageBox.warning(self, "警告", "分析するデータがありません。")
            return
        
        # プログレス管理用の変数
        self.current_progress = 0
        
        def update_progress(message, progress_value=None):
            """プログレス更新用コールバック"""
            if progress_value is not None:
                self.current_progress = progress_value
                self.analysis_progress_bar.setValue(self.current_progress)
            
            self.status_bar.showMessage(message)
            QApplication.processEvents()
        
        try:
            # UIを即座に更新
            self.analysis_progress_bar.setVisible(True)
            self.analysis_progress_bar.setRange(0, 100)  # 0-100%のプログレスバー
            self.analysis_progress_bar.setValue(0)
            self.analyze_btn.setEnabled(False)
            self.auto_insights_btn.setEnabled(False)
            self.infographic_btn.setEnabled(False)
            
            update_progress("インフォグラフィック化を開始中...", 10)
            
            # プログレス更新のカスタムコールバック
            def gemini_progress_callback(message):
                if "データ概要を生成中" in message:
                    update_progress(message, 25)
                elif "インフォグラフィック用データを準備中" in message:
                    update_progress(message, 40)
                elif "HTMLインフォグラフィックを生成中" in message:
                    update_progress(message, 60)
                elif "Gemini AIでHTMLを生成中" in message:
                    update_progress(message, 80)
                else:
                    update_progress(message)
            
            # ユーザーの分析指示を取得
            user_prompt = self.analysis_input.toPlainText().strip()
            if not user_prompt:
                QMessageBox.warning(self, "警告", "分析指示を入力してください。")
                return

            # Gemini APIでHTMLインフォグラフィック生成（プログレス更新付き）
            html_content = self.gemini_client.create_infographic_html(
                self.current_data,
                user_prompt=user_prompt,
                progress_callback=gemini_progress_callback
            )
            
            # 完了時のプログレス
            update_progress("インフォグラフィック生成完了", 95)
            
            # プログレスバーを非表示にしてから結果表示
            self.analysis_progress_bar.setValue(100)
            QApplication.processEvents()
            
            if html_content:
                # HTMLコンテンツを保存（クラス変数として）
                self.current_html_content = html_content
                
                # 結果表示エリアに成功メッセージを表示
                self.analysis_result.setText("📊 HTMLインフォグラフィックが生成されました！\n\n「📄 HTMLダウンロード」ボタンをクリックして保存してください。")
                self.status_bar.showMessage("インフォグラフィック生成完了")
                
                # HTMLダウンロードボタンを有効化
                self.download_html_btn.setEnabled(True)
                
                QMessageBox.information(self, "成功", "HTMLインフォグラフィックが生成されました！\n「📄 HTMLダウンロード」ボタンから保存できます。")
            else:
                self.analysis_result.setText("インフォグラフィック生成に失敗しました。")
                self.status_bar.showMessage("インフォグラフィック生成失敗")
            
            # 少し待ってからプログレスバーを非表示
            QTimer.singleShot(500, lambda: self.analysis_progress_bar.setVisible(False))
                
        except Exception as e:
            logger.error(f"インフォグラフィック生成エラー: {e}")
            # エラー時もプログレスバーを非表示
            self.analysis_progress_bar.setVisible(False)
            QApplication.processEvents()
            
            self.analysis_result.setText(f"インフォグラフィック生成中にエラーが発生しました: {e}")
            QMessageBox.critical(self, "エラー", f"インフォグラフィック生成に失敗しました: {e}")
        finally:
            # 最終的にUIを復元
            self.analyze_btn.setEnabled(True)
            self.auto_insights_btn.setEnabled(True)
            self.infographic_btn.setEnabled(True)
            QApplication.processEvents()
    
    def download_analysis_result(self):
        """分析結果をダウンロード"""
        analysis_text = self.analysis_result.toPlainText().strip()
        
        if not analysis_text or analysis_text in ["", "分析に失敗しました。", "洞察生成に失敗しました。"]:
            QMessageBox.warning(self, "警告", "ダウンロードする分析結果がありません。")
            return
        
        try:
            # ファイル保存ダイアログを表示（テキストとMarkdownの両方をサポート）
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "分析結果を保存", 
                "analysis_result.txt", 
                "Text files (*.txt);;Markdown files (*.md);;All files (*.*)"
            )
            
            if file_path:
                # 現在の日時を取得
                from datetime import datetime
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # ヘッダー情報を追加
                header = f"# Notion データ分析結果\n\n"
                header += f"**生成日時**: {current_time}\n"
                header += f"**データ行数**: {len(self.current_data) if self.current_data is not None else 0}\n"
                header += f"**データ列数**: {len(self.current_data.columns) if self.current_data is not None else 0}\n\n"
                header += "---\n\n"
                
                # ファイル拡張子に応じて内容を調整
                if file_path.endswith('.md'):
                    # Markdownファイルの場合、ヘッダーを追加
                    content = header + analysis_text
                else:
                    # テキストファイルの場合、シンプルなヘッダー
                    simple_header = f"Notion データ分析結果\n"
                    simple_header += f"生成日時: {current_time}\n"
                    simple_header += f"データ行数: {len(self.current_data) if self.current_data is not None else 0}\n"
                    simple_header += f"データ列数: {len(self.current_data.columns) if self.current_data is not None else 0}\n\n"
                    simple_header += "=" * 50 + "\n\n"
                    content = simple_header + analysis_text
                
                # ファイルに保存
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.status_bar.showMessage(f"分析結果を保存しました: {file_path}", 3000)
                
                QMessageBox.information(
                    self, 
                    "保存完了", 
                    f"分析結果を保存しました:\n{file_path}"
                )
                
        except Exception as e:
            logger.error(f"分析結果ダウンロードエラー: {e}")
            QMessageBox.critical(self, "エラー", f"分析結果の保存に失敗しました: {e}")
            self.status_bar.showMessage("分析結果ダウンロード失敗")
    
    def download_html_infographic(self):
        """HTMLインフォグラフィックをダウンロード"""
        if not hasattr(self, 'current_html_content') or not self.current_html_content:
            QMessageBox.warning(self, "警告", "まずインフォグラフィックを生成してください。")
            return
        
        try:
            # ファイル保存ダイアログを表示
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "HTMLインフォグラフィックを保存", 
                "notion_infographic.html", 
                "HTML files (*.html)"
            )
            
            if file_path:
                # HTMLファイルに保存
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.current_html_content)
                
                self.status_bar.showMessage(f"HTMLファイルを保存しました: {file_path}", 3000)
                
                # ブラウザで開くかユーザーに確認
                reply = QMessageBox.question(
                    self, 
                    "保存完了", 
                    f"HTMLファイルを保存しました:\n{file_path}\n\nブラウザで開きますか？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    import webbrowser
                    webbrowser.open(f"file://{file_path}")
                    self.status_bar.showMessage("ブラウザでHTMLを開きました", 2000)
                
        except Exception as e:
            logger.error(f"HTMLダウンロードエラー: {e}")
            QMessageBox.critical(self, "エラー", f"HTMLファイルの保存に失敗しました: {e}")
            self.status_bar.showMessage("HTMLダウンロード失敗") 
    
    def switch_page(self, index):
        """ページ切り替え"""
        # 全てのボタンの選択を解除
        for btn in self.nav_buttons:
            btn.setChecked(False)
        
        # 選択されたボタンをチェック
        self.nav_buttons[index].setChecked(True)
        
        # ページタイトルを更新
        titles = ["接続設定", "データ取得", "AI分析", "設定"]
        self.page_title.setText(titles[index])
        
        # コンテンツページを切り替え
        self.content_stack.setCurrentIndex(index)
        
        # ステータスバーメッセージを更新
        messages = [
            "🔗 Notion APIへの接続設定を行ってください",
            "📥 データを取得してダッシュボードで確認",
            "🤖 AIによるデータ分析を実行",
            "⚙️ アプリケーションの設定を変更"
        ]
        self.status_bar.showMessage(messages[index])