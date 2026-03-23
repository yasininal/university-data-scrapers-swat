import requests
from bs4 import BeautifulSoup
import csv
import datetime
import random
import time
import logging
import pandas as pd
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data" / "raw"

def run_webometrics_scraper(target_url):
    """
    Scrapes university rankings from the Webometrics Türkiye page.

    Args:
        target_url (str): The URL of the Webometrics page to scrape.

    Returns:
        str: Summary of the scraping process (e.g., success message with the number of universities scraped).
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        filename=str(DATA_DIR / 'webometrics_scraper.log'),
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # User-Agent rotation
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
    ]

    # Initialize data storage
    universities = []
    page_number = 1
    same_count = 0  # Counter for consecutive pages with the same total number of universities
    last_count = 0  # Tracks the last total number of universities

    print("Scraping işlemi başlıyor, lütfen bekleyin...")

    try:
        while True:
            # Rotate User-Agent
            headers = {"User-Agent": random.choice(user_agents)}

            # Fetch the page
            logging.info(f"Fetching page {page_number}: {target_url}")
            response = requests.get(target_url, headers=headers, timeout=10)
            time.sleep(random.uniform(1, 3))  # Throttle requests

            if response.status_code == 403:
                logging.error("403 Forbidden: Access denied by the server.")
                return "403 Forbidden: Access denied by the server."

            response.raise_for_status()

            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')

            # Initialize a counter for sequential numbering
            counter = 1

            # Locate the table and extract data
            table = soup.find('table')
            if not table:
                logging.error("Table not found on the page.")
                return "Error: Table not found on the page."

            rows = table.find_all('tr')[1:]  # Skip the header row
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 5:
                    continue
                university_data = {
                    "No": counter,
                    "World Rank": cols[1].text.strip(),
                    "University Name": cols[2].text.strip() if len(cols)>2 else "",
                    "Impact Rank": cols[4].text.strip() if len(cols) > 4 else "",
                    "Openness Rank": cols[5].text.strip() if len(cols) > 5 else "",
                    "Excellence Rank": cols[6].text.strip() if len(cols) > 6 else ""
                }
                universities.append(university_data)
                counter += 1

            # Log progress
            logging.info(f"Page {page_number} scraped successfully. Total universities so far: {len(universities)}")
            print(f"Sayfa {page_number} tamamlandı. Toplam çekilen üniversite sayısı: {len(universities)}")

            # Check if the total number of universities has changed
            if len(universities) == last_count:
                same_count += 1
            else:
                same_count = 0

            last_count = len(universities)

            # Stop if the same count is reached 3 times
            if same_count >= 3:
                logging.info("No new data for 3 consecutive pages. Ending pagination.")
                break

            # Check for pagination (URL parameter)
            next_page_url = f"https://www.webometrics.org/t%C3%BCrkiye?page={page_number + 1}"
            logging.info(f"Checking next page: {next_page_url}")
            next_response = requests.get(next_page_url, headers=headers, timeout=10)
            time.sleep(random.uniform(1, 3))  # Throttle requests

            if next_response.status_code == 404:
                logging.info("Next page returned 404. Ending pagination.")
                break

            next_soup = BeautifulSoup(next_response.text, 'html.parser')
            next_table = next_soup.find('table')

            # Stop if no table is found on the next page
            if not next_table:
                logging.info("No table found on the next page. Ending pagination.")
                break

            target_url = next_page_url
            page_number += 1

        # Generate output filename
        now = datetime.datetime.now()
        filename = DATA_DIR / f"webometrics_{now.strftime('%Y_%m_%d_%H_%M')}.csv"

        # Write data to CSV
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=["No", "World Rank", "University Name", "Impact Rank", "Openness Rank", "Excellence Rank"])
            writer.writeheader()
            writer.writerows(universities)

        logging.info(f"Scraping completed successfully. {len(universities)} universities scraped.")
        print(f"Başarılı: {len(universities)} üniversite çekildi.")
        return f"Başarılı: {len(universities)} üniversite çekildi."

    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        return f"Request error: {e}"

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return f"Unexpected error: {e}"
  
import pandas as pd

# Function to convert CSV to Excel
def convert_csv_to_excel(csv_filename, excel_filename):
    """
    Converts a CSV file to an Excel file.

    Args:
        csv_filename (str): The name of the CSV file to convert.
        excel_filename (str): The name of the output Excel file.

    Returns:
        str: Success message with the Excel file name.
    """
    try:
        # Read the CSV file
        df = pd.read_csv(csv_filename)

        # Write to Excel file
        df.to_excel(excel_filename, index=False, engine='openpyxl')

        return f"Successfully converted {csv_filename} to {excel_filename}."
    except Exception as e:
        return f"Error during conversion: {e}"

# Example usage
# result = convert_csv_to_excel("webometrics_2026_03_17_12_00.csv", "webometrics_2026_03_17_12_00.xlsx")
# print(result)

if __name__ == "__main__":
    url = "https://www.webometrics.org/t%C3%BCrkiye"
    print("Scraping işlemi başlıyor, lütfen bekleyin...")
    sonuc = run_webometrics_scraper(url)
    print(sonuc)