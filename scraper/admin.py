from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from scraper.models import RawTrialData, Trial, TrialVersionPatch, TrialVersion

# Register your models here.

@admin.register(RawTrialData)
class RawTrialDataAdmin(ImportExportModelAdmin):
    pass

@admin.register(TrialVersion)
class TrialVersionAdmin(ImportExportModelAdmin):
    pass

@admin.register(TrialVersionPatch)
class TrialVersionPatchAdmin(ImportExportModelAdmin):
    pass


admin.site.register(Trial)