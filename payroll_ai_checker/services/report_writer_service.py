"""Service for writing test reports to files in CSV format as specified in HLD."""

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..models import TestReport

logger = logging.getLogger(__name__)


class ReportWriterService:
    """Service for writing test reports to CSV files as specified in HLD."""
    
    def __init__(self, output_dir: str = "reports"):
        """Initialize the report writer service.
        
        Args:
            output_dir: Directory to write report files to
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def write_report(self, report: TestReport, include_summary: bool = True) -> dict:
        """Write test report to CSV file as specified in HLD.
        
        Args:
            report: TestReport to write
            include_summary: If True, include overall summary as first row
            
        Returns:
            Dictionary with 'csv' key mapping to written file path
        """
        written_files = {}
        
        try:
            file_path = self._write_csv_report(report, include_summary)
            written_files['csv'] = str(file_path)
            logger.info(f"Wrote CSV report to: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to write CSV report: {e}")
                
        return written_files
    
    def _write_csv_report(self, report: TestReport, include_summary: bool = True) -> Path:
        """Write CSV report as specified in HLD.
        
        Format: test_name, test_type, status, similarity, error, expected_answer, actual_answer, tools_used
        Filename: {agent_slug}_results_{YYYY-MM-DDTHH-MM-SSZ}.csv
        """
        # Generate timestamp in ISO format with UTC timezone
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        
        # Create agent slug (replace underscores/spaces with hyphens for URL-safe format)
        agent_slug = report.agent_name.replace('_', '-').replace(' ', '-').lower()
        
        # Create filename according to HLD specification
        filename = f"{agent_slug}_results_{timestamp}.csv"
        file_path = self.output_dir / filename
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header (append tools_used for visibility of agent tool calls)
            writer.writerow([
                'test_name',
                'test_type',
                'status',
                'similarity',
                'error',
                'expected_answer',
                'actual_answer',
                'tools_used'
            ])
            
            # Add summary row if requested (as special test_name)
            if include_summary:
                writer.writerow([
                    f"OVERALL_SUMMARY_{report.agent_name}",
                    "summary", 
                    report.overall_status.lower(),
                    f"{report.pass_percentage:.1f}%",
                    f"passed: {report.passed}/{report.total_tests}",
                    "",  # empty expected_answer for summary
                    "",  # empty actual_answer for summary
                    ""   # empty tools_used for summary
                ])
            
            # Write individual test results
            for result in report.results:
                # Map comparison_method to test_type, with proper fallbacks
                test_type = result.comparison_method or "unknown"
                
                # For dry runs, try to infer test type from test configuration if available
                # This ensures we show the correct test_type even in dry runs
                if test_type == "unknown" and hasattr(report, '_test_cases_map'):
                    test_case = report._test_cases_map.get(result.test_name)
                    if test_case and hasattr(test_case, 'comparison_method'):
                        test_type = test_case.comparison_method
                
                # Format similarity score
                similarity = ""
                if result.semantic_score is not None:
                    similarity = f"{result.semantic_score:.3f}"
                
                # Format error message (clean for CSV)
                error_message = result.error_message or ""
                # Remove newlines for CSV format compatibility
                error_message = error_message.replace('\n', ' ').replace('\r', ' ')
                
                # Format expected and actual answers (clean for CSV)
                expected_answer = result.expected_response or ""
                actual_answer = result.actual_response or ""
                
                # Clean answers for CSV format compatibility
                expected_answer = expected_answer.replace('\n', ' ').replace('\r', ' ').strip()
                actual_answer = actual_answer.replace('\n', ' ').replace('\r', ' ').strip()
                
                # Derive tools_used string from tool_calls_made (if present)
                tools_used = ""
                try:
                    tool_calls = getattr(result, 'tool_calls_made', None)
                    if tool_calls:
                        extracted_names = []
                        for call in tool_calls:
                            name: str = ""
                            if isinstance(call, dict):
                                # Try common keys first
                                for key in ["name", "tool", "tool_name", "type", "endpoint"]:
                                    if key in call and isinstance(call[key], str) and call[key]:
                                        name = call[key]
                                        break
                                # Try nested function structure (OpenAI-style)
                                if not name and isinstance(call.get("function"), dict):
                                    func_name = call["function"].get("name")
                                    if isinstance(func_name, str) and func_name:
                                        name = func_name
                                # Fallbacks
                                if not name:
                                    name = call.get("path") or call.get("id") or ""
                            if name:
                                extracted_names.append(name)
                        if extracted_names:
                            # Preserve order, remove duplicates
                            seen = set()
                            ordered_unique = []
                            for n in extracted_names:
                                if n not in seen:
                                    ordered_unique.append(n)
                                    seen.add(n)
                            tools_used = ";".join(ordered_unique)
                        else:
                            tools_used = json.dumps(tool_calls)[:200]
                except Exception:
                    # Be resilient: never break report writing due to tools parsing
                    tools_used = ""
                
                writer.writerow([
                    result.test_name,
                    test_type,
                    result.status,
                    similarity,
                    error_message,
                    expected_answer,
                    actual_answer,
                    tools_used
                ])
        
        return file_path
    
    def get_latest_report_path(self, agent_name: str) -> Optional[Path]:
        """Get path to the most recent CSV report file for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Path to latest CSV report file or None if not found
        """
        # Create agent slug (same logic as in _write_csv_report)
        agent_slug = agent_name.replace('_', '-').replace(' ', '-').lower()
        pattern = f"{agent_slug}_results_*.csv"
        
        files = list(self.output_dir.glob(pattern))
        if not files:
            return None
        
        # Sort by modification time, most recent first
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return files[0]