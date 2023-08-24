import time
import json
import os
from dotenv import load_dotenv
import openai
from tqdm.auto import tqdm
import os
from pathlib import Path
import pinecone
import shutil

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

def read_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    return json_data

def run_updater(index_name = 'hc'):
    pinecone_pipeline_root_directory = os.path.dirname(os.path.dirname(__file__))
    output_folder = os.path.join(pinecone_pipeline_root_directory, 'output_files')
    json_file_path = os.path.join(output_folder, 'output.json')
    documents = read_json_file(json_file_path)

    texts = [doc['text'] for doc in documents]


    # initialize connection to pinecone
    pinecone.init(
        api_key=os.getenv('PINECONE_API_KEY'),
        environment=os.getenv('PINECONE_ENVIRONMENT')
    )


    # connect to index
    index = pinecone.Index(index_name)

    # define embed model
    embed_model = "text-embedding-ada-002"

    batch_size = 100  # how many embeddings we create and insert at once

    for i in tqdm(range(0, len(documents), batch_size)):
        # find end of batch
        i_end = min(len(documents), i+batch_size)
        meta_batch = documents[i:i_end]
        # get ids
        ids_batch = [x['id'] for x in meta_batch]
        # get texts to encode
        texts = [x['text'] for x in meta_batch]
        # create embeddings (try-except added to avoid RateLimitError)
        try:
            res = openai.Embedding.create(input=texts, engine=embed_model)
        except:
            done = False
            while not done:
                time.sleep(5)
                try:
                    res = openai.Embedding.create(input=texts, engine=embed_model)
                    done = True
                except:
                    pass
        embeds = [record['embedding'] for record in res['data']]
        # create metadata
        meta_batch = [{'text': x['text'], 'title': x['title'], 'source': x['source']} for x in meta_batch]
        # format the vectors to upsert
        to_upsert = [{'id': id_, 'values': embed, 'metadata': meta} for id_, embed, meta in zip(ids_batch, embeds, meta_batch)]
        # upsert to Pinecone
        index.upsert(vectors=to_upsert)

    print('Database updated!')
    # Cleaning up
    os.remove(json_file_path)
    shutil.rmtree(output_folder)

if __name__ == "__main__":
    run_updater()