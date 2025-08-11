import json
import logging
import sys
from pathlib import Path

import click

from .runner import TestRunner
from .services import TestConfigService
from .models import TestReport


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _display_test_results_console(report: TestReport, test_scope: str) -> None:
    """Display test results in a nice console format."""
    click.echo("\n" + "="*60)
    click.echo(f"🎯 TEST RESULTS - {test_scope}")
    click.echo("="*60)
    
    # Display individual test results
    for result in report.results:
        status_icon = "✅" if result.status == "pass" else "❌" if result.status == "fail" else "⚠️"
        
        # Format test name (truncate if too long)
        test_name = result.test_name[:40] + "..." if len(result.test_name) > 40 else result.test_name
        
        if result.status == "pass":
            click.echo(f"{status_icon} {test_name}")
        elif result.status == "fail":
            score_text = f" (score: {result.semantic_score:.1%})" if result.semantic_score is not None else ""
            click.echo(f"{status_icon} {test_name}{score_text}")
        else:  # error
            error_text = result.error_message or "Unknown error"
            # Highlight HTTP errors more prominently
            if "HTTP" in error_text and ("401" in error_text or "403" in error_text or "500" in error_text):
                click.secho(f"{status_icon} {test_name}", fg="red", bold=True)
                click.secho(f"   🚨 {error_text}", fg="red")
            else:
                click.echo(f"{status_icon} {test_name}")
                click.echo(f"   ⚠️  {error_text}")
    
    # Display summary
    click.echo("\n" + "-"*60)
    click.echo(f"📊 SUMMARY")
    click.echo(f"   Total Tests: {report.total_tests}")
    click.echo(f"   ✅ Passed: {report.passed}")
    click.echo(f"   ❌ Failed: {report.failed}")
    
    if report.errors > 0:
        click.echo(f"   ⚠️  Errors: {report.errors}")
    
    # Success rate with color
    success_rate = report.pass_percentage
    if success_rate >= 80:
        rate_color = "green"
    elif success_rate >= 60:
        rate_color = "yellow"
    else:
        rate_color = "red"
    
    click.echo(f"   🎯 Success Rate: ", nl=False)
    click.secho(f"{success_rate:.1f}%", fg=rate_color, bold=True)
    
    # Overall status
    overall_status = "🎉 ALL TESTS PASSED!" if report.overall_status == "PASSED" else "💥 SOME TESTS FAILED"
    status_color = "green" if report.overall_status == "PASSED" else "red"
    
    click.echo("\n" + "-"*60)
    click.secho(f"🏁 {overall_status}", fg=status_color, bold=True)
    click.echo("="*60 + "\n")


@click.command()
@click.option("--agent", help="Agent name to run tests for (e.g., 'pay-details-us-agent')")
@click.option("--test", help="Run only a specific test file (e.g., 'base_salary_march_2025')")
@click.option("--out", help="Output file path for test results")

@click.option("--list-agents", is_flag=True, help="List all available agents")
@click.option("--format", "output_format", type=click.Choice(["console", "json"]), default="console", help="Output format (console or json)")
@click.option("--dry-run", is_flag=True, help="Validate configurations without sending HTTP requests")

