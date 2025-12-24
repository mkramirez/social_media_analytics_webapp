# Social Media Analytics Platform - User Guide

Welcome to the Social Media Analytics Platform! This guide will help you get started with monitoring and analyzing your social media presence across multiple platforms.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Platform Setup](#platform-setup)
3. [Monitoring](#monitoring)
4. [Analytics](#analytics)
5. [Export & Reports](#export--reports)
6. [Advanced Features](#advanced-features)
7. [Troubleshooting](#troubleshooting)

---

## Getting Started

### 1. Create Your Account

1. Navigate to the platform homepage
2. Click **Sign Up**
3. Enter your email and create a strong password
4. Click **Register**
5. Check your email for a verification link
6. Click the verification link to activate your account

### 2. Log In

1. Navigate to the login page
2. Enter your email and password
3. Click **Log In**
4. You'll be redirected to the dashboard

### 3. Dashboard Overview

After logging in, you'll see the main dashboard with:
- **Platform Overview**: Summary of all monitored platforms
- **Recent Activity**: Latest data collected
- **Active Jobs**: Currently running monitoring jobs
- **Quick Stats**: Total engagement, sentiment scores, etc.

---

## Platform Setup

Before you can start monitoring, you need to set up API credentials for each platform you want to use.

### Twitch Setup

1. Navigate to **Profile Management**
2. Click **Add Profile**
3. Select **Twitch** as the platform
4. Enter the following:
   - **Profile Name**: A friendly name (e.g., "My Twitch Account")
   - **Client ID**: Your Twitch application client ID
   - **Client Secret**: Your Twitch application client secret
5. Click **Save**

**How to get Twitch API credentials:**
1. Go to [Twitch Developers Console](https://dev.twitch.tv/console)
2. Click **Register Your Application**
3. Fill in the application details
4. Copy your **Client ID** and **Client Secret**

### Twitter Setup

1. Navigate to **Profile Management**
2. Click **Add Profile**
3. Select **Twitter** as the platform
4. Enter:
   - **Profile Name**: A friendly name (e.g., "My Twitter Account")
   - **Bearer Token**: Your Twitter API bearer token
5. Click **Save**

**How to get Twitter API credentials:**
1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Create a new project and app
3. Navigate to **Keys and Tokens**
4. Generate a **Bearer Token**

### YouTube Setup

1. Navigate to **Profile Management**
2. Click **Add Profile**
3. Select **YouTube** as the platform
4. Enter:
   - **Profile Name**: A friendly name (e.g., "My YouTube Account")
   - **API Key**: Your YouTube Data API key
5. Click **Save**

**How to get YouTube API credentials:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable **YouTube Data API v3**
4. Create credentials (API Key)

### Reddit Setup

1. Navigate to **Profile Management**
2. Click **Add Profile**
3. Select **Reddit** as the platform
4. Enter:
   - **Profile Name**: A friendly name (e.g., "My Reddit Account")
   - **Client ID**: Your Reddit app client ID
   - **Client Secret**: Your Reddit app client secret
   - **User Agent**: A unique identifier for your app
5. Click **Save**

**How to get Reddit API credentials:**
1. Go to [Reddit App Preferences](https://www.reddit.com/prefs/apps)
2. Click **Create App** or **Create Another App**
3. Select **script** as the app type
4. Note your **client ID** and **client secret**

---

## Monitoring

### Add Entities to Monitor

#### Twitch Channels

1. Navigate to **Twitch** page
2. Select **Single Channel** tab
3. Click **Add Channel**
4. Enter:
   - **API Profile**: Select your Twitch profile
   - **Channel Name**: The streamer's username (e.g., "summit1g")
5. Click **Add**

**Bulk Add:**
1. Select **Bulk Add** tab
2. Enter multiple channel names (one per line)
3. Click **Add All**

#### Twitter Users

1. Navigate to **Twitter** page
2. Click **Add User**
3. Enter:
   - **API Profile**: Select your Twitter profile
   - **Username**: The Twitter username (without @)
4. Click **Add**

**Bulk Add:** Use the bulk add feature to add multiple users at once

#### YouTube Channels

1. Navigate to **YouTube** page
2. Click **Add Channel**
3. Enter:
   - **API Profile**: Select your YouTube profile
   - **Channel ID**: The YouTube channel ID (e.g., "UC...")
4. Click **Add**

**How to find YouTube Channel ID:**
- Visit the channel page
- Click on the channel name
- Look at the URL: `youtube.com/channel/[CHANNEL_ID]`

#### Reddit Subreddits

1. Navigate to **Reddit** page
2. Click **Add Subreddit**
3. Enter:
   - **API Profile**: Select your Reddit profile
   - **Subreddit Name**: The subreddit name (without r/)
4. Click **Add**

### Start Monitoring

1. Find the entity you want to monitor (channel, user, subreddit)
2. Click **Start Monitoring**
3. Set the monitoring interval:
   - **15 minutes**: Very frequent (high API usage)
   - **60 minutes**: Recommended for most use cases
   - **120 minutes**: For less active entities
   - **Custom**: Set your own interval
4. Click **Start**

The platform will now automatically collect data at the specified interval.

### Monitor Your Jobs

1. Navigate to **Jobs** page to see all active monitoring jobs
2. For each job, you can:
   - **Pause**: Temporarily stop monitoring
   - **Resume**: Continue monitoring
   - **Delete**: Stop and remove the job
   - **View History**: See execution history

---

## Analytics

### Engagement Analytics

View engagement metrics across all platforms:

1. Navigate to **Analytics** page
2. Select **Engagement** tab
3. Choose:
   - **Time Range**: 7, 30, or 90 days
   - **Platforms**: Select which platforms to include
4. View metrics:
   - Total engagement (likes, views, scores)
   - Engagement trends over time
   - Top performing content
   - Engagement rate

**Interpreting Engagement Levels:**
- **Excellent**: Top 10% of content
- **High**: Above average performance
- **Medium**: Average performance
- **Low**: Below average performance

### Sentiment Analysis

Analyze the sentiment of text content:

1. Navigate to **Analytics** page
2. Select **Sentiment** tab
3. Choose:
   - **Platform**: Twitter, YouTube comments, Reddit posts
   - **Time Range**: How far back to analyze
4. View:
   - **Average Sentiment**: Overall positive/neutral/negative
   - **Sentiment Distribution**: Breakdown by category
   - **Sentiment Trends**: How sentiment changes over time
   - **Top Positive/Negative**: Specific content examples

**Sentiment Scores:**
- **Positive (0.05 to 1.0)**: Positive sentiment
- **Neutral (-0.05 to 0.05)**: Neutral sentiment
- **Negative (-1.0 to -0.05)**: Negative sentiment

### Trend Analysis

Identify trends and patterns:

1. Navigate to **Analytics** page
2. Select **Trends** tab
3. View:
   - **Engagement Trends**: Are your metrics improving?
   - **Posting Frequency**: How often content is posted
   - **Growth Rate**: Rate of follower/subscriber growth
   - **Forecasts**: Predicted future performance

### Best Posting Times

Find the optimal times to post:

1. Navigate to **Analytics** page
2. Select **Posting Times** tab
3. View:
   - **Heatmap**: Best hours and days to post
   - **Top Hours**: Specific hours with highest engagement
   - **Top Days**: Best days of the week
4. Use these insights to schedule your content

---

## Export & Reports

### Export to CSV

Export your data for external analysis:

1. Navigate to **Export** page
2. Select:
   - **Platform**: Choose which platform to export
   - **Time Range**: How much data to include
   - **Data Type**: All data or specific metrics
3. Click **Export to CSV**
4. Download the generated file

**CSV Files Include:**
- All timestamps
- All engagement metrics
- Content text (where applicable)
- Platform-specific data

### Generate Summary Report

Get a comprehensive summary:

1. Navigate to **Export** page
2. Select **Summary Report** tab
3. Choose:
   - **Platforms**: Which platforms to include
   - **Time Range**: Report period
4. Click **Generate Report**
5. View or download the summary

**Report Includes:**
- Total engagement across platforms
- Sentiment analysis summary
- Top performing content
- Key trends and insights
- Recommendations

---

## Advanced Features

### Real-Time Updates

Monitor changes in real-time:

1. Navigate to **Real-Time** page
2. Connected to WebSocket automatically
3. See live updates as data is collected:
   - New stream going live (Twitch)
   - New tweets posted (Twitter)
   - New videos uploaded (YouTube)
   - New posts in subreddit (Reddit)

### Cross-Platform Comparison

Compare performance across platforms:

1. Navigate to **Analytics** → **Dashboard**
2. View cross-platform metrics:
   - Which platform has highest engagement?
   - Where is sentiment most positive?
   - Which platform is growing fastest?
3. Use insights to focus your efforts

### Bulk Operations

Manage multiple entities efficiently:

**Bulk Add:**
- Add multiple channels/users at once
- Upload from CSV file

**Bulk Actions:**
- Start/stop monitoring for multiple entities
- Delete multiple entities
- Export data for multiple entities

---

## Troubleshooting

### "Invalid Credentials" Error

**Problem:** Your API credentials are not working.

**Solution:**
1. Verify credentials in the platform's developer portal
2. Update your profile with new credentials
3. Restart monitoring jobs

### "Rate Limit Exceeded" Error

**Problem:** You've hit the API rate limit.

**Solution:**
1. Increase monitoring interval (e.g., 60 min → 120 min)
2. Reduce number of monitored entities
3. Wait for rate limit to reset (usually 15 minutes)
4. Consider upgrading your API tier with the platform

### Missing Data

**Problem:** Some data is not appearing.

**Solution:**
1. Check if monitoring job is active
2. View job execution history for errors
3. Verify entity exists and is public
4. Check API credentials are still valid

### Slow Performance

**Problem:** Dashboard or analytics loading slowly.

**Solution:**
1. Reduce time range (e.g., 90 days → 30 days)
2. Clear browser cache
3. Select fewer platforms for comparison
4. Contact support if issue persists

### Can't Start Monitoring

**Problem:** Unable to start a monitoring job.

**Solution:**
1. Ensure you have an API profile set up
2. Verify API credentials are valid
3. Check that you haven't exceeded job limits
4. Try pausing other jobs first

---

## Best Practices

### Monitoring Intervals

- **High Priority**: 15-30 minutes
- **Regular Monitoring**: 60 minutes (recommended)
- **Background Monitoring**: 120+ minutes

### API Usage

- Start with longer intervals, decrease if needed
- Monitor only entities you actively track
- Pause monitoring for inactive entities
- Use bulk operations to save time

### Analytics

- Check analytics weekly for trends
- Compare month-over-month performance
- Use sentiment analysis to guide content strategy
- Export data monthly for long-term tracking

### Data Management

- Regularly export and backup your data
- Remove entities you no longer track
- Keep API credentials up to date
- Review job execution history for errors

---

## Keyboard Shortcuts

- `Ctrl + D`: Go to Dashboard
- `Ctrl + A`: Go to Analytics
- `Ctrl + J`: Go to Jobs
- `Ctrl + E`: Go to Export
- `Ctrl + S`: Save current form
- `Escape`: Close modal/dialog

---

## Support

Need help? Contact us:

- **Email**: support@socialmediaanalytics.com
- **Documentation**: https://docs.socialmediaanalytics.com
- **Community Forum**: https://community.socialmediaanalytics.com
- **GitHub Issues**: https://github.com/yourorg/social-analytics/issues

---

## Changelog

### Version 1.0.0 (2025-12-22)
- Initial release
- Multi-platform monitoring (Twitch, Twitter, YouTube, Reddit)
- Real-time analytics and sentiment analysis
- CSV export functionality
- WebSocket real-time updates

---

**Thank you for using Social Media Analytics Platform!**

We hope this tool helps you gain valuable insights into your social media presence. If you have feature requests or feedback, please let us know!
