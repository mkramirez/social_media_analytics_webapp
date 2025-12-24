"""Export manager for CSV and PDF report generation."""

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
from matplotlib.figure import Figure


class ExportManager:
    """Handles export of analytics data to CSV and PDF formats."""

    @staticmethod
    def export_entities_csv(entities: List[Dict], filepath: str) -> bool:
        """Export entity data to CSV file.

        Args:
            entities: List of entity dictionaries
            filepath: Path to save CSV file

        Returns:
            True if successful, False otherwise
        """
        if not entities:
            return False

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                # Get all unique keys from entities
                fieldnames = set()
                for entity in entities:
                    fieldnames.update(entity.keys())
                fieldnames = sorted(list(fieldnames))

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(entities)

            return True
        except Exception as e:
            print(f"Error exporting entities to CSV: {e}")
            return False

    @staticmethod
    def export_sentiment_csv(sentiment_data: Dict, filepath: str) -> bool:
        """Export sentiment analysis data to CSV.

        Args:
            sentiment_data: Dictionary with sentiment metrics
            filepath: Path to save CSV file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Header
                writer.writerow(['Social Media Analytics - Sentiment Report'])
                writer.writerow(['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                writer.writerow([])

                # Summary metrics
                writer.writerow(['Sentiment Summary'])
                writer.writerow(['Total Positive', sentiment_data.get('total_positive', 0)])
                writer.writerow(['Total Neutral', sentiment_data.get('total_neutral', 0)])
                writer.writerow(['Total Negative', sentiment_data.get('total_negative', 0)])
                writer.writerow([])

                # Time series data if available
                if sentiment_data.get('timestamps'):
                    writer.writerow(['Timestamp', 'Positive', 'Neutral', 'Negative'])
                    timestamps = sentiment_data.get('timestamps', [])
                    positive = sentiment_data.get('positive', [])
                    neutral = sentiment_data.get('neutral', [])
                    negative = sentiment_data.get('negative', [])

                    for i in range(len(timestamps)):
                        writer.writerow([
                            timestamps[i] if i < len(timestamps) else '',
                            positive[i] if i < len(positive) else 0,
                            neutral[i] if i < len(neutral) else 0,
                            negative[i] if i < len(negative) else 0
                        ])

            return True
        except Exception as e:
            print(f"Error exporting sentiment to CSV: {e}")
            return False

    @staticmethod
    def export_engagement_csv(engagement_data: Dict, filepath: str) -> bool:
        """Export engagement metrics to CSV.

        Args:
            engagement_data: Dictionary with engagement metrics
            filepath: Path to save CSV file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Header
                writer.writerow(['Social Media Analytics - Engagement Report'])
                writer.writerow(['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                writer.writerow([])

                # Engagement rates by entity
                writer.writerow(['Entity', 'Engagement Rate', 'Platform'])
                entities = engagement_data.get('entities', [])
                rates = engagement_data.get('rates', [])

                for i, entity in enumerate(entities):
                    rate = rates[i] if i < len(rates) else 0
                    writer.writerow([entity, f"{rate}%", ''])

            return True
        except Exception as e:
            print(f"Error exporting engagement to CSV: {e}")
            return False

    @staticmethod
    def export_trends_csv(trend_data: Dict, filepath: str) -> bool:
        """Export trend analysis data to CSV.

        Args:
            trend_data: Dictionary with trend metrics
            filepath: Path to save CSV file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Header
                writer.writerow(['Social Media Analytics - Trends Report'])
                writer.writerow(['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                writer.writerow([])

                # Time series data
                writer.writerow(['Timestamp', 'Twitter', 'Reddit', 'YouTube', 'Twitch'])
                timestamps = trend_data.get('timestamps', [])
                twitter = trend_data.get('twitter', [])
                reddit = trend_data.get('reddit', [])
                youtube = trend_data.get('youtube', [])
                twitch = trend_data.get('twitch', [])

                max_len = max(len(timestamps), len(twitter), len(reddit), len(youtube), len(twitch))
                for i in range(max_len):
                    writer.writerow([
                        timestamps[i] if i < len(timestamps) else '',
                        twitter[i] if i < len(twitter) else 0,
                        reddit[i] if i < len(reddit) else 0,
                        youtube[i] if i < len(youtube) else 0,
                        twitch[i] if i < len(twitch) else 0
                    ])

            return True
        except Exception as e:
            print(f"Error exporting trends to CSV: {e}")
            return False

    @staticmethod
    def export_comparison_csv(comparison_data: Dict, filepath: str) -> bool:
        """Export comparative analytics to CSV.

        Args:
            comparison_data: Dictionary with comparison metrics
            filepath: Path to save CSV file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Header
                writer.writerow(['Social Media Analytics - Comparison Report'])
                writer.writerow(['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                writer.writerow([])

                # Comparison data
                entities = comparison_data.get('entities', [])
                metrics = comparison_data.get('metrics', [])
                values = comparison_data.get('values', {})

                if entities and metrics:
                    # Create header row
                    header = ['Entity'] + metrics
                    writer.writerow(header)

                    # Write each entity's values
                    for entity in entities:
                        row = [entity]
                        entity_values = values.get(entity, [])
                        row.extend(entity_values)
                        writer.writerow(row)

            return True
        except Exception as e:
            print(f"Error exporting comparison to CSV: {e}")
            return False

    @staticmethod
    def export_overview_pdf(metrics: Dict, time_series_fig: Optional[Figure],
                           comparison_fig: Optional[Figure], filepath: str) -> bool:
        """Export overview analytics to PDF with charts.

        Args:
            metrics: Dictionary with overview metrics
            time_series_fig: Matplotlib figure for time series chart
            comparison_fig: Matplotlib figure for comparison chart
            filepath: Path to save PDF file

        Returns:
            True if successful, False otherwise
        """
        try:
            with PdfPages(filepath) as pdf:
                # Page 1: Summary metrics
                fig = plt.figure(figsize=(8.5, 11))
                fig.text(0.5, 0.95, 'Social Media Analytics - Overview Report',
                        ha='center', fontsize=16, fontweight='bold')
                fig.text(0.5, 0.92, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        ha='center', fontsize=10)

                # Summary statistics
                y_pos = 0.85
                fig.text(0.1, y_pos, 'Summary Statistics', fontsize=14, fontweight='bold')
                y_pos -= 0.05

                stats = [
                    f"Total Entities: {metrics.get('total_entities', 0)}",
                    f"Total Records: {metrics.get('total_records', 0):,}",
                    f"Average Engagement: {metrics.get('avg_engagement', 0):,}",
                    f"Active Since: {metrics.get('active_since', 'N/A')}"
                ]

                for stat in stats:
                    fig.text(0.1, y_pos, stat, fontsize=11)
                    y_pos -= 0.04

                # Platform breakdown
                y_pos -= 0.05
                fig.text(0.1, y_pos, 'Platform Breakdown', fontsize=14, fontweight='bold')
                y_pos -= 0.05

                platform_breakdown = metrics.get('platform_breakdown', {})
                for platform, data in platform_breakdown.items():
                    if isinstance(data, dict) and 'total_entities' in data:
                        platform_name = platform.capitalize()
                        entities = data.get('total_entities', 0)
                        records = data.get('total_records', 0)
                        fig.text(0.1, y_pos, f"{platform_name}: {entities} entities, {records:,} records",
                                fontsize=10)
                        y_pos -= 0.04

                plt.axis('off')
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)

                # Page 2: Time series chart
                if time_series_fig is not None:
                    pdf.savefig(time_series_fig, bbox_inches='tight')

                # Page 3: Comparison chart
                if comparison_fig is not None:
                    pdf.savefig(comparison_fig, bbox_inches='tight')

            return True
        except Exception as e:
            print(f"Error exporting overview to PDF: {e}")
            return False

    @staticmethod
    def export_sentiment_pdf(sentiment_data: Dict, timeline_fig: Optional[Figure],
                            distribution_fig: Optional[Figure], filepath: str) -> bool:
        """Export sentiment analytics to PDF with charts.

        Args:
            sentiment_data: Dictionary with sentiment metrics
            timeline_fig: Matplotlib figure for sentiment timeline
            distribution_fig: Matplotlib figure for sentiment distribution
            filepath: Path to save PDF file

        Returns:
            True if successful, False otherwise
        """
        try:
            with PdfPages(filepath) as pdf:
                # Page 1: Summary
                fig = plt.figure(figsize=(8.5, 11))
                fig.text(0.5, 0.95, 'Social Media Analytics - Sentiment Report',
                        ha='center', fontsize=16, fontweight='bold')
                fig.text(0.5, 0.92, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        ha='center', fontsize=10)

                y_pos = 0.85
                fig.text(0.1, y_pos, 'Sentiment Summary', fontsize=14, fontweight='bold')
                y_pos -= 0.05

                total_positive = sentiment_data.get('total_positive', 0)
                total_neutral = sentiment_data.get('total_neutral', 0)
                total_negative = sentiment_data.get('total_negative', 0)
                total = total_positive + total_neutral + total_negative

                if total > 0:
                    pos_pct = (total_positive / total) * 100
                    neu_pct = (total_neutral / total) * 100
                    neg_pct = (total_negative / total) * 100

                    fig.text(0.1, y_pos, f"Positive: {total_positive:,} ({pos_pct:.1f}%)", fontsize=11)
                    y_pos -= 0.04
                    fig.text(0.1, y_pos, f"Neutral: {total_neutral:,} ({neu_pct:.1f}%)", fontsize=11)
                    y_pos -= 0.04
                    fig.text(0.1, y_pos, f"Negative: {total_negative:,} ({neg_pct:.1f}%)", fontsize=11)
                else:
                    fig.text(0.1, y_pos, "No sentiment data available", fontsize=11)

                plt.axis('off')
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)

                # Page 2: Timeline chart
                if timeline_fig is not None:
                    pdf.savefig(timeline_fig, bbox_inches='tight')

                # Page 3: Distribution chart
                if distribution_fig is not None:
                    pdf.savefig(distribution_fig, bbox_inches='tight')

            return True
        except Exception as e:
            print(f"Error exporting sentiment to PDF: {e}")
            return False

    @staticmethod
    def export_engagement_pdf(engagement_data: Dict, chart_fig: Optional[Figure],
                             filepath: str) -> bool:
        """Export engagement analytics to PDF with charts.

        Args:
            engagement_data: Dictionary with engagement metrics
            chart_fig: Matplotlib figure for engagement chart
            filepath: Path to save PDF file

        Returns:
            True if successful, False otherwise
        """
        try:
            with PdfPages(filepath) as pdf:
                # Page 1: Summary
                fig = plt.figure(figsize=(8.5, 11))
                fig.text(0.5, 0.95, 'Social Media Analytics - Engagement Report',
                        ha='center', fontsize=16, fontweight='bold')
                fig.text(0.5, 0.92, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        ha='center', fontsize=10)

                y_pos = 0.85
                fig.text(0.1, y_pos, 'Engagement Rates by Entity', fontsize=14, fontweight='bold')
                y_pos -= 0.05

                entities = engagement_data.get('entities', [])
                rates = engagement_data.get('rates', [])

                for i, entity in enumerate(entities[:15]):  # Limit to top 15
                    rate = rates[i] if i < len(rates) else 0
                    fig.text(0.1, y_pos, f"{entity}: {rate:.2f}%", fontsize=10)
                    y_pos -= 0.04

                if len(entities) > 15:
                    fig.text(0.1, y_pos, f"... and {len(entities) - 15} more", fontsize=10, style='italic')

                plt.axis('off')
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)

                # Page 2: Chart
                if chart_fig is not None:
                    pdf.savefig(chart_fig, bbox_inches='tight')

            return True
        except Exception as e:
            print(f"Error exporting engagement to PDF: {e}")
            return False

    @staticmethod
    def export_trends_pdf(trend_data: Dict, trend_fig: Optional[Figure],
                         heatmap_fig: Optional[Figure], growth_fig: Optional[Figure],
                         filepath: str) -> bool:
        """Export trend analytics to PDF with charts.

        Args:
            trend_data: Dictionary with trend metrics
            trend_fig: Matplotlib figure for trend line chart
            heatmap_fig: Matplotlib figure for heatmap
            growth_fig: Matplotlib figure for growth chart
            filepath: Path to save PDF file

        Returns:
            True if successful, False otherwise
        """
        try:
            with PdfPages(filepath) as pdf:
                # Page 1: Summary
                fig = plt.figure(figsize=(8.5, 11))
                fig.text(0.5, 0.95, 'Social Media Analytics - Trends Report',
                        ha='center', fontsize=16, fontweight='bold')
                fig.text(0.5, 0.92, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        ha='center', fontsize=10)

                y_pos = 0.85
                fig.text(0.1, y_pos, 'Trend Analysis', fontsize=14, fontweight='bold')
                y_pos -= 0.05

                fig.text(0.1, y_pos, f"Analysis Period: Last 30 days", fontsize=11)
                y_pos -= 0.04
                fig.text(0.1, y_pos, f"Data Points: {len(trend_data.get('timestamps', []))}", fontsize=11)

                plt.axis('off')
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)

                # Add charts
                if trend_fig is not None:
                    pdf.savefig(trend_fig, bbox_inches='tight')
                if heatmap_fig is not None:
                    pdf.savefig(heatmap_fig, bbox_inches='tight')
                if growth_fig is not None:
                    pdf.savefig(growth_fig, bbox_inches='tight')

            return True
        except Exception as e:
            print(f"Error exporting trends to PDF: {e}")
            return False

    @staticmethod
    def export_comparison_pdf(comparison_data: Dict, radar_fig: Optional[Figure],
                             filepath: str) -> bool:
        """Export comparison analytics to PDF with charts.

        Args:
            comparison_data: Dictionary with comparison metrics
            radar_fig: Matplotlib figure for radar chart
            filepath: Path to save PDF file

        Returns:
            True if successful, False otherwise
        """
        try:
            with PdfPages(filepath) as pdf:
                # Page 1: Summary
                fig = plt.figure(figsize=(8.5, 11))
                fig.text(0.5, 0.95, 'Social Media Analytics - Comparison Report',
                        ha='center', fontsize=16, fontweight='bold')
                fig.text(0.5, 0.92, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        ha='center', fontsize=10)

                y_pos = 0.85
                fig.text(0.1, y_pos, 'Entity Comparison', fontsize=14, fontweight='bold')
                y_pos -= 0.05

                entities = comparison_data.get('entities', [])
                metrics = comparison_data.get('metrics', [])

                fig.text(0.1, y_pos, f"Entities Compared: {', '.join(entities)}", fontsize=11)
                y_pos -= 0.04
                fig.text(0.1, y_pos, f"Metrics: {', '.join(metrics)}", fontsize=11)

                plt.axis('off')
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)

                # Page 2: Radar chart
                if radar_fig is not None:
                    pdf.savefig(radar_fig, bbox_inches='tight')

            return True
        except Exception as e:
            print(f"Error exporting comparison to PDF: {e}")
            return False

    @staticmethod
    def export_full_report_pdf(aggregator, filepath: str) -> bool:
        """Export comprehensive analytics report to PDF.

        Args:
            aggregator: DashboardAggregator instance with all data
            filepath: Path to save PDF file

        Returns:
            True if successful, False otherwise
        """
        try:
            from src.dashboard.chart_builder import ChartBuilder

            with PdfPages(filepath) as pdf:
                # Cover page
                fig = plt.figure(figsize=(8.5, 11))
                fig.text(0.5, 0.5, 'Social Media Analytics',
                        ha='center', va='center', fontsize=24, fontweight='bold')
                fig.text(0.5, 0.45, 'Comprehensive Analytics Report',
                        ha='center', va='center', fontsize=16)
                fig.text(0.5, 0.4, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        ha='center', va='center', fontsize=12)
                plt.axis('off')
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)

                # Get all data
                metrics = aggregator.get_unified_metrics()
                time_series = aggregator.get_time_series_data(days=7)
                comparison = aggregator.get_platform_comparison()

                # Overview section with charts
                fig_ts = plt.figure(figsize=(10, 6))
                ChartBuilder.create_time_series_chart(fig_ts, time_series)
                pdf.savefig(fig_ts, bbox_inches='tight')
                plt.close(fig_ts)

                fig_comp = plt.figure(figsize=(10, 6))
                ChartBuilder.create_platform_comparison_chart(fig_comp, comparison)
                pdf.savefig(fig_comp, bbox_inches='tight')
                plt.close(fig_comp)

            return True
        except Exception as e:
            print(f"Error exporting full report to PDF: {e}")
            return False
