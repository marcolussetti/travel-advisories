import os
from time import sleep
import requests
from bs4 import BeautifulSoup
import csv
import json
from datetime import datetime
from markdownify import markdownify as md

BASE_URL = "https://travel.gc.ca"
URL = "https://travel.gc.ca/travelling/advisories"

OUTPUT_CSV = "canada_summary.csv"
OUTPUT_JSON = "canada_summary.json"

DETAILS_PARSING_DELAY = 0.5

def fetch_page(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def parse_advisories(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "reportlist"})
    if not table:
        raise ValueError("Could not find advisory table on the page")
    
    advisories = []
    
    for row in table.find("tbody").find_all("tr"):

        # print(row)
        try:
            columns = row.find_all("td")
            if len(columns) < 3:
                continue


            destination_tag = columns[1].find("a")
            destination = destination_tag.text.strip()
            url = BASE_URL + destination_tag["href"]
            risk_level = columns[2].text.strip()
            last_updated = columns[3].text.strip()
            
            try:
                last_updated = datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S").isoformat()
            except ValueError:
                last_updated = None  # If parsing fails
            
            advisories.append({
                "destination": destination,
                "risk_level": risk_level,
                "last_updated": last_updated,
                "details_url": url,
            })
        except:
            print("Failed to parse a row!")
            try:
                print(row)
            except:
                pass

    advisories.sort(key=lambda x: x["destination"])
    
    return advisories


def parse_country_details(html):
    soup = BeautifulSoup(html, "html.parser")

    name_tag = soup.find("span", {"id": "nameLbl"})
    if not name_tag:
        raise ValueError("Country name is missing from the details page")
    name = name_tag.text.strip()
    update_reason = soup.find("span", {"id": "lastUpdateTextLbl"}).text.strip() if soup.find("span", {"id": "lastUpdateTextLbl"}) else None
    update_date_raw = soup.find("span", {"id": "lastUpdateDateLbl"}).text.strip() if soup.find("span", {"id": "lastUpdateDateLbl"}) else None
    if update_date_raw:
        try:
            update_date = datetime.strptime(update_date_raw, "%B %d, %Y %H:%M").isoformat()
        except ValueError:
            update_date = None  # If parsing fails
    else:
        update_date = None

    # Find all sections which are divs inside div with col-md-8
    sections = soup.select("div.col-md-8 > div")
    if not sections:
        raise ValueError("No sections found in the country details page")
    info = {
        "name": name,
        "update_reason": update_reason,
        "update_date": update_date,
        "sections": {section.get("id"): f"canada/{name}/{section.get('id')}.md" for section in sections}
    }

    os.makedirs(f"canada/{name}", exist_ok=True)
    with open(f"canada/{name}/info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=4)

    # for each div, find the id which is going to identify the section, then convert the inner html to markdown and save it to canada/{name}/{id}.md
    for section in sections:
        section_id = section.get("id")
        # print(section)
        # print(section_id)
        section_name = section.find("h2").text.strip()
        # Convert the section content to markdown
        section_content = md(str(section), heading_style="ATX")

        # Fix relative links in the markdown content
        for link in section.find_all("a", href=True):
            href = link["href"]
            if href.startswith("/"):
                full_url = BASE_URL + href
                section_content = section_content.replace(href, full_url)

        os.makedirs(f"canada/{name}", exist_ok=True)
        with open(f"canada/{name}/{section_id}.md", "w", encoding="utf-8") as f:
            f.write(f"# {section_name}\n\n")
            f.write(section_content)


def save_to_csv(data, filename):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["destination", "risk_level", "last_updated", "details_url"])
        writer.writeheader()
        writer.writerows(data)

def save_to_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def run_country_details(country_url):
    html = fetch_page(country_url)
    parse_country_details(html)


def run_all_countries(since: datetime=None):
    with open("canada_summary.json", "r", encoding="utf-8") as f:
        countries_summary = json.load(f)

    targets = [
        country["details_url"]
        for country in countries_summary
        if since is None or (country["last_updated"] and datetime.fromisoformat(country["last_updated"]) >= since)
    ]

    for country in targets:
        print("Fetching", country)
        try:
            run_country_details(country)
        except ValueError as e:
            print("Failed to fetch", country, e)
        sleep(DETAILS_PARSING_DELAY)


def main():
    start_time = datetime.now()
    html = fetch_page(URL)
    advisories = parse_advisories(html)
    save_to_csv(advisories, OUTPUT_CSV)
    save_to_json(advisories, OUTPUT_JSON)
    print(f"Data saved to {OUTPUT_CSV} and {OUTPUT_JSON}")

    # Now fetch the details that have changed
    if os.path.exists("canada/last_run.txt"):
        with open("canada/last_run.txt", "r", encoding="utf-8") as f:
            last_run = datetime.strptime(f.read().strip(), "%Y-%m-%dT%H:%M:%S")
    else:
        last_run = None
    run_all_countries(last_run)

    with open("canada/last_run.txt", "w", encoding="utf-8") as f:
        f.write(start_time.strftime("%Y-%m-%dT%H:%M:%S"))

if __name__ == "__main__":
    main()