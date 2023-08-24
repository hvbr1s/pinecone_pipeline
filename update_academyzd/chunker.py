import hashlib
import json
import os
import re
from pathlib import Path
from bs4 import BeautifulSoup
from tqdm.auto import tqdm
from collections import Counter
import tiktoken

################### HC CHUNKER ######################
class Document:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata

def load_files(directory_path):
    docs = []
    for file_name in os.listdir(directory_path):
        file_path = os.path.join(directory_path, file_name)
        if os.path.isfile(file_path) and file_name.lower().endswith('.html'):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            soup = BeautifulSoup(content, "html.parser")
            url_meta_tag = soup.find("meta", attrs={"name": "source-url"})

            # Remove <span> tags from the content
            for span_tag in soup.find_all("span"):
                span_tag.unwrap()

            # Remove <path> tags from the content
            for path_tag in soup.find_all("path"):
                path_tag.decompose()

            title_tag = soup.find("h1")
            title = title_tag.text if title_tag else file_name

            if url_meta_tag:
                metadata = {"source-url": url_meta_tag.get("content"), "title": title}
            else:
                metadata = {"title": title}
            # Extract the text, discarding the HTML tags
            text_without_tags = soup.get_text()
            # Collapse any instances of multiple whitespaces down to a single whitespace
            text_with_collapsed_whitespace = re.sub(r'\s+', ' ', text_without_tags)
            docs.append(Document(page_content=text_with_collapsed_whitespace, metadata=metadata))
    return docs

class TextChunker:
    def __init__(self, chunk_size, chunk_overlap, length_function, separators, minimum_chunk_size=5):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.length_function = length_function
        self.separators = separators
        self.minimum_chunk_size = minimum_chunk_size

    def split_text(self, text: str):
        if self.length_function(text) <= self.chunk_size:
            return [text]

        for sep in self.separators:
            chunks = text.split(sep)
            if len(chunks) > 1:
                break

        if len(chunks) == 1:
            return [text]

        chunks_with_overlap = []
        current_chunk = ""
        for chunk in chunks:
            if self.length_function(f'{current_chunk} {chunk}') <= self.chunk_size:
                current_chunk = f'{current_chunk} {chunk}'
            else:
                if current_chunk:
                    chunks_with_overlap.append(current_chunk)
                current_chunk = chunk

        if current_chunk:
            chunks_with_overlap.append(current_chunk)

        # Create overlapping chunks
        overlapping_chunks = []
        for i in range(len(chunks_with_overlap)):
            current_chunk = chunks_with_overlap[i]
            if i < len(chunks_with_overlap) - 1:
                next_chunk = chunks_with_overlap[i + 1]
                overlap_start = max(len(current_chunk) - self.chunk_overlap, 0)
                current_chunk = f'{current_chunk} {next_chunk[:overlap_start]}'
            if len(current_chunk.split()) >= self.minimum_chunk_size:
                # only append the chunk if it has at least the minimum number of words to be considered relevant
                overlapping_chunks.append(current_chunk)

        return overlapping_chunks

# Define the length function
def tiktoken_len(text):
    # Initialize the tokenizer
    tokenizer = tiktoken.get_encoding('cl100k_base')
    tokens = tokenizer.encode(text, disallowed_special=())
    return len(tokens)

def count_chars_in_json(file_name):
    # Read the json file
    with open(file_name, 'r') as f:
        data = json.load(f)

    # Initialize a counter
    char_counts = Counter()

    # Check if data is a list
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                # Get the text
                text = item.get('text', '')

                # Count the characters and update the overall counter
                char_counts.update(Counter(text))

    return char_counts


def run_chunker():
    # Initialize the loader and load documents
    pinecone_pipeline_root_directory = os.path.dirname(os.path.dirname(__file__))
    output_folder = os.path.join(pinecone_pipeline_root_directory, 'output_files')
    scraped_articles_folder = os.path.join(output_folder, 'articles')
    output_filename = os.path.join(output_folder, 'output.json')
    docs = load_files(scraped_articles_folder)  
    print(len(docs))

    # Initialize the chunk list
    chunk_list = []

    # Initialize the text splitter
    text_splitter = TextChunker(
        chunk_size=500,
        chunk_overlap=20,  # number of tokens overlap between chunks
        length_function=tiktoken_len,
        separators=['\n\n', '\n', ' ', '']
    )

    # Process each document
    for doc in tqdm(docs):
        if 'source-url' in doc.metadata:
            url = doc.metadata['source-url']
            # Initialize the MD5 hash object
            md5 = hashlib.md5(url.encode('utf-8'))
            uid = md5.hexdigest()[:12]
        else:
            url = None
            uid = "unknown"

        chunks = text_splitter.split_text(doc.page_content)

        # Create an entry for each chunk
        for i, chunk in enumerate(chunks):
            chunk_list.append({
                'id': f'{uid}-{i}',
                'source': url,
                'title': doc.metadata.get("title"),
                'text': chunk
            })

    # Print the total number of chunks
    print(len(chunk_list))

    ########################## Save documents to a file###########################################
    with open(output_filename, 'w+', encoding='utf-8') as f:
        json.dump(chunk_list, f, ensure_ascii=False)

    # Character count
    counts = count_chars_in_json(output_filename)

    # Compute total number of characters
    total_chars = sum(counts.values())
    print(f'Total characters: {total_chars}')

if __name__ == "__main__":
    run_chunker()