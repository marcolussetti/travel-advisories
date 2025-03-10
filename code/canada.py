import requests
from bs4 import BeautifulSoup
import csv
import json
from datetime import datetime

BASE_URL = "https://travel.gc.ca"
URL = "https://travel.gc.ca/travelling/advisories"

OUTPUT_CSV = "canada_summary.csv"
OUTPUT_JSON = "canada_summary.json"

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

def save_to_csv(data, filename):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["destination", "risk_level", "last_updated", "details_url"])
        writer.writeheader()
        writer.writerows(data)

def save_to_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def main():
    html = fetch_page(URL)
    advisories = parse_advisories(html)
    save_to_csv(advisories, OUTPUT_CSV)
    save_to_json(advisories, OUTPUT_JSON)
    print(f"Data saved to {OUTPUT_CSV} and {OUTPUT_JSON}")


if __name__ == "__main__":
    main()