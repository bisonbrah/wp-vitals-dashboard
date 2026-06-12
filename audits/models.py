from django.db import models


class Site(models.Model):
    """Represents a WordPress install that has been audited."""

    name = models.CharField(max_length=255, unique=True)
    path = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Report(models.Model):
    """Stores the output of a full wp-vitals audit run against a site."""

    HEALTH_CHOICES = [
        ('critical', 'Critical'),
        ('warning', 'Warning'),
        ('healthy', 'Healthy'),
        ('unknown', 'Unknown'),
    ]

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='reports')
    created_at = models.DateTimeField(auto_now_add=True)
    overall_health = models.CharField(max_length=20, choices=HEALTH_CHOICES, default='unknown')

    # Individual audit outputs
    log_report = models.TextField(blank=True)
    plugin_report = models.TextField(blank=True)
    theme_report = models.TextField(blank=True)

    # Synthesized outputs
    executive_summary = models.TextField(blank=True)
    debug_prompts = models.TextField(blank=True)

    # AI-generated comparison between this report and the previous run
    diff_report = models.TextField(blank=True)

    def __str__(self):
        return f"{self.site.name} — {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-created_at']
