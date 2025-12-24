# Data Migration Guide: Desktop App → Web App

This guide will help you migrate your data from the Social Media Analytics Desktop Application to the new Web Application.

## Prerequisites

Before starting the migration:

1. **Register an account** in the web app at `https://your-webapp-url.com`
2. **Set up API credential profiles** for all platforms you want to migrate
3. **Locate your desktop app data** directory (usually `~/.social_media_analytics/data/`)
4. **Install migration dependencies**:
   ```bash
   pip install sqlalchemy psycopg2-binary
   ```

## Migration Steps

### Step 1: Backup Your Data

**IMPORTANT:** Always create a backup before migration!

```bash
# Copy your desktop app data directory
cp -r ~/.social_media_analytics/data /path/to/backup/location
```

### Step 2: Register in Web App

1. Go to the web app registration page
2. Create an account with your email and password
3. Verify your email (check your inbox)
4. Log in to the web app

### Step 3: Create API Profiles

For each platform you use, create an API credential profile:

1. Navigate to **Profile Management** page
2. Click **Add Profile**
3. Select platform (Twitch, Twitter, YouTube, Reddit)
4. Enter your API credentials
5. Save the profile

**Note:** Use the same API credentials you used in the desktop app.

### Step 4: Run Migration Script

```bash
# Navigate to migration directory
cd social_media_analytics_webapp/migration

# Set database connection (if not using environment variable)
export DATABASE_URL="postgresql://user:password@host:port/database"

# Run migration
python migrate_sqlite_to_postgresql.py \
    --user-email your.email@example.com \
    --sqlite-dir ~/.social_media_analytics/data
```

### Step 5: Verify Migration

1. Log in to the web app
2. Check each platform page to verify your data:
   - **Twitch**: Verify channels and stream records
   - **Twitter**: Verify users and tweets
   - **YouTube**: Verify channels and videos
   - **Reddit**: Verify subreddits and posts

## Migration Script Options

```bash
python migrate_sqlite_to_postgresql.py --help

Options:
  --user-email EMAIL        Your web app account email (required)
  --sqlite-dir DIR          Path to desktop app data directory (required)
  --postgres-url URL        PostgreSQL connection URL (optional, uses DATABASE_URL env var if not provided)
```

## Example Migrations

### Example 1: Basic Migration

```bash
python migrate_sqlite_to_postgresql.py \
    --user-email john@example.com \
    --sqlite-dir /Users/john/.social_media_analytics/data
```

### Example 2: Custom PostgreSQL URL

```bash
python migrate_sqlite_to_postgresql.py \
    --user-email jane@example.com \
    --sqlite-dir C:\Users\Jane\AppData\Local\SocialMediaAnalytics\data \
    --postgres-url postgresql://jane:password@db.example.com:5432/analytics
```

### Example 3: Production Migration

```bash
# Set environment variable for security
export DATABASE_URL="postgresql://user:pass@prod-db.amazonaws.com:5432/social_analytics"

# Run migration
python migrate_sqlite_to_postgresql.py \
    --user-email production.user@company.com \
    --sqlite-dir /data/desktop_app_backup/data
```

## Migration Output

The script will show progress and statistics:

```
============================================================
Starting Data Migration: SQLite → PostgreSQL
============================================================
2025-12-22 10:00:00 - INFO - Migrating data for user: john@example.com (ID: 42)
2025-12-22 10:00:01 - INFO - Starting Twitch data migration...
2025-12-22 10:00:01 - INFO - Migrated Twitch channel: summit1g
2025-12-22 10:00:02 - INFO - Twitch migration complete: 5 channels, 150 records
2025-12-22 10:00:02 - INFO - Starting Twitter data migration...
2025-12-22 10:00:03 - INFO - Migrated Twitter user: elonmusk
2025-12-22 10:00:05 - INFO - Twitter migration complete: 3 users, 250 tweets
...
============================================================
Migration Complete!
============================================================
Duration: 8.45 seconds
Statistics:
  Twitch: 5 channels, 150 records
  Twitter: 3 users, 250 tweets
  YouTube: 2 channels, 80 videos
  Reddit: 4 subreddits, 120 posts
```

## Troubleshooting

### Error: "User with email X not found in database"

**Solution:** Make sure you've registered an account in the web app first.

```bash
# Verify your email is correct
python migrate_sqlite_to_postgresql.py --user-email CORRECT_EMAIL@example.com --sqlite-dir ...
```

