#!/usr/bin/env python3
"""
DEMO: Node Inventory Query with Sample Data

This script demonstrates what the Node Inventory Query will produce once 
operational cycle data is ingested. It creates sample data, runs the query, 
and shows the expected output format.

Usage: python demo_node_inventory_query.py
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random

DB_PATH = 'data/gridledger.db'

def create_sample_data(conn, num_nodes=3, cycles_per_node=50):
    """Populate sample cycle data for demonstration"""
    
    cursor = conn.cursor()
    
    # Sample mill IDs (simulating NABIWI and others)
    mills = ['NABIWI', 'KISUTU', 'BANDARI'][:num_nodes]
    
    # Sample statuses with realistic distribution
    statuses = ['SEALED', 'SEALED', 'SEALED', 'VERIFIED', 'VERIFIED', 'INTERRUPTED']
    
    print(f"Generating {cycles_per_node} cycles per node ({num_nodes} nodes)...")
    
    for mill_id in mills:
        start_date = datetime.now() - timedelta(days=365)
        
        for i in range(cycles_per_node):
            cycle_start = start_date + timedelta(days=i*7)
            cycle_end = cycle_start + timedelta(days=6)
            
            # Realistic metrics
            total_usage_kwh = random.uniform(1000, 5000)
            expected_revenue = random.uniform(100, 500)
            adherence = random.uniform(0.85, 1.05)
            total_actual_cash = expected_revenue * adherence
            
            integrity_score = random.uniform(0.85, 1.0)
            variance = random.uniform(0.5, 15.0)
            
            status = random.choice(statuses)
            seal = f"seal_{mill_id}_{i}" if status in ['SEALED', 'VERIFIED'] else None
            anchor = 'ANCHORED' if random.random() > 0.2 else 'PENDING'
            
            cursor.execute("""
                INSERT INTO cycle (
                    mill_id, status, cycle_start, cycle_end,
                    total_usage_kwh, total_actual_cash, expected_revenue,
                    integrity_score, variance, cycle_seal, anchor_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mill_id, status, cycle_start, cycle_end,
                total_usage_kwh, total_actual_cash, expected_revenue,
                integrity_score, variance, seal, anchor
            ))
    
    conn.commit()
    print(f"Created sample data: {num_nodes} nodes x {cycles_per_node} cycles")

def run_node_inventory_query(conn):
    """Execute node-level metrics query"""
    
    query = """
    SELECT
        c.mill_id,
        COUNT(DISTINCT c.id) AS total_cycles,
        COUNT(DISTINCT CASE WHEN c.status = 'SEALED' THEN c.id END) AS sealed_cycles,
        COUNT(DISTINCT CASE WHEN c.status = 'VERIFIED' THEN c.id END) AS verified_cycles,
        COUNT(DISTINCT CASE WHEN c.status IN ('MISSING', 'DISPUTED') THEN c.id END) AS failed_cycles,
        
        ROUND(
            CAST(COUNT(DISTINCT CASE WHEN c.status IN ('SEALED', 'VERIFIED') THEN c.id END) AS FLOAT) /
            NULLIF(COUNT(DISTINCT c.id), 0) * 100, 1
        ) AS verified_completion_rate_pct,
        
        ROUND(AVG(CASE WHEN c.integrity_score IS NOT NULL THEN c.integrity_score END), 3) AS avg_integrity_score,
        ROUND(MIN(CASE WHEN c.integrity_score IS NOT NULL THEN c.integrity_score END), 3) AS min_integrity_score,
        ROUND(MAX(CASE WHEN c.integrity_score IS NOT NULL THEN c.integrity_score END), 3) AS max_integrity_score,
        
        ROUND(AVG(CASE WHEN c.variance IS NOT NULL THEN c.variance END), 2) AS avg_variance,
        ROUND(MIN(CASE WHEN c.variance IS NOT NULL THEN c.variance END), 2) AS min_variance,
        ROUND(MAX(CASE WHEN c.variance IS NOT NULL THEN c.variance END), 2) AS max_variance,
        
        SUM(CASE WHEN c.total_usage_kwh IS NOT NULL THEN c.total_usage_kwh ELSE 0 END) AS total_usage_kwh,
        SUM(CASE WHEN c.total_actual_cash IS NOT NULL THEN c.total_actual_cash ELSE 0 END) AS total_actual_cash,
        SUM(CASE WHEN c.expected_revenue IS NOT NULL THEN c.expected_revenue ELSE 0 END) AS total_expected_revenue,
        
        COUNT(DISTINCT CASE WHEN c.cycle_seal IS NOT NULL THEN c.id END) AS cycles_with_seal,
        COUNT(DISTINCT CASE WHEN c.anchor_status = 'ANCHORED' THEN c.id END) AS cycles_anchored,
        
        MIN(c.cycle_start) AS first_cycle_date,
        MAX(c.cycle_end) AS last_cycle_date,
        
        ROUND(
            AVG(CASE 
                WHEN c.expected_revenue IS NOT NULL AND c.expected_revenue > 0
                THEN (c.total_actual_cash / c.expected_revenue) * 100 
                END), 1
        ) AS avg_adherence_pct

    FROM cycle c
    WHERE c.cycle_start >= '2023-07-01'
    GROUP BY c.mill_id
    ORDER BY COUNT(DISTINCT CASE WHEN c.status = 'SEALED' THEN c.id END) DESC;
    """
    
    df = pd.read_sql_query(query, conn)
    return df

