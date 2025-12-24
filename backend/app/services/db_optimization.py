"""Database optimization utilities and index creation."""

from sqlalchemy import text, Index
from app.database import engine, SessionLocal


def create_performance_indexes():
    """
    Create database indexes for improved query performance.

    Indexes are created on frequently queried columns:
    - Foreign keys (user_id)
    - Timestamp columns (created_at, published_at, recorded_at)
    - Status flags (is_monitoring, is_active, is_live)
    - Platform-specific IDs (tweet_id, video_id, post_id, etc.)
    """
    session = SessionLocal()

    try:
        print("🔧 Creating performance indexes...")

        # Twitter indexes
        indexes = [
            # Tweet indexes
            "CREATE INDEX IF NOT EXISTS idx_tweets_user_id_created ON tweets(user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_tweets_twitter_user_created ON tweets(twitter_user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_tweets_tweet_id ON tweets(tweet_id)",

            # TwitterUser indexes
            "CREATE INDEX IF NOT EXISTS idx_twitter_users_monitoring ON twitter_users(user_id, is_monitoring)",
            "CREATE INDEX IF NOT EXISTS idx_twitter_users_username ON twitter_users(username)",

            # YouTube indexes
            "CREATE INDEX IF NOT EXISTS idx_youtube_videos_user_published ON youtube_videos(user_id, published_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_youtube_videos_channel_published ON youtube_videos(youtube_channel_id, published_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_youtube_videos_video_id ON youtube_videos(video_id)",

            # YouTubeChannel indexes
            "CREATE INDEX IF NOT EXISTS idx_youtube_channels_monitoring ON youtube_channels(user_id, is_monitoring)",
            "CREATE INDEX IF NOT EXISTS idx_youtube_channels_channel_name ON youtube_channels(channel_name)",

            # YouTubeComment indexes
            "CREATE INDEX IF NOT EXISTS idx_youtube_comments_video ON youtube_comments(youtube_video_id, created_at DESC)",

            # Reddit indexes
            "CREATE INDEX IF NOT EXISTS idx_reddit_posts_user_created ON reddit_posts(user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_reddit_posts_subreddit_created ON reddit_posts(reddit_subreddit_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_reddit_posts_post_id ON reddit_posts(post_id)",

            # RedditSubreddit indexes
            "CREATE INDEX IF NOT EXISTS idx_reddit_subreddits_monitoring ON reddit_subreddits(user_id, is_monitoring)",
            "CREATE INDEX IF NOT EXISTS idx_reddit_subreddits_name ON reddit_subreddits(subreddit_name)",

            # RedditComment indexes
            "CREATE INDEX IF NOT EXISTS idx_reddit_comments_post ON reddit_comments(reddit_post_id, created_at DESC)",

            # Twitch indexes
            "CREATE INDEX IF NOT EXISTS idx_stream_records_user_recorded ON stream_records(user_id, recorded_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_stream_records_channel_recorded ON stream_records(twitch_channel_id, recorded_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_stream_records_live ON stream_records(is_live, recorded_at DESC)",

            # TwitchChannel indexes
            "CREATE INDEX IF NOT EXISTS idx_twitch_channels_monitoring ON twitch_channels(user_id, is_monitoring)",
            "CREATE INDEX IF NOT EXISTS idx_twitch_channels_channel_name ON twitch_channels(channel_name)",

            # TwitchVOD indexes
            "CREATE INDEX IF NOT EXISTS idx_twitch_vods_channel_recorded ON twitch_vods(twitch_channel_id, recorded_at DESC)",

            # APIProfile indexes
            "CREATE INDEX IF NOT EXISTS idx_api_profiles_user_platform ON api_profiles(user_id, platform)",
            "CREATE INDEX IF NOT EXISTS idx_api_profiles_active ON api_profiles(user_id, platform, is_active)",

            # Analytics indexes
            "CREATE INDEX IF NOT EXISTS idx_sentiment_cache_user_hash ON sentiment_cache(user_id, text_hash)",
            "CREATE INDEX IF NOT EXISTS idx_sentiment_cache_created ON sentiment_cache(created_at DESC)",

            "CREATE INDEX IF NOT EXISTS idx_analytics_reports_user_type ON analytics_reports(user_id, report_type)",
            "CREATE INDEX IF NOT EXISTS idx_analytics_reports_platform ON analytics_reports(platform, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_analytics_reports_expires ON analytics_reports(expires_at)",

            # UserSession indexes
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(token)",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_expires ON user_sessions(user_id, expires_at)",

            # Composite indexes for common query patterns
            "CREATE INDEX IF NOT EXISTS idx_tweets_engagement ON tweets(user_id, likes DESC, retweets DESC)",
            "CREATE INDEX IF NOT EXISTS idx_youtube_videos_engagement ON youtube_videos(user_id, views DESC, likes DESC)",
            "CREATE INDEX IF NOT EXISTS idx_reddit_posts_engagement ON reddit_posts(user_id, upvotes DESC, num_comments DESC)",
        ]

        for index_sql in indexes:
            try:
                session.execute(text(index_sql))
                print(f"  ✓ Created index: {index_sql.split('idx_')[1].split(' ')[0] if 'idx_' in index_sql else 'custom'}")
            except Exception as e:
                print(f"  ✗ Failed to create index: {e}")

        session.commit()
        print(f"✅ Created {len(indexes)} performance indexes")

    except Exception as e:
        print(f"❌ Error creating indexes: {e}")
        session.rollback()

    finally:
        session.close()


