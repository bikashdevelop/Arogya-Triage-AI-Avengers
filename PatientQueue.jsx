import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

export default function PatientQueue({ patientId }) {
  const [queueInfo, setQueueInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchQueue = async () => {
      try {
        const res = await axios.get(`${API_BASE}/api/queue/me/${patientId}`);
        setQueueInfo(res.data.data);
        setError('');
      } catch (err) {
        setError(err.response?.data?.detail || 'Not in queue');
      } finally {
        setLoading(false);
      }
    };

    fetchQueue();
    const interval = setInterval(fetchQueue, 15000);
    return () => clearInterval(interval);
  }, [patientId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-teal-400 text-lg">Loading your queue...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6 max-w-md text-center">
          <p className="text-red-400 mb-2">⚠️ {error}</p>
          <p className="text-slate-400 text-sm">Please check with the front desk.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 p-4 flex flex-col items-center">
      <div className="w-full max-w-md mb-6 text-center">
        <div className="inline-flex items-center gap-2 text-white">
          <div className="w-8 h-8 rounded-lg bg-teal-500 flex items-center justify-center font-bold text-slate-900">A</div>
          <span className="font-bold">AarogyaTriage</span>
        </div>
      </div>

      <div className="w-full max-w-md bg-slate-800 rounded-2xl border border-slate-700 p-6 shadow-2xl">
        <div className="text-center mb-6">
          <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Your Token</p>
          <p className="text-2xl font-bold text-teal-400 font-mono">{patientId}</p>
        </div>

        <div className="bg-gradient-to-br from-teal-500 to-teal-700 rounded-xl p-6 mb-4 text-center">
          <p className="text-teal-100 text-xs uppercase tracking-wider mb-2">Your Position</p>
          <p className="text-7xl font-extrabold text-white leading-none">{queueInfo.position_in_queue}</p>
          <p className="text-teal-100 text-xs mt-2">{queueInfo.patients_ahead} patients ahead</p>
        </div>

        <div className="bg-slate-900 rounded-xl p-4 mb-4 border border-slate-700 text-center">
          <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Estimated Wait</p>
          <p className="text-3xl font-bold text-white">~{queueInfo.estimated_wait_minutes} <span className="text-base text-slate-400">mins</span></p>
        </div>

        <div className="flex items-center justify-center gap-2 text-teal-400 text-sm">
          <div className="w-2 h-2 rounded-full bg-teal-400 animate-pulse"></div>
          <span>Please wait nearby. You will be called shortly.</span>
        </div>

        <p className="text-center text-slate-500 text-xs mt-4">Auto-refreshing every 15 seconds</p>
      </div>
    </div>
  );
}
