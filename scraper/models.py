from django.db import models

# Create your models here.


class Trial(models.Model):
    """
    Core model representing a single clinical trial.
    """
    nct_id = models.CharField(max_length=20, primary_key=True, help_text="Trial identifier ")
    title = models.CharField(max_length=500)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nct_id}"


class RawTrialData(models.Model):
    """
    Immutable Data Lake: Stores the exact, untouched API response.
    """
    trial = models.ForeignKey(Trial, on_delete=models.CASCADE, related_name='raw_responses')
    version_number = models.IntegerField()
    version_date = models.DateField(null=True, blank=True)
    
    full_api_payload = models.JSONField(help_text="The complete, unmodified JSON dictionary returned by the API")
    
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('trial', 'version_number')


class TrialVersion(models.Model):
    """
    Details of a trial at a specific version date.
    """
    trial = models.ForeignKey(Trial, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField()
    version_date = models.DateField()
    
    recruitment_status = models.CharField(max_length=100)
    enrollment = models.IntegerField(null=True, blank=True)
    
    sponsors = models.JSONField(default=list)
    conditions_module = models.JSONField(default=list)
    primary_outcome = models.JSONField(default=list)    
    study_phase = models.JSONField(default=list)
    locations = models.JSONField(default=list)
    
    investigators = models.JSONField(default=dict)
    eligibility_criteria = models.JSONField(default=dict)
    
    class Meta:
        # Ensure we don't duplicate versions for the same trial
        unique_together = ('trial', 'version_number')
        ordering = ['trial', 'version_number']

    def __str__(self):
        return f"{self.trial.nct_id} - v{self.version_number} ({self.version_date})"


class TrialVersionPatch(models.Model):
    """
    Logs the specific, meaningful changes detected between two sequential versions.
    """
    trial = models.ForeignKey(Trial, on_delete=models.CASCADE, related_name='change_logs')
    from_version = models.IntegerField()
    to_version = models.IntegerField()
    
    # Granular Extraction Data
    module_name = models.CharField(max_length=100)
    operation = models.CharField(max_length=20)
    json_path = models.CharField(max_length=255)
    
    value = models.JSONField(null=True)
    change_value = models.JSONField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"Changes for {self.trial.nct_id}: v{self.from_version} -> v{self.to_version}"
    