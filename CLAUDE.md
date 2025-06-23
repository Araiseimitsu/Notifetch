# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

NotiFetchは、Notionのデータを取得・分析するための日本語デスクトップアプリケーションです。PySide6で構築され、技術知識のないユーザーでもNotionデータベース/ページからデータを抽出し、Google Gemini AIを使って分析できるGUIインターフェースを提供します。

**主要技術**: Python 3.9+, PySide6, Notion API, Google Gemini AI, pandas, cryptography

## 開発コマンド

### アプリケーションの実行
```bash
python main.py
```

### 開発環境のセットアップ
```bash
# 仮想環境の作成
python -m venv venv

# 仮想環境の有効化（Windows）
venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 実行可能ファイルのビルド
```bash
# PyInstallerでspecファイルを使用してビルド
pyinstaller notifetch.spec
```

アプリケーションは`dist/`ディレクトリにビルドされます。異なるバージョン用の複数の.specファイルが存在します。

## アーキテクチャ概要

### コア構造
- **main.py**: タスクバーアイコンとDPIスケーリングのWindows固有最適化を含むアプリケーションエントリーポイント
- **src/config/settings.py**: APIトークン用のFernet暗号化を使用した暗号化設定管理
- **src/core/**: NotionとGeminiサービス用のAPIクライアント
- **src/ui/main_window.py**: メインPySide6 GUIアプリケーション
- **src/utils/**: データ変換ユーティリティとリソース管理

### 主要なアーキテクチャパターン

1. **暗号化設定**: APIトークンはcryptography.Fernetを使用して暗号化され、`~/.notifetch/`に保存
2. **クライアント・サーバーパターン**: Notion APIとGemini AI統合用の個別クライアントクラス
3. **データパイプライン**: Notionデータ → pandas DataFrame → CSV/Excel/HTMLエクスポート → AI分析
4. **GUIファーストデザイン**: 日本語ローカライゼーション対応のPySide6ベースデスクトップアプリケーション

### データフロー
1. ユーザーがNotion APIトークンとページ/データベースIDを入力
2. NotionClientがページネーション対応でデータを取得
3. data_converter.py経由でデータをpandas DataFrameに変換
4. 様々な形式（CSV、Excel、HTML）にエクスポート
5. GeminiClientを使用したオプションのAI分析
6. テキスト/マークダウン/HTMLインフォグラフィックとして結果をエクスポート

## 重要な実装詳細

### セキュリティに関する考慮事項
- APIトークンはFernet対称暗号化を使用して暗号化
- 設定はユーザーホームディレクトリ（`~/.notifetch/`）に保存
- コードベースにハードコードされた秘密情報なし

### Windows最適化
- タスクバーアイコンとDPIスケーリング用の広範なWindows固有コード
- 適切なタスクバー統合のためのctypes経由でのWindows API呼び出し
- アセットバンドリング付きのPyInstallerパッケージング

### エラーハンドリング
- `~/.notifetch/logs/notifetch.log`への包括的ログ記録
- 操作前のAPI接続テスト
- QMessageBoxによる優雅なエラー表示

### データ処理
- 大きなNotionデータベース用のチャンク分割データ取得
- 設定可能な行制限（100-5000行またはカスタム）
- 適切なエンコーディング処理による複数エクスポート形式

## ファイル構造の意味

```
src/
├── config/settings.py     # 暗号化設定管理
├── core/                  # API統合レイヤー
│   ├── notion_client.py   # Notion APIラッパー
│   └── gemini_client.py   # Gemini AIラッパー
├── ui/main_window.py      # メインGUIアプリケーション
└── utils/                 # データ処理ユーティリティ
```

## 開発メモ

- アプリケーションは完全に日本語ローカライズ済み
- 企業環境の非技術ユーザー向けに設計
- エラーハンドリングとユーザーフィードバックに重点
- タスクバーアイコン最適化付きのWindows優先開発
- 現在テストフレームワークは実装されていない
- 複数のspec設定でのPyInstallerによる配布

 
1. **言語**
 
   * すべての回答は必ず日本語で行うこと。
  
2. **開発・実行環境**

   * 開発: WSL (Linux)
   * 実行: Windows
   * パス・ディレクトリ設計は Windows 準拠。

1. **ライブラリ導入とトラブルシュート**

   * 新規ライブラリ導入や解決が難しいエラー時は MCP tool `context7` と DeepWiki で最新情報を確認。

1. **リファクタリング**

   * コード重複・冗長構造を都度排除。

  

5. **ドキュメント管理**

   * プロジェクト直下に `docs/` を作成。
   * `docs/docs.md` にやり取りの結果と考察を記録、更新しながら改善に活用。
