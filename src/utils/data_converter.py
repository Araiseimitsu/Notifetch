import csv
import pandas as pd
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class DataConverter:
    """Notionデータの変換クラス"""
    
    @staticmethod
    def extract_text_from_rich_text(rich_text_list: List[Dict[str, Any]]) -> str:
        """
        リッチテキストから平文テキストを抽出
        
        Args:
            rich_text_list: Notionのリッチテキスト配列
            
        Returns:
            str: 抽出されたテキスト
        """
        if not rich_text_list:
            return ""
        
        text_parts = []
        for rich_text in rich_text_list:
            if "plain_text" in rich_text:
                text_parts.append(rich_text["plain_text"])
            elif "text" in rich_text and "content" in rich_text["text"]:
                text_parts.append(rich_text["text"]["content"])
        
        return "".join(text_parts)
    
    @staticmethod
    def extract_property_value(property_data: Dict[str, Any]) -> Any:
        """
        Notionプロパティから値を抽出
        
        Args:
            property_data: Notionプロパティデータ
            
        Returns:
            Any: 抽出された値
        """
        prop_type = property_data.get("type", "")
        
        if prop_type == "title":
            return DataConverter.extract_text_from_rich_text(property_data.get("title", []))
        elif prop_type == "rich_text":
            return DataConverter.extract_text_from_rich_text(property_data.get("rich_text", []))
        elif prop_type == "number":
            return property_data.get("number", "")
        elif prop_type == "select":
            select_data = property_data.get("select", {})
            return select_data.get("name", "") if select_data else ""
        elif prop_type == "multi_select":
            multi_select_data = property_data.get("multi_select", [])
            return ", ".join([item.get("name", "") for item in multi_select_data])
        elif prop_type == "date":
            date_data = property_data.get("date", {})
            if date_data:
                start = date_data.get("start", "")
                end = date_data.get("end", "")
                if end:
                    return f"{start} - {end}"
                return start
            return ""
        elif prop_type == "checkbox":
            return property_data.get("checkbox", False)
        elif prop_type == "url":
            return property_data.get("url", "")
        elif prop_type == "email":
            return property_data.get("email", "")
        elif prop_type == "phone_number":
            return property_data.get("phone_number", "")
        elif prop_type == "people":
            people_data = property_data.get("people", [])
            return ", ".join([person.get("name", "") for person in people_data])
        elif prop_type == "relation":
            relation_data = property_data.get("relation", [])
            return ", ".join([rel.get("id", "") for rel in relation_data])
        elif prop_type == "formula":
            formula_data = property_data.get("formula", {})
            formula_type = formula_data.get("type", "")
            if formula_type == "string":
                return formula_data.get("string", "")
            elif formula_type == "number":
                return formula_data.get("number", "")
            elif formula_type == "boolean":
                return formula_data.get("boolean", "")
            elif formula_type == "date":
                date_data = formula_data.get("date", {})
                return date_data.get("start", "") if date_data else ""
        elif prop_type == "rollup":
            rollup_data = property_data.get("rollup", {})
            rollup_type = rollup_data.get("type", "")
            if rollup_type == "array":
                array_data = rollup_data.get("array", [])
                # 配列の各要素を処理
                values = []
                for item in array_data:
                    values.append(DataConverter.extract_property_value(item))
                return ", ".join(str(v) for v in values if v)
            elif rollup_type == "number":
                return rollup_data.get("number", "")
        elif prop_type == "created_time":
            return property_data.get("created_time", "")
        elif prop_type == "created_by":
            created_by = property_data.get("created_by", {})
            return created_by.get("name", "")
        elif prop_type == "last_edited_time":
            return property_data.get("last_edited_time", "")
        elif prop_type == "last_edited_by":
            last_edited_by = property_data.get("last_edited_by", {})
            return last_edited_by.get("name", "")
        
        return ""
    
    @staticmethod
    def convert_database_to_dataframe(database_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        NotionデータベースデータをPandas DataFrameに変換
        
        Args:
            database_data: Notionデータベースの行データ
            
        Returns:
            pd.DataFrame: 変換されたDataFrame
        """
        if not database_data:
            return pd.DataFrame()
        
        rows = []
        columns = set()
        
        # すべての列名を収集
        for item in database_data:
            properties = item.get("properties", {})
            columns.update(properties.keys())
        
        columns = sorted(list(columns))
        
        # データを行ごとに処理
        for item in database_data:
            properties = item.get("properties", {})
            row = {}
            
            # 基本情報を追加
            row["ID"] = item.get("id", "")
            row["作成日時"] = item.get("created_time", "")
            row["最終更新日時"] = item.get("last_edited_time", "")
            row["URL"] = item.get("url", "")
            
            # プロパティを処理
            for column in columns:
                property_data = properties.get(column, {})
                row[column] = DataConverter.extract_property_value(property_data)
            
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    @staticmethod
    def convert_blocks_to_dataframe(blocks_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Notionページブロックデータを構造化されたDataFrameに変換
        
        Args:
            blocks_data: Notionページのブロックデータ
            
        Returns:
            pd.DataFrame: 変換されたDataFrame
        """
        if not blocks_data:
            return pd.DataFrame()
        
        rows = []
        
        for block in blocks_data:
            block_type = block.get("type", "")
            block_id = block.get("id", "")
            created_time = block.get("created_time", "")
            last_edited_time = block.get("last_edited_time", "")
            
            content = ""
            
            # ブロックタイプに応じてコンテンツを抽出
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", "quote", "callout"]:
                block_data = block.get(block_type, {})
                rich_text = block_data.get("rich_text", [])
                content = DataConverter.extract_text_from_rich_text(rich_text)
            elif block_type == "bulleted_list_item" or block_type == "numbered_list_item":
                block_data = block.get(block_type, {})
                rich_text = block_data.get("rich_text", [])
                content = DataConverter.extract_text_from_rich_text(rich_text)
            elif block_type == "to_do":
                block_data = block.get(block_type, {})
                rich_text = block_data.get("rich_text", [])
                checked = block_data.get("checked", False)
                text = DataConverter.extract_text_from_rich_text(rich_text)
                content = f"[{'x' if checked else ' '}] {text}"
            elif block_type == "code":
                block_data = block.get(block_type, {})
                rich_text = block_data.get("rich_text", [])
                language = block_data.get("language", "")
                text = DataConverter.extract_text_from_rich_text(rich_text)
                content = f"```{language}\n{text}\n```"
            elif block_type == "table":
                # テーブルは子ブロックから処理する必要がある
                content = "[テーブル]"
            elif block_type == "table_row":
                table_row_data = block.get("table_row", {})
                cells = table_row_data.get("cells", [])
                cell_contents = []
                for cell in cells:
                    cell_text = DataConverter.extract_text_from_rich_text(cell)
                    cell_contents.append(cell_text)
                content = " | ".join(cell_contents)
            
            rows.append({
                "ID": block_id,
                "タイプ": block_type,
                "コンテンツ": content,
                "作成日時": created_time,
                "最終更新日時": last_edited_time
            })
        
        return pd.DataFrame(rows)
    
    @staticmethod
    def save_to_csv(dataframe: pd.DataFrame, file_path: Path, encoding: str = "utf-8") -> bool:
        """
        DataFrameをCSVファイルに保存
        
        Args:
            dataframe: 保存するDataFrame
            file_path: 保存先パス
            encoding: 文字エンコーディング
            
        Returns:
            bool: 保存が成功した場合True
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            dataframe.to_csv(file_path, index=False, encoding=encoding)
            logger.info(f"CSVファイルを保存しました: {file_path}")
            return True
        except Exception as e:
            logger.error(f"CSVファイル保存エラー: {e}")
            return False
    
    @staticmethod
    def save_to_excel(dataframe: pd.DataFrame, file_path: Path) -> bool:
        """
        DataFrameをExcelファイルに保存
        
        Args:
            dataframe: 保存するDataFrame
            file_path: 保存先パス
            
        Returns:
            bool: 保存が成功した場合True
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                dataframe.to_excel(writer, index=False, sheet_name='データ')
            logger.info(f"Excelファイルを保存しました: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Excelファイル保存エラー: {e}")
            return False
    
    @staticmethod
    def generate_summary(dataframe: pd.DataFrame) -> Dict[str, Any]:
        """
        DataFrameの要約情報を生成
        
        Args:
            dataframe: 要約するDataFrame
            
        Returns:
            Dict[str, Any]: 要約情報
        """
        if dataframe.empty:
            return {"rows": 0, "columns": 0, "memory_usage": "0 MB"}
        
        summary = {
            "rows": len(dataframe),
            "columns": len(dataframe.columns),
            "memory_usage": f"{dataframe.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB",
            "column_info": {}
        }
        
        for column in dataframe.columns:
            col_data = dataframe[column]
            summary["column_info"][column] = {
                "dtype": str(col_data.dtype),
                "non_null_count": col_data.count(),
                "null_count": col_data.isnull().sum(),
                "unique_count": col_data.nunique()
            }
        
        return summary 