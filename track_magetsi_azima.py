#!/usr/bin/env python3
"""
Magetsi Azima Tracker for NABIWI Node
Tracks electricity testing periods ("magetsi azima") and analyzes operational impact

"Magetsi azima" = "electricity test" in Chichewa - tracks power outages/testing periods
"""

import sqlite3
import csv
from datetime import datetime, timedelta
from pathlib import Path
import re

DB_PATH = 'data/gridledger.db'
SMS_FILE = 'data/SMS exported from HiSuite2026-03-14_084735150.csv'

class MagetsiAzimaTracker:
    """Tracks electricity testing events for NABIWI node"""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.nabiwi_phone = '+265998265527'
        self._validate_database()

    def _validate_database(self):
        """Ensure database exists"""
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

    def _get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def extract_azima_events_from_sms(self):
        """Extract magetsi azima events from raw SMS data"""
        azima_events = []

        if not Path(SMS_FILE).exists():
            print(f"SMS file not found: {SMS_FILE}")
            return azima_events

        with open(SMS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                phone = row.get('From', '').strip()
                content = row.get('Content', '').strip()
                timestamp = row.get('Time', '').strip()

                # Only process NABIWI messages
                if phone != self.nabiwi_phone:
                    continue

                print(f"DEBUG: Processing NABIWI message: {content[:50]}...")  # Debug print

                # Check for magetsi azima patterns (case insensitive)
                content_lower = content.lower()
                is_azima = ('magets' in content_lower and 'azima' in content_lower) or \
                          ('azima' in content_lower and 'magets' in content_lower) or \
                          ('magets' in content_lower and ('azima' in content_lower or 'azam' in content_lower))

                if is_azima:
                    print(f"DEBUG: Found azima message: {content}")  # Debug print

                    # Parse timestamp
                    try:
                        # Handle different timestamp formats
                        if '/' in timestamp:
                            # Format: 2026/03/02 10:47:45
                            dt = datetime.strptime(timestamp, '%Y/%m/%d %H:%M:%S')
                        else:
                            # Try other formats if needed
                            dt = datetime.fromisoformat(timestamp.replace(' ', 'T'))
                    except:
                        print(f"Could not parse timestamp: {timestamp}")
                        continue

                    azima_events.append({
                        'timestamp': dt,
                        'content': content,
                        'phone': phone
                    })

        return sorted(azima_events, key=lambda x: x['timestamp'])

    def analyze_azima_impact(self, azima_events):
        """Analyze the operational impact of azima events"""
        analysis = {
            'total_azima_events': len(azima_events),
            'events_by_month': {},
            'operational_impact': [],
            'patterns': []
        }

        if not azima_events:
            return analysis

        # Group by month
        for event in azima_events:
            month_key = event['timestamp'].strftime('%Y-%m')
            if month_key not in analysis['events_by_month']:
                analysis['events_by_month'][month_key] = 0
            analysis['events_by_month'][month_key] += 1

        # Analyze operational impact - check cycles around azima events
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            for event in azima_events:
                event_time = event['timestamp']

                # Look for cycles that might be affected (within 24 hours of event)
                start_window = event_time - timedelta(hours=12)
                end_window = event_time + timedelta(hours=12)

                cursor.execute("""
                    SELECT id, cycle_start, cycle_end, status, total_usage_kwh,
                           expected_revenue, total_actual_cash
                    FROM cycle
                    WHERE mill_id = 'NABIWI'
                      AND cycle_start BETWEEN ? AND ?
                    ORDER BY cycle_start
                """, (start_window, end_window))

                affected_cycles = [dict(row) for row in cursor.fetchall()]

                impact = {
                    'event_time': event_time,
                    'event_content': event['content'],
                    'affected_cycles': len(affected_cycles),
                    'cycles_details': affected_cycles,
                    'total_usage_impacted': sum(c.get('total_usage_kwh', 0) for c in affected_cycles),
                    'revenue_impacted': sum(c.get('expected_revenue', 0) for c in affected_cycles)
                }

                analysis['operational_impact'].append(impact)

        # Identify patterns
        if len(azima_events) > 1:
            # Calculate average time between events
            timestamps = [e['timestamp'] for e in azima_events]
            intervals = []
            for i in range(1, len(timestamps)):
                interval = (timestamps[i] - timestamps[i-1]).total_seconds() / 86400  # days
                intervals.append(interval)

            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                analysis['patterns'].append(f"Average {avg_interval:.1f} days between azima events")

        # Check for seasonal patterns
        monthly_counts = analysis['events_by_month']
        if len(monthly_counts) > 3:
            peak_month = max(monthly_counts.items(), key=lambda x: x[1])
            analysis['patterns'].append(f"Peak activity in {peak_month[0]} ({peak_month[1]} events)")

        return analysis

    def generate_report(self):
        """Generate comprehensive magetsi azima tracking report"""
        print("=" * 80)
        print("MAGETSI AZIMA TRACKER - NABIWI NODE")
        print("=" * 80)

        # Extract events
        azima_events = self.extract_azima_events_from_sms()
        print(f"\n[*] Total Magetsi Azima Events: {len(azima_events)}")

        if not azima_events:
            print("[-] No magetsi azima events found in SMS data")
            return

        # Analyze impact
        analysis = self.analyze_azima_impact(azima_events)

        # Monthly breakdown
        print("\n📅 Events by Month:")
        for month, count in sorted(analysis['events_by_month'].items()):
            print(f"  {month}: {count} events")

        # Recent events
        print("\n🕐 Recent Magetsi Azima Events:")
        for event in azima_events[-5:]:  # Last 5 events
            print(f"  {event['timestamp'].strftime('%Y-%m-%d %H:%M')}: {event['content'][:60]}...")

        # Operational impact summary
        total_affected_cycles = sum(impact['affected_cycles'] for impact in analysis['operational_impact'])
        total_usage_impacted = sum(impact['total_usage_impacted'] for impact in analysis['operational_impact'])
        total_revenue_impacted = sum(impact['revenue_impacted'] for impact in analysis['operational_impact'])

        print("\n⚡ Operational Impact Summary:")
        print(f"  Total cycles potentially affected: {total_affected_cycles}")
        print(f"  Total usage potentially impacted: {total_usage_impacted:.1f} kWh")
        print(f"  Total revenue potentially impacted: MK{total_revenue_impacted:,.0f}")

        # Patterns
        if analysis['patterns']:
            print("\n🔍 Detected Patterns:")
            for pattern in analysis['patterns']:
                print(f"  • {pattern}")

        # Reliability metrics
        total_cycles = self._get_nabiwi_cycle_count()
        azima_frequency = len(azima_events) / max(1, total_cycles) * 100

        print("\n📈 Reliability Metrics:")
        print(f"  Azima frequency: {azima_frequency:.2f}% of cycles")
        print(f"  Average events per month: {len(azima_events) / max(1, len(analysis['events_by_month'])):.1f}")

        print("\n" + "=" * 80)

    def _get_nabiwi_cycle_count(self):
        """Get total number of NABIWI cycles"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cycle WHERE mill_id = 'NABIWI'")
            return cursor.fetchone()[0]

    def export_azima_data(self, output_file='nabiwi_magetsi_azima_report.csv'):
        """Export detailed azima tracking data to CSV"""
        azima_events = self.extract_azima_events_from_sms()
        analysis = self.analyze_azima_impact(azima_events)

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Event Timestamp', 'Content', 'Affected Cycles', 'Usage Impact (kWh)', 'Revenue Impact (MK)'])

            for impact in analysis['operational_impact']:
                writer.writerow([
                    impact['event_time'].strftime('%Y-%m-%d %H:%M:%S'),
                    impact['event_content'],
                    impact['affected_cycles'],
                    f"{impact['total_usage_impacted']:.1f}",
                    f"{impact['revenue_impacted']:,.0f}"
                ])

        print(f"✅ Detailed report exported to {output_file}")

def main():
    """Main tracking function"""
    tracker = MagetsiAzimaTracker()

    # Generate comprehensive report
    tracker.generate_report()

    # Export detailed data
    tracker.export_azima_data()

if __name__ == '__main__':
    main()