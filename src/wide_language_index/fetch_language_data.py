#!/usr/bin/env python3

import glob
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set

import requests

DATA_FILE = Path(__file__).parent.parent.parent / "ext" / "language_data.json"


@dataclass
class WikidataEntity:
    id: str
    label: str


@dataclass
class CountryData:
    country: WikidataEntity
    speakers: Optional[int] = None
    official: bool = False


@dataclass
class LanguageData:
    iso_code: str
    wikidata_id: Optional[str] = None
    total_speakers: Optional[int] = None
    countries: List[CountryData] = None
    regions: List[WikidataEntity] = None

    def __post_init__(self):
        if self.countries is None:
            self.countries = []
        if self.regions is None:
            self.regions = []

    @property
    def main_country(self) -> Optional[WikidataEntity]:
        """Determine main country based on speakers and official status."""
        if not self.countries:
            return None

        # First try to find country with most speakers where it's official
        official_countries = [c for c in self.countries if c.official]
        if official_countries:
            sorted_countries = sorted(
                official_countries, key=lambda x: (x.speakers or 0), reverse=True
            )
            return sorted_countries[0].country

        # If no official countries, return country with most speakers
        sorted_countries = sorted(
            self.countries, key=lambda x: (x.speakers or 0), reverse=True
        )
        return sorted_countries[0].country


def fetch_language_data(iso_code: str) -> Optional[LanguageData]:
    """Fetch language data from Wikidata using SPARQL."""
    query = (
        """
    SELECT DISTINCT ?lang ?speakers ?country ?countryLabel ?region ?regionLabel ?countryCount ?isOfficial WHERE {
      ?lang wdt:P220 "%s" .  # ISO 639-3 code
      
      OPTIONAL {
        ?lang wdt:P1098 ?speakers .  # Total speakers
      }
      
      # Get countries and major administrative divisions where the language is used
      OPTIONAL {
        {
          # Get sovereign states where it's official
          ?country wdt:P31 wd:Q3624078 .  # Instance of: sovereign state
          {
            ?country wdt:P37 ?lang .       # Official language
            BIND(true AS ?isOfficial)
          }
          UNION
          {
            ?country wdt:P2936 ?lang .     # Language used
            BIND(false AS ?isOfficial)
          }
        }
        UNION
        {
          # Get major administrative divisions where it's official or widely used
          ?country wdt:P31 wd:Q10864048 .  # Instance of: first-level administrative country subdivision
          {
            ?country wdt:P37 ?lang .
            BIND(true AS ?isOfficial)
          }
          UNION
          {
            ?country wdt:P2936 ?lang .
            BIND(false AS ?isOfficial)
          }
        }
        
        # Get speaker counts if available
        OPTIONAL {
          ?country p:P1098 ?statementNode .
          ?statementNode ps:P1098 ?countryCount .
          ?statementNode pq:P407 ?lang .
        }
      }
      
      # Get geographic regions
      OPTIONAL {
        VALUES ?regionType { 
          wd:Q82794     # Geographic region
          wd:Q37525     # Cultural region
          wd:Q82794     # Linguistic region
        }
        ?region wdt:P31 ?regionType .
        ?lang wdt:P2341 ?region .  # Indigenous to region
      }
      
      # Get labels
      SERVICE wikibase:label { 
        bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en".
        ?country rdfs:label ?countryLabel .
        ?region rdfs:label ?regionLabel .
      }
    }
    """
        % iso_code
    )

    url = "https://query.wikidata.org/sparql"
    headers = {
        "User-Agent": "LanguageIndexEnricher/1.0 (https://github.com/larsyencken/wide-language-index)",
        "Accept": "application/json",
    }

    try:
        response = requests.get(
            url, headers=headers, params={"query": query, "format": "json"}
        )
        response.raise_for_status()

        data = response.json()
        results = data["results"]["bindings"]

        if not results:
            return None

        # Get language ID and total speakers from first result
        lang_id = results[0]["lang"]["value"].split("/")[-1]
        total_speakers = (
            int(results[0]["speakers"]["value"]) if "speakers" in results[0] else None
        )

        # Process countries with deduplication
        countries: dict[str, CountryData] = {}
        for result in results:
            if "country" in result and "countryLabel" in result:
                country_id = result["country"]["value"].split("/")[-1]
                if country_id not in countries:
                    country = WikidataEntity(
                        id=country_id, label=result["countryLabel"]["value"]
                    )
                    speakers = (
                        int(result["countryCount"]["value"])
                        if "countryCount" in result
                        else None
                    )
                    is_official = bool(
                        result.get("isOfficial", {}).get("value", "false") == "true"
                    )
                    countries[country_id] = CountryData(country, speakers, is_official)

        # Process regions with deduplication
        regions: dict[str, WikidataEntity] = {}
        for result in results:
            if "region" in result and "regionLabel" in result:
                region_id = result["region"]["value"].split("/")[-1]
                if region_id not in regions:
                    regions[region_id] = WikidataEntity(
                        id=region_id, label=result["regionLabel"]["value"]
                    )

        return LanguageData(
            iso_code=iso_code,
            wikidata_id=lang_id,
            total_speakers=total_speakers,
            countries=list(countries.values()),
            regions=list(regions.values()),
        )

    except Exception as e:
        print(f"Error fetching data for {iso_code}: {str(e)}")
        return None


