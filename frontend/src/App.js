import { useState, useCallback, useRef, useEffect } from "react";
import "@/App.css";
import axios from "axios";
import { toast } from "sonner";
import { Dashboard } from "@/components/Dashboard";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [results, setResults] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const pollingRef = useRef(null);

  useEffect(() => {
    axios.get(`${API}/accounts`).then((res) => {
      const list = res.data.accounts || [];
      setAccounts(list);
      if (list.length === 1) setSelectedAccountId(list[0].id);
    }).catch((e) => console.error("Failed to fetch accounts:", e));
  }, []);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const fetchResults = useCallback(async (jid) => {
    try {
      const response = await axios.get(`${API}/results/${jid}`);
      setResults(response.data);
    } catch (e) {
      console.error("Failed to fetch results:", e);
    }
  }, []);

  const pollStatus = useCallback((jid) => {
    const poll = async () => {
      try {
        const response = await axios.get(`${API}/status/${jid}`);
        setStatus(response.data);

        if (response.data.completed) {
          stopPolling();
          setIsRunning(false);
          await fetchResults(jid);
        }
      } catch (e) {
        console.error("Polling error:", e);
      }
    };

    poll();
    pollingRef.current = setInterval(poll, 3000);
  }, [stopPolling, fetchResults]);

  const runAnalysis = useCallback(async () => {
    if (!selectedAccountId) {
      toast.error("Please select a LinkedIn account first");
      return;
    }
    setIsRunning(true);
    setError(null);
    setStatus(null);
    setResults(null);
    setJobId(null);

    try {
      const response = await axios.post(`${API}/run-analysis`, { account_id: selectedAccountId });
      const jid = response.data.job_id;
      setJobId(jid);
      toast.success("Analysis started");
      pollStatus(jid);
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || "Failed to start analysis";
      setError(msg);
      setIsRunning(false);
      toast.error(msg);
    }
  }, [selectedAccountId, pollStatus]);

  const retryLeads = useCallback(async (leadNames) => {
    setIsRunning(true);
    setError(null);
    try {
      await axios.post(`${API}/retry-leads`, { job_id: jobId, lead_names: leadNames });
      toast.success(`Retrying ${leadNames.length} lead(s)...`);
      pollStatus(jobId);
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || "Retry failed";
      setError(msg);
      setIsRunning(false);
      toast.error(msg);
    }
  }, [jobId, pollStatus]);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  return (
    <div className="min-h-screen bg-[#f8fafc]">
      <Dashboard
        isRunning={isRunning}
        status={status}
        results={results}
        error={error}
        onRunAnalysis={runAnalysis}
        onRetryLeads={retryLeads}
        jobId={jobId}
        accounts={accounts}
        selectedAccountId={selectedAccountId}
        onAccountChange={setSelectedAccountId}
      />
    </div>
  );
}

export default App;
