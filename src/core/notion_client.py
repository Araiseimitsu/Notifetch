import logging
import time
from typing import List, Dict, Any, Optional
from notion_client import Client
from notion_client.errors import APIResponseError, RequestTimeoutError

logger = logging.getLogger(__name__)

class NotionClient:
    """Notion APIクライアント"""
    
    def __init__(self, token: str):
        """
        初期化
        
        Args:
            token: Notion APIトークン
        """
        self.token = token
        self.client = None
        self.is_connected = False
        
        if token:
            self._initialize_client()
    
    def _initialize_client(self):
        """Notion APIクライアントの初期化"""
        try:
            self.client = Client(auth=self.token)
            self.is_connected = True
            logger.info("Notion APIクライアントが初期化されました")
        except Exception as e:
            logger.error(f"Notion APIクライアントの初期化に失敗: {e}")
            self.is_connected = False
    
    def test_connection(self) -> bool:
        """
        API接続テスト
        
        Returns:
            bool: 接続が成功した場合True
        """
        if not self.client:
            return False
        
        try:
            # ユーザー情報を取得してテスト
            self.client.users.me()
            self.is_connected = True
            logger.info("Notion API接続テストが成功しました")
            return True
        except Exception as e:
            logger.error(f"Notion API接続テストに失敗: {e}")
            self.is_connected = False
            return False
    
    def validate_page_id(self, page_id: str) -> Dict[str, Any]:
        """
        ページIDの検証
        
        Args:
            page_id: 検証するページID
            
        Returns:
            Dict[str, Any]: 検証結果
                - valid: bool - ページIDが有効かどうか
                - exists: bool - ページが存在するかどうか
                - accessible: bool - アクセス権限があるかどうか
                - type: str - 'page', 'database', 'unknown'
                - message: str - 結果メッセージ
                - error_code: str - エラーコード（存在する場合）
        """
        if not self.client or not page_id:
            return {
                "valid": False,
                "exists": False,
                "accessible": False,
                "type": "unknown",
                "message": "APIクライアントが初期化されていないか、ページIDが空です",
                "error_code": "client_not_ready"
            }
        
        try:
            # ページIDの形式をクリーンアップ
            clean_page_id = self._clean_page_id(page_id)
            
            # まずページとして取得を試す
            try:
                page = self.client.pages.retrieve(page_id=clean_page_id)
                logger.info(f"ページID {clean_page_id} が有効です（ページ）")
                return {
                    "valid": True,
                    "exists": True,
                    "accessible": True,
                    "type": "page",
                    "message": "ページが正常に見つかりました",
                    "error_code": None
                }
            except APIResponseError as page_error:
                # ページとして取得できない場合、データベースとして試す
                try:
                    database = self.client.databases.retrieve(database_id=clean_page_id)
                    logger.info(f"ページID {clean_page_id} が有効です（データベース）")
                    return {
                        "valid": True,
                        "exists": True,
                        "accessible": True,
                        "type": "database",
                        "message": "データベースが正常に見つかりました",
                        "error_code": None
                    }
                except APIResponseError as db_error:
                    # 両方で失敗した場合、エラーの種類を判定
                    if page_error.status == 404 and db_error.status == 404:
                        logger.info(f"ページ/データベースが存在しません: {clean_page_id}")
                        return {
                            "valid": False,
                            "exists": False,
                            "accessible": False,
                            "type": "unknown",
                            "message": "指定されたページまたはデータベースが存在しません",
                            "error_code": "not_found"
                        }
                    elif page_error.status == 403 or db_error.status == 403:
                        logger.info(f"ページ/データベースへのアクセス権限がありません: {clean_page_id}")
                        return {
                            "valid": False,
                            "exists": True,  # 存在はするがアクセスできない
                            "accessible": False,
                            "type": "unknown",
                            "message": "ページまたはデータベースにアクセスする権限がありません",
                            "error_code": "access_denied"
                        }
                    else:
                        logger.warning(f"ページID検証で予期しないエラー: {page_error}")
                        return {
                            "valid": False,
                            "exists": False,
                            "accessible": False,
                            "type": "unknown",
                            "message": f"検証中にエラーが発生しました（ステータス: {page_error.status}）",
                            "error_code": "api_error"
                        }
                        
        except Exception as e:
            logger.error(f"ページID検証で予期しないエラー: {e}")
            return {
                "valid": False,
                "exists": False,
                "accessible": False,
                "type": "unknown",
                "message": f"検証中に予期しないエラーが発生しました: {e}",
                "error_code": "unexpected_error"
            }
    
    def _clean_page_id(self, page_id: str) -> str:
        """
        ページIDのクリーンアップ
        
        Args:
            page_id: 元のページID
            
        Returns:
            str: クリーンアップされたページID
        """
        # URLからページIDを抽出
        if "notion.so" in page_id:
            page_id = page_id.split("/")[-1]
            if "?" in page_id:
                page_id = page_id.split("?")[0]
        
        # ハイフンを除去
        page_id = page_id.replace("-", "")
        
        # 32文字のIDのみを保持
        if len(page_id) >= 32:
            page_id = page_id[:32]
        
        return page_id
    
    def get_page_info(self, page_id: str) -> Optional[Dict[str, Any]]:
        """
        ページ情報の取得
        
        Args:
            page_id: ページID
            
        Returns:
            Dict[str, Any]: ページ情報
        """
        if not self.client:
            return None
        
        try:
            clean_page_id = self._clean_page_id(page_id)
            
            # まずページとして取得を試す
            try:
                page = self.client.pages.retrieve(page_id=clean_page_id)
                
                # ページタイトルの取得
                title = "無題"
                if "properties" in page:
                    for prop_name, prop_data in page["properties"].items():
                        if prop_data.get("type") == "title":
                            title_list = prop_data.get("title", [])
                            if title_list:
                                title = title_list[0].get("plain_text", "無題")
                            break
                
                return {
                    "id": page["id"],
                    "title": title,
                    "created_time": page["created_time"],
                    "last_edited_time": page["last_edited_time"],
                    "url": page["url"],
                    "type": "page"
                }
            except APIResponseError:
                # ページとして取得できない場合、データベースとして試す
                try:
                    database = self.client.databases.retrieve(database_id=clean_page_id)
                    
                    # データベースタイトルの取得
                    title = "無題データベース"
                    if "title" in database and database["title"]:
                        title = database["title"][0].get("plain_text", "無題データベース")
                    
                    return {
                        "id": database["id"],
                        "title": title,
                        "created_time": database["created_time"],
                        "last_edited_time": database["last_edited_time"],
                        "url": database["url"],
                        "type": "database"
                    }
                except APIResponseError:
                    return None
                    
        except Exception as e:
            logger.error(f"ページ情報取得エラー: {e}")
            return None
    
    def get_database_data(self, database_id: str, page_size: int = 100, progress_callback=None) -> List[Dict[str, Any]]:
        """
        データベースからデータを取得
        
        Args:
            database_id: データベースID
            page_size: 1回に取得するページ数
            progress_callback: プログレス更新用コールバック関数
            
        Returns:
            List[Dict[str, Any]]: データベースの行データ
        """
        if not self.client:
            return []
        
        all_results = []
        has_more = True
        start_cursor = None
        page_count = 0
        
        try:
            clean_database_id = self._clean_page_id(database_id)
            
            while has_more:
                page_count += 1
                query_params = {"page_size": page_size}
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                
                # プログレス更新
                if progress_callback:
                    progress_callback(f"データ取得中... ({len(all_results)} 件取得済み)")
                
                response = self.client.databases.query(
                    database_id=clean_database_id,
                    **query_params
                )
                
                all_results.extend(response["results"])
                has_more = response["has_more"]
                start_cursor = response.get("next_cursor")
                
                # レート制限対策
                time.sleep(0.1)
            
            logger.info(f"データベースから {len(all_results)} 件のデータを取得しました")
            return all_results
            
        except Exception as e:
            logger.error(f"データベースデータ取得エラー: {e}")
            return []
    
    def get_page_content(self, page_id: str, progress_callback=None) -> List[Dict[str, Any]]:
        """
        ページのコンテンツ（ブロック）を取得
        
        Args:
            page_id: ページID
            progress_callback: プログレス更新用コールバック関数
            
        Returns:
            List[Dict[str, Any]]: ページのブロックデータ
        """
        if not self.client:
            return []
        
        try:
            clean_page_id = self._clean_page_id(page_id)
            blocks = []
            has_more = True
            start_cursor = None
            
            while has_more:
                query_params = {}
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                
                # プログレス更新
                if progress_callback:
                    progress_callback(f"ページコンテンツ取得中... ({len(blocks)} ブロック取得済み)")
                
                response = self.client.blocks.children.list(
                    block_id=clean_page_id,
                    **query_params
                )
                
                blocks.extend(response["results"])
                has_more = response["has_more"]
                start_cursor = response.get("next_cursor")
                
                # レート制限対策
                time.sleep(0.1)
            
            logger.info(f"ページから {len(blocks)} 個のブロックを取得しました")
            return blocks
            
        except Exception as e:
            logger.error(f"ページコンテンツ取得エラー: {e}")
            return []
    
    def is_database(self, page_id: str) -> bool:
        """
        指定されたIDがデータベースかどうかを判定
        
        Args:
            page_id: ページ/データベースID
            
        Returns:
            bool: データベースの場合True
        """
        if not self.client:
            return False
        
        try:
            clean_page_id = self._clean_page_id(page_id)
            
            # まずデータベースとして取得を試す
            try:
                self.client.databases.retrieve(database_id=clean_page_id)
                return True
            except APIResponseError:
                # データベースとして取得できない場合はページとして確認
                try:
                    self.client.pages.retrieve(page_id=clean_page_id)
                    return False
                except APIResponseError:
                    return False
                
        except Exception as e:
            logger.error(f"オブジェクト型判定エラー: {e}")
            return False 