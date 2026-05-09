import requests
import logging

from scraper.models import RawTrialData, Trial, TrialChangeSummary, TrialVersion

logger = logging.getLogger(__name__)


class ExtractionAction:

    HEADERS = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-IN,en-US;q=0.9,en-GB;q=0.8,en;q=0.7',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
    }

    @staticmethod
    def fetch_all_target_trials():
        """Fetches all matching NCT IDs using API pagination."""
        nct_ids = []
        from_ = 0
        limit = 100
        
        url = f"https://clinicaltrials.gov/api/int/studies?aggFilters=phase:3,status:com,studyType:int&checkSpell=true&columns=conditions,interventions,collaborators&from={from_}&limit={limit}"

        while True:
            response = requests.get(url, headers=ExtractionAction.HEADERS)
            response.raise_for_status()
            data = response.json()
            
            hits = data.get('hits', [])
            for hit in hits:
                nct_id = hit['id']
                if nct_id:
                    yield nct_id
            
            # Check for next page
            total = data.get('total', 0)
            start_index = data.get('from')

            if not (total - start_index)  > 0:
                break # We have fetched all 29k IDs

            from_ += limit
                
        return nct_ids

    @staticmethod
    def fetch_trials(limit):
        url = f"https://clinicaltrials.gov/api/int/studies?aggFilters=phase:3,status:com,studyType:int&checkSpell=true&columns=conditions,interventions,collaborators&limit={limit}"

        response = requests.request("GET", url, headers=ExtractionAction.HEADERS, data={})
        response.raise_for_status()     
        nct_ids = [r["id"] for r in response.json()["hits"]]

        return nct_ids
    
    @staticmethod
    def fetch_trial_versions(nct_id):
        url = f"https://clinicaltrials.gov/api/int/studies/{nct_id}?history=true"

        response = requests.request("GET", url, headers=ExtractionAction.HEADERS, data={})
        response.raise_for_status()
        logger.info(f"{url} returned with status code {response.status_code}")
        data = response.json()

        trial, _ = Trial.objects.get_or_create(nct_id=nct_id)

        return data.get("history", {}).get("changes", [])
    
    @staticmethod
    def fetch_single_version(nct_id, version):
        version_number=version['version']
        version_date=version['date']
        
        url = f"https://clinicaltrials.gov/api/int/studies/{nct_id}/history/{version_number}"

        response = requests.request("GET", url, headers=ExtractionAction.HEADERS, data={})
        response.raise_for_status()
        
        full_json = response.json()
        
        data = full_json['study']['protocolSection']
        trial = Trial.objects.get(nct_id=nct_id)
        
        RawTrialData.objects.update_or_create(
            trial=trial,
            version_number=version_number,
            version_date=version_date,
            full_api_payload=full_json
        )
        
        version_data = {
            "trial": trial,
            "version_number": version_number,
            "version_date": version_date,
            "recruitment_status": data['statusModule']['overallStatus'], 
            "sponsors": data['sponsorCollaboratorsModule']['leadSponsor']['name'], 
            "conditions_module": data['conditionsModule'], 
            "primary_outcome": data['outcomesModule']['primaryOutcomes'],
            "study_phase": data['designModule']['phases'][0],
            "enrollment": data['designModule']['enrollmentInfo']['count'],
            "eligibility_criteria": {
                "min_age": data['eligibilityModule'].get('minimumAge'),
                "max_age": data['eligibilityModule'].get('maximumAge')
            },
            "locations": data['contactsLocationsModule'],
            "investigators": data['sponsorCollaboratorsModule']['responsibleParty'],
        }
        TrialVersion.objects.update_or_create(**version_data)
        
        return True

    @staticmethod
    def detect_changes(trial, current_version):
        previous_version = TrialVersion.objects.filter(
            trial=trial,
            version_number = current_version.version_number - 1
        )

        diff_payload = {}
        flags = {
            'status_changed': False,
            'enrollment_updated': False,
            'eligibility_modified': False,
            'sites_changed': False,
            'outcomes_changed': False
        }

        if current_version.recruitment_status != previous_version.recruitment_status:
            flags['status_changed'] = True
            diff_payload['status'] = {
                'old': previous_version.recruitment_status, 
                'new': current_version.recruitment_status
            }

        if current_version.enrollment != previous_version.enrollment:
            flags['enrollment_updated'] = True
            diff_payload['enrollment'] = {
                'old': previous_version.enrollment, 
                'new': current_version.enrollment
            }

        if len(current_version.locations) != len(previous_version.locations):
            flags['sites_changed'] = True
            diff_payload['locations_count'] = {
                'old': len(previous_version.locations), 
                'new': len(current_version.locations)
            }

        if current_version.eligibility_criteria != previous_version.eligibility_criteria:
             flags['eligibility_modified'] = True
            
        if len(current_version.primary_outcome) > 0:
            current_outcome = current_version.primary_outcome
            previous_outcome = previous_version.primary_outcome
            for i in range(len(current_version.primary_outcome)):
                if current_outcome[i]['measure'] != previous_outcome[i]['measure']:
                    diff_payload['primary_outcome'] = {
                        'old': previous_outcome[i]['measure'],
                        'new': current_outcome[i]['measure']
                    }
                    flags['outcomes_changed'] = True
                    break
        
        if any(flags.values()):
            TrialChangeSummary.objects.create(
                trial=trial,
                from_version=previous_version,
                to_version=current_version,
                diff_payload=diff_payload,
                **flags
            )