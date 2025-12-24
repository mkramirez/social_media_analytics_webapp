"""
Integration tests for monitoring workflows and background jobs.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import time

from app.models.user import User
from app.models.platforms.twitch import TwitchChannel, TwitchStreamRecord
from app.models.platforms.twitter import TwitterUser, Tweet
from app.models.monitoring import MonitoringJob, JobExecution


@pytest.mark.integration
@pytest.mark.slow
class TestMonitoringJobLifecycle:
    """Test complete monitoring job lifecycle."""

    @patch("app.services.scheduler_service.scheduler")
    @patch("app.twitch.twitch_api.TwitchAPI")
    def test_create_and_execute_twitch_monitoring_job(
        self, mock_twitch_api, mock_scheduler, client: TestClient,
        auth_headers: dict, twitch_channel: TwitchChannel, test_db: Session
    ):
        """Test creating and executing a Twitch monitoring job."""
        # Mock scheduler to return job
        mock_job = Mock(id="job_123")
        mock_scheduler.add_job.return_value = mock_job

        # Mock Twitch API response
        mock_api_instance = mock_twitch_api.return_value
        mock_api_instance.get_stream_info.return_value = {
            "stream_id": "live_stream_1",
            "title": "Live Stream Title",
            "game_name": "Test Game",
            "viewer_count": 150,
            "started_at": datetime.utcnow().isoformat(),
            "is_live": True
        }

        # Create monitoring job
        response = client.post(
            f"/api/twitch/channels/{twitch_channel.id}/start-monitoring",
            headers=auth_headers,
            json={"interval_minutes": 60}
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

        # Verify job was created
        job = test_db.query(MonitoringJob).filter(
            MonitoringJob.entity_id == twitch_channel.id
        ).first()
        assert job is not None
        assert job.platform == "twitch"
        assert job.interval_minutes == 60
        assert job.is_active is True

        # Verify scheduler was called
        assert mock_scheduler.add_job.called

    @patch("app.services.scheduler_service.scheduler")
    def test_pause_and_resume_monitoring_job(
        self, mock_scheduler, client: TestClient, auth_headers: dict,
        twitch_channel: TwitchChannel, test_db: Session
    ):
        """Test pausing and resuming a monitoring job."""
        # Create job
        job = MonitoringJob(
            user_id=twitch_channel.user_id,
            platform="twitch",
            entity_id=twitch_channel.id,
            job_id="job_123",
            interval_minutes=60,
            is_active=True,
            created_at=datetime.utcnow()
        )
        test_db.add(job)
        test_db.commit()
        test_db.refresh(job)

        # Pause job
        response = client.post(
            f"/api/jobs/{job.id}/pause",
            headers=auth_headers
        )

        assert response.status_code == 200
        test_db.refresh(job)
        assert job.is_active is False
        assert mock_scheduler.pause_job.called

        # Resume job
        response = client.post(
            f"/api/jobs/{job.id}/resume",
            headers=auth_headers
        )

        assert response.status_code == 200
        test_db.refresh(job)
        assert job.is_active is True
        assert mock_scheduler.resume_job.called

    @patch("app.services.scheduler_service.scheduler")
    def test_delete_monitoring_job(
        self, mock_scheduler, client: TestClient, auth_headers: dict,
        twitch_channel: TwitchChannel, test_db: Session
    ):
        """Test deleting a monitoring job."""
        # Create job
        job = MonitoringJob(
            user_id=twitch_channel.user_id,
            platform="twitch",
            entity_id=twitch_channel.id,
            job_id="job_123",
            interval_minutes=60,
            is_active=True,
            created_at=datetime.utcnow()
        )
        test_db.add(job)
        test_db.commit()
        job_id = job.id

        # Delete job
        response = client.delete(
            f"/api/jobs/{job_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert mock_scheduler.remove_job.called

        # Verify deleted from database
        deleted_job = test_db.query(MonitoringJob).filter(
            MonitoringJob.id == job_id
        ).first()
        assert deleted_job is None

    def test_get_all_user_jobs(
        self, client: TestClient, auth_headers: dict, twitch_channel: TwitchChannel,
        test_db: Session, test_user: User
    ):
        """Test getting all monitoring jobs for a user."""
        # Create multiple jobs
        jobs = []
        for i in range(3):
            job = MonitoringJob(
                user_id=test_user.id,
                platform="twitch",
                entity_id=twitch_channel.id,
                job_id=f"job_{i}",
                interval_minutes=60,
                is_active=True,
                created_at=datetime.utcnow()
            )
            jobs.append(job)
            test_db.add(job)

        test_db.commit()

        # Get jobs
        response = client.get("/api/jobs", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_job_isolation_between_users(
        self, client: TestClient, auth_headers: dict, auth_headers2: dict,
        twitch_channel: TwitchChannel, test_db: Session, test_user: User, test_user2: User
    ):
        """Test that users can only access their own jobs."""
        # User 1's job
        job1 = MonitoringJob(
            user_id=test_user.id,
            platform="twitch",
            entity_id=twitch_channel.id,
            job_id="job_user1",
            interval_minutes=60,
            is_active=True,
            created_at=datetime.utcnow()
        )
        test_db.add(job1)
        test_db.commit()

        # User 2 tries to access User 1's job
        response = client.get(f"/api/jobs/{job1.id}", headers=auth_headers2)
        assert response.status_code == 404  # Not found for user 2


@pytest.mark.integration
class TestJobExecution:
    """Test job execution and error handling."""

    @patch("app.twitch.twitch_api.TwitchAPI")
    def test_successful_job_execution(
        self, mock_twitch_api, twitch_channel: TwitchChannel, test_db: Session
    ):
        """Test successful monitoring job execution."""
        # Mock API response
        mock_api_instance = mock_twitch_api.return_value
        mock_api_instance.get_stream_info.return_value = {
            "stream_id": "live_stream_1",
            "title": "Live Stream",
            "game_name": "Test Game",
            "viewer_count": 200,
            "started_at": datetime.utcnow().isoformat(),
            "is_live": True
        }

        # Simulate job execution
        from app.services.monitoring_jobs import execute_twitch_monitoring

        job = MonitoringJob(
            user_id=twitch_channel.user_id,
            platform="twitch",
            entity_id=twitch_channel.id,
            job_id="test_job",
            interval_minutes=60,
            is_active=True,
            created_at=datetime.utcnow()
        )
        test_db.add(job)
        test_db.commit()

        execute_twitch_monitoring(job.id, twitch_channel.user_id, twitch_channel.id, test_db)

        # Verify stream record was created
        record = test_db.query(TwitchStreamRecord).filter(
            TwitchStreamRecord.channel_id == twitch_channel.id
        ).first()
        assert record is not None
        assert record.viewer_count == 200

        # Verify job execution was logged
        execution = test_db.query(JobExecution).filter(
            JobExecution.job_id == job.id
        ).first()
        assert execution is not None
        assert execution.status == "success"

    @patch("app.twitch.twitch_api.TwitchAPI")
    def test_failed_job_execution(
        self, mock_twitch_api, twitch_channel: TwitchChannel, test_db: Session
    ):
        """Test failed monitoring job execution."""
        # Mock API to raise error
        mock_api_instance = mock_twitch_api.return_value
        mock_api_instance.get_stream_info.side_effect = Exception("API Error")

        from app.services.monitoring_jobs import execute_twitch_monitoring

        job = MonitoringJob(
            user_id=twitch_channel.user_id,
            platform="twitch",
            entity_id=twitch_channel.id,
            job_id="test_job",
            interval_minutes=60,
            is_active=True,
            created_at=datetime.utcnow()
        )
        test_db.add(job)
        test_db.commit()

        # Execute job (should handle error gracefully)
        execute_twitch_monitoring(job.id, twitch_channel.user_id, twitch_channel.id, test_db)

        # Verify job execution was logged with error
        execution = test_db.query(JobExecution).filter(
            JobExecution.job_id == job.id
        ).first()
        assert execution is not None
        assert execution.status == "failed"
        assert "error" in execution.error_message.lower()

    def test_job_execution_history(
        self, client: TestClient, auth_headers: dict, twitch_channel: TwitchChannel,
        test_db: Session
    ):
        """Test retrieving job execution history."""
        job = MonitoringJob(
            user_id=twitch_channel.user_id,
            platform="twitch",
            entity_id=twitch_channel.id,
            job_id="test_job",
            interval_minutes=60,
            is_active=True,
            created_at=datetime.utcnow()
        )
        test_db.add(job)
        test_db.commit()

        # Create execution records
        for i in range(5):
            execution = JobExecution(
                job_id=job.id,
                started_at=datetime.utcnow() - timedelta(hours=i),
                completed_at=datetime.utcnow() - timedelta(hours=i) + timedelta(minutes=1),
                status="success",
                records_collected=10 + i
            )
            test_db.add(execution)

        test_db.commit()

        # Get execution history
        response = client.get(
            f"/api/jobs/{job.id}/executions",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        assert all(exec["status"] == "success" for exec in data)


@pytest.mark.integration
class TestSchedulerPersistence:
    """Test scheduler job persistence across restarts."""

    @patch("app.services.scheduler_service.scheduler")
    def test_jobs_restored_on_startup(
        self, mock_scheduler, test_db: Session, test_user: User, twitch_channel: TwitchChannel
    ):
        """Test that active jobs are restored when app starts."""
        # Create active jobs in database
        jobs = []
        for i in range(3):
            job = MonitoringJob(
                user_id=test_user.id,
                platform="twitch",
                entity_id=twitch_channel.id,
                job_id=f"job_{i}",
                interval_minutes=60,
                is_active=True,
                created_at=datetime.utcnow()
            )
            jobs.append(job)
            test_db.add(job)

        test_db.commit()

        # Simulate app startup - restore jobs
        from app.services.scheduler_service import restore_jobs_on_startup

        restore_jobs_on_startup(test_db)

        # Verify all active jobs were added to scheduler
        assert mock_scheduler.add_job.call_count == 3

    @patch("app.services.scheduler_service.scheduler")
    def test_only_active_jobs_restored(
        self, mock_scheduler, test_db: Session, test_user: User, twitch_channel: TwitchChannel
    ):
        """Test that only active jobs are restored."""
        # Create mix of active and inactive jobs
        active_job = MonitoringJob(
            user_id=test_user.id,
            platform="twitch",
            entity_id=twitch_channel.id,
            job_id="active_job",
            interval_minutes=60,
            is_active=True,
            created_at=datetime.utcnow()
        )

        inactive_job = MonitoringJob(
            user_id=test_user.id,
            platform="twitch",
            entity_id=twitch_channel.id,
            job_id="inactive_job",
            interval_minutes=60,
            is_active=False,
            created_at=datetime.utcnow()
        )

        test_db.add(active_job)
        test_db.add(inactive_job)
        test_db.commit()

        from app.services.scheduler_service import restore_jobs_on_startup

        restore_jobs_on_startup(test_db)

        # Only 1 job should be restored
        assert mock_scheduler.add_job.call_count == 1


@pytest.mark.integration
class TestMultiPlatformMonitoring:
    """Test monitoring across multiple platforms."""

    @patch("app.services.scheduler_service.scheduler")
    @patch("app.twitch.twitch_api.TwitchAPI")
    @patch("app.twitter.twitter_api.TwitterAPI")
    def test_concurrent_platform_monitoring(
        self, mock_twitter_api, mock_twitch_api, mock_scheduler,
        client: TestClient, auth_headers: dict, twitch_channel: TwitchChannel,
        twitter_user_entity: TwitterUser, test_db: Session
    ):
        """Test monitoring multiple platforms concurrently."""
        mock_scheduler.add_job.return_value = Mock(id="test_job")

        # Start Twitch monitoring
        response1 = client.post(
            f"/api/twitch/channels/{twitch_channel.id}/start-monitoring",
            headers=auth_headers,
            json={"interval_minutes": 60}
        )

        # Start Twitter monitoring
        response2 = client.post(
            f"/api/twitter/users/{twitter_user_entity.id}/start-monitoring",
            headers=auth_headers,
            json={"interval_minutes": 120}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Verify both jobs were created
        jobs = test_db.query(MonitoringJob).all()
        assert len(jobs) == 2
        platforms = [job.platform for job in jobs]
        assert "twitch" in platforms
        assert "twitter" in platforms

    def test_get_jobs_filtered_by_platform(
        self, client: TestClient, auth_headers: dict, test_db: Session,
        test_user: User, twitch_channel: TwitchChannel
    ):
        """Test filtering jobs by platform."""
        # Create jobs for different platforms
        twitch_job = MonitoringJob(
            user_id=test_user.id,
            platform="twitch",
            entity_id=twitch_channel.id,
            job_id="twitch_job",
            interval_minutes=60,
            is_active=True,
            created_at=datetime.utcnow()
        )

        twitter_job = MonitoringJob(
            user_id=test_user.id,
            platform="twitter",
            entity_id=999,
            job_id="twitter_job",
            interval_minutes=120,
            is_active=True,
            created_at=datetime.utcnow()
        )

        test_db.add(twitch_job)
        test_db.add(twitter_job)
        test_db.commit()

        # Get only Twitch jobs
        response = client.get(
            "/api/jobs",
            headers=auth_headers,
            params={"platform": "twitch"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["platform"] == "twitch"


@pytest.mark.integration
@pytest.mark.slow
class TestRateLimitingInJobs:
    """Test rate limiting in monitoring jobs."""

    @patch("app.twitch.twitch_api.TwitchAPI")
    def test_rate_limit_handling(
        self, mock_twitch_api, twitch_channel: TwitchChannel, test_db: Session
    ):
        """Test handling of API rate limits in jobs."""
        # Mock API to return rate limit error
        from app.exceptions import RateLimitError

        mock_api_instance = mock_twitch_api.return_value
        mock_api_instance.get_stream_info.side_effect = RateLimitError(
            "Rate limit exceeded",
            retry_after=60
        )

        from app.services.monitoring_jobs import execute_twitch_monitoring

        job = MonitoringJob(
            user_id=twitch_channel.user_id,
            platform="twitch",
            entity_id=twitch_channel.id,
            job_id="test_job",
            interval_minutes=60,
            is_active=True,
            created_at=datetime.utcnow()
        )
        test_db.add(job)
        test_db.commit()

        execute_twitch_monitoring(job.id, twitch_channel.user_id, twitch_channel.id, test_db)

        # Verify execution was logged as rate limited
        execution = test_db.query(JobExecution).filter(
            JobExecution.job_id == job.id
        ).first()
        assert execution is not None
        assert execution.status == "rate_limited"
        assert execution.retry_after == 60


@pytest.mark.integration
class TestWebSocketNotifications:
    """Test WebSocket notifications from monitoring jobs."""

    @patch("app.services.websocket_service.connection_manager")
    @patch("app.twitch.twitch_api.TwitchAPI")
    def test_websocket_notification_on_job_completion(
        self, mock_twitch_api, mock_connection_manager,
        twitch_channel: TwitchChannel, test_db: Session
    ):
        """Test that WebSocket notifications are sent on job completion."""
        # Mock API response
        mock_api_instance = mock_twitch_api.return_value
        mock_api_instance.get_stream_info.return_value = {
            "stream_id": "live_stream_1",
            "title": "Live Stream",
            "is_live": True
        }

        from app.services.monitoring_jobs import execute_twitch_monitoring

        job = MonitoringJob(
            user_id=twitch_channel.user_id,
            platform="twitch",
            entity_id=twitch_channel.id,
            job_id="test_job",
            interval_minutes=60,
            is_active=True,
            created_at=datetime.utcnow()
        )
        test_db.add(job)
        test_db.commit()

        execute_twitch_monitoring(job.id, twitch_channel.user_id, twitch_channel.id, test_db)

        # Verify WebSocket notification was sent
        assert mock_connection_manager.send_platform_update.called
