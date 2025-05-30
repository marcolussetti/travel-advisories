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

DETAILS_PARSING_DELAY = 0.01


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


def parse_all_country_infos(urls):
    results = {}
    for url in urls:
        print(f"Fetching country details from {url}")
        html = fetch_page(url)
        destination, last_updated, sections = parse_country_details(html)
        sleep(DETAILS_PARSING_DELAY)
        if destination:
            results[destination] = {"url": url, "sections": sections, "last_updated": last_updated}

    return results

def parse_advisories(html):
    soup = BeautifulSoup(html, "html.parser")

    # **NEW: Extract country data from JavaScript**
    country_info_map = extract_country_info_map(soup)
    country_info_urls = [BASE_URL + c.get("url") + ".html" for c in country_info_map if c.get("url")]
    # print(country_info_urls)

    countries_info = parse_all_country_infos(country_info_urls)
    # print(countries_info)

    # os.exit(0)

    table = soup.find("div", {"class": "table-data"})
    if not table:
        raise ValueError("Could not find advisory table on the page")

    advisories = []
    # Parse advisories
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

            pages = []
            last_updated_details = None

            if destination in countries_info:
                country_info_url = countries_info[destination]["url"]
                pages.extend(countries_info[destination]["sections"])
                last_updated_details = countries_info[destination]["last_updated"]
            elif sanitize_path_element(destination) in countries_info:
                country_info_url = countries_info[sanitize_path_element(destination)]["url"]
                pages.extend(countries_info[sanitize_path_element(destination)]["sections"])
                last_updated_details = countries_info[sanitize_path_element(destination)]["last_updated"]
            else:
                country_info_url = None

            # Parse advisories details

            advisory_details_html = fetch_page(advisory_details_url)
            advisory_md_path = parse_advisory_details(advisory_details_html, destination)
            sleep(DETAILS_PARSING_DELAY)
            if advisory_md_path:
                pages.append({"title": "Advisory", "file": advisory_md_path})


            info = {
                "name": destination,
                "risk_level": risk_level,
                "risk_level_number": risk_level_number,
                "pages": pages,
                "update_date_advisory": last_updated,
                "update_date_details": last_updated_details,
            }
            with open(f"unitedstates/{sanitize_path_element(destination)}/info.json", "w", encoding="utf-8") as f:
                json.dump(info, f, indent=4)

            advisories.append(
                {
                    "destination": destination,
                    "risk_level": risk_level,
                    "last_updated_advisory": last_updated,
                    "advisory_details_url": advisory_details_url,
                    "risk_level_number": risk_level_number,
                    "country_info_url": country_info_url,
                    "last_updated_country_details": last_updated_details,
                }
            )
        except Exception as e:  # Catch a broader range of exceptions
            print(f"Failed to parse a row! {e}")
            try:
                print(row)
            except:
                pass

    advisories.sort(key=lambda x: x["destination"])


    # For each country details that isn't already in advisories, do the parsing
    for country_info_url in country_info_urls:
        if country_info_url not in [advisory["country_info_url"] for advisory in advisories if "country_info_url" in advisory]:
            try:
                destination, last_updated_details, sections = parse_country_details(fetch_page(country_info_url))
                if destination:
                    advisories.append(
                        {
                            "destination": destination,
                            "risk_level": None,
                            "advisory_details_url": None,
                            "risk_level_number": None,
                            "country_info_url": country_info_url,
                            "last_updated_advisory": None,
                            "last_updated_country_details": last_updated_details,
                        }
                    )

                    info = {
                        "name": destination,
                        "risk_level": None,
                        "risk_level_number": None,
                        "pages": sections,
                        "update_date_advisory": None,
                        "update_date_details": last_updated_details,
                    }
                    with open(f"unitedstates/{sanitize_path_element(destination)}/info.json", "w", encoding="utf-8") as f:
                        json.dump(info, f, indent=4)
#             

            except ValueError as e:
                print(f"Failed to fetch {country_info_url}: {e}")
            sleep(DETAILS_PARSING_DELAY)

    return advisories


def extract_country_info_map(soup):
    results = []
    # try:
    # Find the script tag containing the country data
    script_tag = soup.select("div.searchCSI script")
    if not script_tag:
        print("Could not find script tag inside div.searchCSI")
        return results

    script_content = script_tag.pop().string
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
    # print(results)
    return results


def parse_advisory_details(html, destination):
    soup = BeautifulSoup(html, "html.parser")

    sanitized_destination = sanitize_path_element(destination)

    # Extract advisory content
    advisory_content_frame = soup.select_one(".tsg-rwd-main-copy-frame")
    if advisory_content_frame:
        advisory_content = md(str(advisory_content_frame), heading_style="ATX")
        os.makedirs(f"unitedstates/{sanitized_destination}", exist_ok=True)
        with open(
            f"unitedstates/{sanitized_destination}/Advisory.md", "w", encoding="utf-8"
        ) as f:
            f.write(advisory_content)
        return f"unitedstates/{sanitized_destination}/Advisory.md"
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


def parse_country_details(html):
    soup = BeautifulSoup(html, "html.parser")

    try:
        destination = soup.select_one(".tsg-rwd-csi-contry-name").text.strip()
        if not destination or destination.lower() == "null":
            destination = soup.select_one(".tsg-rwd-csi-official-contry-name").text.strip()
            if not destination or destination.lower() == "null":
                destination = None
                raise ValueError("Could not find destination name")

        sanitized_destination = sanitize_path_element(destination)
        print(f"Parsing country details for {destination}")
    except Exception as e:
        print(f"Failed to parse destination: {e}")
        return None, {}

    try:
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
    except Exception as e:
        print(f"Failed to parse sections for {destination}: {e}")
        return destination, {}
    try:
        last_updated_element = soup.select_one(".csi-data-date")
        if last_updated_element:
            last_updated = last_updated_element.text.strip().replace("Last Updated:", "").strip()
            last_updated = datetime.strptime(last_updated, "%B %d, %Y").isoformat()
        else:
            last_updated = None
            print(f"Could not find last updated date for {destination}")
    except Exception as e:
        print(f"Failed to parse last updated date for {destination}: {e}")
        print(last_updated_element)
        last_updated = None

    details = []
    for section in sections:
        try:
            header = section.find("h3") or section.find("h4")
            if header:
                section_name = header.text.strip()
                sanitized_section_name = sanitize_path_element(section_name)
                section_id = (
                    section_name.replace(" ", "_").replace("/", "_").lower()
                )  # Create a unique ID
                section_content = md(str(section), heading_style="ATX")

                filepath = f"unitedstates/{sanitized_destination}/{sanitized_section_name}.md"
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"# {section_name}\n\n")
                    f.write(section_content)
                details.append({"title": section_name, "file": filepath})
            else:
                print(f"Could not find header in section for {destination}")
        except Exception as e:
            print(f"Failed to parse section for {destination}: {e}")

    return destination, last_updated, details


def save_to_csv(data, filename):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "destination",
                "risk_level",
                "last_updated_advisory",
                "advisory_details_url",
                "risk_level_number",
                "country_info_url",
                "last_updated_country_details",
            ],
        )
        writer.writeheader()
        writer.writerows(data)


def save_to_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)




def main():
    start_time = datetime.now()
    html = fetch_page(URL)
    advisories = parse_advisories(html)
    save_to_csv(advisories, OUTPUT_CSV)
    save_to_json(advisories, OUTPUT_JSON)
    print(f"Data saved to {OUTPUT_CSV} and {OUTPUT_JSON}")

if __name__ == "__main__":
    main()