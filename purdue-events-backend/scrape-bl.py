import requests
from bs4 import BeautifulSoup
import json

# Fetching first 100 organizations from BoilerLink API
url = "https://boilerlink.purdue.edu/api/discovery/search/organizations"
params = {
    "top": 100
}
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

response = requests.get(url, params=params, headers=headers)

if response.status_code == 200:
    data = response.json()
    organizations = data.get('value', [])

    print("Extracted Organization Details:")
    for org in organizations:
        name = org.get('Name', 'N/A')
        website_key = org.get('WebsiteKey', 'N/A')
        description = org.get('Description', 'N/A')
        status = org.get('Status', 'N/A')
        categories = org.get('CategoryNames', [])
        

        print(f"Name: {name}")
        print(f"Website Key: {website_key}")
        # print(f"Description: {description}")
        print(f"Status: {status}")
        print(f"Categories: {', '.join(categories) if categories else 'None'}")
        print("-" * 40)
else:
    print(f"Failed to fetch data: {response.status_code}")

# New functionality to extract the Instagram URL from the script tag containing window.initialAppState
url = "https://boilerlink.purdue.edu/organization/launchpad"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html"
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    script_tag = soup.find('script', string=lambda t: t and 'window.initialAppState' in t)

    if script_tag:
        script_content = script_tag.string
        json_data = script_content.split('=', 1)[1].strip().rstrip(';')
        app_state = json.loads(json_data)

        # Extract Instagram URL
        instagram_url = app_state.get('preFetchedData', {}).get('organization', {}).get('socialMedia', {}).get('instagramUrl', 'N/A')
        print(f"Instagram URL: {instagram_url}")
    else:
        print("Script tag with 'window.initialAppState' not found.")
else:
    print(f"Failed to fetch organization page: {response.status_code}")

# Extract Instagram URLs for all organizations
print("Extracting Instagram URLs for all organizations:")
for org in organizations:
    website_key = org.get('WebsiteKey', 'N/A')

    if website_key != 'N/A':
        org_url = f"https://boilerlink.purdue.edu/organization/{website_key}"
        org_response = requests.get(org_url, headers=headers)

        if org_response.status_code == 200:
            soup = BeautifulSoup(org_response.text, 'html.parser')
            script_tag = soup.find('script', string=lambda t: t and 'window.initialAppState' in t)

            if script_tag:
                script_content = script_tag.string
                json_data = script_content.split('=', 1)[1].strip().rstrip(';')
                app_state = json.loads(json_data)

                # Extract Instagram URL
                instagram_url = app_state.get('preFetchedData', {}).get('organization', {}).get('socialMedia', {}).get('instagramUrl', None)
                if instagram_url:
                    print(f"Organization: {org.get('Name', 'N/A')} - Instagram: {instagram_url}")
                else:
                    print(f"Organization: {org.get('Name', 'N/A')} - Instagram: Not available")
            else:
                print(f"Organization: {org.get('Name', 'N/A')} - Failed to find 'window.initialAppState' script tag.")
        else:
            print(f"Organization: {org.get('Name', 'N/A')} - Failed to fetch organization page: {org_response.status_code}")
    else:
        print("Organization with no WebsiteKey found.")