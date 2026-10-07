import React, { useState, useEffect } from 'react';
import api from './api/client';
import DoctorReview from './DoctorReview';

const TRIAGE_META = {
  P1: { label: 'Emergency', wait: '0–5 min', badge: 'bg-red-100 text-red-800 border border-red-300', card: 'border-red-300 bg-red-50', dot: 'bg-red-500', count: 'text-red-700', mts: 'MTS Red · AIIMS Red' },
  P2: { label: 'Very Urgent', wait: '10–30 min', badge: 'bg-orange-100 text-orange-800 border border-orange-300', card: 'border-orange-300 bg-orange-50', dot: 'bg-orange-500', count: 'text-orange-700', mts: 'MTS Orange · AIIMS Yellow' },
  P3: { label: 'Urgent', wait: '30–60 min', badge: 'bg-yellow-100 text-yellow-900 border border-yellow-300', card: 'border-yellow-300 bg-yellow-50', dot: 'bg-yellow-500', count: 'text-yellow-800', mts: 'MTS Yellow · AIIMS Yellow' },
  P4: { label: 'Standard', wait: '120 min', badge: 'bg-green-100 text-green-800 border border-green-300', card: 'border-green-300 bg-green-50', dot: 'bg-green-500', count: 'text-green-700', mts: 'MTS Green · AIIMS Green' },
};

