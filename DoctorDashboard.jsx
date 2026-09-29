import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';
const api = axios.create({ baseURL: API_BASE_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('full_name');
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

// --- UPDATED FOR WHITE THEME ---
const getPriorityBadge = (priority) => {
  switch (priority) {
    case 'P1': return 'bg-red-50 text-red-700 border border-red-200';
    case 'P2': return 'bg-amber-50 text-amber-700 border border-amber-200';
    case 'P3': return 'bg-teal-50 text-teal-700 border border-teal-200';
    case 'P4': return 'bg-slate-100 text-slate-600 border border-slate-200';
    default: return 'bg-slate-100 text-slate-600 border border-slate-200';
  }
};

const getMewsBadge = (score) => {
  if (score >= 5) return 'text-red-600 font-bold';
  if (score >= 3) return 'text-amber-600 font-bold';
  return 'text-teal-600 font-bold';
};

const LoadingSpinner = () => (
  <div className="flex justify-center items-center p-8">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-500"></div>
  </div>
);

export default function DoctorDashboard() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  const [metrics, setMetrics] = useState({ total_active: 0, p1: 0, p2: 0 });
  const [queue, setQueue] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [networkError, setNetworkError] = useState('');
  const dutyOfficer = localStorage.getItem('full_name') || 'Dr. B. K. Jena';

  const [selectedRecordId, setSelectedRecordId] = useState(null);
  const [recordDetails, setRecordDetails] = useState(null);
  const [isModalLoading, setIsModalLoading] = useState(false);
  const [decisionForm, setDecisionForm] = useState({
    decision: 'approve',
    final_priority: 'P1',
    clinical_notes: '',
    action: 'admit'
  });
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);

  const fetchQueue = async () => {
    setIsLoading(true);
    setNetworkError('');
    try {
      const response = await api.get('/api/queue');
      if (response.data.success) {
        const rawMetrics = response.data.data.metrics;
        const normalizedMetrics = {
          total_active: rawMetrics.total_active || 0,
          p1: rawMetrics.p1 !== undefined ? rawMetrics.p1 : (rawMetrics.p1_critical || 0),
          p2: rawMetrics.p2 !== undefined ? rawMetrics.p2 : (rawMetrics.p2_urgent || 0),
        };
        setMetrics(normalizedMetrics);
        setQueue(response.data.data.queue || []);
      }
    } catch (error) {
      if (!error.response) setNetworkError('Backend offline. Please check your connection.');
      else if (error.response.status !== 401) setNetworkError('Failed to fetch queue data.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchQueue();
      const interval = setInterval(fetchQueue, 10000);
      return () => clearInterval(interval);
    }
  }, [token]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoggingIn(true);
    setLoginError('');
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    formData.append('grant_type', 'password');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/login`, formData);
      if (response.data.success) {
        localStorage.setItem('token', response.data.data.access_token);
        localStorage.setItem('full_name', response.data.data.full_name);
        setToken(response.data.data.access_token);
      }
    } catch (error) {
      if (error.response && error.response.status === 401) setLoginError('Invalid credentials');
      else if (!error.response) setLoginError('Backend offline. Cannot connect to server.');
      else setLoginError('An error occurred during login.');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('full_name');
    setToken(null);
  };

  const openReviewModal = async (recordId) => {
    setSelectedRecordId(recordId);
    setIsModalLoading(true);
    try {
      const response = await api.get(`/api/triage/${recordId}`);
      if (response.data.success) {
        setRecordDetails(response.data.data);
        setDecisionForm({
          decision: 'approve',
          final_priority: response.data.data.ai_priority || 'P1',
          clinical_notes: '',
          action: 'admit'
        });
      }
    } catch (error) {
      alert('Failed to fetch patient details.');
      setSelectedRecordId(null);
    } finally {
      setIsModalLoading(false);
    }
  };

  const closeReviewModal = () => {
    setSelectedRecordId(null);
    setRecordDetails(null);
    setSuccessMessage('');
  };

  const submitDecision = async (e) => {
    e.preventDefault();
    setIsSubmittingDecision(true);
    try {
      const response = await api.post(`/api/triage/${selectedRecordId}/decision`, decisionForm);
      if (response.data.success) {
        setSuccessMessage('Decision saved successfully! Patient removed from queue.');
        setTimeout(() => {
          closeReviewModal();
          fetchQueue();
        }, 1500);
      }
    } catch (error) {
      alert('Failed to submit decision. Please try again.');
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  // --- WHITE THEME LOGIN SCREEN ---
  if (!token) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl border border-slate-200 p-8 w-full max-w-md shadow-xl">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-slate-800 mb-2">AarogyaTriage</h1>
            <p className="text-slate-500">Doctor Dashboard Portal</p>
          </div>
          {loginError && <div className="bg-red-50 border border-red-200 text-red-600 p-3 rounded-lg mb-6 text-sm text-center">{loginError}</div>}
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Username</label>
              <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} className="w-full bg-slate-50 border border-slate-300 rounded-lg px-4 py-2 text-slate-800 focus:outline-none focus:border-teal-500" placeholder="e.g., dr_jena" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full bg-slate-50 border border-slate-300 rounded-lg px-4 py-2 text-slate-800 focus:outline-none focus:border-teal-500" placeholder="••••••••" required />
            </div>
            <button type="submit" disabled={isLoggingIn} className="w-full bg-teal-600 hover:bg-teal-700 disabled:bg-teal-300 text-white font-medium py-2.5 rounded-lg transition-colors mt-4 shadow-md">
              {isLoggingIn ? 'Authenticating...' : 'Login to Dashboard'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // --- WHITE THEME DASHBOARD ---
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 p-6">
      {successMessage && (
        <div className="fixed top-4 right-4 bg-emerald-500 text-white px-6 py-3 rounded-lg shadow-lg z-[100] animate-pulse">
          {successMessage}
        </div>
      )}

      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Doctor Review Dashboard</h1>
          <p className="text-slate-500 text-sm">Facility: Primary Health Centre (PHC)</p>
        </div>
        <div className="flex gap-3">
          <button onClick={fetchQueue} className="bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 px-4 py-2 rounded-lg text-sm transition-colors flex items-center gap-2 shadow-sm">Refresh Data</button>
          <button onClick={handleLogout} className="bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 px-4 py-2 rounded-lg text-sm transition-colors shadow-sm">Logout</button>
        </div>
      </div>

      {networkError && <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-lg mb-6">{networkError}</div>}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <p className="text-slate-500 text-sm mb-1 font-medium">Total Active</p>
          <p className="text-3xl font-bold text-slate-800">{metrics.total_active}</p>
        </div>
        <div className="bg-white rounded-xl border border-red-200 p-4 relative overflow-hidden shadow-sm">
          <div className="absolute top-0 right-0 w-16 h-16 bg-red-50 rounded-bl-full" />
          <p className="text-red-600 text-sm mb-1 font-medium">P1 Critical</p>
          <p className="text-3xl font-bold text-red-700">{metrics.p1}</p>
        </div>
        <div className="bg-white rounded-xl border border-amber-200 p-4 relative overflow-hidden shadow-sm">
          <div className="absolute top-0 right-0 w-16 h-16 bg-amber-50 rounded-bl-full" />
          <p className="text-amber-600 text-sm mb-1 font-medium">P2 Urgent</p>
          <p className="text-3xl font-bold text-amber-700">{metrics.p2}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <p className="text-slate-500 text-sm mb-1 font-medium">Duty Medical Officer</p>
          <p className="text-lg font-semibold text-slate-800 mt-2">{dutyOfficer}</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
          <h2 className="font-semibold text-slate-800">Active Triage Queue</h2>
          <span className="text-sm text-slate-500">Sorted by Priority</span>
        </div>
        {isLoading ? <LoadingSpinner /> : queue.length === 0 ? (
          <div className="p-8 text-center text-slate-500">No patients in queue</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 font-medium">Priority</th>
                  <th className="px-6 py-3 font-medium">Patient</th>
                  <th className="px-6 py-3 font-medium">Symptoms</th>
                  <th className="px-6 py-3 font-medium">MEWS</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {queue.map((record) => (
                  <tr key={record.record_id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-bold ${getPriorityBadge(record.priority)}`}>
                        {record.priority}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <p className="font-medium text-slate-800">{record.patient_id}</p>
                      <p className="text-xs text-slate-500">{record.demographics}</p>
                    </td>
                    <td className="px-6 py-4 max-w-xs truncate text-slate-600">{record.symptoms}</td>
                    <td className="px-6 py-4"><span className={getMewsBadge(record.mews)}>{record.mews}</span></td>
                    <td className="px-6 py-4"><span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded border border-slate-200">{record.status}</span></td>
                    <td className="px-6 py-4">
                      <button onClick={() => openReviewModal(record.record_id)} className="bg-teal-600 hover:bg-teal-700 text-white px-3 py-1.5 rounded text-xs font-medium transition-colors shadow-sm">Review</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedRecordId && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-slate-200 shadow-2xl relative">
            <div className="sticky top-0 bg-white border-b border-slate-200 p-4 flex justify-between items-center z-10">
              <h2 className="text-lg font-bold text-slate-800">Clinical Verification & Decision</h2>
              <button onClick={closeReviewModal} className="text-slate-400 hover:text-slate-700 text-xl font-bold">&times;</button>
            </div>
            {isModalLoading ? <LoadingSpinner /> : recordDetails ? (
              <div className="p-6 space-y-6">
                <div className="bg-amber-50 border border-amber-200 text-amber-700 p-3 rounded-lg text-xs font-medium">
                  <strong>STATUTORY NON-DIAGNOSTIC ADVISORY:</strong> CLINICAL ADVISORY ONLY. NOT A MEDICAL DIAGNOSIS.
                </div>
                <div className={`p-4 rounded-lg border ${getPriorityBadge(recordDetails.ai_priority)}`}>
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="text-sm opacity-80 font-medium">AI Suggested Priority</p>
                      <p className="text-2xl font-bold">{recordDetails.ai_priority} - {recordDetails.ai_priority === 'P1' ? 'EMERGENCY' : 'URGENT'}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm opacity-80 font-medium">MEWS Score</p>
                      <p className={`text-2xl font-bold ${getMewsBadge(recordDetails.mews_score)}`}>{recordDetails.mews_score}</p>
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div>
                      <h3 className="text-sm font-bold text-slate-700 mb-2 uppercase tracking-wider">AI Summary</h3>
                      <p className="text-slate-600 bg-slate-50 p-3 rounded border border-slate-200">{recordDetails.summary}</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-700 mb-2 uppercase tracking-wider">Vitals</h3>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="bg-slate-50 p-2 rounded border border-slate-200 text-slate-700">BP: {recordDetails.vitals.bp_systolic}/{recordDetails.vitals.bp_diastolic}</div>
                        <div className="bg-slate-50 p-2 rounded border border-slate-200 text-slate-700">HR: {recordDetails.vitals.heart_rate} bpm</div>
                        <div className="bg-slate-50 p-2 rounded border border-slate-200 text-slate-700">SpO2: {recordDetails.vitals.spo2}%</div>
                        <div className="bg-slate-50 p-2 rounded border border-slate-200 text-slate-700">Temp: {recordDetails.vitals.temperature_f}°F</div>
                        <div className="bg-slate-50 p-2 rounded border border-slate-200 text-slate-700">RR: {recordDetails.vitals.respiratory_rate}/min</div>
                      </div>
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-700 mb-2 uppercase tracking-wider">Timeline</h3>
                      <div className="space-y-3 border-l-2 border-slate-200 pl-4 ml-2">
                        {recordDetails.timeline?.map((item, idx) => (
                          <div key={idx} className="relative">
                            <div className="absolute -left-[21px] top-1 w-3 h-3 bg-teal-500 rounded-full border-2 border-white" />
                            <p className="text-xs text-teal-600 font-bold">{item.time}</p>
                            <p className="text-sm text-slate-600">{item.event}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="space-y-4">
                    <div className="bg-yellow-50 border border-yellow-200 p-3 rounded-lg">
                      <h3 className="text-xs font-bold text-yellow-700 mb-2 uppercase">Identified Clinical Gaps</h3>
                      <ul className="list-disc list-inside text-sm text-yellow-700 space-y-1">
                        {recordDetails.identified_gaps?.map((gap, idx) => <li key={idx}>{gap}</li>)}
                      </ul>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 p-3 rounded-lg">
                      <h3 className="text-xs font-bold text-slate-500 mb-2 uppercase">Follow-up Questions (Nurse)</h3>
                      <ul className="text-sm text-slate-600 space-y-2">
                        {recordDetails.follow_up_questions?.map((q) => (
                          <li key={q.id} className="flex gap-2"><span className="text-teal-600 font-bold">{q.id}:</span> {q.text}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="flex justify-between items-center text-xs text-slate-400">
                      <span>AI Source: <span className="text-teal-600 font-medium">{recordDetails.ai_source || 'groq'}</span></span>
                    </div>
                    <form onSubmit={submitDecision} className="bg-slate-50 p-4 rounded-lg border border-slate-200 mt-4">
                      <h3 className="text-sm font-bold text-slate-800 mb-3">Doctor's Clinical Decision</h3>
                      <div className="space-y-3">
                        <div>
                          <label className="block text-xs text-slate-500 mb-1 font-medium">Decision</label>
                          <select value={decisionForm.decision} onChange={(e) => setDecisionForm({...decisionForm, decision: e.target.value})} className="w-full bg-white border border-slate-300 rounded p-2 text-sm focus:border-teal-500 outline-none text-slate-700">
                            <option value="approve">Approve AI Triage</option>
                            <option value="override">Override Priority</option>
                          </select>
                        </div>
                        {decisionForm.decision === 'override' && (
                          <div>
                            <label className="block text-xs text-slate-500 mb-1 font-medium">Final Priority</label>
                            <select value={decisionForm.final_priority} onChange={(e) => setDecisionForm({...decisionForm, final_priority: e.target.value})} className="w-full bg-white border border-slate-300 rounded p-2 text-sm focus:border-teal-500 outline-none text-slate-700">
                              <option value="P1">P1 - Emergency</option>
                              <option value="P2">P2 - Urgent</option>
                              <option value="P3">P3 - Semi-Urgent</option>
                              <option value="P4">P4 - Routine</option>
                            </select>
                          </div>
                        )}
                        <div>
                          <label className="block text-xs text-slate-500 mb-1 font-medium">Action</label>
                          <select value={decisionForm.action} onChange={(e) => setDecisionForm({...decisionForm, action: e.target.value})} className="w-full bg-white border border-slate-300 rounded p-2 text-sm focus:border-teal-500 outline-none text-slate-700">
                            <option value="admit">Admit to Facility</option>
                            <option value="refer">Refer to Higher Center</option>
                            <option value="opd">Send to OPD</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs text-slate-500 mb-1 font-medium">Clinical Notes</label>
                          <textarea value={decisionForm.clinical_notes} onChange={(e) => setDecisionForm({...decisionForm, clinical_notes: e.target.value})} rows="3" className="w-full bg-white border border-slate-300 rounded p-2 text-sm focus:border-teal-500 outline-none resize-none text-slate-700" placeholder="Enter clinical notes or orders..."></textarea>
                        </div>
                      </div>
                      <button type="submit" disabled={isSubmittingDecision} className="w-full mt-4 bg-teal-600 hover:bg-teal-700 disabled:bg-teal-300 text-white font-medium py-2 rounded transition-colors shadow-sm">
                        {isSubmittingDecision ? 'Saving Decision...' : 'Submit Decision'}
                      </button>
                    </form>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-red-500">Failed to load details.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}