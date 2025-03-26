import re
import json
import csv
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from time import sleep
from markdownify import markdownify as md

BASE_URL = "https://travel.state.gov"
URL = "https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html/"

OUTPUT_CSV = "unitedstates_summary.csv"
OUTPUT_JSON = "unitedstates_summary.json"

DETAILS_PARSING_DELAY = 0.1


def fetch_page(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def sanitize_path_element(path_element):
    # Define the characters to replace
    invalid_chars = r"[\\/:*?\"<>|]"

    # Replace the invalid characters with an underscore
    sanitized = re.sub(invalid_chars, "_", path_element)
    return sanitized.strip()  # Remove leading/trailing whitespace


def parse_advisories(html):
    soup = BeautifulSoup(html, "html.parser")

    # **NEW: Extract country data from JavaScript**
    country_info_map = extract_country_info_map(soup)
    country_info_urls = [c.get("url")for c in country_info_map if c.get("url")]

    table = soup.find("div", {"class": "table-data"})
    if not table:
        raise ValueError("Could not find advisory table on the page")

    advisories = []

    for row in table.find("tbody").find_all("tr"):
        if "data-header" in row.get("class", []):
            continue

        # print(row)
        try:
            columns = row.find_all("td")
            if len(columns) < 3:
                continue

            destination_tag = columns[0].find("a")
            destination = destination_tag.text.strip().replace("Travel Advisory", "").strip()
            advisory_details_url = BASE_URL + destination_tag["href"]
            risk_level = columns[1].text.strip()
            try:
                risk_level_number = int(
                    risk_level.split(":")[0].replace("Level", "").strip()
                )
            except:
                risk_level_number = -1

            last_updated = columns[2].text.strip()

            try:
                last_updated = datetime.strptime(last_updated, "%B %d, %Y").isoformat()
            except ValueError:
                last_updated = None  # If parsing fails

            advisories.append(
                {
                    "destination": destination,
                    "risk_level": risk_level,
                    "last_updated": last_updated,
                    "advisory_details_url": advisory_details_url,
                    "risk_level_number": risk_level_number
                }
            )
        except Exception as e:  # Catch a broader range of exceptions
            print(f"Failed to parse a row! {e}")
            try:
                print(row)
            except:
                pass

    advisories.sort(key=lambda x: x["destination"])

    return advisories


def extract_country_info_map(soup):
    results = []
    # try:
    # Find the script tag containing the country data
    script_tag = soup.select("div.searchCSI script")
    if not script_tag:
        print("Could not find script tag inside div.searchCSI")
        return results

    script_content = script_tag.string
    if not script_content:
        print("Script tag is empty.")
        return results

    for line in script_content.splitlines():
        line = line.strip()
        if line.startswith("{"):  # Only process lines with this value
            data = {}
            parts = line[1:-1].split(",")
            for part in parts:
                if ":" not in part:
                    continue
                key, value = part.split(":", 1)
                key = key.strip().strip("'").strip('"')
                value = value.strip().strip("'").strip('"')
                data[key] = value
            results.append(data)
    print(results)
    return results


def parse_advisory_details(html, destination):
    soup = BeautifulSoup(html, "html.parser")

    # Extract advisory content
    advisory_content_frame = soup.select_one(".tsg-rwd-main-copy-frame")
    if advisory_content_frame:
        advisory_content = md(str(advisory_content_frame), heading_style="ATX")
        os.makedirs(f"unitedstates/{destination}", exist_ok=True)
        with open(
            f"unitedstates/{destination}/Advisory.md", "w", encoding="utf-8"
        ) as f:
            f.write(advisory_content)
    else:
        print(f"Could not find advisory content frame for {destination}")
        return None

    # Extract country details URL
    country_details_url = None
    country_info_link = advisory_content_frame.find(
        "a",
        string=lambda text: text and "country information page" in text.lower(),
    )
    if country_info_link:
        country_details_url = country_info_link["href"]
    else:
        print(f"Could not find country information link for {destination}")

    return country_details_url


def parse_country_details(html, destination):
    soup = BeautifulSoup(html, "html.parser")

    # Find sections
    sections_container = soup.select_one(
        ".tsg-rwd-main-CSI-International-Travel-items-international"
    )
    if not sections_container:
        print(f"Could not find main CSI container for {destination}")
        return {}
    sections = [
        section
        for section in sections_container.find_all("div", recursive=False)
        if "tsg-rwd-accordion-nav-frame-for-freestanding-all-buttons-csi-show"
        not in section.get("class", [])
    ]

    details = {}
    for section in sections:
        header = section.find("h3") or section.find("h4")
        if header:
            section_name = header.text.strip()
            sanitized_section_name = sanitize_path_element(section_name)
            section_id = (
                section_name.replace(" ", "_").replace("/", "_").lower()
            )  # Create a unique ID
            section_content = md(str(section), heading_style="ATX")

            filepath = f"unitedstates/{destination}/{sanitized_section_name}.md"
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {section_name}\n\n")
                f.write(section_content)
            details[section_name] = filepath
        else:
            print(f"Could not find header in section for {destination}")

    return details


def save_to_csv(data, filename):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "destination",
                "risk_level",
                "last_updated",
                "advisory_details_url",
                "risk_level_number",
                "country_details_url",
            ],
        )
        writer.writeheader()
        writer.writerows(data)


