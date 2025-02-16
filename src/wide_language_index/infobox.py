#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "click",
#   "requests",
#   "llm",
# ]
# ///

import json

import click
import llm
import requests

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
DEFAULT_MODEL = "gpt-4o-mini"

KNOWN_PAGES = {
    "arb": "Modern Standard Arabic",
    "din": "Dinka language",
    "ekk": "Estonian language",
    "npi": "Nepali Language",
    "pnb": "Punjabi language",
    "yid": "Yiddish",
    "ydd": "Yiddish",  # Eastern Yiddish, most common variety
    "zsm": "Standard Malay",
}


def get_enwiki_title_from_iso639_3(iso_code: str) -> str | None:
    """
    Query Wikidata for the item matching the given ISO 639-3 code (P220),
    then retrieve the corresponding English Wikipedia page title, if any.
    """
    # We look for any item with P220 == iso_code, and an English Wikipedia sitelink.
    # That sitelink has schema:name = page title.
    # Example: For iso_code='spa', this should find 'Spanish_language'.
    query = f"""
    SELECT ?pageTitle
    WHERE {{
      ?item wdt:P220 "{iso_code}".
      ?article schema:about ?item ;
               schema:isPartOf <https://en.wikipedia.org/> ;
               schema:name ?pageTitle.
    }}
    LIMIT 1
    """
    headers = {
        "User-Agent": "ISO6393LanguageExtractor/1.0 (example@example.com)",
        "Accept": "application/sparql-results+json",
    }
    resp = requests.get(WIKIDATA_SPARQL_URL, params={"query": query}, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    results = data.get("results", {}).get("bindings", [])
    if not results:
        return None
    return results[0]["pageTitle"][
        "value"
    ]  # The title string, e.g., "Spanish language"


def fetch_wikitext(page_title: str) -> str:
    """
    Fetch the raw wikitext for the given English Wikipedia page title.
    """
    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": page_title,
    }
    resp = requests.get(WIKIPEDIA_API_URL, params=params)
    resp.raise_for_status()
    data = resp.json()
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return ""
    page_data = next(iter(pages.values()))
    revisions = page_data.get("revisions", [])
    if not revisions:
        return ""
    return revisions[0].get("slots", {}).get("main", {}).get("*", "")


@click.command()
@click.argument("iso_code")
@click.option("--model", default=DEFAULT_MODEL, help="LLM model name.")
def main(iso_code: str, model: str):
    """
    1. Find the Wikipedia page title for the given ISO 639-3 code using Wikidata.
    2. Fetch that page's wikitext from English Wikipedia.
    3. Prompt an LLM to parse the data similarly to how an infobox might be parsed.
    4. Print the result as JSON.
    """
    record = fetch_language_data(iso_code, model=DEFAULT_MODEL)
    if not record:
        click.echo(f"No language data found for ISO code '{iso_code}'.")
        return

    # Print in a nicely formatted way
    click.echo(json.dumps(record, indent=2))


def fetch_language_data(iso_code: str, model: str = DEFAULT_MODEL) -> dict | None:
    if iso_code in KNOWN_PAGES:
        page_title = KNOWN_PAGES[iso_code]
    else:
        page_title = get_enwiki_title_from_iso639_3(iso_code)
        if not page_title:
            click.echo(f"No English Wikipedia page found for ISO code '{iso_code}'.")
            return

    wikitext = fetch_wikitext(page_title)
    if not wikitext:
        click.echo(f"Failed to fetch wikitext for '{page_title}'.")
        return

    # Prompt the LLM
    model_client = llm.get_model(model)

    # The user can modify this prompt as needed for more/less detail
    prompt = f"""
Here is the raw Wikipedia source for an article titled "{page_title}":
---
{wikitext}
---
The language's ISO 639-3 code is "{iso_code}".

Please parse the article (especially any infobox) to extract:
- The language's most common or official name(s).
- Regions of the world where it is spoken.
- Main countries where it is natively spoken.
- Estimated number of first-language (L1) users.
- Estimated total number of speakers (L1 + L2).
- A hierarchical list of language family memberships.

Return your answer ONLY in JSON with this schema:
{{
  "iso_code": "",
  "name": "",
  "common_name": "",
  "regions": [],
  "main_countries": [],
  "l1_users": 0,
  "all_users": 0,
  "language_family": []
}}
Do not include markdown formatting.
    """

    response = model_client.prompt(prompt)
    content = response.json().get("content", "{}")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        click.echo("LLM response could not be parsed as valid JSON.")
        return

    return parsed


if __name__ == "__main__":
    main()
