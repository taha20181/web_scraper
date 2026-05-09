from celery import shared_task
from scraper.action.extraction import ExtractionAction
import logging


logger = logging.getLogger(__name__)

@shared_task(bind=True)
def kickoff_extraction_pipeline(self, limit):
    try:
        if limit:
            nct_ids = ExtractionAction.fetch_trials(limit)
            for nct_id in nct_ids:
                process_trial_history.delay(nct_id)
        else:
            nct_ids = ExtractionAction.fetch_all_target_trials()        
            nct_id = nct_ids.__next__()
            process_trial_history.delay(nct_id)

    except Exception as e:
        logger.error(f"Failed to fetch trial list: {e}")
        raise self.retry(exc=e, countdown=60)

@shared_task(bind=True, max_retries=3)
def process_trial_history(self, nct_id):
    try:
        versions = ExtractionAction.fetch_trial_versions(nct_id)
        if not versions:
            raise

        for version in versions:
            fetch_single_trial_version.delay(nct_id, version)
    except Exception as e:
        logger.error(f"Error processing {nct_id}: {e}")
        raise self.retry(exc=e, countdown=30)

@shared_task(bind=True, max_retries=3, rate_limit='10/s')
def fetch_single_trial_version(self, nct_id, version):
    try:
        data = ExtractionAction.fetch_single_version(nct_id, version)
    except Exception as e:
        logger.error(f"Error processing {nct_id} - v{version['version']}: {e}")
        raise self.retry(exc=e, countdown=30)
