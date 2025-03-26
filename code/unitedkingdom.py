import os
from time import sleep
import requests
from bs4 import BeautifulSoup
import json
import csv
from datetime import datetime, timezone
from markdownify import markdownify as md
import re

BASE_URL = "https://www.gov.uk"
URL = "https://www.gov.uk/foreign-travel-advice"

OUTPUT_JSON = "unitedkingdom_summary.json"
OUTPUT_CSV = "unitedkingdom_summary.csv"

DETAILS_PARSING_DELAY = 0.5


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


def parse_country_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select("a.govuk-link.countries-list__link")
    countries = [{"name": link.text.strip(), "url": BASE_URL + link["href"]} for link in links]
    return countries

def parse_json_ld(soup):
    # Find all script tags with type application/ld+json
    script_tags = soup.find_all("script", {"type": "application/ld+json"})
    for script in script_tags:
        data = json.loads(script.string)
        if data.get("@type") == "Article":
            date_published = data.get("datePublished")
            date_modified = data.get("dateModified")

            try:
                if date_published:
                    date_published = datetime.fromisoformat(date_published)
            except ValueError:
                date_published = None

            try:
                if date_modified:
                    date_modified = datetime.fromisoformat(date_modified)
            except ValueError:
                date_modified = None

            return date_published, date_modified
    return None, None

