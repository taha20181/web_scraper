from django.core.management.base import BaseCommand
from scraper.tasks import kickoff_extraction_pipeline

class Command(BaseCommand):
    help = 'Kicks off the ClinicalTrials.gov historical extraction pipeline via Celery'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='Number of trials to fetch')

    def handle(self, *args, **kwargs):
        limit = kwargs['limit']
        self.stdout.write(self.style.SUCCESS(f'Queuing pipeline for {limit} trials...'))
        
        # Dispatch to Celery
        kickoff_extraction_pipeline.delay(limit=limit)
        
        self.stdout.write(self.style.SUCCESS('Task dispatched successfully. Check Celery worker logs.'))