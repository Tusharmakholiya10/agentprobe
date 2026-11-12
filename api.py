import sqlite3
import subprocess
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    conn = sqlite3.connect("agentprobe.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.post("/api/campaign/run")
async def run_campaign(background_tasks: BackgroundTasks):
    def run_probe():
        try:
            # Updated to run your local runner.py file directly
            subprocess.run("python runner.py", shell=True, check=True)
        except Exception as e:
            print(f"Error running campaign: {e}")

    background_tasks.add_task(run_probe)
    return {"status": "Campaign successfully started"}

@app.get("/api/campaign/results")
async def get_results():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Updated to use total_cost and total_tokens
        cursor.execute("""
            SELECT COUNT(*) as total_runs, 
                   SUM(total_cost) as total_cost, 
                   SUM(total_tokens) as total_tokens 
            FROM traces
        """)
        summary_row = cursor.fetchone()
        
        # Updated to use total_cost and total_tokens
        cursor.execute("""
            SELECT run_id, task_id, total_cost, total_tokens 
            FROM traces 
            ORDER BY id DESC 
            LIMIT 50
        """)
        traces = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "summary": {
                "total_runs": summary_row["total_runs"] or 0,
                "total_cost": round(summary_row["total_cost"] or 0, 5),
                "total_tokens": summary_row["total_tokens"] or 0
            },
            "traces": traces
        }
    except Exception as e:
        print(f"Database error: {e}")
        return {
            "summary": {"total_runs": 0, "total_cost": 0.0, "total_tokens": 0},
            "traces": []
        }