def analyze_tables():
    """
    Analyze tables to update query planner statistics.

    Run after creating indexes or large data imports.
    """
    session = SessionLocal()

    try:
        print("📊 Analyzing database tables...")

        tables = [
            "users", "api_profiles", "user_sessions",
            "tweets", "twitter_users",
            "youtube_videos", "youtube_channels", "youtube_comments",
            "reddit_posts", "reddit_subreddits", "reddit_comments",
            "stream_records", "twitch_channels", "twitch_vods",
            "sentiment_cache", "analytics_reports"
        ]

        for table in tables:
            try:
                session.execute(text(f"ANALYZE {table}"))
                print(f"  ✓ Analyzed: {table}")
            except Exception as e:
                print(f"  ✗ Failed to analyze {table}: {e}")

        session.commit()
        print("✅ Database analysis complete")

    except Exception as e:
        print(f"❌ Error analyzing tables: {e}")
        session.rollback()

    finally:
        session.close()


def get_slow_queries_report():
    """
    Get report of slow queries (PostgreSQL specific).

    Requires pg_stat_statements extension.

    Returns:
        List of slow query statistics
    """
    session = SessionLocal()

    try:
        # Check if pg_stat_statements is available
        result = session.execute(text("""
            SELECT EXISTS (
                SELECT 1
                FROM pg_extension
                WHERE extname = 'pg_stat_statements'
            )
        """))

        if not result.scalar():
            print("⚠️ pg_stat_statements extension not installed")
            return []

        # Get top 10 slowest queries
        result = session.execute(text("""
            SELECT
                query,
                calls,
                mean_exec_time,
                max_exec_time,
                total_exec_time
            FROM pg_stat_statements
            ORDER BY mean_exec_time DESC
            LIMIT 10
        """))

        queries = []
        for row in result:
            queries.append({
                "query": row[0][:200],  # Truncate long queries
                "calls": row[1],
                "mean_time_ms": round(row[2], 2),
                "max_time_ms": round(row[3], 2),
                "total_time_ms": round(row[4], 2)
            })

        return queries

    except Exception as e:
        print(f"❌ Error getting slow queries: {e}")
        return []

    finally:
        session.close()


def vacuum_database():
    """
    Vacuum database to reclaim storage and update statistics.

    Should be run periodically in production.
    """
    session = SessionLocal()

    try:
        print("🧹 Vacuuming database...")

        # Note: VACUUM cannot run inside a transaction block
        session.connection().connection.set_isolation_level(0)

        session.execute(text("VACUUM ANALYZE"))

        print("✅ Database vacuum complete")

    except Exception as e:
        print(f"❌ Error vacuuming database: {e}")

    finally:
        session.close()


def get_table_sizes():
    """
    Get size statistics for all tables.

    Returns:
        List of table size information
    """
    session = SessionLocal()

    try:
        result = session.execute(text("""
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """))

        tables = []
        for row in result:
            tables.append({
                "schema": row[0],
                "table": row[1],
                "size": row[2],
                "size_bytes": row[3]
            })

        return tables

    except Exception as e:
        print(f"❌ Error getting table sizes: {e}")
        return []

    finally:
        session.close()


if __name__ == "__main__":
    """Run database optimizations."""
    print("=" * 50)
    print("DATABASE OPTIMIZATION UTILITY")
    print("=" * 50)

    # Create indexes
    create_performance_indexes()

    # Analyze tables
    analyze_tables()

    # Show table sizes
    print("\n📊 Table Sizes:")
    sizes = get_table_sizes()
    for table_info in sizes[:10]:  # Show top 10
        print(f"  {table_info['table']}: {table_info['size']}")

    print("\n✅ Optimization complete!")