def save_to_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def run_country_details(
    advisory_details_url, destination, last_updated, country_details_url_from_js
):
    print(f"Fetching advisory details for {destination} from {advisory_details_url}")
    try:
        html = fetch_page(advisory_details_url)
        # country_details_url = parse_advisory_details(html, destination)  #No need to parse again, using value from JS.

        details = {}

        if country_details_url_from_js:
            country_details_url = country_details_url_from_js
            print(f"Fetching country details for {destination} from {country_details_url}")
            html = fetch_page(country_details_url)
            details = parse_country_details(html, destination)
        else:
            country_details_url = parse_advisory_details(
                html, destination
            )  # If JS version is not available, use find via parsing

            if country_details_url:
                print(
                    f"Fetching country details for {destination} from {country_details_url}"
                )
                html = fetch_page(country_details_url)
                details = parse_country_details(html, destination)
            else:
                print(f"No country details to fetch for {destination}")

        # Create the 'info.json' file
        pages = []
        for title, file in details.items():
            pages.append({"title": title, "file": file})

        info = {
            "name": destination,
            "risk_level": None,  # You'll need to fetch risk level from somewhere
            "pages": pages,
            "update_date": last_updated,
        }

        with open(f"unitedstates/{destination}/info.json", "w", encoding="utf-8") as f:
            json.dump(info, f, indent=4)

    except ValueError as e:
        print(f"Failed to fetch details for {destination}: {e}")


def run_all_countries(since: datetime = None):
    with open("unitedstates_summary.json", "r", encoding="utf-8") as f:
        countries_summary = json.load(f)

    targets = [
        (
            country["advisory_details_url"],
            country["destination"],
            country["last_updated"],
            country["country_details_url"],
        )
        for country in countries_summary
        if since is None
        or (country["last_updated"] and datetime.fromisoformat(country["last_updated"]) >= since)
    ]

    for advisory_details_url, destination, last_updated, country_details_url_from_js in targets:
        try:
            destination_sanitized = sanitize_path_element(destination)
            run_country_details(
                advisory_details_url,
                destination_sanitized,
                last_updated,
                country_details_url_from_js,
            )
        except ValueError as e:
            print(f"Failed to fetch {destination}: {e}")
        sleep(DETAILS_PARSING_DELAY)


def main():
    start_time = datetime.now()
    html = fetch_page(URL)
    advisories = parse_advisories(html)
    save_to_csv(advisories, OUTPUT_CSV)
    save_to_json(advisories, OUTPUT_JSON)
    print(f"Data saved to {OUTPUT_CSV} and {OUTPUT_JSON}")

    # Now fetch the details that have changed
    if os.path.exists("unitedstates/last_run.txt"):
        with open("unitedstates/last_run.txt", "r", encoding="utf-8") as f:
            last_run = datetime.strptime(f.read().strip(), "%Y-%m-%dT%H:%M:%S")
    else:
        last_run = None
    run_all_countries(last_run)

    with open("unitedstates/last_run.txt", "w", encoding="utf-8") as f:
        f.write(start_time.strftime("%Y-%m-%dT%H:%M:%S"))


if __name__ == "__main__":
    main()