def generate_quality_gates(df_nodes):
    """Generate quality gate evaluation"""
    
    gates = []
    for _, row in df_nodes.iterrows():
        mill_id = row['mill_id']
        
        # Calculate days span
        if row['first_cycle_date'] and row['last_cycle_date']:
            first = pd.to_datetime(row['first_cycle_date'])
            last = pd.to_datetime(row['last_cycle_date'])
            days_span = (last - first).days
        else:
            days_span = 0
        
        # Glass Box: >=10 sealed AND >=90% adherence
        glass_box = 'PASS' if (row['sealed_cycles'] >= 10 and row['avg_adherence_pct'] >= 90.0) else 'FAIL'
        
        # Forensic: >=5 sealed AND >=90 days AND >=60% completion
        forensic = 'PASS' if (row['sealed_cycles'] >= 5 and days_span >= 90 and row['verified_completion_rate_pct'] >= 60) else 'FAIL'
        
        # ESG: >=12 months AND avg_integrity >= 90%
        esg = 'PASS' if (days_span >= 365 and row['avg_integrity_score'] >= 0.90) else 'FAIL'
        
        # Portfolio: >=1 sealed
        portfolio = 'PASS' if row['sealed_cycles'] >= 1 else 'FAIL'
        
        # Baseline: >=5 cycles
        baseline = 'PASS' if row['total_cycles'] >= 5 else 'FAIL'
        
        gates.append({
            'Node': mill_id,
            'Total': int(row['total_cycles']),
            'Sealed': int(row['sealed_cycles']),
            'Verified': int(row['verified_cycles']),
            'Failed': int(row['failed_cycles']),
            'Completion_%': row['verified_completion_rate_pct'],
            'Avg_Integrity': row['avg_integrity_score'],
            'Glass_Box': glass_box,
            'Forensic': forensic,
            'ESG': esg,
            'Portfolio': portfolio,
            'Baseline': baseline,
        })
    
    return pd.DataFrame(gates)

def main():
    print("=" * 80)
    print("DEMO: Node Inventory Query with Sample Data")
    print("GridLedger IP Ltd · May 2026")
    print("=" * 80)
    print()
    
    # Connect
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Check if sample data already exists
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cycle")
        existing = cursor.fetchone()[0]
        
        if existing > 0:
            print("Sample data already exists. Using existing data.")
        else:
            print("Generating sample data...")
            create_sample_data(conn, num_nodes=3, cycles_per_node=50)
            print()
        
        # Run query
        print("Running Node Inventory Query...")
        df_nodes = run_node_inventory_query(conn)
        
        print(f"Retrieved {len(df_nodes)} node(s)")
        print()
        print("NODE-LEVEL METRICS:")
        print("-" * 80)
        print(df_nodes.to_string(index=False))
        print()
        
        # Generate quality gates
        print("QUALITY GATE EVALUATION:")
        print("-" * 80)
        df_gates = generate_quality_gates(df_nodes)
        print(df_gates.to_string(index=False))
        print()
        
        # Save
        print("Saving demo results...")
        df_nodes.to_csv('demo_node_inventory_metrics.csv', index=False)
        df_gates.to_csv('demo_node_inventory_quality_gates.csv', index=False)
        print("  - demo_node_inventory_metrics.csv")
        print("  - demo_node_inventory_quality_gates.csv")
        
        # Summary
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total Nodes: {len(df_nodes)}")
        print(f"Total Sealed Cycles: {df_nodes['sealed_cycles'].sum()}")
        print(f"Portfolio Adherence: {df_nodes['avg_adherence_pct'].mean():.1f}%")
        print(f"Glass Box Ready: {(df_gates['Glass_Box'] == 'PASS').sum()}/{len(df_gates)}")
        print(f"Forensic Ready: {(df_gates['Forensic'] == 'PASS').sum()}/{len(df_gates)}")
        print(f"ESG Ready: {(df_gates['ESG'] == 'PASS').sum()}/{len(df_gates)}")
        print()
        
    finally:
        conn.close()

if __name__ == '__main__':
    main()
