import os
from time import sleep
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from markdownify import markdownify as md

BASE_URL = "https://www.gov.uk"
URL = "https://www.gov.uk/foreign-travel-advice"

OUTPUT_JSON = "unitedkingdom_summary.json"

DETAILS_PARSING_DELAY = 0.5

def fetch_page(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def parse_country_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select("a.govuk-link.countries-list__link")
    countries = [{"name": link.text.strip(), "url": BASE_URL + link["href"]} for link in links]
    return countries

def parse_country_details(html, country_name):
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

    # Extract the last update date and reason
    update_date = metadata.get("Updated", None)
    update_reason = metadata.get("Latest update", None)

    # Parse the update date
    if update_date:
        try:
            update_date = datetime.strptime(update_date, "%d %B %Y").isoformat()
        except ValueError:
            update_date = None

    # Extract the warnings section (last .gem-c-govspeak element)
    warnings_section = soup.select(".gem-c-govspeak")[-1]

    # Remove the "Get travel advice updates" section and all its following siblings if it exists
    updates_section = warnings_section.find("h2", {"id": "get-travel-advice-updates"})
    if updates_section:
        for sibling in list(updates_section.find_all_next()):
            sibling.extract()
        updates_section.extract()

    warnings_content = md(str(warnings_section), heading_style="ATX")

    # Extract other pages' links from .part-navigation-container
    other_pages = []
    part_navigation = soup.find("aside", {"class": "part-navigation-container"})
    if part_navigation:
        for li in part_navigation.find_all("li"):
            link = li.find("a")
            if link:
                page_title = link.text.strip()
                page_url = BASE_URL + link["href"]
                other_pages.append({
                    "title": page_title,
                    "url": page_url,
                    "file": f"unitedkingdom/{country_name}/{page_title}.md"
                })

    info = {
        "name": name,
        "update_date": update_date,
        "update_reason": update_reason,
        "warnings": f"unitedkingdom/{name}/warnings.md",
        "other_pages": other_pages
    }

    os.makedirs(f"unitedkingdom/{name}", exist_ok=True)
    with open(f"unitedkingdom/{name}/info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=4)

    with open(f"unitedkingdom/{name}/warnings.md", "w", encoding="utf-8") as f:
        f.write(warnings_content)

    # Parse and save other pages
    for page in other_pages:
        print(f"Fetching {page['title']} for {country_name}")
        try:
            page_html = fetch_page(page["url"])
            page_soup = BeautifulSoup(page_html, "html.parser")


            # Remove the cookie banner from the other pages
            cookie_banner = page_soup.find("div", {"id": "global-cookie-message"})
            if cookie_banner:
                cookie_banner.extract()

            print(page_soup)
            page_contents = page_soup.find_all("div", {"class": "govuk-grid-column-two-thirds"})
            page_content = next((content for content in page_contents if content.find("h1")), None)

            if page_content:
                markdown_content = md(str(page_content), heading_style="ATX")
                with open(page["file"], "w", encoding="utf-8") as f:
                    f.write(markdown_content)
        except Exception as e:
            print(f"Failed to fetch {page['title']} for {country_name}: {e}")
        sleep(DETAILS_PARSING_DELAY)

def save_to_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def run_all_countries():
    html = fetch_page(URL)
    countries = parse_country_links(html)

    for country in countries:
        print("Fetching", country["name"])
        try:
            html = fetch_page(country["url"])
            parse_country_details(html, country["name"])
        except ValueError as e:
            print("Failed to fetch", country["name"], e)
        sleep(DETAILS_PARSING_DELAY)

def main():
    start_time = datetime.now()
    run_all_countries()
    print("Data saved to unitedkingdom/ directory")

    with open("unitedkingdom/last_run.txt", "w", encoding="utf-8") as f:
        f.write(start_time.strftime("%Y-%m-%dT%H:%M:%S"))

if __name__ == "__main__":
    main()