def save_language_data(data: dict[str, LanguageData], filename: str = DATA_FILE):
    """Save language data to a JSON file."""
    serializable_data = {
        code: {
            "iso_code": lang.iso_code,
            "wikidata_id": lang.wikidata_id,
            "total_speakers": lang.total_speakers,
            "countries": [
                {
                    "country": {"id": c.country.id, "label": c.country.label},
                    "speakers": c.speakers,
                    "official": c.official,
                }
                for c in lang.countries
            ],
            "regions": [{"id": r.id, "label": r.label} for r in lang.regions],
            "main_country": {
                "id": lang.main_country.id,
                "label": lang.main_country.label,
            }
            if lang.main_country
            else None,
        }
        for code, lang in data.items()
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(serializable_data, f, indent=2, ensure_ascii=False)


def load_existing_languages() -> Set[str]:
    """Load all language codes from the index directory."""
    languages = set()
    for path in glob.glob("index/*/"):
        lang_code = os.path.basename(os.path.dirname(path))
        if len(lang_code) == 3:  # Valid ISO 639-3 codes are 3 characters
            languages.add(lang_code)
    return languages


def load_language_data(filename: str = DATA_FILE) -> dict[str, LanguageData]:
    """Load existing language data from JSON file."""
    if not os.path.exists(filename):
        return {}

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        code: LanguageData(
            iso_code=info["iso_code"],
            wikidata_id=info["wikidata_id"],
            total_speakers=info["total_speakers"],
            countries=[
                CountryData(
                    country=WikidataEntity(**c["country"]),
                    speakers=c["speakers"],
                    official=c["official"],
                )
                for c in info["countries"]
            ],
            regions=[WikidataEntity(**r) for r in info["regions"]],
        )
        for code, info in data.items()
    }


def main():
    # Load existing languages from index
    languages = load_existing_languages()
    print(f"Found {len(languages)} languages in index")

    # Load existing language data
    language_data = load_language_data()
    print(f"Loaded {len(language_data)} existing language records")

    # Find languages that need data
    languages_to_fetch = languages - set(language_data.keys())
    print(f"Need to fetch data for {len(languages_to_fetch)} languages")

    # Fetch missing data
    for iso_code in sorted(languages_to_fetch):
        print(f"Fetching data for {iso_code}...")
        data = fetch_language_data(iso_code)
        if data:
            language_data[iso_code] = data
            # Save after each successful fetch to preserve progress
            save_language_data(language_data)
            print(f"Saved data for {iso_code}")
        else:
            print(f"No data found for {iso_code}")

    print("Complete!")


if __name__ == "__main__":
    main()
