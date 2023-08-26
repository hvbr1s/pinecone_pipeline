from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import time
import httpx
import subprocess
from tqdm import tqdm

app = FastAPI()

scripts_to_run_a = [
    
    "/home/danledger/pinecone_updater/update_academyzd/scraper.py",
    "/home/danledger/pinecone_updater/update_academyzd/chunker.py",
    "/home/danledger/pinecone_updater/update_academyzd/index_booter.py",
    "/home/danledger/pinecone_updater/update_academyzd/updater.py"
    
]

scripts_to_run_b = [
    
    "/home/danledger/pinecone_updater/update_hc/scraper_b.py",
    "/home/danledger/pinecone_updater/update_hc/chunker_b.py",
    "/home/danledger/pinecone_updater/update_hc/index_booter_b.py",
    "/home/danledger/pinecone_updater/update_hc/updater_b.py"
]

@app.get("/")
def read_root():
    return FileResponse("/home/danledger/pinecone_updater/templates/index.html")

@app.get("/fetch_data")
async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://knowlbot.aws.stg.ldg-tech.com/_index')
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="Unable to fetch data")

@app.post("/execute/{script_name}")
async def execute_script(script_name: str):
    if script_name == "orchestrator":
        return run_orchestrator(scripts_to_run_a)
    elif script_name == "orchestrator_b":
        return run_orchestrator(scripts_to_run_b)
    else:
        return {"error": "Invalid script name"}

def run_script(script_name):
    result = subprocess.run(['python', script_name], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"{script_name} ran successfully!")
        print(result.stdout)
    else:
        print(f"Error running {script_name}")
        print(result.stderr)
        exit(1)

def run_orchestrator(scripts_to_run):
    for script in tqdm(scripts_to_run, desc="Running scripts", unit="script"):
        run_script(script)
    return {"status": f"All scripts in {scripts_to_run} executed successfully"}

# start command local: uvicorn server:app --reload
