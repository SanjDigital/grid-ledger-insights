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
        print("\n[*] Events by Month:")
        for month, count in sorted(analysis['events_by_month'].items()):
            print(f"  {month}: {count} events")

        # Recent events
        print("\n[*] Recent Magetsi Azima Events:")
        for event in azima_events[-5:]:  # Last 5 events
            print(f"  {event['timestamp'].strftime('%Y-%m-%d %H:%M')}: {event['content'][:60]}...")

        # Operational impact summary
        total_affected_cycles = sum(impact['affected_cycles'] for impact in analysis['operational_impact'])
        total_usage_impacted = sum(impact['total_usage_impacted'] for impact in analysis['operational_impact'])
        total_revenue_impacted = sum(impact['revenue_impacted'] for impact in analysis['operational_impact'])

        print("\n[*] Operational Impact Summary:")
        print(f"  Total cycles potentially affected: {total_affected_cycles}")
        print(f"  Total usage potentially impacted: {total_usage_impacted:.1f} kWh")
        print(f"  Total revenue potentially impacted: MK{total_revenue_impacted:,.0f}")

        # Patterns
        if analysis['patterns']:
            print("\n[*] Detected Patterns:")
            for pattern in analysis['patterns']:
                print(f"  - {pattern}")

        # Reliability metrics
        total_cycles = self._get_nabiwi_cycle_count()
        azima_frequency = len(azima_events) / max(1, total_cycles) * 100

        print("\n[*] Reliability Metrics:")
        print(f"  Azima frequency: {azima_frequency:.2f}% of cycles")
        print(f"  Average events per month: {len(azima_events) / max(1, len(analysis['events_by_month'])):.1f}")

        print("\n" + "=" * 80)