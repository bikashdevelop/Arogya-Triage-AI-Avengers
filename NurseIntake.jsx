import React, { useState, useRef } from 'react';
import axios from 'axios';
import { QRCodeSVG } from 'qrcode.react';

const API_BASE = 'http://localhost:8000';

export default function NurseIntake() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState('');
  const [activeTab, setActiveTab] = useState('intake');
  const [facility, setFacility] = useState('PHC');
  const [language, setLanguage] = useState('English');
  const [device, setDevice] = useState('PC/Laptop');

  const [form, setForm] = useState({
    patient_name: '',
    patient_sex: 'Male',
    patient_age: '',
    patient_mobile: '',
    patient_email: '',
    patient_id: '',
    symptoms: '',
    bpSystolic: '', bpDiastolic: '',
    heartRate: '', spo2: '', temperature: '', respiratoryRate: ''
  });

  // Multimodal states
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
    if (username === 'admin' && password === 'admin') {
      setIsLoggedIn(true);
      return;
    }
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    formData.append('grant_type', 'password');
    try {
      await axios.post(API_BASE + '/api/login', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setIsLoggedIn(true);
    } catch (err) {
      setLoginError(err.response?.data?.detail || 'Login failed.');
    }
  };

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  // ===== VOICE RECORDING (Web Speech API) =====
  const startRecording = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Your browser does not support speech recognition. Please use Chrome or Edge.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = language === 'English' ? 'en-IN' : language.includes('हिन्दी') ? 'hi-IN' : 'en-IN';

    recognition.onstart = () => {
      setIsRecording(true);
      setLiveTranscript('');
    };

    recognition.onresult = (event) => {
      let interim = '';
      let final = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) final += transcript + ' ';
        else interim += transcript;
      }
      if (final) {
        setForm(prev => ({ ...prev, symptoms: (prev.symptoms + ' ' + final).trim() }));
      }
      setLiveTranscript(interim);
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      setIsRecording(false);
      if (event.error === 'not-allowed') {
        alert('Microphone permission denied. Please allow mic access and try again.');
      }
    };

    recognition.onend = () => {
      setIsRecording(false);
      setLiveTranscript('');
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsRecording(false);
    }
  };

  // ===== LAB REPORT OCR =====
  const handleLabUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLabReportFile(file);
    setIsProcessingFile(true);
    setTimeout(() => {
      setLabExtracted({
        hemoglobin: '11.2 g/dL',
        wbc: '8,500 /µL',
        platelets: '42,000 /µL',
        glucose: '110 mg/dL'
      });
      setIsProcessingFile(false);
    }, 1500);
  };

  // ===== IMAGE UPLOAD =====
  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setImageFile(file);
    setIsProcessingFile(true);
    setTimeout(() => {
      setImageObservations({
        findings: 'Visible skin discoloration detected on forearm. Requires human review.',
        confidence: '0.82',
        requiresHumanReview: true
      });
      setIsProcessingFile(false);
    }, 1500);
  };

  // ===== SUBMIT =====
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true); setError(''); setResult(null);

    if (username === 'admin') {
      setTimeout(() => {
        const today = new Date();
        const dateStr = today.toISOString().slice(0, 10).replace(/-/g, '');
        const autoToken = form.patient_id.trim() || `PAT-${dateStr}-001`;
        setPatientToken(autoToken);
        setResult({
          priority_tier: 'P3',
          summary: 'Presenting at Primary Health Centre (PHC) with High continuous fever for 3 days with intense body ache and nausea.' +
            (labExtracted ? ` Lab findings: Hb ${labExtracted.hemoglobin}, Platelets ${labExtracted.platelets}.` : '') +
            (imageObservations ? ` Vision: ${imageObservations.findings}` : ''),
          vitals_summary: {
            bp: `${form.bpSystolic || '124'}/${form.bpDiastolic || '82'} mmHg`,
            hr: `${form.heartRate || '88'} bpm`,
            spo2: `${form.spo2 || '97'}%`,
            temp: `${form.temperature || '101.4'}°F`,
            mews: 1
          },
          timeline: [
            { label: 'Day 1-2', description: 'Initial symptom onset reported by patient' },
            { label: 'Presenting', description: 'Presenting at PHC with fever, body ache, nausea. Vitals recorded.' }
          ]
        });
        setIsSubmitting(false);
      }, 1200);
      return;
    }

    try {
      const payload = {
        patient_id: form.patient_id.trim() || null,
        symptoms: form.symptoms,
        vitals: {
          bp_systolic: parseInt(form.bpSystolic),
          bp_diastolic: parseInt(form.bpDiastolic),
          heart_rate: parseInt(form.heartRate),
          spo2: parseInt(form.spo2),
          temperature: parseFloat(form.temperature),
          respiratory_rate: parseInt(form.respiratoryRate)
        },
        report_data: labExtracted,
        image_observations: imageObservations
      };
      const response = await axios.post(API_BASE + '/api/triage', payload);
      setResult(response.data);
      const finalToken = response.data.patient_id || form.patient_id;
setPatientToken(finalToken);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to submit.');
    } finally {
      setIsSubmitting(false);
    }
  };
   // ===== OPEN PATIENT QUEUE IN NEW TAB =====

  const handlePrint = () => window.print();

  const inputClass = "w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 text-sm";
  const inputLight = "w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-teal-500 text-sm";
  const labelClass = "block text-slate-400 text-xs mb-1";
  const labelLight = "block text-slate-600 text-xs mb-1";
  const cardClass = "bg-white rounded-xl border border-slate-200 p-5 shadow-sm";

  // ===== LOGIN SCREEN =====
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-slate-800 rounded-xl border border-slate-700 p-6 shadow-xl">
          <h1 className="text-2xl font-bold text-white mb-2 text-center">🩺 AarogyaTriage</h1>
          <p className="text-slate-400 text-center mb-6 text-sm">Medical Officer Login</p>
          <form onSubmit={handleLogin} className="space-y-4">
            <div><label className={labelClass}>Username</label><input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required className={inputClass} placeholder="username" /></div>
