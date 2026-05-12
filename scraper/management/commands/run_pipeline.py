from django.core.management.base import BaseCommand
from scraper.tasks import kickoff_extraction_pipeline

class Command(BaseCommand):
    help = 'Kicks off the ClinicalTrials.gov historical extraction pipeline via Celery'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='Number of trials to fetch')
        parser.add_argument('--nct_id', type=str, default=None, help='NCT ID of single trial to fetch')

    def handle(self, *args, **kwargs):
        limit = kwargs['limit']
        nct_id = kwargs['nct_id']
        self.stdout.write(self.style.SUCCESS(f'Queuing pipeline for {limit} trials...'))
        
        # Dispatch to Celery
        kickoff_extraction_pipeline.delay(limit=limit, nct_id=nct_id)
        
        self.stdout.write(self.style.SUCCESS('Task dispatched successfully. Check Celery worker logs.'))