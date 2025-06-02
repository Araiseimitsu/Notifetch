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
                progress_callback("データ概要を生成中...")
            
            # DataFrameの概要を取得
            data_summary = self._generate_data_summary(dataframe)
            
            # プログレス更新
            if progress_callback:
                progress_callback("サンプルデータを準備中...")
            
            # データのサンプルを取得（最初の10行）
            sample_data = dataframe.head(10).to_string()
            
            # プログレス更新
            if progress_callback:
                progress_callback("分析プロンプトを構築中...")
            
            # プロンプトを構築
            prompt = self._build_analysis_prompt(data_summary, sample_data, analysis_request)
            
            # プログレス更新
            if progress_callback:
                progress_callback("Gemini AIで分析実行中...")
            
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
- 行数: {len(dataframe)}
- 列数: {len(dataframe.columns)}
- 列名: {', '.join(dataframe.columns.tolist())}

各列の情報:
"""
        
        for column in dataframe.columns:
            col_data = dataframe[column]
            summary += f"- {column}: "
            summary += f"データ型={col_data.dtype}, "
            summary += f"非NULL値={col_data.count()}, "
            summary += f"ユニーク値数={col_data.nunique()}\n"
        
        return summary
    
    def _build_analysis_prompt(self, data_summary: str, sample_data: str, analysis_request: str) -> str:
        """
        分析用プロンプトを構築
        
        Args:
            data_summary: データ概要
            sample_data: サンプルデータ
            analysis_request: 分析指示
            
        Returns:
            str: 構築されたプロンプト
        """
        prompt = f"""
あなたはデータ分析の専門家です。以下のNotionから取得したデータを分析してください。

{data_summary}

データサンプル（最初の10行）:
{sample_data}

分析指示:
{analysis_request}

以下の点を考慮して分析してください:
1. データの傾向やパターンを特定する
2. 重要な洞察や発見を明確に示す
3. 可能であれば具体的な数値や例を示す
4. 日本語で分かりやすく回答する
5. 必要に応じて改善提案も含める

分析結果:
"""
        return prompt
    
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
                progress_callback("データ概要を生成中...")
            
            data_summary = self._generate_data_summary(dataframe)
            
            # プログレス更新
            if progress_callback:
                progress_callback("サンプルデータを準備中...")
            
            sample_data = dataframe.head(10).to_string()
            
            # プログレス更新
            if progress_callback:
                progress_callback("洞察生成プロンプトを構築中...")
            
            prompt = f"""
以下のNotionデータから重要な洞察を自動的に抽出してください。

{data_summary}

データサンプル:
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