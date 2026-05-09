from django.contrib import admin

from scraper.models import RawTrialData, Trial, TrialChangeSummary, TrialVersion

# Register your models here.

admin.site.register(Trial)
admin.site.register(RawTrialData)
admin.site.register(TrialVersion)
admin.site.register(TrialChangeSummary)