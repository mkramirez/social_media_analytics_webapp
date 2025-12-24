"""Trend analysis for social media analytics."""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import statistics


class TrendAnalyzer:
    """Analyze trends in social media metrics over time."""

    @staticmethod
    def calculate_growth_rate(
        current_value: float,
        previous_value: float,
        time_period_days: int = 1
    ) -> Dict[str, any]:
        """Calculate growth rate between two values.

        Args:
            current_value: Current period value
            previous_value: Previous period value
            time_period_days: Number of days between measurements

        Returns:
            Dict with absolute_change, percent_change, daily_rate, direction
        """
        if previous_value == 0:
            if current_value > 0:
                return {
                    'absolute_change': current_value,
                    'percent_change': 100.0,
                    'daily_rate': current_value / time_period_days,
                    'direction': 'up'
                }
            return {
                'absolute_change': 0.0,
                'percent_change': 0.0,
                'daily_rate': 0.0,
                'direction': 'stable'
            }

        absolute_change = current_value - previous_value
        percent_change = (absolute_change / previous_value) * 100
        daily_rate = absolute_change / time_period_days

        direction = 'stable'
        if absolute_change > 0:
            direction = 'up'
        elif absolute_change < 0:
            direction = 'down'

        return {
            'absolute_change': absolute_change,
            'percent_change': round(percent_change, 2),
            'daily_rate': round(daily_rate, 2),
            'direction': direction
        }

    @staticmethod
    def analyze_time_series_trend(
        time_series: List[Dict[str, any]],
        value_key: str = 'value'
    ) -> Dict[str, any]:
        """Analyze trend in a time series dataset.

        Args:
            time_series: List of dicts with 'timestamp' and value_key
            value_key: Key name for the value field

        Returns:
            Dict with trend analysis metrics
        """
        if not time_series or len(time_series) < 2:
            return {
                'trend_direction': 'insufficient_data',
                'average_value': 0.0,
                'peak_value': 0.0,
                'low_value': 0.0,
                'volatility': 0.0,
                'data_points': len(time_series)
            }

        values = [item.get(value_key, 0) for item in time_series]

        # Calculate basic statistics
        avg_value = statistics.mean(values)
        peak_value = max(values)
        low_value = min(values)

        # Calculate volatility (standard deviation)
        volatility = statistics.stdev(values) if len(values) > 1 else 0.0

        # Determine trend direction using linear approximation
        # Compare first half average to second half average
        mid_point = len(values) // 2
        first_half_avg = statistics.mean(values[:mid_point]) if mid_point > 0 else 0
        second_half_avg = statistics.mean(values[mid_point:]) if mid_point < len(values) else 0

        if second_half_avg > first_half_avg * 1.05:  # 5% threshold
            trend_direction = 'upward'
        elif second_half_avg < first_half_avg * 0.95:
            trend_direction = 'downward'
        else:
            trend_direction = 'stable'

        return {
            'trend_direction': trend_direction,
            'average_value': round(avg_value, 2),
            'peak_value': peak_value,
            'low_value': low_value,
            'volatility': round(volatility, 2),
            'data_points': len(time_series),
            'first_half_avg': round(first_half_avg, 2),
            'second_half_avg': round(second_half_avg, 2)
        }

    @staticmethod
    def calculate_best_posting_times(
        posts_with_engagement: List[Dict[str, any]],
        timestamp_key: str = 'created_at',
        engagement_key: str = 'engagement'
    ) -> Dict[str, any]:
        """Analyze best times to post based on historical engagement.

        Args:
            posts_with_engagement: List of posts with timestamps and engagement
            timestamp_key: Key for timestamp field
            engagement_key: Key for engagement metric

        Returns:
            Dict with hourly and daily engagement patterns
        """
        if not posts_with_engagement:
            return {
                'best_hour': None,
                'best_day': None,
                'hourly_avg': {},
                'daily_avg': {},
                'heatmap_data': []
            }

        # Parse timestamps and aggregate by hour and day
        hourly_engagement = defaultdict(list)
        daily_engagement = defaultdict(list)
        heatmap = defaultdict(lambda: defaultdict(list))

        for post in posts_with_engagement:
            try:
                timestamp_str = post.get(timestamp_key, '')
                engagement = post.get(engagement_key, 0)

                # Try to parse timestamp
                try:
                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    # Try alternative formats
                    try:
                        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    except:
                        continue

                hour = dt.hour
                day_of_week = dt.strftime('%A')  # Monday, Tuesday, etc.

                hourly_engagement[hour].append(engagement)
                daily_engagement[day_of_week].append(engagement)
                heatmap[day_of_week][hour].append(engagement)

            except Exception:
                continue

        # Calculate averages
        hourly_avg = {
            hour: round(statistics.mean(values), 2)
            for hour, values in hourly_engagement.items()
        }

        daily_avg = {
            day: round(statistics.mean(values), 2)
            for day, values in daily_engagement.items()
        }

        # Find best times
        best_hour = max(hourly_avg.items(), key=lambda x: x[1])[0] if hourly_avg else None
        best_day = max(daily_avg.items(), key=lambda x: x[1])[0] if daily_avg else None

        # Create heatmap data
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        heatmap_data = []

        for day in days_order:
            if day in heatmap:
                for hour in range(24):
                    if hour in heatmap[day]:
                        avg_engagement = round(statistics.mean(heatmap[day][hour]), 2)
                        heatmap_data.append({
                            'day': day,
                            'hour': hour,
                            'engagement': avg_engagement
                        })

        return {
            'best_hour': best_hour,
            'best_day': best_day,
            'hourly_avg': hourly_avg,
            'daily_avg': daily_avg,
            'heatmap_data': heatmap_data
        }

    @staticmethod
    def detect_anomalies(
        time_series: List[Dict[str, any]],
        value_key: str = 'value',
        threshold_std: float = 2.0
    ) -> List[Dict[str, any]]:
        """Detect anomalies in time series data.

        Args:
            time_series: List of dicts with timestamps and values
            value_key: Key name for the value field
            threshold_std: Number of standard deviations for anomaly threshold

        Returns:
            List of anomaly data points
        """
        if not time_series or len(time_series) < 3:
            return []

        values = [item.get(value_key, 0) for item in time_series]

        if len(values) < 2:
            return []

        mean_value = statistics.mean(values)
        std_value = statistics.stdev(values) if len(values) > 1 else 0

        if std_value == 0:
            return []

        anomalies = []
        for item in time_series:
            value = item.get(value_key, 0)
            z_score = abs((value - mean_value) / std_value)

            if z_score > threshold_std:
                anomalies.append({
                    'timestamp': item.get('timestamp'),
                    'value': value,
                    'z_score': round(z_score, 2),
                    'deviation': round(value - mean_value, 2)
                })

        return anomalies

    @staticmethod
    def calculate_moving_average(
        time_series: List[Dict[str, any]],
        value_key: str = 'value',
        window_size: int = 7
    ) -> List[Dict[str, any]]:
        """Calculate moving average for smoothing time series data.

        Args:
            time_series: List of dicts with timestamps and values
            value_key: Key name for the value field
            window_size: Number of data points in moving window

        Returns:
            List of dicts with timestamps and moving averages
        """
        if not time_series or len(time_series) < window_size:
            return []

        result = []
        values = [item.get(value_key, 0) for item in time_series]

        for i in range(len(values) - window_size + 1):
            window = values[i:i + window_size]
            avg = statistics.mean(window)
            result.append({
                'timestamp': time_series[i + window_size - 1].get('timestamp'),
                'moving_average': round(avg, 2),
                'original_value': values[i + window_size - 1]
            })

        return result

    @staticmethod
    def forecast_next_period(
        time_series: List[Dict[str, any]],
        value_key: str = 'value',
        periods_ahead: int = 1
    ) -> Dict[str, any]:
        """Simple linear forecast for next period.

        Args:
            time_series: List of dicts with timestamps and values
            value_key: Key name for the value field
            periods_ahead: Number of periods to forecast

        Returns:
            Dict with forecast value and confidence
        """
        if not time_series or len(time_series) < 2:
            return {
                'forecast': 0.0,
                'confidence': 'low',
                'method': 'insufficient_data'
            }

        values = [item.get(value_key, 0) for item in time_series]

        # Calculate linear trend using first and last values
        first_value = values[0]
        last_value = values[-1]
        num_periods = len(values) - 1

        if num_periods == 0:
            return {
                'forecast': last_value,
                'confidence': 'low',
                'method': 'no_trend'
            }

        trend_per_period = (last_value - first_value) / num_periods
        forecast = last_value + (trend_per_period * periods_ahead)

        # Determine confidence based on volatility
        volatility = statistics.stdev(values) if len(values) > 1 else 0
        mean_value = statistics.mean(values)

        coefficient_of_variation = (volatility / mean_value) if mean_value != 0 else 1.0

        if coefficient_of_variation < 0.2:
            confidence = 'high'
        elif coefficient_of_variation < 0.5:
            confidence = 'medium'
        else:
            confidence = 'low'

        return {
            'forecast': round(forecast, 2),
            'confidence': confidence,
            'method': 'linear_trend',
            'trend_per_period': round(trend_per_period, 2)
        }
