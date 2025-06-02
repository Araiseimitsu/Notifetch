import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QLabel, QLineEdit, QPushButton, QTextEdit,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFileDialog, QComboBox, QGroupBox, QFormLayout,
    QSplitter, QScrollArea, QFrame, QApplication
)
from PySide6.QtCore import Qt, QThread, QObject, Signal, QTimer
from PySide6.QtGui import QFont, QIcon

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
        
        self.page_id_input = QLineEdit()
        self.page_id_input.setPlaceholderText("ページID または URL")
        page_layout.addRow("ページ/データベース ID:", self.page_id_input)
        
        self.validate_page_btn = QPushButton("ページ検証")
        self.validate_page_btn.clicked.connect(self.validate_page_id)
        page_layout.addRow("", self.validate_page_btn)
        
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
        
        analysis_btn_layout.addWidget(self.analyze_btn)
        analysis_btn_layout.addWidget(self.auto_insights_btn)
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
            
            QMessageBox.information(self, "設定保存", "設定が正常に保存されました。")
            logger.info("設定を保存しました")
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
            QMessageBox.critical(self, "エラー", f"設定の保存に失敗しました: {e}")
    
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
                    info_text = f"タイプ: {page_info['type'].upper()}\n"
                    info_text += f"タイトル: {page_info['title']}\n"
                    info_text += f"作成日時: {page_info['created_time']}\n"
                    info_text += f"更新日時: {page_info['last_edited_time']}\n"
                    info_text += f"URL: {page_info['url']}"
                    self.page_info_text.setText(info_text)
                
                success_message = f"✅ {validation_result['message']}\n"
                success_message += f"タイプ: {validation_result['type'].upper()}"
                QMessageBox.information(self, "検証成功", success_message)
                self.status_bar.showMessage(f"ページID検証成功 - {validation_result['type']}")
                
            else:
                # 失敗：詳細な理由を表示
                self.page_info_text.clear()
                
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
    
    def fetch_data(self):
        """データ取得"""
        page_id = self.page_id_input.text().strip()
        if not page_id:
            QMessageBox.warning(self, "警告", "ページIDを入力してください。")
            return
        
        if not self.notion_client:
            QMessageBox.warning(self, "警告", "まずNotion APIに接続してください。")
            return
        
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
                    progress_callback=notion_progress_callback
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
            
            # 完了時のプログレス
            update_progress("データ取得完了", 100)
            
            # 少し待ってからプログレスバーを非表示にして成功メッセージを表示
            QTimer.singleShot(500, lambda: [
                self.progress_bar.setVisible(False),
                QMessageBox.information(self, "成功", f"{len(self.current_data)} 件のデータを取得しました。")
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
            else:
                self.analysis_result.setText("分析に失敗しました。")
                self.status_bar.showMessage("AI分析失敗")
            
            # 少し待ってからプログレスバーを非表示
            QTimer.singleShot(500, lambda: self.analysis_progress_bar.setVisible(False))
                
        except Exception as e:
            logger.error(f"AI分析エラー: {e}")
            # エラー時もプログレスバーを非表示
            self.analysis_progress_bar.setVisible(False)
            QApplication.processEvents()
            
            self.analysis_result.setText(f"分析中にエラーが発生しました: {e}")
            QMessageBox.critical(self, "エラー", f"AI分析に失敗しました: {e}")
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
            else:
                self.analysis_result.setText("洞察生成に失敗しました。")
                self.status_bar.showMessage("自動洞察生成失敗")
            
            # 少し待ってからプログレスバーを非表示
            QTimer.singleShot(500, lambda: self.analysis_progress_bar.setVisible(False))
                
        except Exception as e:
            logger.error(f"自動洞察生成エラー: {e}")
            # エラー時もプログレスバーを非表示
            self.analysis_progress_bar.setVisible(False)
            QApplication.processEvents()
            
            self.analysis_result.setText(f"洞察生成中にエラーが発生しました: {e}")
            QMessageBox.critical(self, "エラー", f"自動洞察生成に失敗しました: {e}")
        finally:
            # 最終的にUIを復元
            self.analyze_btn.setEnabled(True)
            self.auto_insights_btn.setEnabled(True)
            QApplication.processEvents() 