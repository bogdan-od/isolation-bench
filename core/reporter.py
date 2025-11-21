import os
import pandas as pd
from typing import Dict, List
from core.logger import log

class ReportGenerator:
    """
    Generates comprehensive reports from test results.
    Supports multiple output formats: Markdown, HTML, JSON.
    """
    
    def __init__(self, results_dir: str):
        self.results_dir = results_dir
        self.csv_path = os.path.join(results_dir, 'summary.csv')
    
    def generate_all(self):
        """Generate all report formats"""
        try:
            df = pd.read_csv(self.csv_path)
            
            # Generate different report types
            self.generate_summary_md(df)
            self.generate_detailed_md(df)
            self.generate_performance_md(df)
            self.generate_security_md(df)
            
            log("All reports generated successfully", "SUCCESS")
        except Exception as e:
            log(f"Report generation failed: {e}", "ERROR")
    
    def generate_summary_md(self, df: pd.DataFrame):
        """Generate high-level summary report"""
        output_path = os.path.join(self.results_dir, 'summary.md')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Test Execution Summary\n\n")
            
            # Overall statistics
            f.write("## Overall Statistics\n\n")
            f.write(f"- **Total Tests:** {len(df)}\n")
            f.write(f"- **Successful:** {len(df[df['status'] == 'SUCCESS'])}\n")
            f.write(f"- **Failed:** {len(df[df['status'] == 'FAILURE'])}\n")
            f.write(f"- **Timeout:** {len(df[df['status'] == 'TIMEOUT'])}\n")
            f.write(f"- **Partial:** {len(df[df['status'] == 'PARTIAL'])}\n\n")
            
            # Success rate by tool
            f.write("## Success Rate by Tool\n\n")
            success_by_tool = df.groupby('tool')['status'].apply(
                lambda x: f"{(x == 'SUCCESS').sum()}/{len(x)} ({(x == 'SUCCESS').sum()/len(x)*100:.1f}%)"
            )
            f.write(success_by_tool.to_markdown() + "\n\n")
            
            # Quick overview table
            f.write("## Quick Overview\n\n")
            overview_cols = ['experiment_id', 'run_id', 'tool', 'config_type', 'status', 'duration_s']
            f.write(df[overview_cols].to_markdown(index=False) + "\n\n")
        
        log(f"Summary report: {output_path}", "SUCCESS")
    
    def generate_detailed_md(self, df: pd.DataFrame):
        """Generate detailed report with all metrics"""
        output_path = os.path.join(self.results_dir, 'detailed.md')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Detailed Test Results\n\n")
            
            # Group by experiment
            for exp_id in df['experiment_id'].unique():
                exp_df = df[df['experiment_id'] == exp_id]
                
                f.write(f"## {exp_id}\n\n")
                
                # Metrics table
                f.write("### System Metrics\n\n")
                metrics_cols = [
                    'run_id', 'tool', 'status', 'duration_s',
                    'baseline_pids', 'pids_start', 'pids_max', 'pid_growth',
                    'baseline_threads', 'threads_start', 'threads_max', 'thread_growth',
                    'baseline_fds', 'fds_start', 'fds_max', 'fd_growth',
                    'baseline_cpu', 'cpu_avg', 'cpu_max',
                    'mem_start', 'mem_avg', 'mem_max'
                ]
                # Filter to only existing columns
                available_cols = [col for col in metrics_cols if col in exp_df.columns]
                f.write(exp_df[available_cols].to_markdown(index=False) + "\n\n")
                
                # I/O and Network metrics if available
                if 'io_read_mb' in exp_df.columns:
                    f.write("### I/O and Network\n\n")
                    io_cols = ['run_id', 'tool', 'io_read_mb', 'io_write_mb', 
                              'net_sent_mb', 'net_recv_mb']
                    available_io_cols = [col for col in io_cols if col in exp_df.columns]
                    f.write(exp_df[available_io_cols].to_markdown(index=False) + "\n\n")
                
                # Context switches if available
                if 'ctx_switches_vol' in exp_df.columns:
                    f.write("### Context Switches\n\n")
                    ctx_cols = ['run_id', 'tool', 'ctx_switches_vol', 'ctx_switches_invol']
                    available_ctx_cols = [col for col in ctx_cols if col in exp_df.columns]
                    f.write(exp_df[available_ctx_cols].to_markdown(index=False) + "\n\n")
                
                f.write("---\n\n")
        
        log(f"Detailed report: {output_path}", "SUCCESS")
    
    def generate_performance_md(self, df: pd.DataFrame):
        """Generate performance-focused report"""
        output_path = os.path.join(self.results_dir, 'performance.md')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Performance Analysis\n\n")
            
            # Performance baseline tests
            perf_tests = df[df['experiment_id'].str.contains('T0', na=False)]
            
            if not perf_tests.empty:
                f.write("## Performance Baseline\n\n")
                f.write("Duration comparison (lower is better):\n\n")
                
                perf_cols = ['experiment_id', 'tool', 'duration_s', 'cpu_avg', 
                            'mem_avg', 'io_read_mb', 'io_write_mb']
                available_perf_cols = [col for col in perf_cols if col in perf_tests.columns]
                f.write(perf_tests[available_perf_cols].to_markdown(index=False) + "\n\n")
                
                # Calculate overhead relative to Docker baseline
                if 'docker' in perf_tests['tool'].values:
                    f.write("### Overhead Analysis\n\n")
                    
                    for exp_id in perf_tests['experiment_id'].unique():
                        exp_perf = perf_tests[perf_tests['experiment_id'] == exp_id]
                        
                        docker_baseline = exp_perf[exp_perf['tool'] == 'docker']['duration_s'].values
                        if len(docker_baseline) > 0:
                            docker_time = docker_baseline[0]
                            
                            f.write(f"**{exp_id}** (normalized to Docker = 1.0x):\n\n")
                            for _, row in exp_perf.iterrows():
                                overhead = row['duration_s'] / docker_time
                                f.write(f"- {row['tool']}: {overhead:.2f}x ({row['duration_s']:.2f}s)\n")
                            f.write("\n")
            
            # Resource exhaustion tests
            f.write("## Resource Exhaustion Analysis\n\n")
            resource_tests = df[df['experiment_id'].str.contains('T1', na=False)]
            
            if not resource_tests.empty:
                f.write("### PID Growth\n\n")
                if 'pid_growth' in resource_tests.columns:
                    pid_cols = ['experiment_id', 'tool', 'config_type', 'pid_growth', 
                               'pids_max', 'status']
                    f.write(resource_tests[pid_cols].to_markdown(index=False) + "\n\n")
                
                f.write("### Memory Usage\n\n")
                mem_cols = ['experiment_id', 'tool', 'config_type', 'mem_start', 
                           'mem_max', 'mem_growth', 'status']
                available_mem_cols = [col for col in mem_cols if col in resource_tests.columns]
                f.write(resource_tests[available_mem_cols].to_markdown(index=False) + "\n\n")
            
            # Context switches analysis
            if 'ctx_switches_invol' in df.columns:
                f.write("## Context Switch Analysis\n\n")
                f.write("High involuntary context switches indicate CPU throttling or contention.\n\n")
                
                ctx_summary = df.groupby('tool').agg({
                    'ctx_switches_vol': 'mean',
                    'ctx_switches_invol': 'mean'
                }).round(0)
                
                f.write(ctx_summary.to_markdown() + "\n\n")
        
        log(f"Performance report: {output_path}", "SUCCESS")
    
    def generate_security_md(self, df: pd.DataFrame):
        """Generate security-focused report"""
        output_path = os.path.join(self.results_dir, 'security.md')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Security Analysis\n\n")
            
            # Security tests (categories 2-7)
            security_cats = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7']
            security_tests = df[df['experiment_id'].str.contains('|'.join(security_cats), na=False)]
            
            if security_tests.empty:
                f.write("No security tests found.\n")
                return
            
            # Security effectiveness matrix
            f.write("## Security Effectiveness Matrix\n\n")
            f.write("✅ SUCCESS = Attack blocked  \n")
            f.write("❌ FAILURE = Attack succeeded  \n")
            f.write("⚠️ PARTIAL = Partial protection  \n")
            f.write("⏱️ TIMEOUT = Test timed out  \n\n")
            
            # Pivot table: experiments vs tools
            pivot = security_tests.pivot_table(
                index='experiment_id',
                columns='tool',
                values='status',
                aggfunc=lambda x: x.iloc[0] if len(x) > 0 else 'N/A'
            )
            
            # Convert status to symbols
            symbol_map = {
                'SUCCESS': '✅',
                'FAILURE': '❌',
                'PARTIAL': '⚠️',
                'TIMEOUT': '⏱️'
            }
            
            pivot_symbols = pivot.map(lambda x: symbol_map.get(x, x))
            f.write(pivot_symbols.to_markdown() + "\n\n")
            
            # Security score by tool
            f.write("## Security Score by Tool\n\n")
            
            scores = {}
            for tool in security_tests['tool'].unique():
                tool_tests = security_tests[security_tests['tool'] == tool]
                success_count = len(tool_tests[tool_tests['status'] == 'SUCCESS'])
                total = len(tool_tests)
                scores[tool] = f"{success_count}/{total} ({success_count/total*100:.1f}%)"
            
            f.write("| Tool | Score |\n")
            f.write("|------|-------|\n")
            for tool, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
                f.write(f"| {tool} | {score} |\n")
            f.write("\n")
            
            # Breakdown by category
            f.write("## Breakdown by Security Category\n\n")
            
            for cat in security_cats:
                cat_tests = security_tests[security_tests['experiment_id'].str.startswith(cat)]
                if not cat_tests.empty:
                    cat_name = {
                        'T2': 'Filesystem Isolation',
                        'T3': 'Kernel/Proc Isolation',
                        'T4': 'Network Isolation',
                        'T5': 'IPC/Namespace Isolation',
                        'T6': 'Syscall/Seccomp',
                        'T7': 'Advanced Escapes'
                    }.get(cat, cat)
                    
                    f.write(f"### {cat_name}\n\n")
                    
                    cat_cols = ['experiment_id', 'tool', 'config_type', 'status', 'validation_rule']
                    available_cat_cols = [col for col in cat_cols if col in cat_tests.columns]
                    f.write(cat_tests[available_cat_cols].to_markdown(index=False) + "\n\n")
            
            # Weak vs Strong configuration comparison
            f.write("## Configuration Impact\n\n")
            f.write("Comparing weak vs strong configurations:\n\n")
            
            for tool in security_tests['tool'].unique():
                tool_tests = security_tests[security_tests['tool'] == tool]
                
                if 'config_type' in tool_tests.columns:
                    weak = tool_tests[tool_tests['config_type'] == 'weak']
                    strong = tool_tests[tool_tests['config_type'] == 'strong']
                    
                    if not weak.empty and not strong.empty:
                        weak_success = len(weak[weak['status'] == 'SUCCESS'])
                        strong_success = len(strong[strong['status'] == 'SUCCESS'])
                        
                        f.write(f"**{tool}:**\n")
                        f.write(f"- Weak: {weak_success}/{len(weak)} tests passed\n")
                        f.write(f"- Strong: {strong_success}/{len(strong)} tests passed\n")
                        f.write(f"- Improvement: +{strong_success - weak_success} tests\n\n")
        
        log(f"Security report: {output_path}", "SUCCESS")
    
    def generate_comparison_chart_data(self, df: pd.DataFrame) -> Dict:
        """Generate data for charts (can be used by visualization tools)"""
        chart_data = {
            'performance_overhead': {},
            'security_score': {},
            'resource_usage': {}
        }
        
        # Performance overhead by tool
        perf_tests = df[df['experiment_id'].str.contains('T0', na=False)]
        if not perf_tests.empty and 'docker' in perf_tests['tool'].values:
            docker_baseline = perf_tests[perf_tests['tool'] == 'docker']['duration_s'].mean()
            
            for tool in perf_tests['tool'].unique():
                tool_time = perf_tests[perf_tests['tool'] == tool]['duration_s'].mean()
                chart_data['performance_overhead'][tool] = tool_time / docker_baseline
        
        # Security score by tool
        security_tests = df[df['experiment_id'].str.contains('T[2-7]', na=False, regex=True)]
        for tool in security_tests['tool'].unique():
            tool_tests = security_tests[security_tests['tool'] == tool]
            success_rate = len(tool_tests[tool_tests['status'] == 'SUCCESS']) / len(tool_tests)
            chart_data['security_score'][tool] = success_rate
        
        # Average resource usage by tool
        for tool in df['tool'].unique():
            tool_df = df[df['tool'] == tool]
            chart_data['resource_usage'][tool] = {
                'cpu_avg': tool_df['cpu_avg'].mean() if 'cpu_avg' in tool_df.columns else 0,
                'mem_avg': tool_df['mem_avg'].mean() if 'mem_avg' in tool_df.columns else 0,
                'pid_growth_avg': tool_df['pid_growth'].mean() if 'pid_growth' in tool_df.columns else 0
            }
        
        # Save as JSON
        import json
        json_path = os.path.join(self.results_dir, 'chart_data.json')
        with open(json_path, 'w') as f:
            json.dump(chart_data, f, indent=2)
        
        log(f"Chart data: {json_path}", "SUCCESS")
        return chart_data