### Error: "No API profile found for platform 'twitch'"

**Solution:** Create API credential profiles in the web app before migrating.

1. Log in to web app
2. Go to Profile Management
3. Add profiles for all platforms you want to migrate

### Error: "SQLite database not found"

**Solution:** Check the path to your desktop app data directory.

```bash
# Find your data directory
# On macOS/Linux:
ls ~/.social_media_analytics/data/

# On Windows:
dir C:\Users\YourName\AppData\Local\SocialMediaAnalytics\data\

# Use the correct path in migration
python migrate_sqlite_to_postgresql.py --sqlite-dir /correct/path/to/data ...
```

### Error: "Connection to PostgreSQL failed"

**Solution:** Verify your PostgreSQL connection URL.

```bash
# Test connection
psql postgresql://user:password@host:port/database

# If successful, use the same URL in migration
```

### Duplicate Data Warning

**Behavior:** The migration script is idempotent - it skips data that already exists.

If you run the migration multiple times:
- Existing entities (channels, users, subreddits) are skipped
- Existing records (tweets, videos, posts) are skipped
- Only new data is added

This is safe and prevents duplicates.

## Data Mapping

### Desktop App → Web App

| Desktop App | Web App |
|-------------|---------|
| SQLite databases | PostgreSQL database |
| No user accounts | Multi-user with authentication |
| Local file storage | Cloud database |
| Single instance | Accessible from anywhere |

### Database Files

| Platform | Desktop DB File | Web App Table |
|----------|----------------|---------------|
| Twitch | `twitch_data.db` | `twitch_channels`, `twitch_stream_records` |
| Twitter | `twitter_data.db` | `twitter_users`, `tweets` |
| YouTube | `youtube_data.db` | `youtube_channels`, `youtube_videos` |
| Reddit | `reddit_data.db` | `reddit_subreddits`, `reddit_posts` |

## Post-Migration

### Start Monitoring

After migration, you can start monitoring your entities:

1. Navigate to platform page (e.g., Twitch)
2. Find your migrated channel
3. Click **Start Monitoring**
4. Set interval (e.g., 60 minutes)
5. Background job will collect new data automatically

### Set Up Analytics

Your historical data is now available for analytics:

1. Go to **Analytics** page
2. View engagement metrics
3. Analyze sentiment
4. Check trends and forecasts
5. Export reports

### Delete Desktop App Data (Optional)

Once you've verified the migration:

```bash
# Create final backup
cp -r ~/.social_media_analytics/data /final/backup/location

# Delete desktop app data (optional)
rm -rf ~/.social_media_analytics/data
```

**Note:** Keep the backup for at least 30 days to ensure nothing was missed.

## Support

If you encounter issues during migration:

1. Check the migration logs for specific errors
2. Review this troubleshooting section
3. Ensure all prerequisites are met
4. Contact support with:
   - Migration command used
   - Error message (full output)
   - Desktop app data directory structure

## FAQ

### Q: Can I migrate data for multiple users?

**A:** Yes, run the migration script once per user:

```bash
python migrate_sqlite_to_postgresql.py --user-email user1@example.com --sqlite-dir /path/to/user1/data
python migrate_sqlite_to_postgresql.py --user-email user2@example.com --sqlite-dir /path/to/user2/data
```

### Q: What happens to my monitoring jobs?

**A:** Monitoring jobs are NOT migrated. After migration:
1. Your data (channels, tweets, etc.) will be in the web app
2. You must manually start monitoring jobs again
3. Jobs will run automatically in the background

### Q: Will my analytics history be preserved?

**A:** Yes! All historical data (tweets, videos, posts, stream records) is migrated with timestamps, so your analytics will show the complete history.

### Q: Can I continue using the desktop app after migration?

**A:** Yes, but it's not recommended. The desktop app and web app have separate databases. Changes in one won't reflect in the other. We recommend using only the web app after migration.

### Q: How long does migration take?

**A:** It depends on data volume:
- Small (<1000 records): ~10-30 seconds
- Medium (1000-10000 records): ~30-120 seconds
- Large (>10000 records): ~2-5 minutes

### Q: Is the migration reversible?

**A:** The desktop app data remains unchanged (always backup first!). You can continue using the desktop app if needed, but the web app data cannot be migrated back to SQLite.

---

**Last Updated:** 2025-12-22
**Version:** 1.0.0
