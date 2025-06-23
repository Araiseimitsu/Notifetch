# Product Outline

## 1. 概要 / Overview

* プロジェクト名 | Project name: NotiFetch
* 目的・背景 | Goal / Background:

  * Notionのデータを、技術知識なしで誰でも簡単に取得したいに対応
  * 自然言語を用いて、Gemini / MCP等と連携し、データ解析も実現
* 想定ユーザー | Target users: 社内の非エンジニア職 (事務職、マーケター等)
* KPI / 成功指標 |

  * 初回利用までの平均時間
  * CSV変換成功率
  * 解析出力の満足度

## 2. 機能要件 / Features

### 2.1 MVP

1. Notion API連携: トークン、ページID入力
2. データ取得: チャンク分割で全行取得
3. CSV変換: 表示+ダウンロード対応
4. Gemini連携: 自然言語で分析指示
5. 分析結果表示

### 2.2 後续フェーズ

* フィルターUI
* 他ツールとの連携

## 3. 非機能要件 / Non-functional

* 性能 | Performance: チャンクでの初期ロード実装
* セキュリティ | Security: 最小限の外部API接続
* 可用性 | Availability: オンプレのローカル実行環境
* 保守性 | Maintainability: 個人開発で簡易な構成

## 4. システム構成 / System

* アーキテクチャ | Architecture: クライアントはローカル、バックエンドはAPI系接続
* 技術スタック | Tech stack: Python + PySide6 / Gemini + Notion API
* インフラ | Infrastructure: 実行環境は専用PC、オンプレミス

## 5. UI/UX

* デザインコンセプト | Design concept: 親しみやすく、フラットな一線デザイン
* 画面遷移 | Screen flow:

  1. インテグレーション情報入力
  2. ページID入力
  3. データ取得・表示
  4. CSV化
  5. 分析指示
  6. 結果表示
* アクセシビリティ | Accessibility: 社内利用のため日本語主 + 最低限の英語

## 6. 計画 / Plan

* スケジュール | Schedule: (未指定)
* 体制 | Team: 個人開発
* 予算 | Budget: 未定 (自財由来情報あり)

## 7. リスク & 対策 / Risks & Mitigations

* MCP接続不調 → リトライ試行 + ログ出力
* Notion API以外の要件変更 → 構築を簡易化し容易に拡張
