import subprocess
from tqdm import tqdm

scripts_to_run = [
    
    "/home/danledger/pinecone_updater/update_academyzd/index_booter.py", 
    "/home/danledger/pinecone_updater/update_academyzd/scraper.py", 
    "/home/danledger/pinecone_updater/update_academyzd/chunker.py", 
    "/home/danledger/pinecone_updater/update_academyzd/updater.py"
    
]


def run_script(script_name):
    result = subprocess.run(['python', script_name], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"{script_name} ran successfully!")
        print(result.stdout)
    else:
        print(f"Error running {script_name}")
        print(result.stderr)
        exit(1)

if __name__ == "__main__":
    for script in tqdm(scripts_to_run, desc="Running scripts", unit="script"):
        run_script(script)

print('Update complete!')