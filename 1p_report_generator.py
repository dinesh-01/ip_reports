#!/usr/bin/env python3
"""
1P Test Report Generator
Generates HTML stability report for 1P test cases from cx_dashboard database
"""

import pymysql
import sys
from datetime import datetime
import os
from collections import defaultdict

# Database configuration
DB_CONFIG = {
    'host': 'localhost',  # Replace with your database host
    'user': 'root',  # Replace with your database user
    'password': 'root',  # Replace with your database password
    'database': 'cx_dashboard',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    """Create and return database connection"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def execute_query(connection, query):
    """Execute query and return results"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

def get_overall_summary(connection, test_plan_id):
    """Get overall test summary statistics"""
    query = f"""
    WITH latest_runs AS (
        SELECT 
            test_case_key,
            MAX(created_at) as latest_run_time
        FROM tc_test_run
        WHERE test_plan_id = {test_plan_id}
            AND feature LIKE '%[1P]%'
        GROUP BY test_case_key
    ),
    test_data AS (
        SELECT 
            tr.test_case_status,
            tr.test_case_key
        FROM tc_test_run tr
        INNER JOIN latest_runs lr 
            ON tr.test_case_key = lr.test_case_key 
            AND tr.created_at = lr.latest_run_time
        WHERE tr.test_plan_id = {test_plan_id}
            AND tr.feature LIKE '%[1P]%'
    )
    SELECT 
        test_case_status,
        COUNT(DISTINCT test_case_key) as count
    FROM test_data
    GROUP BY test_case_status;
    """
    return execute_query(connection, query)

def get_squad_summary(connection, test_plan_id):
    """Get squad-wise summary"""
    query = f"""
    WITH latest_runs AS (
        SELECT 
            test_case_key,
            MAX(created_at) as latest_run_time
        FROM tc_test_run
        WHERE test_plan_id = {test_plan_id}
            AND feature LIKE '%[1P]%'
        GROUP BY test_case_key
    ),
    test_data AS (
        SELECT 
            tr.owner as squad,
            tr.test_case_status,
            tr.test_case_key
        FROM tc_test_run tr
        INNER JOIN latest_runs lr 
            ON tr.test_case_key = lr.test_case_key 
            AND tr.created_at = lr.latest_run_time
        WHERE tr.test_plan_id = {test_plan_id}
            AND tr.feature LIKE '%[1P]%'
    )
    SELECT 
        squad,
        COUNT(DISTINCT test_case_key) as total_tests,
        SUM(CASE WHEN test_case_status = 'passed' THEN 1 ELSE 0 END) as passed,
        SUM(CASE WHEN test_case_status = 'failed' THEN 1 ELSE 0 END) as failed,
        SUM(CASE WHEN test_case_status = 'blocked' THEN 1 ELSE 0 END) as blocked,
        SUM(CASE WHEN test_case_status = 'application_bug' THEN 1 ELSE 0 END) as app_bug,
        SUM(CASE WHEN test_case_status = 'not_implemented' THEN 1 ELSE 0 END) as not_implemented,
        ROUND(SUM(CASE WHEN test_case_status = 'passed' THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT test_case_key), 1) as success_rate
    FROM test_data
    GROUP BY squad
    ORDER BY total_tests DESC;
    """
    return execute_query(connection, query)

def get_feature_summary(connection, test_plan_id):
    """Get feature-wise summary"""
    query = f"""
    WITH latest_runs AS (
        SELECT 
            test_case_key,
            MAX(created_at) as latest_run_time
        FROM tc_test_run
        WHERE test_plan_id = {test_plan_id}
            AND feature LIKE '%[1P]%'
        GROUP BY test_case_key
    ),
    test_data AS (
        SELECT 
            tr.feature,
            tr.test_case_status,
            tr.test_case_key
        FROM tc_test_run tr
        INNER JOIN latest_runs lr 
            ON tr.test_case_key = lr.test_case_key 
            AND tr.created_at = lr.latest_run_time
        WHERE tr.test_plan_id = {test_plan_id}
            AND tr.feature LIKE '%[1P]%'
    )
    SELECT 
        feature,
        COUNT(DISTINCT test_case_key) as total_tests,
        SUM(CASE WHEN test_case_status = 'passed' THEN 1 ELSE 0 END) as passed,
        SUM(CASE WHEN test_case_status = 'failed' THEN 1 ELSE 0 END) as failed,
        SUM(CASE WHEN test_case_status = 'blocked' THEN 1 ELSE 0 END) as blocked,
        SUM(CASE WHEN test_case_status = 'application_bug' THEN 1 ELSE 0 END) as app_bug,
        SUM(CASE WHEN test_case_status = 'not_implemented' THEN 1 ELSE 0 END) as not_implemented,
        ROUND(SUM(CASE WHEN test_case_status = 'passed' THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT test_case_key), 1) as success_rate
    FROM test_data
    GROUP BY feature
    ORDER BY total_tests DESC;
    """
    return execute_query(connection, query)

def get_feature_breakdown(connection, test_plan_id):
    """Get detailed feature breakdown"""
    query = f"""
    WITH latest_runs AS (
        SELECT 
            test_case_key,
            MAX(created_at) as latest_run_time
        FROM tc_test_run
        WHERE test_plan_id = {test_plan_id}
            AND feature LIKE '%[1P]%'
        GROUP BY test_case_key
    )
    SELECT 
        tr.feature,
        tr.owner as squad,
        tr.test_case_status,
        COUNT(*) as count
    FROM tc_test_run tr
    INNER JOIN latest_runs lr 
        ON tr.test_case_key = lr.test_case_key 
        AND tr.created_at = lr.latest_run_time
    WHERE tr.test_plan_id = {test_plan_id}
        AND tr.feature LIKE '%[1P]%'
    GROUP BY tr.feature, tr.owner, tr.test_case_status
    ORDER BY tr.feature, tr.owner, tr.test_case_status;
    """
    return execute_query(connection, query)

def get_epic_summary(connection, test_plan_id):
    """Get EPIC-wise summary"""
    query = f"""
    WITH latest_runs AS (
        SELECT 
            test_case_key,
            MAX(created_at) as latest_run_time
        FROM tc_test_run
        WHERE test_plan_id = {test_plan_id}
            AND feature LIKE '%[1P]%'
        GROUP BY test_case_key
    ),
    test_data AS (
        SELECT 
            tr.test_case_key,
            tr.test_case_status,
            tr.feature,
            tr.owner
        FROM tc_test_run tr
        INNER JOIN latest_runs lr 
            ON tr.test_case_key = lr.test_case_key 
            AND tr.created_at = lr.latest_run_time
        WHERE tr.test_plan_id = {test_plan_id}
            AND tr.feature LIKE '%[1P]%'
    )
    SELECT 
        COALESCE(e.epic_id, 'No EPIC') as epic_id,
        COALESCE(e.epic_title, 'Test cases without EPIC assignment') as epic_title,
        COUNT(DISTINCT td.test_case_key) as total_tests,
        SUM(CASE WHEN td.test_case_status = 'passed' THEN 1 ELSE 0 END) as passed,
        SUM(CASE WHEN td.test_case_status = 'failed' THEN 1 ELSE 0 END) as failed,
        SUM(CASE WHEN td.test_case_status = 'blocked' THEN 1 ELSE 0 END) as blocked,
        SUM(CASE WHEN td.test_case_status = 'application_bug' THEN 1 ELSE 0 END) as app_bug,
        SUM(CASE WHEN td.test_case_status = 'not_implemented' THEN 1 ELSE 0 END) as not_implemented,
        ROUND(SUM(CASE WHEN td.test_case_status = 'passed' THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT td.test_case_key), 1) as success_rate
    FROM test_data td
    LEFT JOIN tc_case_epic e ON td.test_case_key = e.test_case_id
    GROUP BY e.epic_id, e.epic_title
    ORDER BY total_tests DESC;
    """
    return execute_query(connection, query)

def get_squad_icon_class(squad_name):
    """Get CSS class for squad icon based on squad name"""
    squad_map = {
        'A-Team': 'squad-a',
        'Rajput Royals': 'squad-r',
        'Mavericks': 'squad-m',
        'Pirates': 'squad-p',
        'Ganges Gangsters': 'squad-g',
        'Spartans': 'squad-s',
        'Chalukyas': 'squad-ch',
        'Dravidian Dynamos': 'squad-d',
        'Hackers & Painters': 'squad-h',
        'ShadowFax': 'squad-sh',
        'Autobots': 'squad-au',
        'Chera super kings': 'squad-c',
        'Rashtrakutas': 'squad-r'
    }
    return squad_map.get(squad_name, 'squad-d')

def get_squad_initial(squad_name):
    """Get initial letter for squad icon"""
    initials_map = {
        'A-Team': 'A',
        'Rajput Royals': 'R',
        'Mavericks': 'M',
        'Pirates': 'P',
        'Ganges Gangsters': 'G',
        'Spartans': 'S',
        'Chalukyas': 'C',
        'Dravidian Dynamos': 'D',
        'Hackers & Painters': 'H',
        'ShadowFax': 'S',
        'Autobots': 'A',
        'Chera super kings': 'C',
        'Rashtrakutas': 'R'
    }
    return initials_map.get(squad_name, squad_name[0].upper())

def get_health_class(success_rate):
    """Get health class based on success rate"""
    if success_rate >= 95:
        return 'health-excellent'
    elif success_rate >= 80:
        return 'health-good'
    elif success_rate >= 60:
        return 'health-fair'
    elif success_rate >= 40:
        return 'health-poor'
    else:
        return 'health-critical'

def get_status_display(status):
    """Get display text for status"""
    status_map = {
        'passed': 'Passed',
        'failed': 'Failed',
        'blocked': 'Blocked',
        'application_bug': 'Application Bug',
        'not_implemented': 'Not Implemented'
    }
    return status_map.get(status, status.title())

def save_test_run_trend(connection, test_plan_id, overall_summary):
    """Save test run results to test_run_trend table"""
    try:
        # Calculate totals from overall summary
        passed = next((item['count'] for item in overall_summary if item['test_case_status'] == 'passed'), 0)
        failed = next((item['count'] for item in overall_summary if item['test_case_status'] == 'failed'), 0)
        blocked = next((item['count'] for item in overall_summary if item['test_case_status'] == 'blocked'), 0)
        app_bug = next((item['count'] for item in overall_summary if item['test_case_status'] == 'application_bug'), 0)
        not_implemented = next((item['count'] for item in overall_summary if item['test_case_status'] == 'not_implemented'), 0)
        
        # Current date in YYYY-MM-DD format
        run_date = datetime.now().strftime('%Y-%m-%d')
        
        # Check if entry already exists for today
        check_query = f"""
        SELECT id FROM test_run_trend 
        WHERE test_plan_id = {test_plan_id} AND run_date = '{run_date}'
        """
        
        with connection.cursor() as cursor:
            cursor.execute(check_query)
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                update_query = f"""
                UPDATE test_run_trend 
                SET passed = {passed}, 
                    failed = {failed}, 
                    blocked = {blocked}, 
                    application_bug = {app_bug}, 
                    not_implemented = {not_implemented}
                WHERE test_plan_id = {test_plan_id} AND run_date = '{run_date}'
                """
                cursor.execute(update_query)
                print(f"Updated existing trend record for plan {test_plan_id} on {run_date}")
            else:
                # Insert new record
                insert_query = f"""
                INSERT INTO test_run_trend 
                (test_plan_id, passed, failed, blocked, application_bug, not_implemented, run_date)
                VALUES ({test_plan_id}, {passed}, {failed}, {blocked}, {app_bug}, {not_implemented}, '{run_date}')
                """
                cursor.execute(insert_query)
                print(f"Inserted new trend record for plan {test_plan_id} on {run_date}")
            
            connection.commit()
            
        return True
    except Exception as e:
        print(f"Error saving test run trend: {e}")
        connection.rollback()
        return False

def generate_notable_findings(overall_summary, squad_summary, feature_summary, epic_summary):
    """Generate notable findings and analysis"""
    findings = []
    
    # Calculate totals
    total_tests = sum(item['count'] for item in overall_summary)
    passed = next((item['count'] for item in overall_summary if item['test_case_status'] == 'passed'), 0)
    failed = next((item['count'] for item in overall_summary if item['test_case_status'] == 'failed'), 0)
    blocked = next((item['count'] for item in overall_summary if item['test_case_status'] == 'blocked'), 0)
    app_bug = next((item['count'] for item in overall_summary if item['test_case_status'] == 'application_bug'), 0)
    not_implemented = next((item['count'] for item in overall_summary if item['test_case_status'] == 'not_implemented'), 0)
    
    overall_pass_rate = round((passed / total_tests * 100), 1) if total_tests > 0 else 0
    
    # Overall health finding
    if overall_pass_rate >= 95:
        findings.append({
            'type': 'success',
            'title': 'Excellent Overall Test Health',
            'description': f'The test suite demonstrates exceptional stability with {overall_pass_rate}% pass rate across {total_tests} test cases.'
        })
    elif overall_pass_rate >= 80:
        findings.append({
            'type': 'warning',
            'title': 'Good Overall Test Health with Room for Improvement',
            'description': f'The test suite shows {overall_pass_rate}% pass rate. Focus on addressing {app_bug + not_implemented} issues to achieve excellent status.'
        })
    else:
        findings.append({
            'type': 'danger',
            'title': 'Test Suite Needs Attention',
            'description': f'The test suite has only {overall_pass_rate}% pass rate. Immediate action required to improve stability.'
        })
    
    # Squad performance findings
    top_squads = sorted(squad_summary, key=lambda x: float(x['success_rate']), reverse=True)[:3]
    bottom_squads = [s for s in squad_summary if float(s['success_rate']) < 95 and s['total_tests'] > 5]
    
    if top_squads:
        top_squad_names = ', '.join([s['squad'] for s in top_squads[:3]])
        findings.append({
            'type': 'success',
            'title': 'Top Performing Squads',
            'description': f'{top_squad_names} are leading with 100% pass rates, demonstrating excellent test maintenance and quality practices.'
        })
    
    if bottom_squads:
        for squad in bottom_squads:
            issues = []
            if int(squad['app_bug']) > 0:
                issues.append(f"{squad['app_bug']} application bugs")
            if int(squad['not_implemented']) > 0:
                issues.append(f"{squad['not_implemented']} not implemented")
            if int(squad['failed']) > 0:
                issues.append(f"{squad['failed']} failures")
            
            if issues:
                findings.append({
                    'type': 'warning',
                    'title': f'{squad["squad"]} Needs Attention',
                    'description': f'Success rate of {squad["success_rate"]}% with {" and ".join(issues)}. Consider prioritizing bug fixes and test implementation.'
                })
    
    # Feature-specific findings
    critical_features = [f for f in feature_summary if float(f['success_rate']) < 80 and f['total_tests'] > 10]
    perfect_features = [f for f in feature_summary if float(f['success_rate']) == 100 and f['total_tests'] > 50]
    
    if critical_features:
        for feature in critical_features:
            findings.append({
                'type': 'danger',
                'title': f'Critical: {feature["feature"]}',
                'description': f'Only {feature["success_rate"]}% pass rate with {feature["total_tests"]} tests. This feature requires immediate attention.'
            })
    
    if perfect_features:
        feature_names = ', '.join([f['feature'] for f in perfect_features[:3]])
        findings.append({
            'type': 'success',
            'title': 'Highly Stable Features',
            'description': f'{feature_names} show 100% pass rates with significant test coverage, indicating mature and stable implementations.'
        })
    
    # EPIC findings
    problematic_epics = [e for e in epic_summary if float(e['success_rate']) < 90 and e['epic_id'] != 'No EPIC']
    unassigned_count = next((e['total_tests'] for e in epic_summary if e['epic_id'] == 'No EPIC'), 0)
    
    if problematic_epics:
        for epic in problematic_epics[:3]:  # Top 3 problematic EPICs
            findings.append({
                'type': 'danger',
                'title': f'EPIC {epic["epic_id"]} Issues',
                'description': f'{epic["epic_title"][:50]}... has {epic["success_rate"]}% pass rate. Review and address {int(epic["app_bug"]) + int(epic["not_implemented"])} issues.'
            })
    
    if unassigned_count > 100:
        findings.append({
            'type': 'info',
            'title': 'Large Number of Unassigned Tests',
            'description': f'{unassigned_count} test cases are not linked to any EPIC. Consider improving test traceability for better project tracking.'
        })
    
    # Test distribution finding
    largest_feature = max(feature_summary, key=lambda x: x['total_tests'])
    if largest_feature['total_tests'] > total_tests * 0.3:
        findings.append({
            'type': 'info',
            'title': 'Test Distribution Imbalance',
            'description': f'{largest_feature["feature"]} contains {round(largest_feature["total_tests"]/total_tests*100, 1)}% of all tests. Consider if this reflects actual feature complexity or indicates need for test redistribution.'
        })
    
    # Application bug concentration
    if app_bug > 0:
        bug_features = [f for f in feature_summary if int(f['app_bug']) > 0]
        if bug_features:
            bug_feature_names = ', '.join([f'{f["feature"]} ({f["app_bug"]} bugs)' for f in bug_features[:3]])
            findings.append({
                'type': 'warning',
                'title': 'Application Bugs Concentration',
                'description': f'Total {app_bug} application bugs found primarily in: {bug_feature_names}. These should be prioritized for fixes.'
            })
    
    # Not implemented tests
    if not_implemented > 0:
        ni_features = [f for f in feature_summary if int(f['not_implemented']) > 0]
        if ni_features:
            findings.append({
                'type': 'info',
                'title': 'Pending Test Implementation',
                'description': f'{not_implemented} tests are marked as not implemented, primarily in {", ".join([f["feature"] for f in ni_features])}.'
            })
    
    # Test automation analysis
    total_squads = len(squad_summary)
    perfect_squads = len([s for s in squad_summary if float(s['success_rate']) == 100])
    if perfect_squads > total_squads * 0.7:
        findings.append({
            'type': 'success',
            'title': 'Strong Team Performance',
            'description': f'{perfect_squads} out of {total_squads} squads achieved 100% pass rate, indicating strong quality culture across teams.'
        })
    
    # Feature complexity analysis
    avg_tests_per_feature = total_tests / len(feature_summary) if feature_summary else 0
    complex_features = [f for f in feature_summary if f['total_tests'] > avg_tests_per_feature * 2]
    if complex_features:
        findings.append({
            'type': 'info',
            'title': 'High Complexity Features',
            'description': f'{len(complex_features)} features have significantly higher test counts than average ({round(avg_tests_per_feature, 1)}), indicating higher complexity: {", ".join([f["feature"] for f in complex_features[:3]])}.'
        })
    
    # Test execution trend
    if failed == 0 and blocked == 0:
        if app_bug > 0 or not_implemented > 0:
            findings.append({
                'type': 'warning',
                'title': 'No Test Failures but Issues Present',
                'description': f'While no tests are failing or blocked, there are {app_bug + not_implemented} issues (bugs/not implemented). This suggests good test stability but pending work items.'
            })
        else:
            findings.append({
                'type': 'success',
                'title': 'Perfect Test Execution',
                'description': 'All tests are passing with no failures, blocks, bugs, or pending implementations. This is exceptional!'
            })
    
    return findings

def generate_html_report(test_plan_id, overall_summary, squad_summary, feature_summary, 
                        feature_breakdown, epic_summary):
    """Generate the HTML report with navigation menu"""
    
    # Calculate totals
    total_tests = sum(item['count'] for item in overall_summary)
    passed = next((item['count'] for item in overall_summary if item['test_case_status'] == 'passed'), 0)
    failed = next((item['count'] for item in overall_summary if item['test_case_status'] == 'failed'), 0)
    blocked = next((item['count'] for item in overall_summary if item['test_case_status'] == 'blocked'), 0)
    app_bug = next((item['count'] for item in overall_summary if item['test_case_status'] == 'application_bug'), 0)
    not_implemented = next((item['count'] for item in overall_summary if item['test_case_status'] == 'not_implemented'), 0)
    
    # Generate notable findings
    notable_findings = generate_notable_findings(overall_summary, squad_summary, feature_summary, epic_summary)
    
    # Generate findings HTML
    findings_html = ""
    for finding in notable_findings:
        icon = "✓" if finding['type'] == 'success' else "⚠" if finding['type'] == 'warning' else "✗" if finding['type'] == 'danger' else "ℹ"
        findings_html += f"""
            <div class="finding finding-{finding['type']}">
                <div class="finding-icon">{icon}</div>
                <div class="finding-content">
                    <h3 class="finding-title">{finding['title']}</h3>
                    <p class="finding-description">{finding['description']}</p>
                </div>
            </div>
        """
    
    # Current date
    current_date = datetime.now().strftime("%B %d, %Y")
    
    # Generate KPI cards
    kpi_cards = f"""
        <div class="kpi-container">
            <div class="kpi-card passed">
                <p class="kpi-title">Passed</p>
                <p class="kpi-value">{passed}</p>
                <p class="kpi-percentage">{round(passed/total_tests*100, 1) if total_tests > 0 else 0}% of total</p>
                <div class="kpi-indicator"></div>
            </div>
            
            <div class="kpi-card failed">
                <p class="kpi-title">Failed</p>
                <p class="kpi-value">{failed}</p>
                <p class="kpi-percentage">{round(failed/total_tests*100, 1) if total_tests > 0 else 0}% of total</p>
                <div class="kpi-indicator"></div>
            </div>
            
            <div class="kpi-card blocked">
                <p class="kpi-title">Blocked</p>
                <p class="kpi-value">{blocked}</p>
                <p class="kpi-percentage">{round(blocked/total_tests*100, 1) if total_tests > 0 else 0}% of total</p>
                <div class="kpi-indicator"></div>
            </div>
            
            <div class="kpi-card bug">
                <p class="kpi-title">Application Bug</p>
                <p class="kpi-value">{app_bug}</p>
                <p class="kpi-percentage">{round(app_bug/total_tests*100, 1) if total_tests > 0 else 0}% of total</p>
                <div class="kpi-indicator"></div>
            </div>
            
            <div class="kpi-card not-implemented">
                <p class="kpi-title">Not Implemented</p>
                <p class="kpi-value">{not_implemented}</p>
                <p class="kpi-percentage">{round(not_implemented/total_tests*100, 1) if total_tests > 0 else 0}% of total</p>
                <div class="kpi-indicator"></div>
            </div>
        </div>
    """
    
    # Generate squad performance table
    squad_rows = ""
    for squad in squad_summary:
        squad_icon_class = get_squad_icon_class(squad['squad'])
        squad_initial = get_squad_initial(squad['squad'])
        health_class = get_health_class(float(squad['success_rate']))
        
        squad_rows += f"""
            <tr>
                <td class="squad-column">
                    <span class="squad-icon {squad_icon_class}">{squad_initial}</span>
                    {squad['squad']}
                </td>
                <td>{squad['total_tests']}</td>
                <td>{squad['passed']}</td>
                <td>{squad['failed']}</td>
                <td>{squad['blocked']}</td>
                <td>{squad['app_bug']}</td>
                <td>{squad['not_implemented']}</td>
                <td>{squad['success_rate']}%</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-value {health_class}" style="width: {squad['success_rate']}%"></div>
                    </div>
                </td>
            </tr>
        """
    
    # Generate feature health table
    feature_rows = ""
    for feature in feature_summary:
        health_class = get_health_class(float(feature['success_rate']))
        
        feature_rows += f"""
            <tr>
                <td>{feature['feature']}</td>
                <td>{feature['total_tests']}</td>
                <td>{feature['passed']}</td>
                <td>{feature['failed']}</td>
                <td>{feature['blocked']}</td>
                <td>{feature['app_bug']}</td>
                <td>{feature['not_implemented']}</td>
                <td>{feature['success_rate']}%</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-value {health_class}" style="width: {feature['success_rate']}%"></div>
                    </div>
                </td>
            </tr>
        """
    
    # Generate feature breakdown table
    breakdown_rows = ""
    current_feature = None
    feature_totals = defaultdict(int)
    
    # Calculate totals per feature
    for item in feature_breakdown:
        feature_totals[item['feature']] += item['count']
    
    for item in feature_breakdown:
        if current_feature != item['feature']:
            current_feature = item['feature']
            breakdown_rows += f"""
                <tr class="feature-header">
                    <td colspan="4">{item['feature']} ({feature_totals[item['feature']]} total)</td>
                </tr>
            """
        
        squad_icon_class = get_squad_icon_class(item['squad'])
        squad_initial = get_squad_initial(item['squad'])
        status_class = f"status-{item['test_case_status'].replace('_', '-')}"
        status_display = get_status_display(item['test_case_status'])
        
        breakdown_rows += f"""
            <tr>
                <td>{item['feature']}</td>
                <td class="squad-column">
                    <span class="squad-icon {squad_icon_class}">{squad_initial}</span>
                    {item['squad']}
                </td>
                <td><span class="status {status_class}">{status_display}</span></td>
                <td>{item['count']}</td>
            </tr>
        """
    
    # Generate EPIC-wise stability table
    epic_rows = ""
    for epic in epic_summary:
        health_class = get_health_class(float(epic['success_rate']))
        
        # Special formatting for certain rows
        row_style = ""
        epic_id_style = ""
        if epic['epic_id'] == 'No EPIC':
            row_style = 'style="background-color: #f0f0f0;"'
            epic_id_style = 'style="background-color: #ddd;"'
        elif float(epic['success_rate']) == 0:
            row_style = 'style="background-color: #ffe6e6;"'
        
        epic_title_display = epic['epic_title']
        if epic['epic_id'] == 'No EPIC':
            epic_title_display = f"<em>{epic['epic_title']}</em>"
        
        epic_rows += f"""
            <tr {row_style}>
                <td><span class="epic-id" {epic_id_style}>{epic['epic_id']}</span></td>
                <td>{epic_title_display}</td>
                <td>{epic['total_tests']}</td>
                <td>{epic['passed']}</td>
                <td>{epic['failed']}</td>
                <td>{epic['blocked']}</td>
                <td>{epic['app_bug']}</td>
                <td>{epic['not_implemented']}</td>
                <td>{epic['success_rate']}%</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-value {health_class}" style="width: {epic['success_rate']}%"></div>
                    </div>
                </td>
            </tr>
        """
    
    # HTML template
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>1P Test Cases Stability Dashboard</title>
    <style>
        {get_css_styles()}
    </style>
</head>
<body>
    <!-- Navigation Menu -->
    <nav class="nav-menu">
        <div class="nav-container">
            <div class="nav-brand">1P Test Dashboard</div>
            <ul class="nav-links">
                <li><a href="#overview">Overview</a></li>
                <li><a href="#findings">Key Findings</a></li>
                <li><a href="#squad-performance">Squad Performance</a></li>
                <li><a href="#feature-health">Feature Health</a></li>
                <li><a href="#feature-breakdown">Feature Breakdown</a></li>
                <li><a href="#epic-stability">EPIC Stability</a></li>
            </ul>
        </div>
    </nav>
    
    <!-- Back to top button -->
    <button class="back-to-top" id="backToTop" title="Go to top">↑</button>
    
    <div class="container" style="padding-top: 80px;">
        <header id="overview">
            <h1>1P Test Cases Stability Dashboard</h1>
            <p>Detailed quality metrics for 1P features from the latest test execution</p>
            
            <div class="header-details">
                <div class="test-plan-info">Test Plan ID: {test_plan_id}</div>
                <div class="test-plan-info">Total Test Cases: {total_tests}</div>
            </div>
            
            <p class="timestamp">Last updated: {current_date}</p>
        </header>
        
        {kpi_cards}
        
        <div class="section" id="findings">
            <h2 class="section-title">Notable Findings and Analysis</h2>
            <p style="margin-bottom: 20px;">Key insights and recommendations based on test execution results:</p>
            <div class="findings-container">
                {findings_html}
            </div>
        </div>
        
        <div class="section" id="squad-performance">
            <h2 class="section-title">Squad Performance Summary</h2>
            <table>
                <thead>
                    <tr>
                        <th>Squad</th>
                        <th>Total Tests</th>
                        <th>Passed</th>
                        <th>Failed</th>
                        <th>Blocked</th>
                        <th>App Bug</th>
                        <th>Not Implemented</th>
                        <th>Success Rate</th>
                        <th>Health</th>
                    </tr>
                </thead>
                <tbody>
                    {squad_rows}
                </tbody>
            </table>
        </div>
        
        <div class="section" id="feature-health">
            <h2 class="section-title">Feature Health Overview</h2>
            <table>
                <thead>
                    <tr>
                        <th>Feature</th>
                        <th>Total Tests</th>
                        <th>Passed</th>
                        <th>Failed</th>
                        <th>Blocked</th>
                        <th>App Bug</th>
                        <th>Not Implemented</th>
                        <th>Success Rate</th>
                        <th>Health</th>
                    </tr>
                </thead>
                <tbody>
                    {feature_rows}
                </tbody>
            </table>
        </div>
        
        <div class="section" id="feature-breakdown">
            <h2 class="section-title">Detailed Breakdown by Feature</h2>
            <table>
                <thead>
                    <tr>
                        <th>1P Feature</th>
                        <th>Squad</th>
                        <th>Status</th>
                        <th>Count</th>
                    </tr>
                </thead>
                <tbody>
                    {breakdown_rows}
                </tbody>
            </table>
        </div>
        
        <div class="section" id="epic-stability">
            <h2 class="section-title">EPIC-wise Stability Report</h2>
            <p style="margin-bottom: 20px;">Test execution results grouped by EPIC showing quality metrics for each major initiative:</p>
            <table>
                <thead>
                    <tr>
                        <th>EPIC ID</th>
                        <th>EPIC Title</th>
                        <th>Total Tests</th>
                        <th>Passed</th>
                        <th>Failed</th>
                        <th>Blocked</th>
                        <th>App Bug</th>
                        <th>Not Implemented</th>
                        <th>Success Rate</th>
                        <th>Health</th>
                    </tr>
                </thead>
                <tbody>
                    {epic_rows}
                </tbody>
            </table>
        </div>
        
        <footer>
            <p>Generated on {current_date} | Test Plan ID: {test_plan_id} | 1P Features Test Execution Report</p>
            <p>© 2025 Quality Metrics Dashboard. All rights reserved.</p>
        </footer>
    </div>
    
    <script>
        // Smooth scrolling for navigation links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
            anchor.addEventListener('click', function (e) {{
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {{
                    target.scrollIntoView({{
                        behavior: 'smooth',
                        block: 'start'
                    }});
                }}
            }});
        }});
        
        // Back to top button functionality
        const backToTopBtn = document.getElementById('backToTop');
        
        window.addEventListener('scroll', () => {{
            if (window.pageYOffset > 300) {{
                backToTopBtn.style.display = 'block';
            }} else {{
                backToTopBtn.style.display = 'none';
            }}
        }});
        
        backToTopBtn.addEventListener('click', () => {{
            window.scrollTo({{
                top: 0,
                behavior: 'smooth'
            }});
        }});
        
        // Highlight active section in navigation
        const sections = document.querySelectorAll('.section, header');
        const navLinks = document.querySelectorAll('.nav-links a');
        
        window.addEventListener('scroll', () => {{
            let current = '';
            sections.forEach(section => {{
                const sectionTop = section.offsetTop;
                const sectionHeight = section.clientHeight;
                if (pageYOffset >= sectionTop - 100) {{
                    current = section.getAttribute('id');
                }}
            }});
            
            navLinks.forEach(link => {{
                link.classList.remove('active');
                if (link.getAttribute('href') === '#' + current) {{
                    link.classList.add('active');
                }}
            }});
        }});
    </script>