@click.option("--keep-stubs", is_flag=True, help="Keep stub service running after tests complete (for manual testing)")
@click.option("--no-stubs", is_flag=True, help="Skip stub service - test against real services (integration testing)")
@click.option("--stubs-port", type=int, default=9876, show_default=True, help="Port for the stub HTTP service")
@click.option("--stubs-host", type=str, default="0.0.0.0", show_default=True, help="Host for the stub HTTP service")
def main(agent, test, out, list_agents, output_format, dry_run, keep_stubs, no_stubs, stubs_port, stubs_host):
    """AI Answer Checker CLI - regression runner for AI responses."""
    
    # Initialize test config service
    try:
        test_service = TestConfigService("agent_tests")
    except Exception as e:
        click.echo(f"❌ Error initializing test service: {e}", err=True)
        sys.exit(1)
    
    # Handle list agents command
    if list_agents:
        click.echo("🔍 Discovering available agents...")
        agents = test_service.discover_agents()
        if agents:
            click.echo(f"\n📋 Available agents ({len(agents)}):")
            for i, agent_name in enumerate(agents, 1):
                click.echo(f"  {i}. {agent_name}")
        else:
            click.echo("❌ No agents found in tests directory")
        return
    
    # Validate agent parameter
    if not agent:
        click.echo("❌ Error: --agent parameter is required", err=True)
        click.echo("💡 Use --list-agents to see available agents")
        sys.exit(1)
    
    # Load test configuration
    if output_format == "console":
        click.echo(f"🚀 Loading tests for agent: {agent}")
    
    try:
        # Load test suite (single test or all tests)
        if test:
            test_suite = test_service.load_single_test(agent, test)
        else:
            test_suite = test_service.load_agent_test_suite(agent)
        
        # Display test suite info (only in console mode)
        if output_format == "console":
            if test:
                click.echo(f"✅ Successfully loaded single test '{test}' for agent '{agent}'")
            else:
                click.echo(f"✅ Successfully loaded test suite for '{agent}'")
            click.echo(f"📊 Total test cases: {test_suite.total_tests}")
            
            if test_suite.total_tests > 0:
                click.echo(f"\n📝 Test cases:")
                for i, test_case in enumerate(test_suite.test_cases, 1):
                    click.echo(f"  {i}. {test_case.test_name}")
                    click.echo(f"     📝 Input: {test_case.user_input[:60]}{'...' if len(test_case.user_input) > 60 else ''}")
                    click.echo(f"     🎯 Threshold: {test_case.semantic_threshold}")
                    if test_case.tool_stubs:
                        tools = list(test_case.tool_stubs.keys())
                        click.echo(f"     🔧 Tools: {', '.join(tools)}")
                    click.echo()
        
        # Run tests using TestRunner
        if output_format == "console":
            if test:
                click.echo(f"\n🚀 Running single test '{test}' for '{agent}' in 'dev' environment")
            else:
                click.echo(f"\n🚀 Running tests for '{agent}' in 'dev' environment")
            if dry_run:
                click.echo("🔍 Dry run mode - no HTTP requests will be sent")
            elif no_stubs:
                click.echo("🌐 No-stubs mode - testing against real services")
        
        # Validate conflicting options
        if no_stubs and keep_stubs:
            click.echo("❌ Cannot use --no-stubs and --keep-stubs together", err=True)
            sys.exit(1)
        
        if no_stubs and dry_run:
            click.echo("❌ Cannot use --no-stubs and --dry-run together (dry-run already skips stubs)", err=True)
            sys.exit(1)
        
        # Execute tests
        runner = TestRunner(tests_dir="agent_tests", reports_dir="reports")
        # Apply stub service network settings
        if hasattr(runner, 'stub_service'):
            runner.stub_service.port = stubs_port
            runner.stub_service.host = stubs_host
        report = runner.run_tests_from_suite(
            test_suite=test_suite,
            environment="dev",
            dry_run=dry_run,
            write_reports=(not dry_run),  # Only write reports for real runs
            keep_stubs=keep_stubs,
            no_stubs=no_stubs
        )
        
        # Show stub service information if keeping it running
        if keep_stubs and report.total_tests > 0:
            click.echo("\n" + "="*60)
            click.secho("🔧 STUB SERVICE RUNNING", fg="yellow", bold=True)
            click.echo("="*60)
            click.echo(f"📍 Base URL: http://localhost:9876")
            click.echo(f"🏥 Health Check: http://localhost:9876/health")
            click.echo(f"📋 Available endpoints:")
            
            # Show available tool endpoints
            if hasattr(runner, 'stub_service') and runner.stub_service.tool_stubs:
                for tool_name in runner.stub_service.tool_stubs.keys():
                    click.echo(f"   • GET/POST http://localhost:9876/{tool_name}")
            
            click.echo(f"\n💡 Test these endpoints in Postman or curl!")
            click.echo(f"🛑 Press Ctrl+C when done to stop the stub service")
            click.echo("="*60 + "\n")
            
            # Keep the application running until user stops it
            try:
                click.echo("⏳ Waiting for manual testing... (Press Ctrl+C to stop)")
                import signal
                import time
                
                def signal_handler(sig, frame):
                    click.echo("\n🛑 Stopping stub service...")
                    if hasattr(runner, 'stub_service'):
                        runner.stub_service.stop()
                        click.echo("✅ Stub service stopped. Goodbye!")
                    exit(0)
                
                signal.signal(signal.SIGINT, signal_handler)
                
                # Keep running until interrupted
                while True:
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                click.echo("\n🛑 Stopping stub service...")
                if hasattr(runner, 'stub_service'):
                    runner.stub_service.stop()
                    click.echo("✅ Stub service stopped. Goodbye!")
                exit(0)
        
        # Output results based on format
        if output_format == "json":
            # JSON output for CI/CD systems
            json_result = {
                "agent": agent,
                "environment": "dev",
                "dry_run": dry_run,
                "success_rate": report.pass_percentage,
                "total_tests": report.total_tests,
                "passed": report.passed,
                "failed": report.failed,
                "errors": report.errors,
                "execution_time_ms": report.execution_time_total_ms,
                "status": report.overall_status.lower(),
                "threshold_met": report.pass_percentage >= 80.0,
                "tests": [
                    {
                        "name": result.test_name,
                        "status": result.status,
                        "comparison_method": result.comparison_method,
                        "score": result.semantic_score,
                        "error": result.error_message
                    }
                    for result in report.results
                ]
            }
            click.echo(json.dumps(json_result, indent=2))
        else:
            # Console output - display test results summary
            _display_test_results_console(report, test if test else "ALL TESTS")
        
        # Set exit code based on threshold
        if report.errors > 0 or report.pass_percentage < 80.0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except FileNotFoundError as e:
        click.echo(f"❌ Agent not found: {e}", err=True)
        click.echo("💡 Use --list-agents to see available agents")
        sys.exit(1)
    except ValueError as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        logger.exception("Unexpected error in CLI")
        sys.exit(1)


if __name__ == "__main__":
    main()