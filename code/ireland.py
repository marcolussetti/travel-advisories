import os
from time import sleep
import requests
from bs4 import BeautifulSoup
import json
import csv
from datetime import datetime, timezone
from markdownify import markdownify as md
import re

BASE_URL = "https://www.ireland.ie"
URL = "https://www.ireland.ie/en/dfa/overseas-travel/advice/"

OUTPUT_JSON = "ireland_summary.json"
OUTPUT_CSV = "ireland_summary.csv"

DETAILS_PARSING_DELAY = 0.5

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"


def fetch_page(url):
    headers = {'User-Agent': USER_AGENT}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text


def parse_country_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select(".article-cards a")
    countries = [{"name": link.text.strip(), "url": BASE_URL + link["href"]} for link in links]
    return countries


def sanitize_path_element(path_element):
    # Define the characters to replace
    invalid_chars = r"[\\/:*?\"<>|]"

    # Replace the invalid characters with an underscore
    sanitized = re.sub(invalid_chars, "_", path_element)
    return sanitized.strip()  # Remove leading/trailing whitespace


def parse_country_details(html, country_name, since):
    soup = BeautifulSoup(html, "html.parser")

    # Extract the country name
    name = soup.find("h1").text.strip()

    # Extract Overall Security Status
    summary_element = soup.select_one("#main-header .travel-landing--summary")
    risk_level = summary_element.text.strip() if summary_element else "No summary found"

    # Extract metadata (last updated)
    update_text_element = soup.find("div", class_="update-text", string=lambda text: text and "Updated on:" in text)
    last_updated_text = update_text_element.text.strip() if update_text_element else None

    last_modified = None
    if last_updated_text:
        try:
            date_string = last_updated_text.replace("Updated on: ", "")
            last_modified = datetime.strptime(date_string, "%d %B %Y")
        except ValueError:
            print(f"Could not parse date from: {last_updated_text}")
            last_modified = None

    if since and last_modified and last_modified < since:
        print(f"Skipping {name} as it has not been updated since {since}")
        return name, last_modified, risk_level

    # Extract advice sections and save them
    sections_files = save_advice_sections(soup, country_name)
    # print(f"Processed ireland/{country_name}/Advice sections.md")

    pages = []
    for section_name, section_file in sections_files.items():
        pages.append({
            "title": section_name,
            "file": section_file,
            # "update_date": last_modified.isoformat() if last_modified else None
        })

    info = {
        "name": name,
        "risk_level": risk_level,
        "pages": pages,
        "update_date": last_modified.isoformat() if last_modified else None
    }

    sanitized_name = sanitize_path_element(name)  # Sanitize the country name
    os.makedirs(f"ireland/{sanitized_name}", exist_ok=True)
    with open(f"ireland/{sanitized_name}/info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=4)

    print(f"Processed {name}")

    return name, last_modified, risk_level


def save_advice_sections(soup, country_name):
    # Find all advice sections within .section elements
    sections = soup.select(".section .accordion")

    sections_files = {}
    for section in sections:
        # Extract the title from h2 element for filename
        title_element = section.find("h2")
        if title_element:
            title = title_element.text.strip()
            sanitized_title = sanitize_path_element(title)  # Sanitize title
            sanitized_country_name = sanitize_path_element(country_name)
            filename = f"ireland/{sanitized_country_name}/{sanitized_title}.md"
        else:
            # if there is no h2 title, make a file entitled Misc
            title = "Misc"
            sanitized_country_name = sanitize_path_element(country_name)
            filename = f"ireland/{sanitized_country_name}/Misc.md"

        # Save each advice section in its own file
        markdown_content = md(str(section), heading_style="ATX")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        sections_files[title] = filename
        print(f"Processed ireland/{sanitized_country_name}/{title}.md")

    return sections_files


def save_to_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def save_to_csv(data, filename):
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["destination", "risk_level", "last_updated", "details_url"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in data:
            writer.writerow(row)


def run_all_countries(since: datetime = None):
    html = fetch_page(URL)
    countries = parse_country_links(html)

    summary_data = []

    for country in countries:
        print("Fetching", country["name"])
        try:
            html = fetch_page(country["url"])
            name, last_modified, risk_level = parse_country_details(html, country["name"], since)
            summary_data.append({
                "destination": name,
                "risk_level": risk_level,
                "last_updated": last_modified.isoformat() if last_modified else None,
                "details_url": country["url"]
            })
        except Exception as e:
            print("Failed to fetch", country["name"], e)
            print(e)  # Print the exception for debugging
        sleep(DETAILS_PARSING_DELAY)

    save_to_json(summary_data, OUTPUT_JSON)
    save_to_csv(summary_data, OUTPUT_CSV)


def main():
    start_time = datetime.now(timezone.utc)
    # Now fetch the details that have changed
    if os.path.exists("ireland/last_run.txt"):
        with open("ireland/last_run.txt", "r", encoding="utf-8") as f:
            last_run = datetime.fromisoformat(f.read().strip())
    else:
        last_run = None

    run_all_countries(last_run)

    with open("ireland/last_run.txt", "w", encoding="utf-8") as f:
        f.write(start_time.isoformat())


if __name__ == "__main__":
    main()