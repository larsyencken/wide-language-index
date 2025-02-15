#!/usr/bin/env python3

import glob
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set

import llm

DATA_FILE = Path(__file__).parent.parent.parent / "ext" / "language_data.json"
MODEL = "gpt-4o-mini"


@dataclass
class LanguageData:
    iso_code: str
    name: str
    common_name: Optional[str]
    countries: List[str]
    regions: List[str]
    l1_users: int
    all_users: int
    language_family: List[str]


def fetch_language_data(iso_code: str) -> Optional[LanguageData]:
    m = llm.get_model(MODEL)
    prompt = f"""
    In what world regions is the language with iso code "{iso_code}" spoken? What is the most common name used for it? 
    Respond only in JSON with no markdown formatting, e.g.
    {{"iso_code": "yue", "name": "Yue Chinese", "common_name": "Cantonese", "regions": ["East Asia"], "main_countries": ["China"], "l1_users": 86000000, "all_users": 87000000, "language_family": ["Sino-Tibetan", "Sinitic", "Chinese", "Yue"]}}
    """
    response = json.loads(m.prompt(prompt).json()["content"])
    print(response)
    return LanguageData(
        iso_code=iso_code,
        name=response["name"],
        common_name=response["common_name"],
        regions=response["regions"],
        countries=response["main_countries"],
        l1_users=response["l1_users"],
        all_users=response["all_users"],
        language_family=response["language_family"],
    )


def save_language_data(data: dict[str, LanguageData], filename: str = DATA_FILE):
    """Save language data to a JSON file."""
    records = []
    for _, lang_data in sorted(data.items()):
        records.append(
            {
                "iso_code": lang_data.iso_code,
                "name": lang_data.name,
                "common_name": lang_data.common_name,
                "regions": lang_data.regions,
                "countries": lang_data.countries,
                "l1_users": lang_data.l1_users,
                "all_users": lang_data.all_users,
                "language_family": lang_data.language_family,
            }
        )
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


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
        row["iso_code"]: LanguageData(
            iso_code=row["iso_code"],
            name=row["name"],
            common_name=row["common_name"],
            regions=row["regions"],
            countries=row["countries"],
            l1_users=row["l1_users"],
            all_users=row["all_users"],
            language_family=row["language_family"],
        )
        for row in data
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
