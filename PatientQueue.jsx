import React, { useState, useEffect } from 'react';

export default function PatientQueue({ patientId }) {
  const [queueInfo, setQueueInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchQueue = () => {
      // MOCK MODE
      setQueueInfo({
        position: 3,
        estimatedWaitMinutes: 24,
        status: 'waiting',
        priority: 'P3',
        nowServing: 'PAT-20260918-002',
        totalInQueue: 8
      });
      setLoading(false);
    };
    fetchQueue();
    const interval = setInterval(fetchQueue, 10000);
    return () => clearInterval(interval);
  }, [patientId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-teal-400 text-lg">Loading your queue...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 p-4 flex flex-col items-center">
      {/* Header */}
      <div className="w-full max-w-md mb-6 text-center">
        <div className="inline-flex items-center gap-2 text-white">
          <div className="w-8 h-8 rounded-lg bg-teal-500 flex items-center justify-center font-bold text-slate-900">A</div>
          <span className="font-bold">AarogyaTriage</span>
        </div>
      </div>

      <div className="w-full max-w-md bg-slate-800 rounded-2xl border border-slate-700 p-6 shadow-2xl">
        
        {/* Patient Token */}
        <div className="text-center mb-6">
          <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Your Token</p>
          <p className="text-2xl font-bold text-teal-400 font-mono">{patientId}</p>
        </div>

        {/* Position Card */}
        <div className="bg-gradient-to-br from-teal-500 to-teal-700 rounded-xl p-6 mb-4 text-center">
          <p className="text-teal-100 text-xs uppercase tracking-wider mb-2">Your Position</p>
          <p className="text-7xl font-extrabold text-white leading-none">{queueInfo.position}</p>
          <p className="text-teal-100 text-xs mt-2">out of {queueInfo.totalInQueue} in queue</p>
        </div>

        {/* Wait Time */}
        <div className="bg-slate-900 rounded-xl p-4 mb-4 border border-slate-700 text-center">
          <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Estimated Wait</p>
          <p className="text-3xl font-bold text-white">~{queueInfo.estimatedWaitMinutes} <span className="text-base text-slate-400">mins</span></p>
        </div>

        {/* Now Serving */}
        <div className="bg-slate-900 rounded-xl p-4 mb-6 border border-slate-700 text-center">
          <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Now Serving</p>
          <p className="text-lg font-bold text-teal-400 font-mono">{queueInfo.nowServing}</p>
        </div>

        {/* Live indicator */}
        <div className="flex items-center justify-center gap-2 text-teal-400 text-sm">
          <div className="w-2 h-2 rounded-full bg-teal-400 animate-pulse"></div>
          <span>Please wait nearby. You will be called shortly.</span>
        </div>

        <p className="text-center text-slate-500 text-xs mt-4">
          Auto-refreshing every 10 seconds
        </p>
      </div>

      <p className="text-slate-500 text-xs mt-6 text-center max-w-md">
        Keep this page open. Your position updates automatically.
      </p>
    </div>
  );
}
