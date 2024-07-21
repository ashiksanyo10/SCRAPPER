import pandas as pd
from bs4 import BeautifulSoup
from helium import start_chrome, go_to, write, press, find_all
import time
from datetime import datetime

def get_movie_details(movie_name, director_name):
    base_url = "https://www.classificationoffice.govt.nz/find-a-rating/?search="
    search_url = base_url + movie_name.replace(" ", "+")
    
    # Start Helium browser session
    browser = start_chrome(search_url, headless=True)
    
    time.sleep(5)  # Wait for the page to load

    # Get the page source and parse it with BeautifulSoup
    page_source = browser.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    
    # Find all movie listings on the page
    listings = soup.find_all('div', {'data-listing': ''})
    
    # Prepare a dictionary to store the details
    details = {
        'movie_name': movie_name,
        'director_name': director_name,
        'classification': 'N/A',
        'release_year': 'N/A',
        'run_time': 'N/A',
        'label_issued_by': 'N/A'
    }

    found = False

    for listing in listings:
        title_tag = listing.find('h3', class_='h2')
        if title_tag is None:
            continue  # Skip this listing if the title tag is not found
        
        title = title_tag.get_text(strip=True)
        
        director_tag = listing.find('p', class_='small')
        if director_tag is None:
            continue  # Skip this listing if the director tag is not found
        
        director_text = director_tag.get_text(strip=True)
        if director_name in director_text:
            found = True
            
            # Extract classification
            classification_tag = listing.find('p', class_='large mb-2')
            if classification_tag:
                details['classification'] = classification_tag.get_text(strip=True)
            else:
                print("Classification tag not found for movie:", movie_name)
            
            # Extract the release year and runtime
            table = listing.find('table', class_='rating-result-table')
            if table:
                lines = table.get_text(separator="\n", strip=True).split('\n')
                for i, line in enumerate(lines):
                    if 'Running time:' in line:
                        details['run_time'] = lines[i + 1].strip()
                    elif 'Label issued by:' in line:
                        details['label_issued_by'] = lines[i + 1].strip()
            
            # Extract release year from the director text
            parts = director_text.split(',')
            if len(parts) > 1:
                details['release_year'] = parts[0].strip()
            
            break
    
    if not found:
        details = {
            'movie_name': movie_name,
            'director_name': director_name,
            'classification': 'N/A',
            'release_year': 'N/A',
            'run_time': 'N/A',
            'label_issued_by': 'N/A'
        }
    
    return details

# Read the Excel file
excel_file = "Book1-sampleRun.xlsx"  # Update with your Excel file path
df = pd.read_excel(excel_file)

# Prepare a list to store the results
results = []

# Iterate over each row in the DataFrame
for index, row in df.iterrows():
    movie_name = row['Movie_name']
    director_name = row['Director_name']
    
    movie_details = get_movie_details(movie_name, director_name)
    results.append(movie_details)

# Create a DataFrame from the results
results_df = pd.DataFrame(results)

# Get the current date and format the filename
date_str = datetime.now().strftime("%Y-%m-%d")
filename = f"{date_str}-NewWebsite1.xlsx"

# Save the DataFrame to an Excel file
results_df.to_excel(filename, index=False)

print(f"Movie details have been saved to {filename}")
