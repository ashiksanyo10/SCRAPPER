import time
import logging
from flask import Flask, request, send_file, jsonify
from helium import start_chrome, write, click, S, find_all, get_driver
from bs4 import BeautifulSoup
import pandas as pd
from openpyxl import load_workbook

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

# File paths
output_file_path = 'rating.xlsx'

def wait_for_element(selector, timeout=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if selector.exists():
            return True
        time.sleep(0.5)
    return False

def nz_title_check(movie_names):
    browser = start_chrome('https://www.fvlb.org.nz/', headless=True)

    all_movies_details = []

    for i, movie_name in enumerate(movie_names):
        if i > 0 and i % 10 == 0:
            logging.debug("1 minute of batch break - please wait")
            time.sleep(60)  # 1 minute delay after every batch of 10 movies

        search_title_input = S("#fvlb-input")
        exact_match_checkbox = S("#ExactSearch")
        search_button = S(".submitBtn")

        write(movie_name, into=search_title_input)
        click(exact_match_checkbox)
        click(search_button)

        if not wait_for_element(S('.result-title')):
            all_movies_details.append({
                'is_listed': "No",
                'title_name': movie_name,
                'dir_name': 'N/A',
                'MR': 'N/A',
                'CD': 'N/A',
                'runtime': 'N/A'
            })
            continue

        time.sleep(3)  # 3 seconds delay between each movie search

        movie_links = find_all(S('.result-title'))
        exact_match_found = False

        for link in movie_links:
            if link.web_element.text.strip() == movie_name:
                click(link)
                exact_match_found = True
                break

        if not exact_match_found:
            write('', into=search_title_input)
            click(search_button)

            if not wait_for_element(S('.result-title')):
                all_movies_details.append({
                    'title_name': movie_name,
                    'dir_name': 'N/A',
                    'MR': 'N/A',
                    'CD': 'N/A',
                    'runtime': 'N/A'
                })
                continue

            time.sleep(3)  # 3 seconds delay between each movie search

            movie_links = find_all(S('.result-title'))

            for link in movie_links:
                if movie_name.lower() in link.web_element.text.strip().lower():
                    click(link)
                    exact_match_found = True
                    break

        if not exact_match_found:
            all_movies_details.append({
                'title_name': movie_name,
                'dir_name': 'N/A',
                'MR': 'N/A',
                'CD': 'N/A',
                'runtime': 'N/A'
            })
            continue

        if not wait_for_element(S('h1')):
            all_movies_details.append({
                'title_name': movie_name,
                'dir_name': 'N/A',
                'MR': 'N/A',
                'CD': 'N/A',
                'runtime': 'N/A'
            })
            continue

        time.sleep(1)

        page_source = get_driver().page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        movie_details = {}
        title_element = soup.find('h1')
        movie_details['title_name'] = title_element.text.strip() if title_element else 'N/A'

        director_element = soup.find('div', class_='film-director')
        movie_details['dir_name'] = director_element.text.strip().replace('Directed by ', '') if director_element else 'N/A'

        classification_element = soup.find('div', class_='film-classification')
        if classification_element:
            classification_text = classification_element.text.strip()
            movie_details['MR'] = classification_text.split(' ')[0] if classification_text else 'N/A'
            movie_details['CD'] = ' '.join(classification_text.split(' ')[1:]) if classification_text else 'N/A'
        else:
            movie_details['MR'] = 'N/A'
            movie_details['CD'] = 'N/A'

        runtime_element = soup.find_all('div', class_='film-approved')[1]
        runtime = runtime_element.text.strip().replace('This title has a runtime of ', '').replace(' minutes.', '')
        movie_details['runtime'] = runtime if runtime else 'N/A'

        all_movies_details.append(movie_details)

        browser.back()

    get_driver().quit()

    return all_movies_details

@app.route('/')
def index():
    return send_file('index1.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        file = request.files['file']
        if file.filename.endswith('.xlsx'):
            # Process the Excel file
            df = pd.read_excel(file)
            movie_names = df['title_name'].tolist()  # Adjust based on your Excel structure
            scraped_data = nz_title_check(movie_names)
            output_df = pd.DataFrame(scraped_data)
            output_df.to_excel(output_file_path, index=False)
            return jsonify({'download_url': '/download'})
        else:
            return jsonify({'error': 'Invalid file format, must be .xlsx'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process', methods=['POST'])
def process_movie_names():
    try:
        data = request.json
        movie_names = data.get('movieNames', [])
        if not movie_names:
            return jsonify({'error': 'No movie names provided'}), 400

        scraped_data = nz_title_check(movie_names)
        output_df = pd.DataFrame(scraped_data)
        output_df.to_excel(output_file_path, index=False)
        return jsonify({'download_url': '/download'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download')
def download_file():
    return send_file(output_file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
