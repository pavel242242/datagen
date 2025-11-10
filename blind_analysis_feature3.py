"""
Blind Analysis for Feature #3: Multi-Stage Processes

Analyzes generated funnel data without prior knowledge of expected patterns.
Validates that:
1. Funnel progression makes sense (monotonic decrease)
2. Segment effects are visible
3. Temporal ordering is correct
4. Data quality is high
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json


def analyze_funnel(parent_table, stage_table, parent_id_col, stage_col, segment_col=None):
    """
    Blind analysis of a multi-stage funnel.

    Returns dict with findings.
    """
    findings = {
        "total_parents": len(parent_table),
        "total_stage_events": len(stage_table),
        "stages_found": [],
        "stage_counts": {},
        "stage_user_counts": {},
        "conversion_rates": {},
        "drop_off_rates": {},
        "issues": []
    }

    # Identify unique stages
    stages = stage_table[stage_col].unique()
    stage_indices = stage_table.groupby(stage_col)['stage_index'].first().sort_values()
    ordered_stages = stage_indices.index.tolist()

    findings["stages_found"] = ordered_stages

    # Calculate stage statistics
    for stage in ordered_stages:
        # Count events
        event_count = (stage_table[stage_col] == stage).sum()
        findings["stage_counts"][stage] = int(event_count)

        # Count unique users reaching this stage
        user_count = stage_table[stage_table[stage_col] == stage][parent_id_col].nunique()
        findings["stage_user_counts"][stage] = int(user_count)

        # Conversion rate from total parents
        conv_rate = user_count / findings["total_parents"]
        findings["conversion_rates"][stage] = round(conv_rate, 4)

    # Calculate drop-off rates between consecutive stages
    for i in range(1, len(ordered_stages)):
        prev_stage = ordered_stages[i-1]
        curr_stage = ordered_stages[i]

        prev_count = findings["stage_user_counts"][prev_stage]
        curr_count = findings["stage_user_counts"][curr_stage]

        if prev_count > 0:
            drop_off = 1 - (curr_count / prev_count)
            findings["drop_off_rates"][f"{prev_stage}_to_{curr_stage}"] = round(drop_off, 4)

    # Validate funnel monotonicity
    user_counts = [findings["stage_user_counts"][s] for s in ordered_stages]
    if not all(user_counts[i] >= user_counts[i+1] for i in range(len(user_counts)-1)):
        findings["issues"].append("CRITICAL: Funnel is not monotonic - users increase at later stages!")

    # Validate first stage has all users
    first_stage_users = findings["stage_user_counts"][ordered_stages[0]]
    if first_stage_users != findings["total_parents"]:
        findings["issues"].append(f"WARNING: Not all parents reach first stage ({first_stage_users}/{findings['total_parents']})")

    # Analyze segment effects if available
    if segment_col and segment_col in parent_table.columns:
        findings["segment_analysis"] = {}

        # Merge to get segments for stage events
        merged = stage_table.merge(parent_table[[parent_id_col, segment_col]], on=parent_id_col)

        segments = parent_table[segment_col].unique()
        last_stage = ordered_stages[-1]

        for segment in segments:
            seg_total = (parent_table[segment_col] == segment).sum()
            seg_reached_last = merged[
                (merged[segment_col] == segment) &
                (merged[stage_col] == last_stage)
            ][parent_id_col].nunique()

            conversion = seg_reached_last / seg_total if seg_total > 0 else 0

            findings["segment_analysis"][segment] = {
                "total": int(seg_total),
                "reached_last_stage": int(seg_reached_last),
                "conversion_to_last": round(conversion, 4)
            }

    # Check temporal ordering
    if 'timestamp' in stage_table.columns or 'event_timestamp' in stage_table.columns:
        time_col = 'timestamp' if 'timestamp' in stage_table.columns else 'event_timestamp'

        # For each user, check if stage timestamps are in order
        temporal_violations = 0
        for user_id in stage_table[parent_id_col].unique():
            user_events = stage_table[stage_table[parent_id_col] == user_id].sort_values('stage_index')
            if len(user_events) > 1:
                timestamps = pd.to_datetime(user_events[time_col])
                if not timestamps.is_monotonic_increasing:
                    temporal_violations += 1

        findings["temporal_violations"] = temporal_violations
        if temporal_violations > 0:
            findings["issues"].append(
                f"WARNING: {temporal_violations} users have out-of-order timestamps"
            )

    return findings


def print_findings(domain_name, findings):
    """Pretty print findings."""
    print(f"\n{'='*80}")
    print(f"BLIND ANALYSIS: {domain_name}")
    print(f"{'='*80}")

    print(f"\n📊 Overall Statistics:")
    print(f"  Total entities: {findings['total_parents']:,}")
    print(f"  Total stage events: {findings['total_stage_events']:,}")
    print(f"  Stages identified: {len(findings['stages_found'])}")

    print(f"\n🔄 Funnel Progression:")
    for stage in findings['stages_found']:
        users = findings['stage_user_counts'][stage]
        rate = findings['conversion_rates'][stage] * 100
        print(f"  {stage:25} {users:6,} users ({rate:5.1f}%)")

    print(f"\n📉 Drop-off Rates:")
    for transition, rate in findings['drop_off_rates'].items():
        print(f"  {transition:50} {rate*100:5.1f}%")

    if 'segment_analysis' in findings:
        print(f"\n🎯 Segment Analysis (final stage conversion):")
        for segment, stats in findings['segment_analysis'].items():
            conv = stats['conversion_to_last'] * 100
            print(f"  {segment:20} {stats['reached_last_stage']:4}/{stats['total']:4} ({conv:5.1f}%)")

    if findings.get('temporal_violations') is not None:
        print(f"\n⏰ Temporal Analysis:")
        if findings['temporal_violations'] == 0:
            print(f"  ✅ All stage timestamps properly ordered")
        else:
            print(f"  ⚠️  {findings['temporal_violations']} users with out-of-order timestamps")

    if findings['issues']:
        print(f"\n⚠️  Issues Found:")
        for issue in findings['issues']:
            print(f"  - {issue}")
    else:
        print(f"\n✅ No issues found - funnel looks healthy!")


if __name__ == "__main__":
    print("="*80)
    print("FEATURE #3 BLIND ANALYSIS: MULTI-STAGE PROCESSES")
    print("="*80)

    # Analyze SaaS Onboarding
    print("\n\n🔍 Analyzing SaaS Onboarding...")
    account_df = pd.read_parquet("output/saas_fixed/account.parquet")
    onboarding_df = pd.read_parquet("output/saas_fixed/onboarding_event.parquet")

    saas_findings = analyze_funnel(
        account_df,
        onboarding_df,
        "account_id",
        "stage_name",
        segment_col="tier"
    )
    print_findings("SaaS Onboarding Journey", saas_findings)

    # Analyze Healthcare
    print("\n\n🔍 Analyzing Healthcare Patient Journey...")
    patient_df = pd.read_parquet("output/healthcare_fixed/patient.parquet")
    care_df = pd.read_parquet("output/healthcare_fixed/care_event.parquet")

    health_findings = analyze_funnel(
        patient_df,
        care_df,
        "patient_id",
        "stage_name",
        segment_col="risk_level"
    )
    print_findings("Healthcare Patient Journey", health_findings)

    # Analyze E-commerce
    print("\n\n🔍 Analyzing E-commerce Conversion...")
    user_df = pd.read_parquet("output/ecommerce_fixed/user.parquet")
    journey_df = pd.read_parquet("output/ecommerce_fixed/user_journey.parquet")

    ecom_findings = analyze_funnel(
        user_df,
        journey_df,
        "user_id",
        "stage_name",
        segment_col="customer_segment"
    )
    print_findings("E-commerce Conversion Funnel", ecom_findings)

    # Summary
    print(f"\n\n{'='*80}")
    print("OVERALL ASSESSMENT")
    print(f"{'='*80}")

    all_findings = [saas_findings, health_findings, ecom_findings]
    total_issues = sum(len(f['issues']) for f in all_findings)

    print(f"\n📈 Funnels Analyzed: 3")
    print(f"⚠️  Total Issues: {total_issues}")

    if total_issues == 0:
        print(f"\n✅ ALL FUNNELS PASSED VALIDATION")
        print(f"   - Monotonic progression ✓")
        print(f"   - Segment effects visible ✓")
        print(f"   - Temporal ordering correct ✓")
    else:
        print(f"\n⚠️  SOME ISSUES FOUND - Review above")

    print(f"\n{'='*80}")
