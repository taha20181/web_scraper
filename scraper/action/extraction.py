import requests
import logging

from scraper.models import RawTrialData, Trial, TrialVersionPatch, TrialVersion

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
        versions = data.get("history", {}).get("changes", [])

        return versions
    
    @staticmethod
    def fetch_single_version(nct_id, version):
        version_number=version['version']
        version_date=version['date']
        
        url = f"https://clinicaltrials.gov/api/int/studies/{nct_id}/history/{version_number}"

        response = requests.request("GET", url, headers=ExtractionAction.HEADERS, data={})
        logger.info(f"{url} returned with status code {response.status_code}")
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
        trial_version, created = TrialVersion.objects.update_or_create(**version_data)

        if version_number > 0:
            ExtractionAction.detect_changes(trial, trial_version)
        
        return True

    @staticmethod
    def detect_changes(trial, current_version):
        current_version_num = current_version.version_number
        prev_version_num = current_version_num - 1

        url = f"https://clinicaltrials.gov/api/int/studies/{trial.nct_id}/history/{prev_version_num}?patchToVersion={current_version_num}"
        
        response = requests.request("GET", url, headers=ExtractionAction.HEADERS, data={})
        logger.info(f"{url} returned with status code {response.status_code}")
        response.raise_for_status()

        data = response.json()
        patches = data.get('patch', [])

        prev_version = RawTrialData.objects.get(trial=trial, version_number=prev_version_num)
        payload = prev_version.full_api_payload.get("study", {})

        for patch in patches:

            operation = patch.get("op")
            path = patch.get("path")
            change_value = patch.get("value")
            value = payload
            for key in path.split("/"):
                if key == "":
                    continue

                if isinstance(value, list):
                    continue

                try:
                    list_index = int(key)
                    if isinstance(list_index, int):
                        value = value[key]
                        continue
                except:
                    pass
                
                value = value.get(key, {})

            module_name = path.split("/")[2]

            TrialVersionPatch.objects.create(
                trial=trial,
                from_version=prev_version_num,
                to_version=current_version_num,
                operation=operation,
                module_name=module_name,
                value=value,
                change_value=change_value,
                json_path=path
            )