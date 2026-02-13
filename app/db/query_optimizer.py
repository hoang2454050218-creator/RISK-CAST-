"""
Database query optimizer for RISKCAST.

This module implements GAP B4.1: Query optimization not implemented.
Analyzes and optimizes database queries for better performance.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import re
import structlog

logger = structlog.get_logger(__name__)


class QueryType(str, Enum):
    """Types of SQL queries."""
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    OTHER = "other"


class OptimizationPriority(str, Enum):
    """Priority levels for optimization suggestions."""
    CRITICAL = "critical"  # Must fix
    HIGH = "high"          # Should fix
    MEDIUM = "medium"      # Nice to have
    LOW = "low"            # Minor improvement


@dataclass
class IndexSuggestion:
    """Suggested index for optimization."""
    table_name: str
    columns: List[str]
    index_type: str  # btree, hash, gin, gist
    reason: str
    estimated_improvement_pct: float
    priority: OptimizationPriority
    
    @property
    def index_name(self) -> str:
        """Generate index name."""
        cols = "_".join(self.columns[:3])
        return f"idx_{self.table_name}_{cols}"
    
    @property
    def create_statement(self) -> str:
        """Generate CREATE INDEX statement."""
        cols = ", ".join(self.columns)
        return (
            f"CREATE INDEX {self.index_name} "
            f"ON {self.table_name} ({cols})"
        )


@dataclass
class QueryRewrite:
    """Suggested query rewrite."""
    original_query: str
    optimized_query: str
    reason: str
    estimated_improvement_pct: float
    priority: OptimizationPriority


@dataclass
class QueryAnalysis:
    """Analysis of a single query."""
    query_hash: str
    query_text: str
    query_type: QueryType
    
    # Performance metrics
    avg_execution_time_ms: float
    max_execution_time_ms: float
    execution_count: int
    total_time_ms: float
    
    # Analysis results
    tables_accessed: List[str]
    columns_filtered: List[str]
    columns_ordered: List[str]
    columns_grouped: List[str]
    joins: List[Tuple[str, str, str]]  # (table1, table2, condition)
    
    # Issues detected
    issues: List[str] = field(default_factory=list)
    
    # Suggestions
    index_suggestions: List[IndexSuggestion] = field(default_factory=list)
    rewrites: List[QueryRewrite] = field(default_factory=list)
    
    @property
    def score(self) -> float:
        """Calculate optimization priority score."""
        # Higher score = more important to optimize
        time_factor = self.total_time_ms / 1000  # Seconds of total time
        issue_factor = len(self.issues) * 10
        return time_factor + issue_factor


@dataclass
class OptimizationReport:
    """Complete optimization report."""
    report_id: str
    generated_at: datetime
    period_hours: int
    
    # Summary
    queries_analyzed: int
    total_execution_time_ms: float
    queries_with_issues: int
    
    # Top issues
    slow_queries: List[QueryAnalysis]
    missing_indexes: List[IndexSuggestion]
    rewrite_suggestions: List[QueryRewrite]
    
    # Estimated impact
    estimated_time_savings_pct: float
    
    # Action items
    priority_actions: List[str]


class QueryParser:
    """Parse SQL queries to extract structure."""
    
    # Regex patterns for SQL parsing
    _SELECT_PATTERN = re.compile(
        r"SELECT\s+(.+?)\s+FROM\s+(\w+)",
        re.IGNORECASE | re.DOTALL
    )
    _WHERE_PATTERN = re.compile(
        r"WHERE\s+(.+?)(?:ORDER BY|GROUP BY|LIMIT|$)",
        re.IGNORECASE | re.DOTALL
    )
    _ORDER_PATTERN = re.compile(
        r"ORDER BY\s+(.+?)(?:LIMIT|$)",
        re.IGNORECASE | re.DOTALL
    )
    _GROUP_PATTERN = re.compile(
        r"GROUP BY\s+(.+?)(?:ORDER BY|HAVING|LIMIT|$)",
        re.IGNORECASE | re.DOTALL
    )
    _JOIN_PATTERN = re.compile(
        r"(LEFT |RIGHT |INNER |OUTER )?JOIN\s+(\w+)\s+(?:AS\s+)?(\w+)?\s+ON\s+(.+?)(?:LEFT|RIGHT|INNER|OUTER|JOIN|WHERE|ORDER|GROUP|LIMIT|$)",
        re.IGNORECASE | re.DOTALL
    )
    _COLUMN_PATTERN = re.compile(r"(\w+)\.(\w+)|(\w+)")
    
    def parse(self, query: str) -> Dict[str, Any]:
        """Parse a SQL query."""
        query_type = self._detect_type(query)
        
        result = {
            "type": query_type,
            "tables": [],
            "columns_selected": [],
            "columns_filtered": [],
            "columns_ordered": [],
            "columns_grouped": [],
            "joins": [],
        }
        
        if query_type == QueryType.SELECT:
            result.update(self._parse_select(query))
        
        return result
    
    def _detect_type(self, query: str) -> QueryType:
        """Detect query type."""
        query_upper = query.strip().upper()
        
        if query_upper.startswith("SELECT"):
            return QueryType.SELECT
        elif query_upper.startswith("INSERT"):
            return QueryType.INSERT
        elif query_upper.startswith("UPDATE"):
            return QueryType.UPDATE
        elif query_upper.startswith("DELETE"):
            return QueryType.DELETE
        return QueryType.OTHER
    
    def _parse_select(self, query: str) -> Dict[str, Any]:
        """Parse SELECT query."""
        result = {
            "tables": [],
            "columns_selected": [],
            "columns_filtered": [],
            "columns_ordered": [],
            "columns_grouped": [],
            "joins": [],
        }
        
        # Extract main table
        select_match = self._SELECT_PATTERN.search(query)
        if select_match:
            result["tables"].append(select_match.group(2))
        
        # Extract WHERE columns
        where_match = self._WHERE_PATTERN.search(query)
        if where_match:
            where_clause = where_match.group(1)
            result["columns_filtered"] = self._extract_columns(where_clause)
        
        # Extract ORDER BY columns
        order_match = self._ORDER_PATTERN.search(query)
        if order_match:
            order_clause = order_match.group(1)
            result["columns_ordered"] = self._extract_columns(order_clause)
        
        # Extract GROUP BY columns
        group_match = self._GROUP_PATTERN.search(query)
        if group_match:
            group_clause = group_match.group(1)
            result["columns_grouped"] = self._extract_columns(group_clause)
        
        # Extract JOINs
        for join_match in self._JOIN_PATTERN.finditer(query):
            join_type = join_match.group(1) or "INNER"
            table = join_match.group(2)
            result["tables"].append(table)
            result["joins"].append((
                result["tables"][0] if result["tables"] else "",
                table,
                join_match.group(4).strip(),
            ))
        
        return result
    
    def _extract_columns(self, clause: str) -> List[str]:
        """Extract column names from a clause."""
        columns = []
        for match in self._COLUMN_PATTERN.finditer(clause):
            if match.group(2):
                columns.append(match.group(2))
            elif match.group(3) and match.group(3).upper() not in (
                "AND", "OR", "NOT", "IN", "BETWEEN", "LIKE", "IS", "NULL",
                "TRUE", "FALSE", "ASC", "DESC"
            ):
                columns.append(match.group(3))
        return list(set(columns))


class QueryOptimizer:
    """
    Analyzes and optimizes database queries.
    
    Provides index suggestions, query rewrites, and performance analysis.
    """
    
    def __init__(
        self,
        db_connection: Optional[Any] = None,
    ):
        self._db = db_connection
        self._parser = QueryParser()
        self._query_stats: Dict[str, QueryAnalysis] = {}
        self._existing_indexes: Set[str] = set()
        
        # Optimization rules
        self._slow_query_threshold_ms = 100  # Queries slower than this
        self._index_benefit_threshold = 1000  # Rows to benefit from index
    
    def record_query(
        self,
        query: str,
        execution_time_ms: float,
        rows_affected: int = 0,
    ) -> None:
        """Record a query execution for analysis."""
        import hashlib
        
        # Normalize query for grouping
        normalized = self._normalize_query(query)
        query_hash = hashlib.md5(normalized.encode()).hexdigest()[:16]
        
        if query_hash in self._query_stats:
            stats = self._query_stats[query_hash]
            stats.execution_count += 1
            stats.total_time_ms += execution_time_ms
            stats.avg_execution_time_ms = (
                stats.total_time_ms / stats.execution_count
            )
            stats.max_execution_time_ms = max(
                stats.max_execution_time_ms,
                execution_time_ms
            )
        else:
            parsed = self._parser.parse(query)
            self._query_stats[query_hash] = QueryAnalysis(
                query_hash=query_hash,
                query_text=query,
                query_type=parsed["type"],
                avg_execution_time_ms=execution_time_ms,
                max_execution_time_ms=execution_time_ms,
                execution_count=1,
                total_time_ms=execution_time_ms,
                tables_accessed=parsed.get("tables", []),
                columns_filtered=parsed.get("columns_filtered", []),
                columns_ordered=parsed.get("columns_ordered", []),
                columns_grouped=parsed.get("columns_grouped", []),
                joins=parsed.get("joins", []),
            )
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for grouping similar queries."""
        # Replace literal values with placeholders
        normalized = re.sub(r"'[^']*'", "'?'", query)
        normalized = re.sub(r"\b\d+\b", "?", normalized)
        # Remove extra whitespace
        normalized = " ".join(normalized.split())
        return normalized.lower()
    
    def analyze_query(self, query: str) -> QueryAnalysis:
        """Analyze a single query for optimization opportunities."""
        import hashlib
        
        parsed = self._parser.parse(query)
        query_hash = hashlib.md5(query.encode()).hexdigest()[:16]
        
        analysis = QueryAnalysis(
            query_hash=query_hash,
            query_text=query,
            query_type=parsed["type"],
            avg_execution_time_ms=0,
            max_execution_time_ms=0,
            execution_count=0,
            total_time_ms=0,
            tables_accessed=parsed.get("tables", []),
            columns_filtered=parsed.get("columns_filtered", []),
            columns_ordered=parsed.get("columns_ordered", []),
            columns_grouped=parsed.get("columns_grouped", []),
            joins=parsed.get("joins", []),
        )
        
        # Detect issues
        analysis.issues = self._detect_issues(analysis)
        
        # Generate suggestions
        analysis.index_suggestions = self._suggest_indexes(analysis)
        analysis.rewrites = self._suggest_rewrites(analysis)
        
        return analysis
    
    def _detect_issues(self, analysis: QueryAnalysis) -> List[str]:
        """Detect potential issues with a query."""
        issues = []
        
        query_upper = analysis.query_text.upper()
        
        # SELECT * detection
        if "SELECT *" in query_upper:
            issues.append("SELECT * should be replaced with specific columns")
        
        # Missing WHERE clause on UPDATE/DELETE
        if analysis.query_type in [QueryType.UPDATE, QueryType.DELETE]:
            if "WHERE" not in query_upper:
                issues.append(
                    f"{analysis.query_type.value.upper()} without WHERE clause"
                )
        
        # OR in WHERE clause (often inefficient)
        if " OR " in query_upper and "WHERE" in query_upper:
            issues.append("OR in WHERE clause may prevent index usage")
        
        # LIKE with leading wildcard
        if re.search(r"LIKE\s+'%", query_upper):
            issues.append("LIKE with leading wildcard prevents index usage")
        
        # Functions on indexed columns
        for col in analysis.columns_filtered:
            if re.search(rf"(UPPER|LOWER|DATE|EXTRACT)\s*\(\s*{col}", query_upper):
                issues.append(f"Function on column {col} prevents index usage")
        
        # Missing LIMIT on large result sets
        if (
            analysis.query_type == QueryType.SELECT
            and "LIMIT" not in query_upper
            and len(analysis.joins) > 0
        ):
            issues.append("Consider adding LIMIT to prevent large result sets")
        
        # Implicit type conversion
        if re.search(r"=\s*'\d+'", analysis.query_text):
            issues.append("Potential implicit type conversion (string to number)")
        
        # N+1 query pattern detection
        if (
            analysis.execution_count > 10
            and analysis.avg_execution_time_ms < 5
        ):
            issues.append("Possible N+1 query pattern - consider batching")
        
        return issues
    
    def _suggest_indexes(self, analysis: QueryAnalysis) -> List[IndexSuggestion]:
        """Suggest indexes based on query analysis."""
        suggestions = []
        
        for table in analysis.tables_accessed:
            # Index for WHERE columns
            if analysis.columns_filtered:
                # Check if index might already exist
                potential_index = f"idx_{table}_" + "_".join(
                    analysis.columns_filtered[:2]
                )
                if potential_index not in self._existing_indexes:
                    suggestions.append(IndexSuggestion(
                        table_name=table,
                        columns=analysis.columns_filtered[:3],
                        index_type="btree",
                        reason="Columns used in WHERE clause",
                        estimated_improvement_pct=30.0,
                        priority=OptimizationPriority.HIGH,
                    ))
            
            # Index for ORDER BY columns
            if analysis.columns_ordered:
                suggestions.append(IndexSuggestion(
                    table_name=table,
                    columns=analysis.columns_ordered[:2],
                    index_type="btree",
                    reason="Columns used in ORDER BY",
                    estimated_improvement_pct=20.0,
                    priority=OptimizationPriority.MEDIUM,
                ))
            
            # Covering index for frequently joined tables
            if analysis.joins:
                for t1, t2, condition in analysis.joins:
                    if t2 == table:
                        join_cols = self._parser._extract_columns(condition)
                        if join_cols:
                            suggestions.append(IndexSuggestion(
                                table_name=table,
                                columns=join_cols[:2],
                                index_type="btree",
                                reason=f"Join condition with {t1}",
                                estimated_improvement_pct=40.0,
                                priority=OptimizationPriority.HIGH,
                            ))
        
        return suggestions
    
    def _suggest_rewrites(self, analysis: QueryAnalysis) -> List[QueryRewrite]:
        """Suggest query rewrites for optimization."""
        rewrites = []
        query = analysis.query_text
        query_upper = query.upper()
        
        # SELECT * -> specific columns
        if "SELECT *" in query_upper:
            # Can't know specific columns without schema
            rewrites.append(QueryRewrite(
                original_query=query,
                optimized_query=query.replace("SELECT *", "SELECT <specific_columns>"),
                reason="SELECT specific columns instead of *",
                estimated_improvement_pct=10.0,
                priority=OptimizationPriority.MEDIUM,
            ))
        
        # OR -> UNION
        if " OR " in query_upper and "WHERE" in query_upper:
            rewrites.append(QueryRewrite(
                original_query=query,
                optimized_query="Consider using UNION instead of OR",
                reason="UNION can use indexes better than OR",
                estimated_improvement_pct=25.0,
                priority=OptimizationPriority.MEDIUM,
            ))
        
        # NOT IN -> NOT EXISTS
        if "NOT IN" in query_upper:
            rewrites.append(QueryRewrite(
                original_query=query,
                optimized_query=re.sub(
                    r"NOT IN\s*\(SELECT",
                    "NOT EXISTS (SELECT 1 FROM",
                    query,
                    flags=re.IGNORECASE
                ),
                reason="NOT EXISTS is often faster than NOT IN",
                estimated_improvement_pct=20.0,
                priority=OptimizationPriority.MEDIUM,
            ))
        
        # COUNT(*) -> COUNT(1)
        if "COUNT(*)" in query_upper:
            rewrites.append(QueryRewrite(
                original_query=query,
                optimized_query=query.replace("COUNT(*)", "COUNT(1)"),
                reason="COUNT(1) can be slightly faster",
                estimated_improvement_pct=5.0,
                priority=OptimizationPriority.LOW,
            ))
        
        return rewrites
    
    def generate_report(
        self,
        period_hours: int = 24,
    ) -> OptimizationReport:
        """Generate optimization report."""
        import uuid
        
        now = datetime.utcnow()
        
        # Get all recorded queries
        all_queries = list(self._query_stats.values())
        
        # Analyze each query
        for query in all_queries:
            query.issues = self._detect_issues(query)
            query.index_suggestions = self._suggest_indexes(query)
            query.rewrites = self._suggest_rewrites(query)
        
        # Sort by optimization score
        sorted_queries = sorted(all_queries, key=lambda q: q.score, reverse=True)
        
        # Collect all suggestions
        all_indexes: Dict[str, IndexSuggestion] = {}
        all_rewrites: List[QueryRewrite] = []
        
        for query in sorted_queries:
            for idx in query.index_suggestions:
                key = f"{idx.table_name}:{','.join(idx.columns)}"
                if key not in all_indexes:
                    all_indexes[key] = idx
            all_rewrites.extend(query.rewrites)
        
        # Calculate totals
        total_time = sum(q.total_time_ms for q in all_queries)
        queries_with_issues = sum(1 for q in all_queries if q.issues)
        
        # Estimate savings
        estimated_savings = 0.0
        for idx in all_indexes.values():
            estimated_savings += idx.estimated_improvement_pct
        estimated_savings = min(50.0, estimated_savings / max(1, len(all_indexes)))
        
        # Generate priority actions
        actions = []
        
        # Add index creation actions
        for idx in sorted(
            all_indexes.values(),
            key=lambda i: i.estimated_improvement_pct,
            reverse=True
        )[:5]:
            actions.append(idx.create_statement)
        
        # Add top issues
        for query in sorted_queries[:3]:
            if query.issues:
                actions.append(f"Fix: {query.issues[0]} in query {query.query_hash}")
        
        return OptimizationReport(
            report_id=f"opt_{uuid.uuid4().hex[:12]}",
            generated_at=now,
            period_hours=period_hours,
            queries_analyzed=len(all_queries),
            total_execution_time_ms=total_time,
            queries_with_issues=queries_with_issues,
            slow_queries=sorted_queries[:10],
            missing_indexes=list(all_indexes.values()),
            rewrite_suggestions=all_rewrites[:10],
            estimated_time_savings_pct=estimated_savings,
            priority_actions=actions,
        )
    
    async def explain_query(self, query: str) -> Dict[str, Any]:
        """Get query execution plan (requires database connection)."""
        if not self._db:
            return {"error": "No database connection"}
        
        try:
            # This would execute EXPLAIN ANALYZE
            result = await self._db.fetch_one(f"EXPLAIN ANALYZE {query}")
            return {"plan": result}
        except Exception as e:
            return {"error": str(e)}
    
    def register_existing_index(self, index_name: str) -> None:
        """Register an existing index to avoid duplicate suggestions."""
        self._existing_indexes.add(index_name)
    
    def clear_stats(self) -> None:
        """Clear recorded query statistics."""
        self._query_stats.clear()
        logger.info("query_stats_cleared")
