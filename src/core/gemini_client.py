import logging
import google.generativeai as genai
from typing import Optional, Dict, Any
import pandas as pd
import json

logger = logging.getLogger(__name__)

class GeminiClient:
    """Gemini APIクライアント"""
    
    def __init__(self, api_key: str):
        """
        初期化
        
        Args:
            api_key: Gemini APIキー
        """
        self.api_key = api_key
        self.model = None
        self.is_connected = False
        
        if api_key:
            self._initialize_client()
    
    def _initialize_client(self):
        """Gemini APIクライアントの初期化"""
        try:
            genai.configure(api_key=self.api_key)
            # 最新のGeminiモデルを使用
            self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
            # self.model = genai.GenerativeModel('gemma-3n-e4b-it')
            self.is_connected = True
            logger.info("Gemini APIクライアントが初期化されました")
        except Exception as e:
            logger.error(f"Gemini APIクライアントの初期化に失敗: {e}")
            self.is_connected = False
    
    def test_connection(self) -> bool:
        """
        API接続テスト
        
        Returns:
            bool: 接続が成功した場合True
        """
        if not self.model:
            return False
        
        try:
            # 簡単なテストプロンプトを送信
            response = self.model.generate_content("Hello")
            self.is_connected = True
            logger.info("Gemini API接続テストが成功しました")
            return True
        except Exception as e:
            logger.error(f"Gemini API接続テストに失敗: {e}")
            self.is_connected = False
            return False
    
    def analyze_data(self, dataframe: pd.DataFrame, analysis_request: str, progress_callback=None) -> Optional[str]:
        """
        データ分析を実行
        
        Args:
            dataframe: 分析対象のDataFrame
            analysis_request: 分析指示（自然言語）
            progress_callback: プログレス更新用コールバック関数
            
        Returns:
            str: 分析結果
        """
        if not self.model:
            logger.error("Gemini APIクライアントが初期化されていません")
            return None
        
        try:
            # プログレス更新
            if progress_callback:
                progress_callback("データを準備中...")
            
            # データ量に応じてサンプル数を決定
            total_rows = len(dataframe)
            if total_rows <= 100:
                # 100行以下の場合は全データを送信
                sample_data = dataframe.to_string()
            elif total_rows <= 1000:
                # 1000行以下の場合は最初の100行を送信
                sample_data = dataframe.head(100).to_string()
            else:
                # 1000行を超える場合は最初の200行を送信
                sample_data = dataframe.head(200).to_string()
            
            # プログレス更新
            if progress_callback:
                progress_callback("AI分析を実行中...")
            
            # 極限までシンプルに：ユーザーの質問とデータのみ
            prompt = f"""{analysis_request}

データ:
{sample_data}"""
            
            # Gemini APIに送信
            response = self.model.generate_content(prompt)
            
            logger.info("データ分析が完了しました")
            return response.text
            
        except Exception as e:
            logger.error(f"データ分析エラー: {e}")
            return f"分析中にエラーが発生しました: {e}"
    
    def _generate_data_summary(self, dataframe: pd.DataFrame) -> str:
        """
        DataFrameの概要を生成
        
        Args:
            dataframe: 対象のDataFrame
            
        Returns:
            str: データ概要
        """
        summary = f"""
データ概要:
- 行数: {len(dataframe):,}
- 列数: {len(dataframe.columns)}
- 列名: {', '.join(dataframe.columns.tolist())}
- データサイズ: {dataframe.memory_usage(deep=True).sum() / 1024:.1f} KB

各列の詳細情報:"""
        
        for column in dataframe.columns:
            col_data = dataframe[column]
            summary += f"\n- {column}:"
            summary += f"\n  - データ型: {col_data.dtype}"
            summary += f"\n  - 非NULL値: {col_data.count():,}/{len(dataframe):,} ({col_data.count()/len(dataframe)*100:.1f}%)"
            summary += f"\n  - ユニーク値数: {col_data.nunique():,}"
            
            # 数値列の場合は基本統計量を追加
            if col_data.dtype in ['int64', 'float64', 'int32', 'float32']:
                try:
                    stats = col_data.describe()
                    summary += f"\n  - 統計量: 平均={stats['mean']:.2f}, 中央値={stats['50%']:.2f}, 標準偏差={stats['std']:.2f}"
                    summary += f"\n  - 範囲: 最小値={stats['min']:.2f}, 最大値={stats['max']:.2f}"
                except:
                    pass
            
            # 欠損値の情報
            null_count = col_data.isnull().sum()
            if null_count > 0:
                summary += f"\n  - 欠損値: {null_count:,}個 ({null_count/len(dataframe)*100:.1f}%)"
        
        summary += "\n"
        return summary
    
    # def _build_analysis_prompt(self, data_summary: str, sample_data: str, analysis_request: str) -> str:
    #     """
    #     分析用プロンプトを構築（非使用）
    #     
    #     Args:
    #         data_summary: データ概要
    #         sample_data: サンプルデータ
    #         analysis_request: 分析指示
    #         
    #     Returns:
    #         str: 構築されたプロンプト
    #     """
    #     # このメソッドは使用されなくなりました
    #     # ユーザー入力をそのまま適用するためanalyze_dataメソッドで直接プロンプトを構築
    #     prompt = f"""
    # あなたはデータ分析の専門家です。以下のNotionから取得したデータを分析してください。
    # 
    # {data_summary}
    # 
    # データサンプル（最初の10行）:
    # {sample_data}
    # 
    # 分析指示:
    # {analysis_request}
    # 
    # 以下の点を考慮して分析してください:
    # 1. データの傾向やパターンを特定する
    # 2. 重要な洞察や発見を明確に示す
    # 3. 可能であれば具体的な数値や例を示す
    # 4. 日本語で分かりやすく回答する
    # 5. 必要に応じて改善提案も含める
    # 
    # 分析結果:
    # """
    #     return prompt
    
    def generate_insights(self, dataframe: pd.DataFrame, progress_callback=None) -> Optional[str]:
        """
        データから自動的に洞察を生成
        
        Args:
            dataframe: 分析対象のDataFrame
            progress_callback: プログレス更新用コールバック関数
            
        Returns:
            str: 生成された洞察
        """
        if not self.model:
            logger.error("Gemini APIクライアントが初期化されていません")
            return None
        
        try:
            # プログレス更新
            if progress_callback:
                progress_callback("データを準備中...")
            
            data_summary = self._generate_data_summary(dataframe)
            
            # プログレス更新
            if progress_callback:
                progress_callback("洞察分析データを準備中...")
            
            # データ量に応じてサンプル数を決定
            total_rows = len(dataframe)
            if total_rows <= 100:
                # 100行以下の場合は全データを送信
                sample_data = dataframe.to_string()
                data_description = "データサンプル（全データ）"
            elif total_rows <= 1000:
                # 1000行以下の場合は最初の100行を送信
                sample_data = dataframe.head(100).to_string()
                data_description = "データサンプル（最初の100行）"
            else:
                # 1000行を超える場合は最初の200行を送信
                sample_data = dataframe.head(200).to_string()
                data_description = "データサンプル（最初の200行）"
            
            # プログレス更新
            if progress_callback:
                progress_callback("洞察生成プロンプトを構築中...")
            
            prompt = f"""
以下のNotionデータから重要な洞察を自動的に抽出してください。

{data_summary}

{data_description}:
{sample_data}

以下の観点から分析してください:
1. データの全体的な傾向
2. 注目すべき値や異常値
3. データの品質や完全性
4. 潜在的な改善点
5. ビジネス上の示唆

日本語で分かりやすく回答してください。
"""
            
            # プログレス更新
            if progress_callback:
                progress_callback("Gemini AIで洞察を生成中...")
            
            response = self.model.generate_content(prompt)
            logger.info("自動洞察生成が完了しました")
            return response.text
            
        except Exception as e:
            logger.error(f"自動洞察生成エラー: {e}")
            return f"洞察生成中にエラーが発生しました: {e}"
    
    def create_infographic_html(self, dataframe: pd.DataFrame, user_prompt: str = "", progress_callback=None) -> Optional[str]:
        """
        データからHTMLインフォグラフィックを生成
        
        Args:
            dataframe: 分析対象のDataFrame
            user_prompt: ユーザーからの特別な指示（オプション）
            progress_callback: プログレス更新用コールバック関数
            
        Returns:
            str: 生成されたHTMLコンテンツ
        """
        if not self.model:
            logger.error("Gemini APIクライアントが初期化されていません")
            return None
        
        try:
            # プログレス更新
            if progress_callback:
                progress_callback("データを準備中...")
            
            data_summary = self._generate_data_summary(dataframe)
            
            # プログレス更新
            if progress_callback:
                progress_callback("インフォグラフィック用データを準備中...")
            
            # 適応的データサンプリング
            total_rows = len(dataframe)
            if total_rows <= 50:
                # 50行以下の場合は全データを送信
                sample_data = dataframe.to_string()
                data_description = "データサンプル（全データ）"
            elif total_rows <= 200:
                # 200行以下の場合は最初の50行を送信
                sample_data = dataframe.head(50).to_string()
                data_description = "データサンプル（最初の50行）"
            else:
                # 200行を超える場合は最初の100行を送信
                sample_data = dataframe.head(100).to_string()
                data_description = "データサンプル（最初の100行）"
            
            # プログレス更新
            if progress_callback:
                progress_callback("HTMLインフォグラフィックを生成中...")
            
            # インフォグラフィック生成用プロンプト
            prompt = f"""
以下のデータをもとに、美しいHTMLインフォグラフィックを作成してください。

{data_summary}

{data_description}:
{sample_data}

{f"特別な指示: {user_prompt}" if user_prompt else ""}

以下の要件でHTMLを生成してください:

1. **完全なHTMLドキュメント**: <!DOCTYPE html>から</html>まで
2. **レスポンシブデザイン**: モバイルとデスクトップに対応
3. **モダンなCSS**: Flexbox/Grid、グラデーション、シャドウ
4. **美しいカラーパレット**: プロフェッショナルな色使い
5. **カードレイアウト**: 重要な統計情報をカード形式で表示
6. **データ可視化**: 簡単なチャート（CSS/HTMLのみ）
7. **印刷対応**: @media print スタイル
8. **日本語対応**: 美しい日本語フォント

HTMLの構成:
- ヘッダー: タイトルと概要
- 主要統計カード: 重要な数値を大きく表示
- データ洞察セクション: 分析結果を視覚的に
- チャート/グラフ: データの傾向を表示
- フッター: 生成日時

CSS は <style> タグ内に埋め込み、JavaScript が必要な場合は <script> タグ内に記述してください。
外部ライブラリは使用せず、純粋なHTML/CSS/JavaScriptのみで実装してください。

完全なHTMLコードのみを返してください（説明文は不要）。
"""
            
            # プログレス更新
            if progress_callback:
                progress_callback("Gemini AIでHTMLを生成中...")
            
            response = self.model.generate_content(prompt)
            logger.info("HTMLインフォグラフィック生成が完了しました")
            return response.text
            
        except Exception as e:
            logger.error(f"HTMLインフォグラフィック生成エラー: {e}")
            return f"HTMLインフォグラフィック生成中にエラーが発生しました: {e}" 