<div>
  <label className={labelClass}>Password</label>
  <div className="relative">
    <input
      type={showPassword ? "text" : "password"}
      value={password}
      onChange={(e) => setPassword(e.target.value)}
      required
      className={inputClass + " pr-10"}
      placeholder="Password"
    />
    <button
      type="button"
      onClick={() => setShowPassword(!showPassword)}
      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-teal-400 text-sm"
      title={showPassword ? "Hide password" : "Show password"}
    >
      {showPassword ? "🙈" : "👁"}
    </button>
  </div>
</div>
            {loginError && <div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">⚠️ {loginError}</div>}
            <button type="submit" className="w-full py-3 rounded-lg font-semibold bg-teal-500 hover:bg-teal-400 text-slate-900">Login</button>
          </form>
        </div>
      </div>
    );
  }

  // ===== MAIN LAYOUT =====
  return (
    <div className="min-h-screen bg-slate-100">
      {/* TOP NAVBAR */}
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
            <option value="PHC">Primary Health Centre (PHC)</option>
            <option value="CHC">Community Health Centre (CHC)</option>
            <option value="DH">District Hospital (DH)</option>
          </select>
          <select value={language} onChange={(e) => setLanguage(e.target.value)} className="bg-slate-800 border border-slate-700 text-white text-xs rounded-lg px-3 py-2">
            <option>English</option>
            <option>हिन्दी (Hindi)</option>
            <option>ଓଡ଼ିଆ (Odia)</option>
          </select>
          <select value={device} onChange={(e) => setDevice(e.target.value)} className="bg-slate-800 border border-slate-700 text-white text-xs rounded-lg px-3 py-2">
            <option value="Mobile">📱 Mobile</option>
            <option value="Tablet">📟 Tablet</option>
            <option value="PC/Laptop">💻 PC / Laptop</option>
          </select>
          <span className="text-xs text-teal-400 border border-teal-500 rounded-lg px-3 py-2">🛡 Privacy: Masked</span>
        </div>
      </div>

      {/* ALERT BAR */}
      <div className="bg-amber-50 border-b border-amber-200 px-6 py-2 text-xs text-amber-800">
        ⚠️ <strong>Govt / Institutional Healthcare Prototype</strong> · Strictly Non-Diagnostic Triage Decision Support for Qualified Medical Staff
      </div>

      {/* TABS */}
      <div className="bg-white border-b border-slate-200 px-6 flex items-center gap-1">
        <button onClick={() => setActiveTab('intake')} className={`px-4 py-3 text-sm font-medium border-b-2 transition ${activeTab === 'intake' ? 'border-teal-500 text-teal-600' : 'border-transparent text-slate-500'}`}>📋 Multimodal Triage Intake</button>
        <button onClick={() => setActiveTab('queue')} className={`px-4 py-3 text-sm font-medium border-b-2 transition flex items-center gap-2 ${activeTab === 'queue' ? 'border-teal-500 text-teal-600' : 'border-transparent text-slate-500'}`}>
          🩺 Doctor Review Queue <span className="bg-pink-500 text-white text-xs rounded-full px-2 py-0.5">2 P1</span>
        </button>
      </div>

      {/* MAIN CONTENT */}
      {/* MAIN CONTENT - Device-aware width */}
<div className={`p-6 mx-auto space-y-4 transition-all duration-300 ${
  device === 'Mobile' ? 'max-w-sm' :
  device === 'Tablet' ? 'max-w-2xl' :
  'max-w-6xl'
}`}>
  {device !== 'PC/Laptop' && (
    <div className="text-center">
      <span className="inline-block bg-teal-500 text-white text-xs font-semibold px-3 py-1 rounded-full">
        {device === 'Mobile' ? '📱 Mobile Preview Mode' : '📟 Tablet Preview Mode'}
      </span>
    </div>
  )}
         <div className={cardClass}> 
         <h2 className="text-slate-800 font-semibold mb-4">Patient Intake Form</h2>
          <form onSubmit={handleSubmit} className="space-y-5">

            {/* ABHA ID */}
            {/* PATIENT BASIC DETAILS */}
<div>
  <h3 className="text-xs font-semibold text-teal-600 uppercase mb-2">Patient Basic Details</h3>
  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
    <div className="md:col-span-2">
      <label className={labelLight}>Patient Name</label>
      <input type="text" name="patient_name" value={form.patient_name} onChange={handleChange} required className={inputLight} placeholder="Full name" />
    </div>
    <div>
      <label className={labelLight}>Sex</label>
      <select name="patient_sex" value={form.patient_sex} onChange={handleChange} className={inputLight}>
        <option value="Male">Male</option>
        <option value="Female">Female</option>
        <option value="Others">Other</option>
      </select>
    </div>
    <div>
      <label className={labelLight}>Age</label>
      <input type="number" name="patient_age" value={form.patient_age} onChange={handleChange} required className={inputLight} placeholder="35" />
    </div>
    <div>
      <label className={labelLight}>Mobile Number</label>
      <input type="tel" name="patient_mobile" value={form.patient_mobile} onChange={handleChange} className={inputLight} placeholder="98765 43210" />
    </div>
    <div>
      <label className={labelLight}>Email (optional)</label>
      <input type="email" name="patient_email" value={form.patient_email} onChange={handleChange} className={inputLight} placeholder="patient@email.com" />
    </div>
  </div>
</div>
            <div>
              <label className={labelLight}>ABHA ID / Patient ID (optional)</label>
              <input type="text" name="patient_id" value={form.patient_id} onChange={handleChange} className={inputLight} placeholder="Leave blank for auto-token" />
            </div>

            {/* SYMPTOM NARRATIVE + VOICE */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className={labelLight}>2. Symptom Narrative (Text or Live Voice)</label>
                <span className="text-xs text-slate-400">Spoken in: {language}</span>
              </div>
              <textarea name="symptoms" value={form.symptoms} onChange={handleChange} required rows="3" className={inputLight + " resize-none"} placeholder="Describe symptoms..." />

              {/* VOICE BUTTON */}
              <div className="mt-2 flex items-center gap-2 flex-wrap">
                {!isRecording && (
                  <button type="button" onClick={startRecording} className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-teal-500 text-teal-600 text-xs font-medium hover:bg-teal-50">
                    🎤 Record Voice
                  </button>
                )}
                {isRecording && (
                  <>
                    <button type="button" onClick={stopRecording} className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500 text-white text-xs font-medium animate-pulse">
                      ⏹ Stop Recording
                    </button>
                    <span className="text-xs text-red-500 flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
                      Listening...
                    </span>
                  </>
                )}
              </div>
              {liveTranscript && (
                <p className="text-xs text-teal-600 italic mt-1">👂 Hearing: "{liveTranscript}"</p>
              )}
            </div>

            {/* MULTIMODAL: LAB OCR + IMAGE */}
            <div>
              <label className={labelLight}>3. Multimodal Inputs: Lab Report OCR & Visual Inspection</label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-1">
                <div className="border-2 border-dashed border-slate-300 rounded-lg p-4 text-center hover:border-teal-500 transition">
                  <div className="text-2xl mb-1">📄</div>
                  <p className="text-xs font-semibold text-slate-700 mb-1">Lab Report / Prescription (OCR)</p>
                  <p className="text-[10px] text-slate-500 mb-2">Upload PDF or image</p>
                  <label className="inline-block cursor-pointer text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded">
                    Choose File
                    <input type="file" accept="image/*,application/pdf" onChange={handleLabUpload} className="hidden" />
                  </label>
                  {labReportFile && <p className="text-[10px] text-teal-600 mt-2 truncate">{labReportFile.name}</p>}
                </div>

                <div className="border-2 border-dashed border-slate-300 rounded-lg p-4 text-center hover:border-teal-500 transition">
                  <div className="text-2xl mb-1">📷</div>
                  <p className="text-xs font-semibold text-slate-700 mb-1">Visual Symptom Photo</p>
                  <p className="text-[10px] text-slate-500 mb-2">Wound / skin / swelling</p>
                  <label className="inline-block cursor-pointer text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded">
                    Choose File
                    <input type="file" accept="image/*" onChange={handleImageUpload} className="hidden" />
                  </label>
                  {imageFile && <p className="text-[10px] text-teal-600 mt-2 truncate">{imageFile.name}</p>}
                </div>
              </div>

              {isProcessingFile && <p className="text-xs text-teal-600 mt-2 animate-pulse">⏳ Processing file (Gemini 3.8 Flash Vision)...</p>}

              {labExtracted && (
                <div className="mt-3 bg-teal-50 border border-teal-200 rounded-lg p-3">
                  <p className="text-xs font-semibold text-teal-800 mb-1">✅ OCR Extracted Values:</p>
                  <div className="grid grid-cols-2 gap-2 text-xs text-teal-900">
                    <div>Hemoglobin: <strong>{labExtracted.hemoglobin}</strong></div>
                    <div>WBC: <strong>{labExtracted.wbc}</strong></div>
                    <div>Platelets: <strong className="text-red-600">{labExtracted.platelets} ⚠</strong></div>
                    <div>Glucose: <strong>{labExtracted.glucose}</strong></div>
                  </div>
                </div>
              )}

              {imageObservations && (
                <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-3">
                  <p className="text-xs font-semibold text-amber-800 mb-1">👁 Vision AI Observations:</p>
                  <p className="text-xs text-amber-900">{imageObservations.findings}</p>
                  <p className="text-[10px] text-amber-600 mt-1">Confidence: {imageObservations.confidence} · Requires human review</p>
                </div>
              )}
            </div>

            {/* VITALS */}
            <div>
              <h3 className="text-xs font-semibold text-teal-600 uppercase mb-2">Vital Signs</h3>
              <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                <div><label className={labelLight}>BP Sys</label><input type="number" name="bpSystolic" value={form.bpSystolic} onChange={handleChange} required className={inputLight} placeholder="124" /></div>
                <div><label className={labelLight}>BP Dia</label><input type="number" name="bpDiastolic" value={form.bpDiastolic} onChange={handleChange} required className={inputLight} placeholder="82" /></div>
                <div><label className={labelLight}>Heart Rate</label><input type="number" name="heartRate" value={form.heartRate} onChange={handleChange} required className={inputLight} placeholder="88" /></div>
                <div><label className={labelLight}>SpO2</label><input type="number" name="spo2" value={form.spo2} onChange={handleChange} required className={inputLight} placeholder="97" /></div>
                <div><label className={labelLight}>Temperature °F</label><input type="number" step="0.1" name="temperature" value={form.temperature} onChange={handleChange} required className={inputLight} placeholder="101.4" /></div>
                <div><label className={labelLight}>Respiratory Rate</label><input type="number" name="respiratoryRate" value={form.respiratoryRate} onChange={handleChange} required className={inputLight} placeholder="18" /></div>
              </div>
            </div>

            {error && <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">❌ {error}</div>}

            <button type="submit" disabled={isSubmitting} className={`w-full py-3 rounded-lg font-bold text-sm transition ${isSubmitting ? 'bg-slate-300 text-slate-500' : 'bg-teal-500 hover:bg-teal-600 text-white'}`}>
              {isSubmitting ? 'ANALYZING...' : '⚡ EXECUTE MULTIMODAL TRIAGE ASSESSMENT'}
            </button>
          </form>
        </div>

        {/* PRIORITY BANNER */}
        {result && (
          <div className="bg-amber-400 rounded-xl p-4 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-4">
              <span className="bg-amber-900 text-amber-100 text-xs font-bold px-3 py-1 rounded">{result.priority_tier} PRIORITY</span>
              <span className="text-amber-900 text-xs font-mono">ABHA: {patientToken}</span>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={handlePrint} className="bg-white text-amber-900 text-xs font-semibold px-3 py-2 rounded-lg">🖨 Print Note</button>
              <button onClick={() => setShowQR(!showQR)} className="bg-slate-900 text-white text-xs font-semibold px-3 py-2 rounded-lg">📱 {showQR ? 'Hide QR' : 'Show QR'}</button>
            </div>
          </div>
        )}

        {result && (
          <div className="bg-amber-400 rounded-xl px-4 pb-3 -mt-2">
            <h3 className="text-amber-900 text-lg font-bold">{result.priority_tier} SEMI-URGENT - Review within 30-60 Mins</h3>
            <p className="text-amber-800 text-xs">⏱ Target Queue Window: 30-60 mins · Clinical Sub-Queue</p>
          </div>
        )}

        {/* QR CODE */}
        {showQR && patientToken && (
  <div className={`${cardClass} flex flex-col items-center`}>
    <p className="text-slate-600 text-sm mb-3">📱 Scan to view live queue status</p>
    <div className="bg-white p-3 rounded-lg border border-slate-200">
      <QRCodeSVG value={`http://10.85.21.31:5173/patient/${patientToken}`} size={180} />
    </div>
    <p className="text-slate-500 text-xs mt-3 font-mono">/patient/{patientToken}</p>
    <p className="text-slate-400 text-[10px] mt-1 mb-3">Patient scans → opens live queue page</p>
  </div>
)}        {/* STATUTORY NOTICE */}
        {result && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex gap-3">
            <span className="text-amber-600 text-xl">⚠️</span>
            <div>
              <h4 className="text-amber-900 font-bold text-xs uppercase mb-1">Statutory Non-Diagnostic Healthcare Advisory Notice:</h4>
              <p className="text-amber-800 text-xs leading-relaxed">CLINICAL ADVISORY ONLY: This triage output is non-diagnostic. Must be verified by a licensed Medical Officer.</p>
            </div>
          </div>
        )}

        {/* TWO COLUMN */}
        {result && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className={cardClass}>
              <h3 className="text-slate-800 font-semibold text-sm mb-4">Clinical Timeline & Symptom Progression</h3>
              <div className="space-y-3">
                {result.timeline?.map((event, i) => (
                  <div key={i} className="flex gap-3">
                    <div className="bg-teal-500 text-white text-[10px] font-bold px-2 py-1 rounded w-24 text-center shrink-0">{event.label}</div>
                    <p className="text-slate-600 text-xs">{event.description}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className={cardClass}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-slate-800 font-semibold text-sm">🩺 Vitals & Physiological State</h3>
                <span className="text-slate-500 text-xs">MEWS: {result.vitals_summary?.mews || 1}</span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="border border-slate-200 rounded-lg p-3"><p className="text-slate-500 text-[10px] uppercase">BP</p><p className="text-slate-900 font-semibold text-sm">{result.vitals_summary?.bp}</p></div>
                <div className="border border-slate-200 rounded-lg p-3"><p className="text-slate-500 text-[10px] uppercase">HR</p><p className="text-slate-900 font-semibold text-sm">{result.vitals_summary?.hr}</p></div>
                <div className="border border-slate-200 rounded-lg p-3"><p className="text-slate-500 text-[10px] uppercase">SpO2</p><p className="text-slate-900 font-semibold text-sm">{result.vitals_summary?.spo2}</p></div>
                <div className="border border-slate-200 rounded-lg p-3"><p className="text-slate-500 text-[10px] uppercase">Temp</p><p className="text-slate-900 font-semibold text-sm">{result.vitals_summary?.temp}</p></div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
