import json
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup


USER_AGENT_HEADERS = {
    "User-Agent": "Mozilla/5.0",
}


def fetch_organizations(top: int = 100) -> List[Dict]:
    """Fetch the first `top` organizations from BoilerLink discovery API.

    Returns the list of organization objects (from the 'value' field).
    """
    url = "https://boilerlink.purdue.edu/api/discovery/search/organizations"
    params = {"top": top}

    resp = requests.get(url, params=params, headers={**USER_AGENT_HEADERS, "Accept": "application/json"})
    resp.raise_for_status()
    data = resp.json()
    return data.get('value', [])


def fetch_org_page(website_key: str) -> Optional[str]:
    """Fetch HTML for a given organization website key. Returns HTML or None on failure."""
    url = f"https://boilerlink.purdue.edu/organization/{website_key}"
    resp = requests.get(url, headers={**USER_AGENT_HEADERS, "Accept": "text/html"})
    if resp.status_code != 200:
        return None
    return resp.text


def extract_instagram_from_html(html: str) -> Optional[str]:
    """Extract the instagramUrl from the `window.initialAppState` script in the org page HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    script_tag = soup.find('script', string=lambda t: t and 'window.initialAppState' in t)
    if not script_tag:
        return None
    script_content = script_tag.string
    json_data = script_content.split('=', 1)[1].strip().rstrip(';')
    app_state = json.loads(json_data)
    return app_state.get('preFetchedData', {}).get('organization', {}).get('socialMedia', {}).get('instagramUrl')


def get_instagram_for_orgs(orgs: List[Dict]) -> List[Dict]:
    """Given a list of organization objects, return a list with org name and instagram url (if any)."""
    results = []
    i = 0
    for org in orgs:
        if i % 10 == 0:
            print(f"Processing #{i} : {org.get('Name')}")
        name = org.get('Name')
        website_key = org.get('WebsiteKey')
        if not website_key:
            results.append({"name": name, "website_key": None, "instagram": None})
            continue
        html = fetch_org_page(website_key)
        if not html:
            results.append({"name": name, "website_key": website_key, "instagram": None})
            continue
        ig = extract_instagram_from_html(html)
        results.append({"name": name, "website_key": website_key, "instagram": ig})
        i += 1
    return results


if __name__ == '__main__':
    # quick runner - edit values here
    TOP = 100

    orgs = fetch_organizations(TOP)
    for o in orgs[:5]:
        print(o.get('Name'), '-', o.get('WebsiteKey'))

    print('\nFetching Instagram URLs for first 100 orgs (may take a while):')
    mapped = get_instagram_for_orgs(orgs)
    for m in mapped:
        print(m['name'], '->', m['instagram'])