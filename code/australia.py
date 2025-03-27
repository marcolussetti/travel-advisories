import os
from time import sleep
import requests
from bs4 import BeautifulSoup
import csv
import json
from datetime import datetime, timezone
from markdownify import markdownify as md
import tls_client
import re

BASE_URL = "https://www.smartraveller.gov.au"
URL = "https://www.smartraveller.gov.au/destinations"

OUTPUT_CSV = "australia_summary.csv"
OUTPUT_JSON = "australia_summary.json"

DETAILS_PARSING_DELAY = 0.5

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def fetch_page(url):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    session = tls_client.Session(
        client_identifier="chrome_120",
        random_tls_extension_order=True
    )

    try:
        response = session.get(url, headers=headers)
        # tls_client responses don't have raise_for_status.  Check status manually.
        if response.status_code >= 400:
            raise requests.exceptions.RequestException(f"HTTP Error: {response.status_code} for URL: {url}")
        return response.text
    except Exception as e:
        print(f"Problem fetching {url}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request Error fetching {url}: {e}")  # Using the requests exception.
        return None


def parse_advisories(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="views-table")
    if not table:
        raise ValueError("Could not find advisory table on the page")

    advisories = []

    print("Fetching advisory table")

    for row in table.find("tbody").find_all("tr"):
        try:
            columns = row.find_all("td")
            if len(columns) < 4:
                continue

            destination_tag = columns[0].find("a")
            destination = destination_tag.text.strip()
            url = BASE_URL + destination_tag["href"]
            risk_level = columns[2].text.strip()

            last_updated_tag = columns[3].find("time")
            last_updated = last_updated_tag["datetime"] if last_updated_tag else None

            advisories.append({
                "destination": destination,
                "risk_level": risk_level,
                "last_updated": last_updated,
                "url": url,  # Rename details_url to url
            })
        except Exception as e:
            print(f"Failed to parse a row: {e}")
            try:
                print(row)
            except:
                pass

    advisories.sort(key=lambda x: x["destination"])

    return advisories

def sanitize_path_element(path_element):
    # Define the characters to replace
    invalid_chars = r"[\\/:*?\"<>|]"

    # Replace the invalid characters with an underscore
    sanitized = re.sub(invalid_chars, "_", path_element)
    return sanitized.strip()  # Remove leading/trailing whitespace


def parse_country_details(html, advisory, country_name):
    """Parses the HTML content of a country's Smartraveller details page."""
    soup = BeautifulSoup(html, 'html.parser')
    print(f"Parsing details for {country_name}")



    sanitized_country_name = sanitize_path_element(country_name)

    details = {}

    # 1. Overview Section
    overview_node = soup.select_one("div.node__content")

    if overview_node:
        # overview_content = overview_node.get_text(separator="\n", strip=True)
        overview_md = md(str(overview_node), heading_style="ATX")
        overview_filename = f"australia/{sanitized_country_name}/overview.md"
        os.makedirs(f"australia/{sanitized_country_name}", exist_ok=True)
        with open(overview_filename, "w", encoding="utf-8") as f:
            f.write(f"# Overview\n\n")
            f.write(overview_md)
        details["overview"] = overview_filename
    else:
        details["overview"] = "No overview found."
        print(f"Warning: No overview section found for {country_name}")

    # 2. Other Sections
    other_sections = soup.select("div.full-bleed > .field > .field__items > .field__item > .paragraph")
    details["pages"] = []  # Store other sections in a list

    for section in other_sections:
        h3 = section.find("h3")
        if h3:
            title = h3.get_text(strip=True)
        else:
            title = "Untitled Section with missing h3"
            print(f"Warning: Section with missing h3 found for {country_name}")
        # Remove the h3 element so that we don't get the title text twice
        # Removing before converting to markdown seems to keep it out!
        h3_to_remove = section.find("h3")
        if h3_to_remove:
            h3_to_remove.decompose()

        # content = section.get_text(separator="\n", strip=True)

        # Convert to Markdown *after* removing the h3
        content_md = md(str(section), heading_style="ATX")

        # Use the title as the filename to make it more descriptive. We also need to sanitise the titles so that there are no weird characters and spaces.
        section_filename = f"australia/{sanitized_country_name}/{''.join(c if c.isalnum() else '_' for c in title)}.md"
        with open(section_filename, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(content_md)

        details["pages"].append({"title": title, "file": section_filename})

    # Add the URL and advisory information
    details["url"] = advisory["url"]
    details["advisory_level"] = advisory["risk_level"]  # advisory_level did not exist, using risk_level field
    details["destination"] = country_name  # Ensure the country name is ALWAYS saved.
    details["last_updated"] = advisory["last_updated"]

    # 3. Save to file
    if country_name:
        info_file_path = f"australia/{country_name}/info.json"
        with open(info_file_path, "w", encoding="utf-8") as f:
            json.dump(details, f, indent=4)
    else:
        print("Country name not found. Skipping details parsing.")
        return

    return details


def save_to_csv(data, filename):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["destination", "risk_level", "last_updated", "url"])
        writer.writeheader()
        writer.writerows(data)


def save_to_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def run_country_details(country_url, advisory):
    print(f"Fetching {country_url}")
    html = fetch_page(country_url)
    if html:
        parse_country_details(html, advisory, advisory["destination"])  # Passing country_name
    else:
        print(f"Skipping {country_url} due to fetch error.")


def run_all_countries(summary_data, since: datetime = None):
    targets = [
        country
        for country in summary_data
        if since is None or (country["last_updated"] and datetime.fromisoformat(country["last_updated"]).replace(tzinfo=timezone.utc) >= since)
    ]

    total_countries = len(targets)
    for i, country in enumerate(targets):
        print(f"Fetching {i + 1}/{total_countries}: {country['destination']}")
        try:
            run_country_details(country["url"], country)
        except ValueError as e:
            print(f"Failed to fetch {country['destination']}: {e}")
        sleep(DETAILS_PARSING_DELAY)


def main():
    start_time = datetime.now(timezone.utc)
    print("Fetching the main page")
    html = fetch_page(URL)
    if html:
        print("Fetched the main page")
        advisories = parse_advisories(html)
        save_to_csv(advisories, OUTPUT_CSV)
        save_to_json(advisories, OUTPUT_JSON)
        print(f"Data saved to {OUTPUT_CSV} and {OUTPUT_JSON}")

        # Now fetch the details that have changed
        summary_data = json.load(open("australia_summary.json"))

        if os.path.exists("australia/last_run.txt"):
            with open("australia/last_run.txt", "r", encoding="utf-8") as f:
                try:
                    last_run = datetime.strptime(f.read().strip(), "%Y-%m-%dT%H:%M:%S")
                    last_run = last_run.replace(tzinfo=timezone.utc)
                except ValueError:
                    last_run = None  # Handle cases where the file contains invalid data
        else:
            last_run = None
        run_all_countries(summary_data, last_run)

        with open("australia/last_run.txt", "w", encoding="utf-8") as f:
            f.write(start_time.strftime("%Y-%m-%dT%H:%M:%S"))
    else:
        print("Failed to fetch main page. Exiting.")


if __name__ == "__main__":
    main()