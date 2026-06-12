from django.core.management.base import BaseCommand
from audits.models import Site, Report
from anthropic import Anthropic
import os

# Import the audit functions from wp-vitals
from report import generate_executive_summary, generate_debug_prompts
from main import run_log_analysis
from audit_plugins import run_plugin_audit
from audit_theme import run_theme_audit

# Anthropic client for diff generation
client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))


def generate_diff(site_name: str, previous: Report, current_data: dict) -> str | None:
    """
    Compare the previous report to the current audit results.
    Sends both to Claude and returns a plain-language diff summary
    showing what's resolved, what's new, and what remains.

    :param site_name: Display name of the site being audited.
    :param previous: The most recent Report object from the database.
    :param current_data: Dict containing the current audit report strings.
    :return: Formatted diff string from Claude, or None on failure.
    """
    message = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=1024,
        messages=[
            {
                'role': 'user',
                'content': f"""You are a WordPress developer comparing two audit reports for site: {site_name}

PREVIOUS REPORT (run on {previous.created_at.strftime('%Y-%m-%d %H:%M')} UTC):

Log Analysis:
{previous.log_report or 'No data'}

Plugin Audit:
{previous.plugin_report or 'No data'}

Theme Audit:
{previous.theme_report or 'No data'}

Executive Summary:
{previous.executive_summary or 'No data'}

---

CURRENT REPORT:

Log Analysis:
{current_data.get('log_report', 'No data')}

Plugin Audit:
{current_data.get('plugin_report', 'No data')}

Theme Audit:
{current_data.get('theme_report', 'No data')}

Executive Summary:
{current_data.get('executive_summary', 'No data')}

---

Compare the two reports and provide:
1. **Resolved** - Issues present in the previous report that are no longer present
2. **New Issues** - Issues in the current report that were not in the previous report
3. **Unchanged** - Issues that remain from the previous report
4. **Overall Trend** - Is the site getting better, worse, or staying the same?

Be specific. Reference plugin names, file paths, and error types where relevant.
Max 20 lines."""
            }
        ]
    )

    return message.content[0].text


class Command(BaseCommand):
    """Django management command to run a full wp-vitals audit and save results."""

    help = 'Run a full wp-vitals audit against a local WordPress install'

    def add_arguments(self, parser):
        # Required: the site folder name matching LOCAL_SITES_PATH
        parser.add_argument('site', type=str, help='Site folder name (e.g. evanghenry)')

        # Optional: target a specific theme
        parser.add_argument('--theme', type=str, default=None, help='Theme folder name')

        # Optional: scope log analysis to N days back
        parser.add_argument('--days', type=int, default=30, help='Days back for log analysis')

    def handle(self, *args, **options):
        site_name = options['site']
        theme = options['theme']
        days = options['days']

        self.stdout.write(f'\nRunning full audit for: {site_name}')
        self.stdout.write('=' * 60)

        # Get or create the Site record in the database
        site, created = Site.objects.get_or_create(
            name=site_name,
            defaults={'path': f'Local Sites/{site_name}'}
        )

        if created:
            self.stdout.write(f'  New site added: {site_name}')

        # Fetch the most recent previous report before running the new one
        previous_report = site.reports.first()

        # Run all three audits
        self.stdout.write('\n[ 1/3 ] Analyzing error logs...')
        log_result = run_log_analysis(site=site_name, days=days)

        self.stdout.write('[ 2/3 ] Auditing plugins...')
        plugin_result = run_plugin_audit(site=site_name)

        self.stdout.write('[ 3/3 ] Auditing theme dependencies...')
        theme_result = run_theme_audit(site=site_name, theme=theme)

        # Generate the executive summary and debug prompts
        self.stdout.write('\nGenerating executive summary...')
        summary = generate_executive_summary(site_name, log_result, plugin_result, theme_result)
        prompts = generate_debug_prompts(log_result, plugin_result, theme_result)

        # Determine overall health by checking all three reports
        health = 'unknown'
        all_reports = ' '.join(filter(None, [
            log_result.get('report') if log_result else None,
            plugin_result.get('report') if plugin_result else None,
            theme_result.get('report') if theme_result else None,
        ])).lower()

        if 'critical' in all_reports:
            health = 'critical'
        elif 'warning' in all_reports:
            health = 'warning'
        elif 'healthy' in all_reports:
            health = 'healthy'

        # Build current report data dict for diff generation
        current_data = {
            'log_report': log_result['report'] if log_result and log_result.get('report') else '',
            'plugin_report': plugin_result['report'] if plugin_result and plugin_result.get('report') else '',
            'theme_report': theme_result['report'] if theme_result and theme_result.get('report') else '',
            'executive_summary': summary or '',
        }

        # Generate diff if a previous report exists
        diff = None
        if previous_report:
            self.stdout.write('Generating diff against previous report...')
            diff = generate_diff(site_name, previous_report, current_data)

        # Save the report to the database
        report = Report.objects.create(
            site=site,
            overall_health=health,
            log_report=current_data['log_report'],
            plugin_report=current_data['plugin_report'],
            theme_report=current_data['theme_report'],
            executive_summary=current_data['executive_summary'],
            debug_prompts=prompts or '',
            diff_report=diff or '',
        )

        self.stdout.write(f'\nReport saved. ID: {report.id} | Health: {health}')

        if diff:
            self.stdout.write('\n--- DIFF FROM PREVIOUS REPORT ---')
            self.stdout.write(diff)

        self.stdout.write('=' * 60)
