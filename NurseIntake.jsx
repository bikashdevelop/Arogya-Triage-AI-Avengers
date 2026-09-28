import React, { useState, useRef } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import api from './api/client';

export default function NurseIntake() {
  const [isLoggedIn, setIsLoggedIn] = useState(!!sessionStorage.getItem('access_token'));
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [activeTab, setActiveTab] = useState('intake');
  const [facility, setFacility] = useState('PHC');
  const [language, setLanguage] = useState('English');

  const [form, setForm] = useState({
    patient_name: '', patient_sex: 'Male', patient_age: '', patient_id: '',
    symptoms: '',
    bpSystolic: '', bpDiastolic: '', heartRate: '', spo2: '', temperature: '', respiratoryRate: '',
  });

  const [isRecording, setIsRecording] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState('');
  const recognitionRef = useRef(null);

  const [labReportFile, setLabReportFile] = useState(null);
  const [labExtracted, setLabExtracted] = useState(null);
  const [imageFile, setImageFile] = useState(null);
  const [imageObservations, setImageObservations] = useState(null);
  const [isProcessingFile, setIsProcessingFile] = useState(false);

  const [result, setResult] = useState(null);
  const [patientToken, setPatientToken] = useState(null);
  const [showQR, setShowQR] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  // ===== LOGIN =====
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
      setIsLoggedIn(true);
    } catch (err) {
      setLoginError(err.response?.data?.detail || 'Login failed. Check credentials.');
    }
  };

  const handleLogout = () => {
    sessionStorage.clear();
    setIsLoggedIn(false);
    setResult(null);
  };

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  // ===== VOICE (Web Speech API) =====
  const startRecording = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return alert('Use Chrome or Edge for voice input.');

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang =
      language.includes('हिन्दी') ? 'hi-IN' :
      language.includes('ଓଡ଼ିଆ') ? 'or-IN' : 'en-IN';

    recognition.onstart = () => { setIsRecording(true); setLiveTranscript(''); };
    recognition.onresult = (event) => {
      let interim = '', final = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) final += t + ' ';
        else interim += t;
      }
      if (final) setForm((prev) => ({ ...prev, symptoms: (prev.symptoms + ' ' + final).trim() }));
      setLiveTranscript(interim);
    };
    recognition.onerror = () => setIsRecording(false);
    recognition.onend = () => { setIsRecording(false); setLiveTranscript(''); };

    recognitionRef.current = recognition;
    recognition.start();
  };

  const stopRecording = () => {
    recognitionRef.current?.stop();
    setIsRecording(false);
  };

  // ===== REAL OCR UPLOAD =====
  const handleLabUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLabReportFile(file);
    setIsProcessingFile(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await api.post('/api/reports/extract', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setLabExtracted(res.data.data);
    } catch (err) {
      alert('OCR failed: ' + (err.response?.data?.detail || 'Try again'));
    } finally {
      setIsProcessingFile(false);
    }
  };

  // ===== REAL VISION UPLOAD =====
  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setImageFile(file);
    setIsProcessingFile(true);
    try {
      const fd = new FormData();
      fd.append('image', file);
      const res = await api.post('/api/vision/analyze', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setImageObservations(res.data.data);
    } catch (err) {
      alert('Vision failed: ' + (err.response?.data?.detail || 'Try again'));
    } finally {
      setIsProcessingFile(false);
    }
  };

  // ===== SUBMIT (MATCHES BACKEND SCHEMA) =====
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');
    setResult(null);

    try {
      const payload = {
        patient: {
          patient_id: form.patient_id.trim() || 'auto',
          abha_id: form.patient_id.trim() || 'UNKNOWN',
          age: parseInt(form.patient_age) || 0,
          sex: form.patient_sex.toLowerCase(),
          name: form.patient_name,
          language: 'en',
        },
        facility_type: facility,
        symptoms_text: form.symptoms,
        vitals: {
          bp_systolic: parseInt(form.bpSystolic) || 0,
          bp_diastolic: parseInt(form.bpDiastolic) || 0,
          heart_rate: parseInt(form.heartRate) || 0,
          spo2: parseInt(form.spo2) || 0,
          temperature_f: parseFloat(form.temperature) || 0,
          respiratory_rate: parseInt(form.respiratoryRate) || 0,
        },
      };

      const res = await api.post('/api/triage', payload);
      setResult(res.data.data);
      setPatientToken(res.data.data.patient_id);
    } catch (err) {
      setError(err.response?.data?.detail || 'Submission failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePrint = () => window.print();

  const inputLight = "w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 text-sm focus:outline-none focus:border-teal-500";
  const labelLight = "block text-slate-600 text-xs mb-1";
  const cardClass = "bg-white rounded-xl border border-slate-200 p-5 shadow-sm";

  // ===== LOGIN SCREEN =====
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-slate-800 rounded-xl border border-slate-700 p-6 shadow-xl">
          <h1 className="text-2xl font-bold text-white mb-2 text-center">🩺 AarogyaTriage</h1>
          <p className="text-slate-400 text-center mb-6 text-sm">Nurse / Medical Officer Login</p>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-slate-400 text-xs mb-1">Username</label>
              <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm"
                placeholder="nurse1" />
            </div>
            <div>
              <label className="block text-slate-400 text-xs mb-1">Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm"
                placeholder="nurse123" />
            </div>
            {loginError && <div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">⚠️ {loginError}</div>}
            <button type="submit" className="w-full py-3 rounded-lg font-semibold bg-teal-500 hover:bg-teal-400 text-slate-900">Login</button>
            <p className="text-xs text-slate-500 text-center">Demo: <strong>nurse1 / nurse123</strong> or <strong>dr_jena / doctor123</strong></p>
          </form>
        </div>
      </div>
    );
  }

  // ===== MAIN APP =====
  return (
    <div className="min-h-screen bg-slate-100">
      {/* NAVBAR */}
      <div className="bg-slate-900 border-b border-slate-700 px-6 py-3 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-teal-500 flex items-center justify-center text-slate-900 font-bold">A</div>
          <div>
            <h1 className="text-white font-bold text-lg leading-tight">AarogyaTriage</h1>
            <p className="text-teal-400 text-[10px] uppercase tracking-widest">India-Wide AI</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <select value={facility} onChange={(e) => setFacility(e.target.value)} className="bg-slate-800 border border-slate-700 text-white text-xs rounded-lg px-3 py-2">
            <option value="PHC">Primary Health Centre</option>
            <option value="CHC">Community Health Centre</option>
            <option value="DH">District Hospital</option>
          </select>
          <select value={language} onChange={(e) => setLanguage(e.target.value)} className="bg-slate-800 border border-slate-700 text-white text-xs rounded-lg px-3 py-2">
            <option>English</option>
            <option>हिन्दी (Hindi)</option>
            <option>ଓଡ଼ିଆ (Odia)</option>
          </select>
          <span className="text-xs text-teal-400 border border-teal-500 rounded-lg px-3 py-2">🛡 Privacy: Masked</span>
          <button onClick={handleLogout} className="text-xs text-slate-400 hover:text-white px-3 py-2">Logout</button>
        </div>
      </div>

      {/* ALERT BAR */}
      <div className="bg-amber-50 border-b border-amber-200 px-6 py-2 text-xs text-amber-800">
        ⚠️ <strong>Strictly Non-Diagnostic Triage Decision Support</strong> · For Qualified Medical Staff Only
      </div>

      {/* MAIN CONTENT */}
      <div className="p-6 mx-auto max-w-6xl space-y-4">
        <div className={cardClass}>
          <h2 className="text-slate-800 font-semibold mb-4">Patient Intake Form</h2>
          <form onSubmit={handleSubmit} className="space-y-5">

            {/* PATIENT DETAILS */}
            <div>
              <h3 className="text-xs font-semibold text-teal-600 uppercase mb-2">Patient Details</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <div className="md:col-span-2">
                  <label className={labelLight}>Full Name</label>
                  <input type="text" name="patient_name" value={form.patient_name} onChange={handleChange} required className={inputLight} placeholder="Ramesh Kumar" />
                </div>
                <div>
                  <label className={labelLight}>Sex</label>
                  <select name="patient_sex" value={form.patient_sex} onChange={handleChange} className={inputLight}>
                    <option>Male</option><option>Female</option><option>Others</option>
                  </select>
                </div>
                <div>
                  <label className={labelLight}>Age</label>
                  <input type="number" name="patient_age" value={form.patient_age} onChange={handleChange} required className={inputLight} placeholder="56" />
                </div>
                <div className="md:col-span-2">
                  <label className={labelLight}>ABHA ID / Patient ID (optional)</label>
                  <input type="text" name="patient_id" value={form.patient_id} onChange={handleChange} className={inputLight} placeholder="Leave blank for auto-token" />
                </div>
              </div>
            </div>

            {/* SYMPTOMS + VOICE */}
            <div>
              <label className={labelLight}>Symptoms (Text or Voice)</label>
              <textarea name="symptoms" value={form.symptoms} onChange={handleChange} required rows="3"
                className={inputLight + " resize-none"} placeholder="Crushing chest pain radiating to jaw for 45 mins..." />

              <div className="mt-2 flex items-center gap-2 flex-wrap">
                {!isRecording ? (
                  <button type="button" onClick={startRecording} className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-teal-500 text-teal-600 text-xs">
                    🎤 Record Voice
                  </button>
                ) : (
                  <>
                    <button type="button" onClick={stopRecording} className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500 text-white text-xs animate-pulse">
                      ⏹ Stop
                    </button>
                    <span className="text-xs text-red-500">Listening...</span>
                  </>
                )}
              </div>
              {liveTranscript && <p className="text-xs text-teal-600 italic mt-1">👂 "{liveTranscript}"</p>}
            </div>

            {/* MULTIMODAL UPLOADS */}
            <div>
              <label className={labelLight}>Multimodal Inputs (Lab Report + Photo)</label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-1">
                <div className="border-2 border-dashed border-slate-300 rounded-lg p-4 text-center">
                  <div className="text-2xl mb-1">📄</div>
                  <p className="text-xs font-semibold text-slate-700 mb-1">Lab Report (OCR)</p>
                  <label className="inline-block cursor-pointer text-xs bg-slate-100 px-3 py-1.5 rounded">
                    Choose File
                    <input type="file" accept="image/*,application/pdf" onChange={handleLabUpload} className="hidden" />
                  </label>
                  {labReportFile && <p className="text-[10px] text-teal-600 mt-2 truncate">{labReportFile.name}</p>}
                </div>

                <div className="border-2 border-dashed border-slate-300 rounded-lg p-4 text-center">
                  <div className="text-2xl mb-1">📷</div>
                  <p className="text-xs font-semibold text-slate-700 mb-1">Rash / Wound Photo</p>
                  <label className="inline-block cursor-pointer text-xs bg-slate-100 px-3 py-1.5 rounded">
                    Choose File
                    <input type="file" accept="image/*" onChange={handleImageUpload} className="hidden" />
                  </label>
                  {imageFile && <p className="text-[10px] text-teal-600 mt-2 truncate">{imageFile.name}</p>}
                </div>
              </div>

              {isProcessingFile && <p className="text-xs text-teal-600 mt-2 animate-pulse">⏳ Processing...</p>}

              {labExtracted && (
                <div className="mt-3 bg-teal-50 border border-teal-200 rounded-lg p-3 text-xs">
                  <p className="font-semibold text-teal-800 mb-1">✅ OCR Extracted:</p>
                  <pre className="text-teal-900 whitespace-pre-wrap">{JSON.stringify(labExtracted, null, 2)}</pre>
                </div>
              )}

              {imageObservations && (
                <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs">
                  <p className="font-semibold text-amber-800 mb-1">👁 Vision Observations:</p>
                  <p className="text-amber-900">{imageObservations.observations?.[0] || JSON.stringify(imageObservations)}</p>
                </div>
              )}
            </div>

            {/* VITALS */}
            <div>
              <h3 className="text-xs font-semibold text-teal-600 uppercase mb-2">Vital Signs</h3>
              <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                <div><label className={labelLight}>BP Sys</label><input type="number" name="bpSystolic" value={form.bpSystolic} onChange={handleChange} required className={inputLight} placeholder="174" /></div>
                <div><label className={labelLight}>BP Dia</label><input type="number" name="bpDiastolic" value={form.bpDiastolic} onChange={handleChange} required className={inputLight} placeholder="104" /></div>
                <div><label className={labelLight}>HR</label><input type="number" name="heartRate" value={form.heartRate} onChange={handleChange} required className={inputLight} placeholder="108" /></div>
                <div><label className={labelLight}>SpO2</label><input type="number" name="spo2" value={form.spo2} onChange={handleChange} required className={inputLight} placeholder="92" /></div>
                <div><label className={labelLight}>Temp °F</label><input type="number" step="0.1" name="temperature" value={form.temperature} onChange={handleChange} required className={inputLight} placeholder="98.2" /></div>
                <div><label className={labelLight}>RR</label><input type="number" name="respiratoryRate" value={form.respiratoryRate} onChange={handleChange} required className={inputLight} placeholder="26" /></div>
              </div>
            </div>

            {error && <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">❌ {error}</div>}

            <button type="submit" disabled={isSubmitting}
              className={`w-full py-3 rounded-lg font-bold text-sm ${isSubmitting ? 'bg-slate-300 text-slate-500' : 'bg-teal-500 hover:bg-teal-600 text-white'}`}>
              {isSubmitting ? 'ANALYZING...' : '⚡ EXECUTE MULTIMODAL TRIAGE'}
            </button>
          </form>
        </div>

        {/* RESULT */}
        {result && (
          <>
            <div className="bg-amber-400 rounded-xl p-4 flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-4">
                <span className="bg-amber-900 text-amber-100 text-xs font-bold px-3 py-1 rounded">{result.priority} PRIORITY</span>
                <span className="text-amber-900 text-xs font-mono">{patientToken}</span>
              </div>
              <div className="flex items-center gap-3">
                <button onClick={handlePrint} className="bg-white text-amber-900 text-xs font-semibold px-3 py-2 rounded-lg">🖨 Print</button>
                <button onClick={() => setShowQR(!showQR)} className="bg-slate-900 text-white text-xs font-semibold px-3 py-2 rounded-lg">📱 {showQR ? 'Hide QR' : 'Show QR'}</button>
              </div>
            </div>

            {showQR && patientToken && (
              <div className={cardClass + " flex flex-col items-center"}>
                <p className="text-slate-600 text-sm mb-3">Scan to view your queue status</p>
                <QRCodeSVG value={`${window.location.origin}/patient/${patientToken}`} size={180} />
                <p className="text-slate-500 text-xs mt-3 font-mono">/patient/{patientToken}</p>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className={cardClass}>
                <h3 className="text-slate-800 font-semibold text-sm mb-3">🩺 Vitals & MEWS</h3>
                <p className="text-xs text-slate-500 mb-2">MEWS Score: <strong>{result.mews_score}</strong></p>
                <div className="space-y-2">
                  {result.routing?.recommended_department && (
                    <div className="text-xs"><strong>Department:</strong> {result.routing.recommended_department}</div>
                  )}
                  {result.routing?.inter_facility_referral && (
                    <div className="text-xs text-red-600">{result.routing.inter_facility_referral}</div>
                  )}
                </div>
              </div>

              <div className={cardClass}>
                <h3 className="text-slate-800 font-semibold text-sm mb-3">🧠 AI Summary</h3>
                <p className="text-slate-600 text-xs leading-relaxed">{result.summary || 'Summary not available.'}</p>
              </div>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
              <p className="text-amber-800 text-xs"><strong>⚠️ CLINICAL ADVISORY ONLY:</strong> Non-diagnostic. Must be verified by a licensed Medical Officer.</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