</body>
</html>"""
    
    return html

def get_css_styles():
    """Return CSS styles for the HTML report with navigation"""
    return """
        :root {
            --primary-color: #3498db;
            --success-color: #2ecc71;
            --warning-color: #f39c12;
            --danger-color: #e74c3c;
            --info-color: #1abc9c;
            --dark-color: #34495e;
            --light-color: #ecf0f1;
            --border-radius: 8px;
            --box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            --transition: all 0.3s ease;
        }
        
        /* Smooth scrolling */
        html {
            scroll-behavior: smooth;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f7fa;
            padding: 0;
            margin: 0;
        }
        
        /* Navigation Menu Styles */
        .nav-menu {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background-color: var(--dark-color);
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
            z-index: 1000;
        }
        
        .nav-container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 60px;
        }
        
        .nav-brand {
            color: white;
            font-size: 20px;
            font-weight: bold;
            text-decoration: none;
        }
        
        .nav-links {
            display: flex;
            list-style: none;
            margin: 0;
            padding: 0;
            gap: 30px;
        }
        
        .nav-links a {
            color: #bdc3c7;
            text-decoration: none;
            padding: 5px 10px;
            border-radius: 5px;
            transition: var(--transition);
            font-size: 15px;
        }
        
        .nav-links a:hover {
            color: white;
            background-color: rgba(255, 255, 255, 0.1);
        }
        
        .nav-links a.active {
            color: white;
            background-color: var(--primary-color);
        }
        
        /* Back to top button */
        .back-to-top {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 50px;
            height: 50px;
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: 50%;
            font-size: 24px;
            cursor: pointer;
            display: none;
            z-index: 999;
            transition: var(--transition);
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
        }
        
        .back-to-top:hover {
            background-color: var(--dark-color);
            transform: translateY(-3px);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background-color: #fff;
            box-shadow: var(--box-shadow);
            padding: 20px;
            border-radius: var(--border-radius);
            margin-bottom: 30px;
            text-align: center;
            position: relative;
            scroll-margin-top: 80px;
        }
        
        h1 {
            color: var(--dark-color);
            margin-bottom: 10px;
            font-size: 28px;
        }
        
        .header-details {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-top: 15px;
            gap: 20px;
            flex-wrap: wrap;
        }
        
        .test-plan-info {
            background-color: var(--dark-color);
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            font-weight: bold;
            display: inline-block;
        }
        
        .timestamp {
            color: #777;
            font-style: italic;
            margin-top: 10px;
            font-size: 14px;
        }
        
        .kpi-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .kpi-card {
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--box-shadow);
            padding: 20px;
            text-align: center;
            transition: var(--transition);
        }
        
        .kpi-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
        }
        
        .kpi-title {
            font-size: 16px;
            color: #777;
            margin-bottom: 10px;
        }
        
        .kpi-value {
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .kpi-percentage {
            font-size: 14px;
            color: #777;
            margin-bottom: 10px;
        }
        
        .kpi-indicator {
            height: 5px;
            width: 100%;
            border-radius: 5px;
            margin-top: 10px;
        }
        
        .passed .kpi-value { color: var(--success-color); }
        .failed .kpi-value { color: var(--danger-color); }
        .blocked .kpi-value { color: var(--warning-color); }
        .bug .kpi-value { color: var(--info-color); }
        .not-implemented .kpi-value { color: #95a5a6; }
        
        .passed .kpi-indicator { background-color: var(--success-color); }
        .failed .kpi-indicator { background-color: var(--danger-color); }
        .blocked .kpi-indicator { background-color: var(--warning-color); }
        .bug .kpi-indicator { background-color: var(--info-color); }
        .not-implemented .kpi-indicator { background-color: #95a5a6; }
        
        .section {
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--box-shadow);
            padding: 25px;
            margin-bottom: 30px;
            scroll-margin-top: 80px;
        }
        
        .section-title {
            font-size: 20px;
            color: var(--dark-color);
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        
        th {
            background-color: var(--dark-color);
            color: white;
            text-align: left;
            padding: 12px 15px;
            font-weight: 600;
        }
        
        th:first-child {
            border-top-left-radius: 8px;
        }
        
        th:last-child {
            border-top-right-radius: 8px;
        }
        
        td {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }
        
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        tr:hover {
            background-color: #f5f5f5;
        }
        
        .feature-header {
            background-color: #f1f8ff;
            font-weight: bold;
            font-size: 15px;
            color: var(--primary-color);
            border-left: 4px solid var(--primary-color);
        }
        
        .status {
            display: inline-flex;
            align-items: center;
            padding: 5px 10px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 14px;
        }
        
        .status::before {
            content: '';
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        
        .status-passed {
            background-color: rgba(46, 204, 113, 0.1);
            color: var(--success-color);
        }
        
        .status-passed::before {
            background-color: var(--success-color);
        }
        
        .status-failed {
            background-color: rgba(231, 76, 60, 0.1);
            color: var(--danger-color);
        }
        
        .status-failed::before {
            background-color: var(--danger-color);
        }
        
        .status-blocked {
            background-color: rgba(243, 156, 18, 0.1);
            color: var(--warning-color);
        }
        
        .status-blocked::before {
            background-color: var(--warning-color);
        }
        
        .status-application-bug {
            background-color: rgba(26, 188, 156, 0.1);
            color: var(--info-color);
        }
        
        .status-application-bug::before {
            background-color: var(--info-color);
        }
        
        .status-not-implemented {
            background-color: rgba(149, 165, 166, 0.1);
            color: #95a5a6;
        }
        
        .status-not-implemented::before {
            background-color: #95a5a6;
        }
        
        .progress-bar {
            height: 6px;
            background-color: #eee;
            border-radius: 3px;
            margin-top: 5px;
            overflow: hidden;
        }
        
        .progress-value {
            height: 100%;
            border-radius: 3px;
        }
        
        .health-excellent { background-color: #27ae60; }
        .health-good { background-color: #2ecc71; }
        .health-fair { background-color: #f39c12; }
        .health-poor { background-color: #e67e22; }
        .health-critical { background-color: #e74c3c; }
        
        .squad-column {
            display: flex;
            align-items: center;
        }
        
        .squad-icon {
            width: 20px;
            height: 20px;
            background-color: #ddd;
            border-radius: 50%;
            margin-right: 10px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 12px;
            color: white;
        }
        
        .squad-a { background-color: #3498db; }
        .squad-r { background-color: #9b59b6; }
        .squad-m { background-color: #f1c40f; }
        .squad-p { background-color: #e74c3c; }
        .squad-g { background-color: #2ecc71; }
        .squad-s { background-color: #e67e22; }
        .squad-c { background-color: #1abc9c; }
        .squad-d { background-color: #34495e; }
        .squad-h { background-color: #16a085; }
        .squad-sh { background-color: #7f8c8d; }
        .squad-au { background-color: #8e44ad; }
        .squad-ch { background-color: #d35400; }
        
        footer {
            text-align: center;
            padding: 20px;
            font-size: 14px;
            color: #777;
            border-top: 1px solid #eee;
            margin-top: 30px;
        }
        
        .epic-info {
            font-size: 12px;
            color: #666;
            margin-left: 20px;
        }
        
        .epic-id {
            background-color: #f0f0f0;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
        }
        
        /* Notable Findings Styles */
        .findings-container {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .finding {
            display: flex;
            align-items: flex-start;
            gap: 15px;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid;
        }
        
        .finding-success {
            background-color: rgba(46, 204, 113, 0.05);
            border-left-color: var(--success-color);
        }
        
        .finding-warning {
            background-color: rgba(243, 156, 18, 0.05);
            border-left-color: var(--warning-color);
        }
        
        .finding-danger {
            background-color: rgba(231, 76, 60, 0.05);
            border-left-color: var(--danger-color);
        }
        
        .finding-info {
            background-color: rgba(52, 152, 219, 0.05);
            border-left-color: var(--primary-color);
        }
        
        .finding-icon {
            font-size: 24px;
            width: 30px;
            text-align: center;
            flex-shrink: 0;
        }
        
        .finding-success .finding-icon { color: var(--success-color); }
        .finding-warning .finding-icon { color: var(--warning-color); }
        .finding-danger .finding-icon { color: var(--danger-color); }
        .finding-info .finding-icon { color: var(--primary-color); }
        
        .finding-content {
            flex: 1;
        }
        
        .finding-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 5px;
            color: var(--dark-color);
        }
        
        .finding-description {
            font-size: 14px;
            color: #555;
            line-height: 1.5;
            margin: 0;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .nav-container {
                flex-direction: column;
                height: auto;
                padding: 10px 20px;
            }
            
            .nav-brand {
                margin-bottom: 10px;
            }
            
            .nav-links {
                flex-wrap: wrap;
                gap: 10px;
                justify-content: center;
            }
            
            .nav-links a {
                font-size: 13px;
                padding: 3px 8px;
            }
            
            .kpi-container {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .section {
                padding: 15px;
            }
            
            th, td {
                padding: 8px;
            }
            
            table {
                font-size: 14px;
            }
            
            .back-to-top {
                width: 40px;
                height: 40px;
                font-size: 20px;
                bottom: 20px;
                right: 20px;
            }
        }
        
        @media (max-width: 500px) {
            .kpi-container {
                grid-template-columns: 1fr;
            }
            
            .header-details {
                flex-direction: column;
                gap: 10px;
            }
        }
    """

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python 1p_report_generator.py <test_plan_id>")
        sys.exit(1)
    
    test_plan_id = sys.argv[1]
    
    try:
        test_plan_id = int(test_plan_id)
    except ValueError:
        print("Error: Test plan ID must be a number")
        sys.exit(1)
    
    print(f"Generating report for test plan ID: {test_plan_id}")
    
    # Connect to database
    connection = get_db_connection()
    
    try:
        # Fetch all required data
        print("Fetching overall summary...")
        overall_summary = get_overall_summary(connection, test_plan_id)
        
        if not overall_summary:
            print(f"No test data found for test plan ID: {test_plan_id}")
            sys.exit(1)
        
        print("Fetching squad summary...")
        squad_summary = get_squad_summary(connection, test_plan_id)
        
        print("Fetching feature summary...")
        feature_summary = get_feature_summary(connection, test_plan_id)
        
        print("Fetching feature breakdown...")
        feature_breakdown = get_feature_breakdown(connection, test_plan_id)
        
        print("Fetching EPIC summary...")
        epic_summary = get_epic_summary(connection, test_plan_id)
        
        # Save test run trend
        print("Saving test run trend...")
        save_test_run_trend(connection, test_plan_id, overall_summary)
        
        # Generate HTML report
        print("Generating HTML report...")
        html_content = generate_html_report(
            test_plan_id, 
            overall_summary, 
            squad_summary, 
            feature_summary, 
            feature_breakdown,
            epic_summary
        )
        
        # Write to file
        filename = f"{datetime.now().strftime('%Y%m%d')}_1p_report.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Print summary
        total_tests = sum(item['count'] for item in overall_summary)
        passed = next((item['count'] for item in overall_summary if item['test_case_status'] == 'passed'), 0)
        pass_rate = round((passed / total_tests * 100), 1) if total_tests > 0 else 0
        
        print(f"\n{'='*50}")
        print(f"Report generated successfully: {filename}")
        print(f"{'='*50}")
        print(f"Test Plan ID: {test_plan_id}")
        print(f"Total Test Cases: {total_tests}")
        print(f"Pass Rate: {pass_rate}%")
        print(f"{'='*50}\n")
        
    except Exception as e:
        print(f"Error generating report: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        connection.close()

if __name__ == "__main__":
    main()