def parse_country_details(html, country_name, since):
    sanitized_country_name = sanitize_path_element(country_name)
    soup = BeautifulSoup(html, "html.parser")

    # Remove the cookie banner section
    cookie_banner = soup.find("div", {"id": "global-cookie-message"})
    if cookie_banner:
        cookie_banner.extract()

    # Extract the country name
    name = soup.find("h1").text.strip()

    # Extract metadata
    metadata = {}
    metadata_list = soup.find("dl", {"class": "gem-c-metadata__list"})
    if metadata_list:
        for dt, dd in zip(metadata_list.find_all("dt"), metadata_list.find_all("dd")):
            key = dt.text.strip().replace(":", "")
            value = dd.text.strip()
            metadata[key] = value

    date_published, date_modified = parse_json_ld(soup)

    last_modified = None
    if date_modified:
        last_modified = date_modified
    else:
        update_date = metadata.get("Updated", None)
        update_reason = metadata.get("Latest update", None)

        if update_date:
            try:
                last_modified = datetime.strptime(update_date, "%d %B %Y")
            except ValueError:
                pass
    # print("Last modified")
    # print(last_modified)

    # print("since")
    # print(since)

    if since and last_modified and last_modified < since:
        print(f"Skipping {name} as it has not been updated")
        return name, last_modified

    # Extract warnings and save them
    warnings_file = save_warnings_section(soup, sanitized_country_name)
    print(f"Processed page unitedkingdom/{sanitized_country_name}/Warnings and insurance.md")

    # Extract other pages' links and save them
    other_pages = parse_and_save_other_pages(soup, sanitized_country_name)

    pages = []
    if warnings_file:
        pages.append({
            "title": "Warnings and insurance",
            "file": warnings_file,
            "update_date": last_modified.isoformat() if last_modified else None
        })
    for page in other_pages:
        pages.append(page)

    info = {
        "name": name,
        "update_reason": update_reason,
        "pages": pages,
        "update_date": last_modified.isoformat() if last_modified else None
    }

    os.makedirs(f"unitedkingdom/{sanitized_country_name}", exist_ok=True)
    with open(f"unitedkingdom/{sanitized_country_name}/info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=4)

    print(f"Processed {name}")

    return name, update_date

def save_warnings_section(soup, country_name):
    # Remove the "Get travel advice updates" section and all its following siblings if it exists
    updates_section = soup.find("h2", {"id": "get-travel-advice-updates"})
    if updates_section:
        for sibling in list(updates_section.find_all_next()):
            sibling.extract()
        updates_section.extract()

    warnings_file = f"unitedkingdom/{country_name}/Warnings and insurance.md"
    save_page_from_soup(soup, warnings_file)
    return warnings_file


def parse_and_save_other_pages(soup, country_name):
    other_pages = []
    part_navigation = soup.find("aside", {"class": "part-navigation-container"})
    if part_navigation:
        for li in part_navigation.find_all("li"):
            link = li.find("a")
            if link and ("email alerts" not in link.text.strip().lower()):  # Skip "Get email alerts" pages
                page_title = link.text.strip()
                page_title_sanitized = sanitize_path_element(page_title)
                page_url = BASE_URL + link["href"]
                page_file = f"unitedkingdom/{country_name}/{page_title_sanitized}.md"
                other_pages.append({
                    "title": page_title,
                    "url": page_url,
                    "file": page_file,
                    # "update_date": None  # Always seems the same :)
                })

                # Fetch and save the page content
                date_modified = fetch_and_save_page(page_url, page_file)

                # other_pages[-1]["update_date"] = date_modified

    return other_pages


def extract_content(page_soup):
    try:
        # Remove the cookie banner from the page
        cookie_banner = page_soup.find("div", {"id": "global-cookie-message"})
        if cookie_banner:
            cookie_banner.extract()

        page_contents = page_soup.find_all("div", {"class": "govuk-grid-column-two-thirds"})

        # Iterate through the page contents to find the second <h1>
        page_content = None
        h1_count = 0
        for content in page_contents:
            h1_tags = content.find_all("h1")
            if len(h1_tags) >= 1:
                h1_count += 1
                if h1_count == 2:  # Select the second match
                    page_content = content
                    break

        return page_content
    except Exception as e:
        print(f"Failed to extract content: {e}")
        return None


def save_page_from_soup(soup, file_path):
    try:
        page_content = extract_content(soup)
        if page_content:
            markdown_content = md(str(page_content), heading_style="ATX")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
        else:
            print(f"No content found to save for {file_path}")
    except Exception as e:
        print(f"Failed to save file {file_path}: {e}")


def fetch_and_save_page(url, file_path):
    try:
        page_html = fetch_page(url)
        page_soup = BeautifulSoup(page_html, "html.parser")

        save_page_from_soup(page_soup, file_path)
        print(f"Processed page {file_path}")
    except Exception as e:
        print(f"Failed to fetch page at {url}: {e}")

    try:
        _, date_modified = parse_json_ld(page_soup)
    except Exception as e:
        print(f"Failed to fetch page at {url}: {e}")
    return date_modified


def save_to_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def save_to_csv(data, filename):
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["destination", "last_updated", "details_url"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in data:
            writer.writerow(row)

def run_all_countries(since: datetime=None):
    html = fetch_page(URL)
    countries = parse_country_links(html)

    summary_data = []

    for country in countries:
        print("Fetching", country["name"])
        try:
            html = fetch_page(country["url"])
            name, last_modified = parse_country_details(html, country["name"], since)
            summary_data.append({
                "destination": name,
                "last_updated": last_modified.isoformat(),
                "details_url": country["url"]
            })
        except ValueError as e:
            print("Failed to fetch", country["name"], e)
        sleep(DETAILS_PARSING_DELAY)

    save_to_json(summary_data, OUTPUT_JSON)
    save_to_csv(summary_data, OUTPUT_CSV)

def main():
    start_time = datetime.now(timezone.utc)
    # Now fetch the details that have changed
    if os.path.exists("unitedkingdom/last_run.txt"):
        with open("unitedkingdom/last_run.txt", "r", encoding="utf-8") as f:
            last_run = datetime.fromisoformat(f.read().strip())
    else:
        last_run = None

    run_all_countries(last_run)

    with open("unitedkingdom/last_run.txt", "w", encoding="utf-8") as f:
        f.write(start_time.isoformat())

if __name__ == "__main__":
    main()