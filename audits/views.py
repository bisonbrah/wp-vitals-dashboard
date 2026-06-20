from django.shortcuts import render, get_object_or_404
from .models import Site, Report


def dashboard(request):
    """
    Main dashboard view. Lists all audited sites with their latest health status.
    """
    sites = Site.objects.prefetch_related('reports').all()

    site_data = []
    for site in sites:
        latest = site.reports.first()
        site_data.append({
            'site': site,
            'latest_report': latest,
        })

    return render(request, 'audits/dashboard.html', {'site_data': site_data})


def site_detail(request, site_name):
    """
    Shows all audit reports for a single site, newest first.
    """
    site = get_object_or_404(Site, name=site_name)
    reports = site.reports.all()

    return render(request, 'audits/site_detail.html', {
        'site': site,
        'reports': reports,
    })


def report_detail(request, report_id):
    """
    Shows the full output of a single audit report, including the diff if available.
    """
    report = get_object_or_404(Report, id=report_id)

    return render(request, 'audits/report_detail.html', {'report': report})