export default function DoctorDashboard() {
  const [isLoggedIn, setIsLoggedIn] = useState(!!sessionStorage.getItem('access_token'));
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');

  const [queue, setQueue] = useState([]);
  const [metrics, setMetrics] = useState({ total_active: 0, p1: 0, p2: 0, p3: 0, p4: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('ALL');
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const [reviewRecordId, setReviewRecordId] = useState(null);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    formData.append('grant_type', 'password');

    try {
      const res = await api.post('/api/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      sessionStorage.setItem('access_token', res.data.access_token);
      sessionStorage.setItem('role', res.data.role);
      sessionStorage.setItem('full_name', res.data.full_name);

      if (res.data.role !== 'doctor') {
        setLoginError('This account does not have doctor access');
        sessionStorage.clear();
        return;
      }
      setIsLoggedIn(true);
    } catch (err) {
      setLoginError(err.response?.data?.detail || 'Login failed.');
    }
  };

  const handleLogout = () => {
    sessionStorage.clear();
    window.location.href = '/';
  };

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/queue');
      const q = res.data.data.queue || [];
      setQueue(q);
      setMetrics({
        total_active: q.length,
        p1: q.filter((r) => r.priority === 'P1').length,
        p2: q.filter((r) => r.priority === 'P2').length,
        p3: q.filter((r) => r.priority === 'P3').length,
        p4: q.filter((r) => r.priority === 'P4').length,
      });
      setLastRefresh(new Date());
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load queue');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isLoggedIn) return;
    fetchQueue();
    const interval = setInterval(fetchQueue, 5000);
    return () => clearInterval(interval);
  }, [isLoggedIn]);

  const filteredQueue = filter === 'ALL' ? queue : queue.filter((r) => r.priority === filter);

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-teal-600 text-white text-2xl font-bold mb-3">
              A
            </div>
            <h1 className="text-2xl font-bold text-slate-900">AarogyaTriage</h1>
            <p className="text-sm text-slate-500 mt-1">Medical Officer Console</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Username</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  placeholder="dr_jena"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
              {loginError && (
                <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {loginError}
                </div>
              )}
              <button
                type="submit"
                className="w-full bg-teal-600 hover:bg-teal-700 text-white font-medium rounded-lg py-2.5 text-sm"
              >
                Sign in
              </button>
            </form>
          </div>
          <p className="text-xs text-slate-500 text-center mt-4">
            Demo credentials: dr_jena / doctor123
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center font-bold text-sm">
              A
            </div>
            <div>
              <h1 className="text-sm font-semibold text-slate-900">AarogyaTriage</h1>
              <p className="text-xs text-slate-500">
                {sessionStorage.getItem('full_name') || 'Medical Officer'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden md:flex items-center gap-1.5 text-xs font-medium text-emerald-600">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Live · refreshed {lastRefresh.toLocaleTimeString()}
            </span>
            <button
              onClick={fetchQueue}
              className="text-xs font-medium text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-md hover:bg-slate-100"
            >
              Refresh
            </button>
            <button
              onClick={handleLogout}
              className="text-xs font-medium text-slate-600 hover:text-red-600 px-3 py-1.5 rounded-md hover:bg-slate-100"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-center gap-2 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-5">
          <span className="font-medium">Non-diagnostic triage support</span>
          <span className="text-amber-700">·</span>
          <span>All AI outputs require physician verification</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {['P1', 'P2', 'P3', 'P4'].map((p) => {
            const m = TRIAGE_META[p];
            return (
              <div key={p} className={`border-2 rounded-lg p-4 ${m.card}`}>
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${m.dot}`}></span>
                  <span className="text-xs font-bold text-slate-800">{p}</span>
                  <span className="text-xs text-slate-600">· {m.label}</span>
                </div>
                <p className={`text-4xl font-bold mt-3 ${m.count}`}>
                  {metrics[p.toLowerCase()] || 0}
                </p>
                <p className="text-[10px] text-slate-600 mt-1">Wait target: {m.wait}</p>
              </div>
            );
          })}
        </div>

        <div className="flex items-center gap-2 mb-4 flex-wrap">
          {['ALL', 'P1', 'P2', 'P3', 'P4'].map((tab) => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`text-xs font-medium px-3 py-1.5 rounded-md border transition-colors ${
                filter === tab
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
              }`}
            >
              {tab === 'ALL'
                ? `All (${metrics.total_active})`
                : `${tab} (${metrics[tab.toLowerCase()] || 0})`}
            </button>
          ))}
        </div>

        {error && (
          <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-4">
            {error}
          </div>
        )}

        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-200 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Active Triage Queue</h2>
            <span className="text-xs text-slate-500">Sorted by Manchester priority</span>
          </div>

          {loading && queue.length === 0 ? (
            <div className="py-16 text-center text-sm text-slate-500">Loading queue…</div>
          ) : filteredQueue.length === 0 ? (
            <div className="py-16 text-center text-sm text-slate-500">
              No patients in this category
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs font-medium text-slate-500 uppercase tracking-wide bg-slate-50">
                  <th className="px-5 py-3 w-32">Priority</th>
                  <th className="px-5 py-3">Patient</th>
                  <th className="px-5 py-3">Chief complaint</th>
                  <th className="px-5 py-3 w-20">MEWS</th>
                  <th className="px-5 py-3 w-32">Status</th>
                  <th className="px-5 py-3 w-24 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredQueue.map((r) => {
                  const m = TRIAGE_META[r.priority] || TRIAGE_META.P4;
                  return (
                    <tr key={r.record_id} className="hover:bg-slate-50">
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${m.dot}`}></span>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${m.badge}`}>
                            {r.priority}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-400 mt-1">{m.label}</p>
                      </td>
                      <td className="px-5 py-4">
                        <div className="text-sm font-medium text-slate-900">
                          {r.patient_id}
                        </div>
                        <div className="text-xs text-slate-500 mt-0.5">{r.demographics}</div>
                        {r.allergies && r.allergies.toLowerCase() !== 'none' && (
                          <div className="text-[10px] text-red-600 font-semibold mt-0.5">
                            ⚠️ {r.allergies}
                          </div>
                        )}
                      </td>
                      <td className="px-5 py-4">
                        <p className="text-sm text-slate-700 max-w-md truncate">{r.symptoms}</p>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          {r.assigned_department || 'General OPD'}
                        </p>
                      </td>
                      <td className="px-5 py-4">
                        <span className="text-sm font-medium text-slate-700">{r.mews}</span>
                      </td>
                      <td className="px-5 py-4">
                        <span className="text-xs text-slate-500">{r.status}</span>
                      </td>
                      <td className="px-5 py-4 text-right">
                        <button
                          onClick={() => setReviewRecordId(r.record_id)}
                          className="text-xs font-medium text-teal-700 hover:text-teal-900 border border-teal-200 hover:border-teal-300 bg-teal-50 px-3 py-1.5 rounded-md"
                        >
                          Review
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </main>

      {reviewRecordId && (
        <DoctorReview
          recordId={reviewRecordId}
          onClose={() => setReviewRecordId(null)}
          onSaved={fetchQueue}
        />
      )}
    </div>
  );
}