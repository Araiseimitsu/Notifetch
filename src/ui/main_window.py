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
    QListWidgetItem, QMenu, QInputDialog, QDialog
)
from PySide6.QtCore import Qt, QThread, QObject, Signal, QTimer
from PySide6.QtGui import QFont, QIcon, QAction

from ..config.settings import Settings
from ..core.notion_client import NotionClient
from ..core.gemini_client import GeminiClient
from ..utils.data_converter import DataConverter

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """メインウィンドウクラス"""
    
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.notion_client = None
        self.gemini_client = None
        self.current_data = None
        
        self.init_ui()
        self.load_settings()
        
        # テーマを初期読み込み時に適用
        self.apply_theme()
        
        # デフォルトのウィンドウサイズとタイトル
        self.setWindowTitle("NotiFetch - Notion データ取得・分析ツール")
        self.setGeometry(100, 100, 1200, 800)
    
    def init_ui(self):
        """UI初期化"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        main_layout = QVBoxLayout(central_widget)
        
        # タブウィジェット
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 各タブを作成
        self.create_connection_tab()
        self.create_data_tab()
        self.create_analysis_tab()
        self.create_settings_tab()
        
        # ステータスバー
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
    
    def create_connection_tab(self):
        """接続設定タブの作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Notion API設定グループ
        notion_group = QGroupBox("Notion API 設定")
        notion_layout = QFormLayout(notion_group)
        
        self.notion_token_input = QLineEdit()
        self.notion_token_input.setEchoMode(QLineEdit.Password)
        self.notion_token_input.setPlaceholderText("secret_...")
        notion_layout.addRow("API トークン:", self.notion_token_input)
        
        self.test_connection_btn = QPushButton("接続テスト")
        self.test_connection_btn.clicked.connect(self.test_notion_connection)
        notion_layout.addRow("", self.test_connection_btn)
        
        # ページID設定グループ
        page_group = QGroupBox("ページ/データベース設定")
        page_layout = QFormLayout(page_group)
        
        # ページID入力とボタンのレイアウト
        page_input_layout = QHBoxLayout()
        self.page_id_input = QLineEdit()
        self.page_id_input.setPlaceholderText("ページID または URL")
        
        self.history_btn = QPushButton("履歴")
        self.history_btn.clicked.connect(self.show_page_history)
        self.history_btn.setMaximumWidth(60)
        
        page_input_layout.addWidget(self.page_id_input)
        page_input_layout.addWidget(self.history_btn)
        
        page_layout.addRow("ページ/データベース ID:", page_input_layout)
        
        # 検証ボタンと編集ボタン
        button_layout = QHBoxLayout()
        self.validate_page_btn = QPushButton("ページ検証")
        self.validate_page_btn.clicked.connect(self.validate_page_id)
        
        self.edit_page_btn = QPushButton("ページ編集")
        self.edit_page_btn.clicked.connect(self.edit_current_page)
        self.edit_page_btn.setEnabled(False)
        
        button_layout.addWidget(self.validate_page_btn)
        button_layout.addWidget(self.edit_page_btn)
        
        page_layout.addRow("", button_layout)
        
        # ページ情報表示
        self.page_info_text = QTextEdit()
        self.page_info_text.setMaximumHeight(100)
        self.page_info_text.setReadOnly(True)
        page_layout.addRow("ページ情報:", self.page_info_text)
        
        # レイアウトに追加
        layout.addWidget(notion_group)
        layout.addWidget(page_group)
        layout.addStretch()
        
        self.tabs.addTab(tab, "🔗 接続設定")
    
    def create_data_tab(self):
        """データ取得タブの作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # データ取得設定グループ
        fetch_settings_group = QGroupBox("データ取得設定")
        fetch_settings_layout = QFormLayout(fetch_settings_group)
        
        # 取得行数指定
        self.fetch_limit_combo = QComboBox()
        self.fetch_limit_combo.addItems([
            "すべて",
            "100行",
            "500行", 
            "1000行",
            "2000行",
            "5000行",
            "カスタム"
        ])
        self.fetch_limit_combo.currentTextChanged.connect(self.on_fetch_limit_changed)
        fetch_settings_layout.addRow("取得行数:", self.fetch_limit_combo)
        
        # カスタム行数入力（初期は非表示）
        self.custom_limit_input = QLineEdit()
        self.custom_limit_input.setPlaceholderText("カスタム行数を入力 (例: 10000)")
        self.custom_limit_input.setVisible(False)
        fetch_settings_layout.addRow("カスタム行数:", self.custom_limit_input)
        
        # 取得ボタン
        button_layout = QHBoxLayout()
        self.fetch_data_btn = QPushButton("データ取得開始")
        self.fetch_data_btn.clicked.connect(self.fetch_data)
        button_layout.addWidget(self.fetch_data_btn)
        button_layout.addStretch()
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # データプレビューテーブル
        self.data_table = QTableWidget()
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # エクスポートボタン
        export_layout = QHBoxLayout()
        self.export_csv_btn = QPushButton("CSV エクスポート")
        self.export_csv_btn.clicked.connect(self.export_csv)
        self.export_csv_btn.setEnabled(False)
        
        self.export_excel_btn = QPushButton("Excel エクスポート")
        self.export_excel_btn.clicked.connect(self.export_excel)
        self.export_excel_btn.setEnabled(False)
        
        export_layout.addWidget(self.export_csv_btn)
        export_layout.addWidget(self.export_excel_btn)
        export_layout.addStretch()
        
        # データ概要
        self.data_summary_text = QTextEdit()
        self.data_summary_text.setMaximumHeight(120)
        self.data_summary_text.setReadOnly(True)
        
        # レイアウトに追加
        layout.addWidget(fetch_settings_group)
        layout.addLayout(button_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("データプレビュー:"))
        layout.addWidget(self.data_table)
        layout.addWidget(QLabel("データ概要:"))
        layout.addWidget(self.data_summary_text)
        layout.addLayout(export_layout)
        
        self.tabs.addTab(tab, "📥 データ取得")
    
    def create_analysis_tab(self):
        """分析タブの作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Gemini API設定
        gemini_group = QGroupBox("Gemini API 設定")
        gemini_layout = QFormLayout(gemini_group)
        
        self.gemini_api_key_input = QLineEdit()
        self.gemini_api_key_input.setEchoMode(QLineEdit.Password)
        self.gemini_api_key_input.setPlaceholderText("AIza...")
        gemini_layout.addRow("API キー:", self.gemini_api_key_input)
        
        self.test_gemini_btn = QPushButton("Gemini 接続テスト")
        self.test_gemini_btn.clicked.connect(self.test_gemini_connection)
        gemini_layout.addRow("", self.test_gemini_btn)
        
        # 分析指示入力
        analysis_group = QGroupBox("分析指示")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.analysis_input = QTextEdit()
        self.analysis_input.setPlaceholderText("データについて分析したい内容を自然言語で入力してください。\n例: このデータの傾向を教えて、売上が最も高い月は？")
        self.analysis_input.setMaximumHeight(100)
        analysis_layout.addWidget(self.analysis_input)
        
        # 分析ボタン
        analysis_btn_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("分析実行")
        self.analyze_btn.clicked.connect(self.run_analysis)
        self.analyze_btn.setEnabled(False)
        
        self.auto_insights_btn = QPushButton("自動洞察生成")
        self.auto_insights_btn.clicked.connect(self.generate_auto_insights)
        self.auto_insights_btn.setEnabled(False)
        
        self.infographic_btn = QPushButton("📊 インフォグラフィック化")
        self.infographic_btn.clicked.connect(self.create_infographic)
        self.infographic_btn.setEnabled(False)
        
        analysis_btn_layout.addWidget(self.analyze_btn)
        analysis_btn_layout.addWidget(self.auto_insights_btn)
        analysis_btn_layout.addWidget(self.infographic_btn)
        analysis_btn_layout.addStretch()
        
        analysis_layout.addLayout(analysis_btn_layout)
        
        # 分析用プログレスバー（データ取得タブと同じ位置）
        self.analysis_progress_bar = QProgressBar()
        self.analysis_progress_bar.setVisible(False)
        analysis_layout.addWidget(self.analysis_progress_bar)
        
        # 分析結果表示
        result_group = QGroupBox("分析結果")
        result_layout = QVBoxLayout(result_group)
        
        self.analysis_result = QTextEdit()
        self.analysis_result.setReadOnly(True)
        result_layout.addWidget(self.analysis_result)
        
        # HTMLダウンロードボタン
        result_btn_layout = QHBoxLayout()
        self.download_analysis_btn = QPushButton("📝 分析結果ダウンロード")
        self.download_analysis_btn.clicked.connect(self.download_analysis_result)
        self.download_analysis_btn.setEnabled(False)
        
        self.download_html_btn = QPushButton("📄 HTMLダウンロード")
        self.download_html_btn.clicked.connect(self.download_html_infographic)
        self.download_html_btn.setEnabled(False)
        result_btn_layout.addWidget(self.download_analysis_btn)
        result_btn_layout.addWidget(self.download_html_btn)
        result_btn_layout.addStretch()
        result_layout.addLayout(result_btn_layout)
        
        # レイアウトに追加
        layout.addWidget(gemini_group)
        layout.addWidget(analysis_group)
        layout.addWidget(result_group)
        
        self.tabs.addTab(tab, "🤖 AI分析")
    
    def create_settings_tab(self):
        """設定タブの作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 一般設定
        general_group = QGroupBox("一般設定")
        general_layout = QFormLayout(general_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark"])
        general_layout.addRow("テーマ:", self.theme_combo)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["ja", "en"])
        general_layout.addRow("言語:", self.language_combo)
        
        # データ設定
        data_group = QGroupBox("データ設定")
        data_layout = QFormLayout(data_group)
        
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["utf-8", "shift_jis", "cp932"])
        data_layout.addRow("CSV エンコーディング:", self.encoding_combo)
        
        # 保存ボタン
        self.save_settings_btn = QPushButton("設定保存")
        self.save_settings_btn.clicked.connect(self.save_settings)
        
        # レイアウトに追加
        layout.addWidget(general_group)
        layout.addWidget(data_group)
        layout.addWidget(self.save_settings_btn)
        layout.addStretch()
        
        self.tabs.addTab(tab, "⚙️ 設定")
    
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
            
            # 最後のページIDの読み込み
            last_page_id = self.settings.get_last_page_id()
            if last_page_id:
                self.page_id_input.setText(last_page_id)
            
            # UI設定の読み込み
            theme = self.settings.get_ui_setting("theme", "light")
            self.theme_combo.setCurrentText(theme)
            
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
            self.settings.set_last_page_id(self.page_id_input.text())
            
            # UI設定の保存
            self.settings.set_ui_setting("theme", self.theme_combo.currentText())
            self.settings.set_ui_setting("language", self.language_combo.currentText())
            self.settings.set_ui_setting("csv_encoding", self.encoding_combo.currentText())
            
            # テーマを即座に適用
            self.apply_theme()
            
            QMessageBox.information(self, "設定保存", "設定が正常に保存されました。")
            logger.info("設定を保存しました")
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
            QMessageBox.critical(self, "エラー", f"設定の保存に失敗しました: {e}")
    
    def apply_theme(self):
        """テーマの適用"""
        theme = self.settings.get_ui_setting("theme", "light")
        
        if theme == "dark":
            # ダークテーマのスタイルシート
            dark_style = """
            /* 全体のデフォルト色設定 */
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            /* メッセージボックス */
            QMessageBox {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QMessageBox QLabel {
                color: #ffffff;
                background-color: #2b2b2b;
            }
            QMessageBox QPushButton {
                background-color: #4a90e2;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #357abd;
            }
            QMessageBox QPushButton:pressed {
                background-color: #2968a3;
            }
            /* タブウィジェット */
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555;
                padding: 8px 15px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4a90e2;
                border-bottom-color: #4a90e2;
            }
            QTabBar::tab:hover {
                background-color: #4c4c4c;
            }
            /* グループボックス */
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 1ex;
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
                background-color: #2b2b2b;
            }
            /* 入力フィールド */
            QLineEdit, QTextEdit {
                border: 2px solid #555;
                border-radius: 5px;
                padding: 5px;
                background-color: #3c3c3c;
                color: #ffffff;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #4a90e2;
            }
            /* コンボボックス */
            QComboBox {
                border: 2px solid #555;
                border-radius: 5px;
                padding: 5px;
                background-color: #3c3c3c;
                color: #ffffff;
                min-width: 100px;
            }
            QComboBox:focus {
                border-color: #4a90e2;
            }
            QComboBox::drop-down {
                background-color: #4c4c4c;
                border: none;
            }
            QComboBox::down-arrow {
                color: #ffffff;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555;
                selection-background-color: #4a90e2;
                selection-color: #ffffff;
            }
            /* ボタン */
            QPushButton {
                background-color: #4a90e2;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2968a3;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
            /* テーブル */
            QTableWidget {
                gridline-color: #555;
                background-color: #3c3c3c;
                alternate-background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555;
            }
            QTableWidget::item {
                border: none;
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #4a90e2;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #4a90e2;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            /* スクロールバー */
            QScrollBar:vertical {
                background-color: #3c3c3c;
                width: 15px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical {
                background-color: #555;
                border-radius: 7px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                border: none;
            }
            QScrollBar:horizontal {
                background-color: #3c3c3c;
                height: 15px;
                border-radius: 7px;
            }
            QScrollBar::handle:horizontal {
                background-color: #555;
                border-radius: 7px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #666;
            }
            /* プログレスバー */
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                text-align: center;
                background-color: #3c3c3c;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #4a90e2;
                border-radius: 3px;
            }
            /* ステータスバー */
            QStatusBar {
                background-color: #2b2b2b;
                color: #ffffff;
                border-top: 1px solid #555;
            }
            /* ラベル */
            QLabel {
                color: #ffffff;
                background-color: transparent;
            }
            /* フレーム */
            QFrame {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            """
            self.setStyleSheet(dark_style)
        else:
            # ライトテーマ（デフォルト）のスタイルシート
            light_style = """
            /* 全体のデフォルト色設定 */
            QWidget {
                background-color: #ffffff;
                color: #000000;
            }
            QMainWindow {
                background-color: #ffffff;
                color: #000000;
            }
            /* メッセージボックス */
            QMessageBox {
                background-color: #ffffff;
                color: #000000;
            }
            QMessageBox QLabel {
                color: #000000;
                background-color: #ffffff;
            }
            QMessageBox QPushButton {
                background-color: #4a90e2;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #357abd;
            }
            QMessageBox QPushButton:pressed {
                background-color: #2968a3;
            }
            /* タブウィジェット */
            QTabWidget::pane {
                border: 1px solid #ddd;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                color: #000000;
                border: 1px solid #ddd;
                padding: 8px 15px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4a90e2;
                color: #ffffff;
                border-bottom-color: #4a90e2;
            }
            QTabBar::tab:hover {
                background-color: #e0e0e0;
            }
            /* グループボックス */
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 5px;
                margin-top: 1ex;
                background-color: #ffffff;
                color: #000000;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #000000;
                background-color: #ffffff;
            }
            /* 入力フィールド */
            QLineEdit, QTextEdit {
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 5px;
                background-color: #ffffff;
                color: #000000;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #4a90e2;
            }
            /* コンボボックス */
            QComboBox {
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 5px;
                background-color: #ffffff;
                color: #000000;
                min-width: 100px;
            }
            QComboBox:focus {
                border-color: #4a90e2;
            }
            QComboBox::drop-down {
                background-color: #f0f0f0;
                border: none;
            }
            QComboBox::down-arrow {
                color: #000000;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #ddd;
                selection-background-color: #4a90e2;
                selection-color: #ffffff;
            }
            /* ボタン */
            QPushButton {
                background-color: #4a90e2;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2968a3;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
            /* テーブル */
            QTableWidget {
                gridline-color: #ddd;
                background-color: #ffffff;
                alternate-background-color: #f9f9f9;
                color: #000000;
                border: 1px solid #ddd;
            }
            QTableWidget::item {
                border: none;
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #4a90e2;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #4a90e2;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            /* スクロールバー */
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 15px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical {
                background-color: #ccc;
                border-radius: 7px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #bbb;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                border: none;
            }
            QScrollBar:horizontal {
                background-color: #f0f0f0;
                height: 15px;
                border-radius: 7px;
            }
            QScrollBar::handle:horizontal {
                background-color: #ccc;
                border-radius: 7px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #bbb;
            }
            /* プログレスバー */
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 5px;
                text-align: center;
                background-color: #ffffff;
                color: #000000;
            }
            QProgressBar::chunk {
                background-color: #4a90e2;
                border-radius: 3px;
            }
            /* ステータスバー */
            QStatusBar {
                background-color: #ffffff;
                color: #000000;
                border-top: 1px solid #ddd;
            }
            /* ラベル */
            QLabel {
                color: #000000;
                background-color: transparent;
            }
            /* フレーム */
            QFrame {
                background-color: #ffffff;
                color: #000000;
            }
            """
            self.setStyleSheet(light_style)
        
        logger.info(f"テーマを{theme}に変更しました")
    
    def test_notion_connection(self):
        """Notion接続テスト"""
        token = self.notion_token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "警告", "APIトークンを入力してください。")
            return
        
        try:
            self.notion_client = NotionClient(token)
            if self.notion_client.test_connection():
                QMessageBox.information(self, "成功", "Notion APIに正常に接続されました。")
                self.status_bar.showMessage("Notion API 接続成功")
            else:
                QMessageBox.critical(self, "エラー", "Notion APIに接続できませんでした。")
                self.status_bar.showMessage("Notion API 接続失敗")
        except Exception as e:
            logger.error(f"接続テストエラー: {e}")
            QMessageBox.critical(self, "エラー", f"接続テストに失敗しました: {e}")
    
    def test_gemini_connection(self):
        """Gemini接続テスト"""
        api_key = self.gemini_api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "警告", "Gemini APIキーを入力してください。")
            return
        
        try:
            self.gemini_client = GeminiClient(api_key)
            if self.gemini_client.test_connection():
                QMessageBox.information(self, "成功", "Gemini APIに正常に接続されました。")
                self.status_bar.showMessage("Gemini API 接続成功")
                # 分析ボタンを有効化
                if self.current_data is not None and not self.current_data.empty:
                    self.analyze_btn.setEnabled(True)
                    self.auto_insights_btn.setEnabled(True)
                    self.infographic_btn.setEnabled(True)
            else:
                QMessageBox.critical(self, "エラー", "Gemini APIに接続できませんでした。")
                self.status_bar.showMessage("Gemini API 接続失敗")
        except Exception as e:
            logger.error(f"Gemini接続テストエラー: {e}")
            QMessageBox.critical(self, "エラー", f"Gemini接続テストに失敗しました: {e}")
    
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
    
    def display_summary(self, dataframe):
        """データ概要の表示"""
        summary = DataConverter.generate_summary(dataframe)
        
        summary_text = f"行数: {summary['rows']}\n"
        summary_text += f"列数: {summary['columns']}\n"
        summary_text += f"メモリ使用量: {summary['memory_usage']}\n\n"
        
        if len(dataframe) > 1000:
            summary_text += "※プレビューでは最初の1000行のみ表示されています\n\n"
        
        summary_text += "列情報:\n"
        for col, info in summary['column_info'].items():
            summary_text += f"  {col}: {info['non_null_count']}/{summary['rows']} 値\n"
        
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
                QMessageBox.information(self, "成功", f"CSVファイルを保存しました:\n{file_path}")
            else:
                QMessageBox.critical(self, "エラー", "CSVファイルの保存に失敗しました。")
    
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
                QMessageBox.information(self, "成功", f"Excelファイルを保存しました:\n{file_path}")
            else:
                QMessageBox.critical(self, "エラー", "Excelファイルの保存に失敗しました。")
    
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
            
            # Gemini APIでHTMLインフォグラフィック生成（プログレス更新付き）
            html_content = self.gemini_client.create_infographic_html(
                self.current_data,
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