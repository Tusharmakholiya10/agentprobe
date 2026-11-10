"use client";

import { useState, useEffect } from "react";
import { Play, BarChart3, ShieldAlert, Activity } from "lucide-react";

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchResults = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/campaign/results");
      const json = await res.json();
      if (!json.error) setData(json);
    } catch (err) {
      console.error("Failed to fetch results", err);
    }
  };

  useEffect(() => {
    fetchResults();
  }, []);

  const runCampaign = async () => {
    setLoading(true);
    try {
      await fetch("http://127.0.0.1:8000/api/campaign/run", { method: "POST" });
      // Poll for results after a few seconds
      setTimeout(async () => {
        await fetchResults();
        setLoading(false);
      }, 3000);
    } catch (err) {
      console.error("Failed to run campaign", err);
      setLoading(false);
    }
  };

  return (
    <main className="p-8 min-h-screen bg-gray-50 text-gray-900">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <ShieldAlert className="text-red-500" /> 
            AgentProbe Dashboard
          </h1>
          <button 
            onClick={runCampaign}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium flex items-center gap-2 disabled:opacity-50"
          >
            {loading ? <Activity className="animate-spin" /> : <Play size={18} />}
            {loading ? "Running Campaign..." : "Run Campaign"}
          </button>
        </div>

        {data && data.summary && (
          <div className="grid grid-cols-3 gap-6 mb-8">
            <div className="bg-white p-6 rounded-xl shadow-sm border">
              <p className="text-sm text-gray-500 font-medium">Total Runs</p>
              <p className="text-3xl font-bold mt-2">{data.summary.total_runs}</p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow-sm border">
              <p className="text-sm text-gray-500 font-medium">Total Cost</p>
              <p className="text-3xl font-bold mt-2">${data.summary.total_cost}</p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow-sm border">
              <p className="text-sm text-gray-500 font-medium">Total Tokens</p>
              <p className="text-3xl font-bold mt-2">{data.summary.total_tokens}</p>
            </div>
          </div>
        )}

        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <div className="p-6 border-b bg-gray-50">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <BarChart3 size={20} /> Trace Logs
            </h2>
          </div>
          <div className="p-6 overflow-x-auto">
            {data && data.traces ? (
              <table className="w-full text-left">
                <thead>
                  <tr className="text-sm text-gray-500 border-b">
                    <th className="pb-3">Run ID</th>
                    <th className="pb-3">Task ID</th>
                    <th className="pb-3 text-right">Cost</th>
                    <th className="pb-3 text-right">Tokens</th>
                  </tr>
                </thead>
                <tbody>
                  {data.traces.map((trace: any, i: number) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="py-4 font-mono text-xs text-blue-600">{trace.run_id.slice(0,12)}...</td>
                      <td className="py-4">{trace.task_id}</td>
                      <td className="py-4 text-right">${trace.total_cost.toFixed(5)}</td>
                      <td className="py-4 text-right">{trace.total_tokens}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-gray-500 text-center py-8">No traces found. Run a campaign!</p>
            )}
          </div>
        </div>
      </div>
    </main>
  );
} 