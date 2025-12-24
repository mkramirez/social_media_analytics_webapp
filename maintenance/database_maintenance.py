"""
Database Maintenance and Optimization Script

Performs routine database maintenance including:
- VACUUM and ANALYZE operations
- Index rebuilding
- Statistics updates
- Cleanup of old data
- Connection pool management
- Query performance analysis

Usage:
    python database_maintenance.py --operation vacuum
    python database_maintenance.py --operation analyze
    python database_maintenance.py --operation cleanup --days 90
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import engine
from app.services.logging_service import logger


class DatabaseMaintenance:
    """Database maintenance operations."""

    def __init__(self, database_url: str = None):
        """Initialize database connection."""
        if database_url:
            self.conn = psycopg2.connect(database_url)
        else:
            # Use SQLAlchemy engine URL
            url = str(engine.url)
            self.conn = psycopg2.connect(url.replace("postgresql://", "postgresql+psycopg2://"))

        self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        self.cursor = self.conn.cursor()

        logger.info("Connected to database for maintenance")

    def vacuum_database(self, full: bool = False, analyze: bool = True):
        """
        Run VACUUM on database to reclaim storage and update statistics.

        Args:
            full: Run VACUUM FULL (locks tables, but reclaims more space)
            analyze: Also run ANALYZE to update statistics
        """
        logger.info("Starting database VACUUM operation...")

        try:
            if full:
                logger.warning("Running VACUUM FULL - this will lock tables!")
                command = "VACUUM FULL"
            else:
                command = "VACUUM"

            if analyze:
                command += " ANALYZE"

            self.cursor.execute(command)
            logger.info(f"✅ {command} completed successfully")

        except Exception as e:
            logger.error(f"VACUUM operation failed: {e}")
            raise

    def analyze_database(self):
        """Run ANALYZE to update query planner statistics."""
        logger.info("Running ANALYZE operation...")

        try:
            self.cursor.execute("ANALYZE")
            logger.info("✅ ANALYZE completed successfully")

        except Exception as e:
            logger.error(f"ANALYZE operation failed: {e}")
            raise

    def reindex_database(self):
        """Rebuild all indexes in the database."""
        logger.info("Rebuilding all indexes...")

        try:
            # Get all indexes
            self.cursor.execute("""
                SELECT schemaname, tablename, indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname
            """)

            indexes = self.cursor.fetchall()
            logger.info(f"Found {len(indexes)} indexes to rebuild")

            for schema, table, index in indexes:
                try:
                    logger.info(f"  Rebuilding {index}...")
                    self.cursor.execute(f"REINDEX INDEX {schema}.{index}")
                except Exception as e:
                    logger.warning(f"  Failed to rebuild {index}: {e}")

            logger.info("✅ Index rebuild completed")

        except Exception as e:
            logger.error(f"REINDEX operation failed: {e}")
            raise

    def cleanup_old_data(self, days: int = 90):
        """
        Clean up old data (older than specified days).

        Args:
            days: Delete data older than this many days
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        logger.info(f"Cleaning up data older than {days} days (before {cutoff_date})...")

        tables_to_clean = [
            ("job_executions", "completed_at"),
            ("twitch_stream_records", "recorded_at"),
            ("tweets", "fetched_at"),
            ("youtube_videos", "fetched_at"),
            ("reddit_posts", "fetched_at"),
            ("sentiment_cache", "created_at")
        ]

        total_deleted = 0

        for table, date_column in tables_to_clean:
            try:
                self.cursor.execute(f"""
                    DELETE FROM {table}
                    WHERE {date_column} < %s
                """, (cutoff_date,))

                deleted_count = self.cursor.rowcount
                total_deleted += deleted_count

                if deleted_count > 0:
                    logger.info(f"  Deleted {deleted_count} rows from {table}")

            except Exception as e:
                logger.warning(f"  Failed to clean {table}: {e}")

        logger.info(f"✅ Cleanup completed - {total_deleted} total rows deleted")

        # Run VACUUM after cleanup
        if total_deleted > 1000:
            logger.info("Running VACUUM after cleanup...")
            self.vacuum_database(full=False, analyze=True)

    def get_table_sizes(self) -> List[Dict[str, Any]]:
        """Get size information for all tables."""
        logger.info("Analyzing table sizes...")

        self.cursor.execute("""
            SELECT
                table_schema,
                table_name,
                pg_size_pretty(pg_total_relation_size(quote_ident(table_schema) || '.' || quote_ident(table_name))) AS size,
                pg_total_relation_size(quote_ident(table_schema) || '.' || quote_ident(table_name)) AS size_bytes
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY pg_total_relation_size(quote_ident(table_schema) || '.' || quote_ident(table_name)) DESC
        """)

        results = []
        for schema, table, size, size_bytes in self.cursor.fetchall():
            results.append({
                "schema": schema,
                "table": table,
                "size": size,
                "size_bytes": size_bytes
            })

        logger.info("Table sizes:")
        for result in results[:10]:  # Show top 10
            logger.info(f"  {result['table']}: {result['size']}")

        return results

    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get slow queries from pg_stat_statements.

        Note: Requires pg_stat_statements extension to be enabled.
        """
        logger.info("Fetching slow queries...")

        try:
            self.cursor.execute("""
                SELECT
                    query,
                    calls,
                    total_exec_time,
                    mean_exec_time,
                    max_exec_time
                FROM pg_stat_statements
                ORDER BY mean_exec_time DESC
                LIMIT %s
            """, (limit,))

            results = []
            for query, calls, total_time, mean_time, max_time in self.cursor.fetchall():
                results.append({
                    "query": query[:200],  # Truncate long queries
                    "calls": calls,
                    "total_time_ms": round(total_time, 2),
                    "mean_time_ms": round(mean_time, 2),
                    "max_time_ms": round(max_time, 2)
                })

            logger.info(f"Top {len(results)} slow queries:")
            for i, result in enumerate(results, 1):
                logger.info(f"  {i}. Mean: {result['mean_time_ms']}ms, Calls: {result['calls']}")
                logger.info(f"     Query: {result['query']}")

            return results

        except Exception as e:
            logger.warning(f"Could not fetch slow queries: {e}")
            logger.info("Enable pg_stat_statements extension to track query performance")
            return []

    def check_index_usage(self):
        """Check index usage statistics."""
        logger.info("Analyzing index usage...")

        self.cursor.execute("""
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch
            FROM pg_stat_user_indexes
            ORDER BY idx_scan ASC
            LIMIT 20
        """)

        unused_indexes = []
        for schema, table, index, scans, tuples_read, tuples_fetched in self.cursor.fetchall():
            if scans == 0:
                unused_indexes.append({
                    "table": table,
                    "index": index,
                    "scans": scans
                })

        if unused_indexes:
            logger.warning(f"Found {len(unused_indexes)} potentially unused indexes:")
            for idx in unused_indexes[:10]:
                logger.warning(f"  {idx['table']}.{idx['index']} - {idx['scans']} scans")
        else:
            logger.info("All indexes are being used")

    def check_bloat(self):
        """Check for table and index bloat."""
        logger.info("Checking for table bloat...")

        self.cursor.execute("""
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                round(100 * pg_total_relation_size(schemaname||'.'||tablename) /
                      NULLIF(pg_database_size(current_database()), 0), 2) AS percent_of_db
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 10
        """)

        logger.info("Largest tables:")
        for schema, table, size, percent in self.cursor.fetchall():
            logger.info(f"  {table}: {size} ({percent}% of database)")

    def update_statistics(self):
        """Update database statistics."""
        logger.info("Updating database statistics...")

        try:
            # Reset statistics
            self.cursor.execute("SELECT pg_stat_reset()")

            # Update table statistics
            self.analyze_database()

            logger.info("✅ Statistics updated successfully")

        except Exception as e:
            logger.error(f"Failed to update statistics: {e}")
            raise

    def check_connections(self):
        """Check database connection statistics."""
        logger.info("Checking database connections...")

        self.cursor.execute("""
            SELECT
                count(*) as total,
                count(*) FILTER (WHERE state = 'active') as active,
                count(*) FILTER (WHERE state = 'idle') as idle,
                count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
            FROM pg_stat_activity
            WHERE datname = current_database()
        """)

        total, active, idle, idle_in_tx = self.cursor.fetchone()

        logger.info(f"Connection statistics:")
        logger.info(f"  Total: {total}")
        logger.info(f"  Active: {active}")
        logger.info(f"  Idle: {idle}")
        logger.info(f"  Idle in transaction: {idle_in_tx}")

        if idle_in_tx > 5:
            logger.warning(f"⚠️  High number of idle in transaction connections ({idle_in_tx})")

    def run_full_maintenance(self, days_to_keep: int = 90):
        """Run complete maintenance routine."""
        logger.info("=" * 60)
        logger.info("Starting Full Database Maintenance")
        logger.info("=" * 60)

        # Cleanup old data
        self.cleanup_old_data(days=days_to_keep)

        # Vacuum and analyze
        self.vacuum_database(full=False, analyze=True)

        # Update statistics
        self.update_statistics()

        # Check table sizes
        self.get_table_sizes()

        # Check connections
        self.check_connections()

        # Check index usage
        self.check_index_usage()

        # Check for bloat
        self.check_bloat()

        # Get slow queries
        self.get_slow_queries()

        logger.info("=" * 60)
        logger.info("✅ Full Database Maintenance Completed")
        logger.info("=" * 60)

    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Database maintenance script")
    parser.add_argument(
        "--operation",
        choices=["vacuum", "analyze", "reindex", "cleanup", "full", "stats", "check"],
        default="full",
        help="Maintenance operation to perform"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Days of data to keep (for cleanup operation)"
    )
    parser.add_argument(
        "--database-url",
        help="Database URL (uses environment variable if not provided)"
    )

    args = parser.parse_args()

    try:
        maintenance = DatabaseMaintenance(database_url=args.database_url)

        if args.operation == "vacuum":
            maintenance.vacuum_database()
        elif args.operation == "analyze":
            maintenance.analyze_database()
        elif args.operation == "reindex":
            maintenance.reindex_database()
        elif args.operation == "cleanup":
            maintenance.cleanup_old_data(days=args.days)
        elif args.operation == "stats":
            maintenance.get_table_sizes()
            maintenance.get_slow_queries()
        elif args.operation == "check":
            maintenance.check_connections()
            maintenance.check_index_usage()
            maintenance.check_bloat()
        elif args.operation == "full":
            maintenance.run_full_maintenance(days_to_keep=args.days)

        maintenance.close()

    except Exception as e:
        logger.error(f"Maintenance failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
