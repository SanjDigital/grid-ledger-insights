#!/usr/bin/env python3
"""
Node Inventory Query - Executable Implementation

GridLedger IP Ltd · May 2026
Generates per-node metrics for quality gate evaluation
"""

import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = 'data/gridledger.db'

def run_node_inventory_query():
    """Execute node-level metrics query"""
    
    conn = sqlite3.connect(DB_PATH)
    
    query = """
    SELECT
        c.mill_id,
        COUNT(DISTINCT c.id) AS total_cycles,
        COUNT(DISTINCT CASE WHEN c.status = 'SEALED' THEN c.id END) AS sealed_cycles,
        COUNT(DISTINCT CASE WHEN c.status = 'VERIFIED' THEN c.id END) AS verified_cycles,
        COUNT(DISTINCT CASE WHEN c.status IN ('MISSING', 'DISPUTED') THEN c.id END) AS failed_cycles,
        COUNT(DISTINCT CASE WHEN c.status = 'INTERRUPTED' THEN c.id END) AS interrupted_cycles,
        
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
    
    try:
        df_nodes = pd.read_sql_query(query, conn)
        return df_nodes
    finally:
        conn.close()

def run_glass_box_query():
    """Identify nodes with >=10 consecutive clean cycles"""
    
    conn = sqlite3.connect(DB_PATH)
    
    query = """
    WITH ordered_cycles AS (
        SELECT
            mill_id,
            id AS cycle_id,
            status AS cycle_status,
            cycle_start,
            cycle_end,
            CASE 
                WHEN total_actual_cash IS NOT NULL 
                    AND expected_revenue IS NOT NULL 
                    AND expected_revenue > 0
                THEN (total_actual_cash / expected_revenue) * 100
                ELSE NULL
            END AS adherence_pct,
            CASE 
                WHEN status IN ('SEALED', 'VERIFIED') 
                    AND CASE 
                        WHEN total_actual_cash IS NOT NULL 
                            AND expected_revenue IS NOT NULL 
                            AND expected_revenue > 0
                        THEN (total_actual_cash / expected_revenue) * 100
                        ELSE 0
                    END >= 90.0
                THEN 1 
                ELSE 0 
            END AS is_clean,
            ROW_NUMBER() OVER (PARTITION BY mill_id ORDER BY cycle_start) AS rn,
            ROW_NUMBER() OVER (
                PARTITION BY mill_id, 
                CASE 
                    WHEN status IN ('SEALED', 'VERIFIED') 
                        AND CASE 
                            WHEN total_actual_cash IS NOT NULL 
                                AND expected_revenue IS NOT NULL 
                                AND expected_revenue > 0
                            THEN (total_actual_cash / expected_revenue) * 100
                            ELSE 0
                        END >= 90.0
                    THEN 1 
                    ELSE 0 
                END
                ORDER BY cycle_start
            ) AS clean_rn
        FROM cycle
        WHERE cycle_start IS NOT NULL
    ),

    consecutive_groups AS (
        SELECT
            mill_id,
            is_clean,
            rn - clean_rn AS grp,
            COUNT(*) AS consecutive_count,
            MIN(cycle_start) AS window_start,
            MAX(cycle_end) AS window_end
        FROM ordered_cycles
        WHERE is_clean = 1
        GROUP BY mill_id, is_clean, rn - clean_rn
    )

    SELECT
        mill_id,
        MAX(consecutive_count) AS max_consecutive_clean_cycles,
        window_start,
        window_end
    FROM consecutive_groups
    WHERE consecutive_count >= 10
    GROUP BY mill_id
    ORDER BY MAX(consecutive_count) DESC;
    """
    
    try:
        df_glass_box = pd.read_sql_query(query, conn)
        return df_glass_box
    finally:
        conn.close()

def run_portfolio_query():
    """Get portfolio-level aggregation"""
    
    conn = sqlite3.connect(DB_PATH)
    
    query = """
    SELECT
        COUNT(DISTINCT mill_id) AS total_nodes,
        COUNT(DISTINCT CASE WHEN status = 'SEALED' THEN id END) AS total_sealed_cycles,
        SUM(total_usage_kwh) AS portfolio_total_kwh,
        SUM(total_actual_cash) AS portfolio_total_cash,
        SUM(expected_revenue) AS portfolio_expected_revenue,
        
        ROUND(AVG(integrity_score), 3) AS portfolio_avg_integrity_score
        
    FROM cycle
    WHERE cycle_start >= '2023-07-01';
    """
    
    try:
        df_portfolio = pd.read_sql_query(query, conn)
        return df_portfolio
    finally:
        conn.close()

def generate_quality_gate_table(df_nodes, df_glass_box):
    """Create quality gate evaluation table"""
    
    if df_nodes is None or df_nodes.empty:
        print("No operational data to evaluate")
        return None
    
    df_glass_box_set = set(df_glass_box['mill_id']) if df_glass_box is not None and not df_glass_box.empty else set()
    
    quality_gates = []
    
    for _, row in df_nodes.iterrows():
        mill_id = row['mill_id']
        
        # Glass Box: >=10 consecutive clean
        glass_box = 'YES' if mill_id in df_glass_box_set else 'NO'
        
        # Forensic: >=5 sealed, >=90 days, >=60% completion
        days_span = 0
        if row['first_cycle_date'] and row['last_cycle_date']:
            first = pd.to_datetime(row['first_cycle_date'])
            last = pd.to_datetime(row['last_cycle_date'])
            days_span = (last - first).days
        
        forensic = 'YES' if (row['sealed_cycles'] >= 5 and days_span >= 90 and row['verified_completion_rate_pct'] >= 60) else 'NO'
        
        # ESG: >=12 months, avg_integrity >= 90%
        esg = 'YES' if (days_span >= 365 and row['avg_integrity_score'] is not None and row['avg_integrity_score'] >= 0.90) else 'NO'
        
        # Portfolio: >=1 sealed
        portfolio = 'YES' if row['sealed_cycles'] >= 1 else 'NO'
        
        # Baseline: >=5 cycles
        baseline = 'YES' if row['total_cycles'] >= 5 else 'NO'
        
        quality_gates.append({
            'Node': mill_id,
            'Total_Cycles': int(row['total_cycles']),
            'Sealed': int(row['sealed_cycles']),
            'Verified': int(row['verified_cycles']),
            'Failed': int(row['failed_cycles']),
            'Completion_%': row['verified_completion_rate_pct'],
            'Avg_Integrity': row['avg_integrity_score'],
            'Avg_Variance': row['avg_variance'],
            'Days_Span': days_span,
            'Glass_Box': glass_box,
            'Forensic': forensic,
            'ESG': esg,
            'Portfolio': portfolio,
            'Baseline': baseline,
        })
    
    return pd.DataFrame(quality_gates)

def main():
    print("=" * 80)
    print("NODE INVENTORY QUERY v1.0")
    print("GridLedger IP Ltd - May 2026")
    print("=" * 80)
    print()
    
    # Run queries
    print("[1/3] Running node-level metrics query...")
    df_nodes = run_node_inventory_query()
    
    print("[2/3] Running Glass Box qualification query...")
    df_glass_box = run_glass_box_query()
    
    print("[3/3] Running portfolio aggregation...")
    df_portfolio = run_portfolio_query()
    
    print()
    print("-" * 80)
    print("RESULTS")
    print("-" * 80)
    print()
    
    if df_nodes is None or df_nodes.empty:
        print("DATABASE STATUS: No operational data found")
        print()
        print("The database schema is initialized but contains no cycle data.")
        print("Monetization path evaluation requires:")
        print("  - Mill configuration and registration")
        print("  - Cycle data ingestion from operational sources")
        print("  - Reconciliation record completion")
        print()
        print("To proceed:")
        print("  1. Ingest cycle data from operational mills")
        print("  2. Re-run: python run_node_inventory_query.py")
        return
    
    print(f"[NODES] Retrieved metrics for {len(df_nodes)} node(s)")
    print()
    print(df_nodes.to_string(index=False))
    print()
    
    if df_glass_box is not None and not df_glass_box.empty:
        print(f"[GLASS BOX] {len(df_glass_box)} node(s) qualify for Glass Box certification")
        print()
        print(df_glass_box.to_string(index=False))
        print()
    else:
        print("[GLASS BOX] No nodes qualify (requires >=10 consecutive clean cycles)")
        print()
    
    if df_portfolio is not None and not df_portfolio.empty:
        print("[PORTFOLIO SUMMARY]")
        print()
        print(df_portfolio.to_string(index=False))
        print()
    
    # Generate quality gate table
    print("[QUALITY GATE EVALUATION]")
    print()
    df_quality = generate_quality_gate_table(df_nodes, df_glass_box)
    if df_quality is not None:
        print(df_quality.to_string(index=False))
        print()
        
        # Save outputs
        print("Saving results...")
        df_nodes.to_csv('node_inventory_metrics.csv', index=False)
        df_quality.to_csv('node_inventory_quality_gates.csv', index=False)
        
        try:
            with pd.ExcelWriter('node_inventory_results.xlsx', engine='openpyxl') as writer:
                df_nodes.to_excel(writer, sheet_name='Node Metrics', index=False)
                df_quality.to_excel(writer, sheet_name='Quality Gates', index=False)
                if df_portfolio is not None and not df_portfolio.empty:
                    df_portfolio.to_excel(writer, sheet_name='Portfolio', index=False)
            print("  - node_inventory_results.xlsx")
        except Exception as e:
            print(f"  (Excel export not available: {e})")
        
        print("  - node_inventory_metrics.csv")
        print("  - node_inventory_quality_gates.csv")
    
    print()
    print("=" * 80)
    print("Execution complete - NODE INVENTORY QUERY v1.0")
    print("=" * 80)

if __name__ == '__main__':
    main()
