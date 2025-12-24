"""
AWS CloudWatch Monitoring Setup Script

This script creates CloudWatch alarms and dashboards for monitoring
the Social Media Analytics Platform in production.

Usage:
    python cloudwatch_setup.py --environment production
"""

import boto3
import argparse
import json
from typing import List, Dict, Any


class CloudWatchMonitoring:
    """Set up CloudWatch monitoring and alarms."""

    def __init__(self, environment: str = "production", region: str = "us-east-1"):
        """
        Initialize CloudWatch monitoring.

        Args:
            environment: Deployment environment (production, staging)
            region: AWS region
        """
        self.environment = environment
        self.region = region
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.sns = boto3.client('sns', region_name=region)
        self.ecs = boto3.client('ecs', region_name=region)

        # Configuration
        self.cluster_name = "social-analytics-cluster"
        self.service_name = "backend-service"
        self.alb_name = "social-analytics-alb"
        self.db_instance = "social-analytics-db"
        self.redis_cluster = "social-analytics-redis"

    def create_sns_topic(self) -> str:
        """Create SNS topic for alerts."""
        topic_name = f"social-analytics-alerts-{self.environment}"

        try:
            response = self.sns.create_topic(Name=topic_name)
            topic_arn = response['TopicArn']
            print(f"✅ Created SNS topic: {topic_arn}")
            return topic_arn
        except self.sns.exceptions.TopicLimitExceededException:
            # Topic already exists, get ARN
            topics = self.sns.list_topics()
            for topic in topics['Topics']:
                if topic_name in topic['TopicArn']:
                    print(f"ℹ️  SNS topic already exists: {topic['TopicArn']}")
                    return topic['TopicArn']

    def subscribe_email_to_alerts(self, topic_arn: str, email: str):
        """Subscribe email address to alerts."""
        try:
            self.sns.subscribe(
                TopicArn=topic_arn,
                Protocol='email',
                Endpoint=email
            )
            print(f"✅ Subscribed {email} to alerts (check email to confirm)")
        except Exception as e:
            print(f"⚠️  Failed to subscribe email: {e}")

    def create_ecs_alarms(self, topic_arn: str):
        """Create ECS service alarms."""
        print("\n🔧 Creating ECS alarms...")

        alarms = [
            {
                "name": f"{self.environment}-ecs-high-cpu",
                "description": "Alert when ECS CPU utilization exceeds 80%",
                "metric_name": "CPUUtilization",
                "namespace": "AWS/ECS",
                "threshold": 80.0,
                "comparison": "GreaterThanThreshold",
                "period": 300,
                "evaluation_periods": 2,
                "dimensions": [
                    {"Name": "ServiceName", "Value": self.service_name},
                    {"Name": "ClusterName", "Value": self.cluster_name}
                ]
            },
            {
                "name": f"{self.environment}-ecs-high-memory",
                "description": "Alert when ECS memory utilization exceeds 85%",
                "metric_name": "MemoryUtilization",
                "namespace": "AWS/ECS",
                "threshold": 85.0,
                "comparison": "GreaterThanThreshold",
                "period": 300,
                "evaluation_periods": 2,
                "dimensions": [
                    {"Name": "ServiceName", "Value": self.service_name},
                    {"Name": "ClusterName", "Value": self.cluster_name}
                ]
            },
            {
                "name": f"{self.environment}-ecs-service-unhealthy",
                "description": "Alert when ECS service has unhealthy tasks",
                "metric_name": "HealthyHostCount",
                "namespace": "AWS/ApplicationELB",
                "threshold": 1.0,
                "comparison": "LessThanThreshold",
                "period": 60,
                "evaluation_periods": 2,
                "dimensions": [
                    {"Name": "TargetGroup", "Value": "targetgroup/social-analytics-backend-tg/*"},
                    {"Name": "LoadBalancer", "Value": f"app/{self.alb_name}/*"}
                ]
            }
        ]

        for alarm in alarms:
            self._create_alarm(alarm, topic_arn)

    def create_alb_alarms(self, topic_arn: str):
        """Create Application Load Balancer alarms."""
        print("\n🔧 Creating ALB alarms...")

        alarms = [
            {
                "name": f"{self.environment}-alb-high-response-time",
                "description": "Alert when ALB response time exceeds 1 second",
                "metric_name": "TargetResponseTime",
                "namespace": "AWS/ApplicationELB",
                "threshold": 1.0,
                "comparison": "GreaterThanThreshold",
                "period": 300,
                "evaluation_periods": 2,
                "statistic": "Average",
                "dimensions": [
                    {"Name": "LoadBalancer", "Value": f"app/{self.alb_name}/*"}
                ]
            },
            {
                "name": f"{self.environment}-alb-5xx-errors",
                "description": "Alert when 5XX errors exceed 10 per minute",
                "metric_name": "HTTPCode_Target_5XX_Count",
                "namespace": "AWS/ApplicationELB",
                "threshold": 10.0,
                "comparison": "GreaterThanThreshold",
                "period": 60,
                "evaluation_periods": 1,
                "statistic": "Sum",
                "dimensions": [
                    {"Name": "LoadBalancer", "Value": f"app/{self.alb_name}/*"}
                ]
            },
            {
                "name": f"{self.environment}-alb-4xx-errors",
                "description": "Alert when 4XX errors exceed 50 per minute",
                "metric_name": "HTTPCode_Target_4XX_Count",
                "namespace": "AWS/ApplicationELB",
                "threshold": 50.0,
                "comparison": "GreaterThanThreshold",
                "period": 60,
                "evaluation_periods": 3,
                "statistic": "Sum",
                "dimensions": [
                    {"Name": "LoadBalancer", "Value": f"app/{self.alb_name}/*"}
                ]
            }
        ]

        for alarm in alarms:
            self._create_alarm(alarm, topic_arn)

    def create_rds_alarms(self, topic_arn: str):
        """Create RDS database alarms."""
        print("\n🔧 Creating RDS alarms...")

        alarms = [
            {
                "name": f"{self.environment}-rds-high-cpu",
                "description": "Alert when RDS CPU exceeds 75%",
                "metric_name": "CPUUtilization",
                "namespace": "AWS/RDS",
                "threshold": 75.0,
                "comparison": "GreaterThanThreshold",
                "period": 300,
                "evaluation_periods": 2,
                "dimensions": [
                    {"Name": "DBInstanceIdentifier", "Value": self.db_instance}
                ]
            },
            {
                "name": f"{self.environment}-rds-low-storage",
                "description": "Alert when RDS free storage falls below 10GB",
                "metric_name": "FreeStorageSpace",
                "namespace": "AWS/RDS",
                "threshold": 10000000000,  # 10GB in bytes
                "comparison": "LessThanThreshold",
                "period": 300,
                "evaluation_periods": 1,
                "dimensions": [
                    {"Name": "DBInstanceIdentifier", "Value": self.db_instance}
                ]
            },
            {
                "name": f"{self.environment}-rds-high-connections",
                "description": "Alert when RDS database connections exceed 80% of max",
                "metric_name": "DatabaseConnections",
                "namespace": "AWS/RDS",
                "threshold": 80.0,  # Adjust based on instance type
                "comparison": "GreaterThanThreshold",
                "period": 300,
                "evaluation_periods": 2,
                "dimensions": [
                    {"Name": "DBInstanceIdentifier", "Value": self.db_instance}
                ]
            },
            {
                "name": f"{self.environment}-rds-high-read-latency",
                "description": "Alert when RDS read latency exceeds 100ms",
                "metric_name": "ReadLatency",
                "namespace": "AWS/RDS",
                "threshold": 0.1,  # 100ms in seconds
                "comparison": "GreaterThanThreshold",
                "period": 300,
                "evaluation_periods": 2,
                "dimensions": [
                    {"Name": "DBInstanceIdentifier", "Value": self.db_instance}
                ]
            }
        ]

        for alarm in alarms:
            self._create_alarm(alarm, topic_arn)

    def create_redis_alarms(self, topic_arn: str):
        """Create ElastiCache Redis alarms."""
        print("\n🔧 Creating Redis alarms...")

        alarms = [
            {
                "name": f"{self.environment}-redis-high-cpu",
                "description": "Alert when Redis CPU exceeds 75%",
                "metric_name": "CPUUtilization",
                "namespace": "AWS/ElastiCache",
                "threshold": 75.0,
                "comparison": "GreaterThanThreshold",
                "period": 300,
                "evaluation_periods": 2,
                "dimensions": [
                    {"Name": "CacheClusterId", "Value": self.redis_cluster}
                ]
            },
            {
                "name": f"{self.environment}-redis-high-memory",
                "description": "Alert when Redis memory usage exceeds 80%",
                "metric_name": "DatabaseMemoryUsagePercentage",
                "namespace": "AWS/ElastiCache",
                "threshold": 80.0,
                "comparison": "GreaterThanThreshold",
                "period": 300,
                "evaluation_periods": 2,
                "dimensions": [
                    {"Name": "CacheClusterId", "Value": self.redis_cluster}
                ]
            },
            {
                "name": f"{self.environment}-redis-evictions",
                "description": "Alert when Redis has evictions",
                "metric_name": "Evictions",
                "namespace": "AWS/ElastiCache",
                "threshold": 0.0,
                "comparison": "GreaterThanThreshold",
                "period": 300,
                "evaluation_periods": 1,
                "statistic": "Sum",
                "dimensions": [
                    {"Name": "CacheClusterId", "Value": self.redis_cluster}
                ]
            }
        ]

        for alarm in alarms:
            self._create_alarm(alarm, topic_arn)

    def create_application_alarms(self, topic_arn: str):
        """Create custom application metric alarms."""
        print("\n🔧 Creating application alarms...")

        alarms = [
            {
                "name": f"{self.environment}-app-high-error-rate",
                "description": "Alert when application error rate exceeds 5%",
                "metric_name": "ErrorRate",
                "namespace": "SocialAnalytics/Application",
                "threshold": 5.0,
                "comparison": "GreaterThanThreshold",
                "period": 300,
                "evaluation_periods": 2,
                "dimensions": []
            },
            {
                "name": f"{self.environment}-app-failed-jobs",
                "description": "Alert when monitoring jobs are failing",
                "metric_name": "FailedJobs",
                "namespace": "SocialAnalytics/Jobs",
                "threshold": 10.0,
                "comparison": "GreaterThanThreshold",
                "period": 300,
                "evaluation_periods": 1,
                "statistic": "Sum",
                "dimensions": []
            },
            {
                "name": f"{self.environment}-app-slow-api-calls",
                "description": "Alert when API calls are slow (p99 > 2s)",
                "metric_name": "APILatencyP99",
                "namespace": "SocialAnalytics/Performance",
                "threshold": 2000.0,  # 2 seconds in milliseconds
                "comparison": "GreaterThanThreshold",
                "period": 300,
                "evaluation_periods": 2,
                "dimensions": []
            }
        ]

        for alarm in alarms:
            self._create_alarm(alarm, topic_arn)

    def _create_alarm(self, alarm_config: Dict[str, Any], topic_arn: str):
        """Create a CloudWatch alarm."""
        try:
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_config["name"],
                AlarmDescription=alarm_config["description"],
                MetricName=alarm_config["metric_name"],
                Namespace=alarm_config["namespace"],
                Statistic=alarm_config.get("statistic", "Average"),
                Period=alarm_config["period"],
                EvaluationPeriods=alarm_config["evaluation_periods"],
                Threshold=alarm_config["threshold"],
                ComparisonOperator=alarm_config["comparison"],
                Dimensions=alarm_config.get("dimensions", []),
                AlarmActions=[topic_arn],
                TreatMissingData="notBreaching"
            )
            print(f"  ✅ Created alarm: {alarm_config['name']}")
        except Exception as e:
            print(f"  ⚠️  Failed to create alarm {alarm_config['name']}: {e}")

    def create_dashboard(self):
        """Create CloudWatch dashboard."""
        print("\n🔧 Creating CloudWatch dashboard...")

        dashboard_body = {
            "widgets": [
                # ECS Metrics
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            ["AWS/ECS", "CPUUtilization", {"stat": "Average"}],
                            [".", "MemoryUtilization", {"stat": "Average"}]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "ECS Resource Utilization",
                        "yAxis": {"left": {"min": 0, "max": 100}}
                    }
                },
                # ALB Metrics
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            ["AWS/ApplicationELB", "TargetResponseTime", {"stat": "Average"}],
                            ["...", {"stat": "p99"}]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "ALB Response Time"
                    }
                },
                # Error Rates
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", {"stat": "Sum"}],
                            [".", "HTTPCode_Target_4XX_Count", {"stat": "Sum"}],
                            [".", "HTTPCode_Target_2XX_Count", {"stat": "Sum"}]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "HTTP Response Codes"
                    }
                },
                # RDS Metrics
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            ["AWS/RDS", "CPUUtilization", {"stat": "Average"}],
                            [".", "DatabaseConnections", {"stat": "Average"}],
                            [".", "FreeStorageSpace", {"stat": "Average"}]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "RDS Metrics"
                    }
                },
                # Redis Metrics
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            ["AWS/ElastiCache", "CPUUtilization", {"stat": "Average"}],
                            [".", "DatabaseMemoryUsagePercentage", {"stat": "Average"}],
                            [".", "CacheHits", {"stat": "Sum"}],
                            [".", "CacheMisses", {"stat": "Sum"}]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Redis Metrics"
                    }
                },
                # Application Metrics
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            ["SocialAnalytics/Application", "TotalRequests", {"stat": "Sum"}],
                            [".", "ErrorRate", {"stat": "Average"}]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "Application Metrics"
                    }
                }
            ]
        }

        try:
            self.cloudwatch.put_dashboard(
                DashboardName=f"social-analytics-{self.environment}",
                DashboardBody=json.dumps(dashboard_body)
            )
            print(f"✅ Created dashboard: social-analytics-{self.environment}")
            print(f"   View at: https://console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name=social-analytics-{self.environment}")
        except Exception as e:
            print(f"⚠️  Failed to create dashboard: {e}")

    def setup_all(self, alert_email: str):
        """Set up all monitoring."""
        print("=" * 60)
        print(f"Setting up CloudWatch Monitoring for {self.environment}")
        print("=" * 60)

        # Create SNS topic
        topic_arn = self.create_sns_topic()

        # Subscribe email
        if alert_email:
            self.subscribe_email_to_alerts(topic_arn, alert_email)

        # Create alarms
        self.create_ecs_alarms(topic_arn)
        self.create_alb_alarms(topic_arn)
        self.create_rds_alarms(topic_arn)
        self.create_redis_alarms(topic_arn)
        self.create_application_alarms(topic_arn)

        # Create dashboard
        self.create_dashboard()

        print("\n" + "=" * 60)
        print("✅ Monitoring setup complete!")
        print("=" * 60)
        print(f"SNS Topic ARN: {topic_arn}")
        print(f"Dashboard: social-analytics-{self.environment}")
        print("\nNext steps:")
        print("1. Confirm email subscription (check your inbox)")
        print("2. Review alarms in CloudWatch console")
        print("3. Customize thresholds as needed")
        print("4. Test alerts with CloudWatch alarm test feature")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Set up CloudWatch monitoring")
    parser.add_argument(
        "--environment",
        choices=["production", "staging"],
        default="production",
        help="Deployment environment"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region"
    )
    parser.add_argument(
        "--alert-email",
        required=True,
        help="Email address for alerts"
    )

    args = parser.parse_args()

    monitoring = CloudWatchMonitoring(
        environment=args.environment,
        region=args.region
    )

    monitoring.setup_all(alert_email=args.alert_email)


if __name__ == "__main__":
    main()
