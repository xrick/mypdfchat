"""
Retrieval Providers - Relational database interface and DuckDB implementation
"""
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from app.domain.models import RelationalDBConfig, SpecData
from app.infra.logging import setup_logger

logger = setup_logger(__name__)


class RelationalDBInterface(ABC):
    """Abstract relational database interface"""
    
    @abstractmethod
    async def query_by_modeltypes(
        self,
        modeltypes: List[str],
        fields: Optional[List[str]] = None
    ) -> List[SpecData]:
        """Query products by model types"""
        pass
    
    @abstractmethod
    async def query_all(
        self,
        limit: int = 100,
        fields: Optional[List[str]] = None
    ) -> List[SpecData]:
        """Query all products with limit"""
        pass
    
    @abstractmethod
    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute custom SQL query"""
        pass


class DuckDBProvider(RelationalDBInterface):
    """DuckDB relational database implementation"""
    
    # Essential fields for efficient queries (60% I/O reduction)
    ESSENTIAL_FIELDS = [
        "modeltype", "modelname", "cpu", "gpu", "memory", 
        "storage", "display", "battery", "weight", "price"
    ]
    
    def __init__(self, config: RelationalDBConfig):
        """
        Initialize DuckDB connection
        
        Args:
            config: Relational database configuration
        """
        self.config = config
        self._conn = None
        
    def _get_connection(self):
        """Get or create DuckDB connection"""
        if self._conn is None:
            try:
                import duckdb
                
                self._conn = duckdb.connect(self.config.database_path)
                logger.info(f"Connected to DuckDB: {self.config.database_path}")
            except ImportError:
                logger.error("duckdb package not installed")
                raise
            except Exception as e:
                logger.error(f"Failed to connect to DuckDB: {e}")
                raise
        
        return self._conn
    
    async def query_by_modeltypes(
        self,
        modeltypes: List[str],
        fields: Optional[List[str]] = None
    ) -> List[SpecData]:
        """
        Query products by model types
        
        Args:
            modeltypes: List of model type strings
            fields: Optional list of field names to retrieve
            
        Returns:
            List of specification data
        """
        conn = self._get_connection()
        
        try:
            # Use essential fields if not specified
            query_fields = fields or self.ESSENTIAL_FIELDS
            fields_str = ", ".join(query_fields)
            
            # Build parameterized query
            placeholders = ", ".join(["?" for _ in modeltypes])
            query = f"""
                SELECT {fields_str}
                FROM {self.config.table_name}
                WHERE modeltype IN ({placeholders})
            """
            
            result = conn.execute(query, modeltypes).fetchall()
            columns = [desc[0] for desc in conn.description]
            
            spec_data_list = []
            for row in result:
                row_dict = dict(zip(columns, row))
                spec_data = SpecData(
                    modeltype=row_dict.get("modeltype", ""),
                    modelname=row_dict.get("modelname", ""),
                    specs={k: v for k, v in row_dict.items() 
                           if k not in ["modeltype", "modelname"]},
                    source="database"
                )
                spec_data_list.append(spec_data)
            
            return spec_data_list
            
        except Exception as e:
            logger.error(f"DuckDB query_by_modeltypes error: {e}")
            return []
    
    async def query_all(
        self,
        limit: int = 100,
        fields: Optional[List[str]] = None
    ) -> List[SpecData]:
        """
        Query all products with limit
        
        Args:
            limit: Maximum number of results
            fields: Optional list of field names to retrieve
            
        Returns:
            List of specification data
        """
        conn = self._get_connection()
        
        try:
            # Use essential fields if not specified
            query_fields = fields or self.ESSENTIAL_FIELDS
            fields_str = ", ".join(query_fields)
            
            query = f"""
                SELECT {fields_str}
                FROM {self.config.table_name}
                LIMIT ?
            """
            
            result = conn.execute(query, [limit]).fetchall()
            columns = [desc[0] for desc in conn.description]
            
            spec_data_list = []
            for row in result:
                row_dict = dict(zip(columns, row))
                spec_data = SpecData(
                    modeltype=row_dict.get("modeltype", ""),
                    modelname=row_dict.get("modelname", ""),
                    specs={k: v for k, v in row_dict.items() 
                           if k not in ["modeltype", "modelname"]},
                    source="database"
                )
                spec_data_list.append(spec_data)
            
            return spec_data_list
            
        except Exception as e:
            logger.error(f"DuckDB query_all error: {e}")
            return []
    
    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute custom SQL query
        
        Args:
            query: SQL query string
            
        Returns:
            List of result dictionaries
        """
        conn = self._get_connection()
        
        try:
            result = conn.execute(query).fetchall()
            columns = [desc[0] for desc in conn.description]
            
            return [dict(zip(columns, row)) for row in result]
            
        except Exception as e:
            logger.error(f"DuckDB execute_query error: {e}")
            return []
    
    async def create_table_if_not_exists(self, schema: Dict[str, str]):
        """
        Create table if it doesn't exist
        
        Args:
            schema: Dictionary mapping column names to types
        """
        conn = self._get_connection()
        
        try:
            columns_def = ", ".join([f"{name} {dtype}" for name, dtype in schema.items()])
            query = f"""
                CREATE TABLE IF NOT EXISTS {self.config.table_name} (
                    {columns_def}
                )
            """
            
            conn.execute(query)
            logger.info(f"Created table: {self.config.table_name}")
            
        except Exception as e:
            logger.error(f"DuckDB create_table error: {e}")
            raise
