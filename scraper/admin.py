from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from scraper.models import RawTrialData, Trial, TrialChangeSummary, TrialVersion

# Register your models here.

@admin.register(RawTrialData)
class RawTrialDataAdmin(ImportExportModelAdmin):
    pass

@admin.register(TrialVersion)
class TrialVersionAdmin(ImportExportModelAdmin):
    pass

# @admin.register(RawTrialData)
# class RawTrialDataAdmin(ImportExportModelAdmin):
#     pass

admin.site.register(Trial)
admin.site.register(TrialChangeSummary)