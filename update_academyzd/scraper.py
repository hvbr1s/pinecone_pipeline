import os
import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import shutil
from datetime import date

load_dotenv()
ZD_USER = os.getenv("ZD_USER")
ZD_PASSWORD = os.getenv("ZD_PASSWORD")
# Check to make sure neither environment variable is missing
assert ZD_USER and ZD_PASSWORD, "Make sure your environment variables are populated in .env"

def clean_and_save_html(article_url, output_folder):
    response = requests.get(article_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract the <article> tag
    article_tag = soup.find('article')

    if not article_tag:
        print(f"No <article> tag found in {article_url}")
        return

    # Create a new BeautifulSoup object for cleaned content
    cleaned_soup = BeautifulSoup('<html><head></head><body></body></html>', 'html.parser')

    # Add the URL to the <meta> section
    meta = cleaned_soup.new_tag('meta', content=article_url, attrs={'name': 'source-url'})
    cleaned_soup.head.append(meta)

    # Append the <article> tag to the cleaned_soup's <body> tag
    cleaned_soup.body.append(article_tag)

    # Save the cleaned HTML content to a file
    tokenized_url = article_url.split('/')
    output_filename = ''
    for token in tokenized_url[::-1]:
        if token:
            output_filename = token
            break
    filename = os.path.join(output_folder, f'{output_filename}.html')
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(str(cleaned_soup.prettify()))

def scrape_zendesk(output_folder: str, article_ids_to_skip: list = [], zendesk_base_url = 'https://ledger.zendesk.com', locale = 'en-us'):
    endpoint = f'{zendesk_base_url}/api/v2/help_center/{locale.lower()}/articles.json'
    while endpoint:
        response = requests.get(endpoint, auth=(ZD_USER, ZD_PASSWORD))
        assert response.status_code == 200, f'Failed to retrieve articles with error {response.status_code}'
        data = response.json()

        for article in data['articles']:
            if not article['body'] or article['draft'] or article['id'] in article_ids_to_skip:
                continue
            title = '<h1>' + article['title'] + '</h1>'
            url = article['html_url']
            meta_url = f'<meta name="source-url" content="{url}">'
            filename = f"zd_{article['id']}_{locale}.html"
            with open(os.path.join(output_folder, filename), mode='w', encoding='utf-8') as f:
                f.write(f'<!DOCTYPE html><html><head>{meta_url}</head><body>{title}\n{article["body"]}</body></html>')
            print(f"{article['id']} copied!")

        endpoint = data['next_page']

def scrape_urls(output_folder, url_file_path):
    # Read article URLs from the text file
    with open(url_file_path, 'r') as file:
        article_urls = [line.strip() for line in file]

    for url in article_urls:
        if url.startswith('https://www.ledger.com/academy/tutorials/') or url.startswith('#'):
            # Cut out all of the academy tutorials, and also any lines in the file that begin with #
            # (this will allow someone to comment out particular articles that are problematic if necessary)
            print(f"Skipping URL: {url}")
            continue
        clean_and_save_html(url, output_folder)

def scrape_other_articles(output_folder, source_directory):
    # get a list of files in the source directory
    files = os.listdir(source_directory)

    # loop through the files and copy them to the destination directory
    for file in files:
        src_file = os.path.join(source_directory, file)
        dst_file = os.path.join(output_folder, file)
        shutil.copy(src_file, dst_file)

    print("Other articles copied successfully.")

def run_scraper():
    # The folder containing the folder that contains this file.  i.e. the "pinecone_pipeline" folder
    pinecone_pipeline_root_directory = os.path.dirname(os.path.dirname(__file__))
    output_folder = os.path.join(pinecone_pipeline_root_directory, 'output_files', 'articles')

    # clear out any files that might be there, and create the folders if they don't exist.
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)

    scrape_zendesk(output_folder, article_ids_to_skip=[360015559320, 
                                                       9731871986077, 
                                                       9746372672925, 
                                                       360000105374, 
                                                       360006284494, 
                                                       7410961987869, 
                                                       360033473414
                                                       ])
    scrape_urls(output_folder, os.path.join(pinecone_pipeline_root_directory, 'url.txt'))
    scrape_other_articles(output_folder, os.path.join(pinecone_pipeline_root_directory, 'other_articles'))

if __name__ == "__main__":
    run_scraper()