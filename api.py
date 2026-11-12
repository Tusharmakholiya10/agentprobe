import sqlite3
import subprocess
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

# 1. Initialize FastAPI
app = FastAPI()

# 2. Add CORS Middleware (Crucial for Vercel -> Render connection)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows any frontend domain to connect
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST)
    allow_headers=["*"],  # Allows all headers
)

# 3. Database Connection Helper
def get_db_connection():
    # Update "agentprobe.db" if your database file is named differently!
    conn = sqlite3.connect("agentprobe.db")
    conn.row_factory = sqlite3.Row
    return conn

# 4. Trigger Campaign Endpoint
@app.post("/api/campaign/run")
async def run_campaign(background_tasks: BackgroundTasks):
    def run_probe():
        try:
            # Run the CLI command directly
            subprocess.run("agentprobe run", shell=True, check=True)
        except Exception as e:
            print(f"Error running campaign: {e}")

    background_tasks.add_task(run_probe)
    return {"status": "Campaign successfully started"}

# 5. Retrieve Results Endpoint
@app.get("/api/campaign/results")
async def get_results():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch high-level summary
        # Update table/column names if your schema is different
        cursor.execute("""
            SELECT COUNT(*) as total_runs, 
                   SUM(cost) as total_cost, 
                   SUM(tokens) as total_tokens 
            FROM traces
        """)
        summary_row = cursor.fetchone()
        
        # Fetch individual trace logs
        cursor.execute("""
            SELECT run_id, task_id, cost as total_cost, tokens as total_tokens 
            FROM traces 
            ORDER BY id DESC 
            LIMIT 50
        """)
        traces = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        # Return exact JSON structure expected by the Next.js dashboard
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
        # Failsafe return if the database is empty or doesn't exist yet
        return {
            "summary": {"total_runs": 0, "total_cost": 0.0, "total_tokens": 0},
            "traces": []
        }