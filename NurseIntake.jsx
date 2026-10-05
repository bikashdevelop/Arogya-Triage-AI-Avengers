import React, { useState, useRef } from 'react';
import axios from 'axios';
import { QRCodeSVG } from 'qrcode.react';
import DoctorReview from './DoctorReview';
import ReferralNote from './ReferralNote';

const API_BASE = 'http://localhost:8000';

const PRIORITY_INFO = {
  P1: { urgency: 'Immediate / Emergent', wait: '0 minutes' },
  P2: { urgency: 'Very Urgent', wait: 'Within 10 minutes' },
  P3: { urgency: 'Urgent', wait: 'Within 60 minutes' },
  P4: { urgency: 'Standard', wait: 'Within 120 minutes' },
};

const DOCTORS = [
  { id: 1, name: 'Dr. B. K. Jena', dept: 'Cardiology', available: false, reason: 'On Leave', experience: 15 },
  { id: 2, name: 'Dr. P. Das', dept: 'Cardiology', available: true, experience: 12 },
  { id: 3, name: 'Dr. R. Nayak', dept: 'Cardiology', available: true, experience: 10 },
  { id: 4, name: 'Dr. A. K. Mishra', dept: 'General Medicine', available: true, experience: 20 },
  { id: 5, name: 'Dr. S. Behera', dept: 'General Medicine', available: true, experience: 8 },
  { id: 6, name: 'Dr. S. Patnaik', dept: 'Pediatrics', available: true, experience: 14 },
  { id: 7, name: 'Dr. M. Sahoo', dept: 'Pediatrics', available: false, reason: 'In Surgery', experience: 11 },
  { id: 8, name: 'Dr. K. Panda', dept: 'Orthopedics', available: true, experience: 18 },
  { id: 9, name: 'Dr. T. Kumar', dept: 'Orthopedics', available: true, experience: 7 },
  { id: 10, name: 'Dr. R. Mohanty', dept: 'Emergency', available: true, experience: 16 },
  { id: 11, name: 'Dr. N. Swain', dept: 'Obstetrics & Gynecology', available: true, experience: 13 },
  { id: 12, name: 'Dr. K. Jena', dept: 'Dermatology', available: true, experience: 9 },
];

const BYPASS_REASONS = [
  '🫀 Cardiac Arrest',
  '🩸 Severe Bleeding',
  '😰 Not Breathing',
  '😵 Unconscious',
  '🧠 Stroke / Paralysis',
  '🔥 Severe Burns',
  '🚗 Road Accident',
  '🐍 Snake Bite / Poisoning',
  '⚡ Seizure',
  '⚠️ Other Critical',
];

export default function NurseIntake() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState('');
  const [facility, setFacility] = useState('PHC');
  const [language, setLanguage] = useState('English');

  const [form, setForm] = useState({
    patient_name: '',
    patient_sex: 'Male',
    patient_age: '',
    patient_mobile: '',
    patient_email: '',
    patient_category: 'None',
    patient_id: '',
    symptoms: '',
    bpSystolic: '',
    bpDiastolic: '',
    heartRate: '',
    spo2: '',
    temperature: '',
    respiratoryRate: '',
    symptom_onset: '',
    prior_visit_date: '',
    report_date: '',
    current_medicines: '',
    blood_group: '',
    known_allergies: '',
    chronic_conditions: [],
    past_surgeries: '',
    family_history: '',
  });

  const [showEmergencyBypass, setShowEmergencyBypass] = useState(false);
  const [bypassReason, setBypassReason] = useState('');
  const [bypassLocation, setBypassLocation] = useState('Casualty Room 1');
  const [bypassActivated, setBypassActivated] = useState(false);
  const [emergencyLog, setEmergencyLog] = useState([]);

  const [isRecording, setIsRecording] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [dynamicQuestions, setDynamicQuestions] = useState([]);
  const [followupAnswers, setFollowupAnswers] = useState({});
  const [questionsGenerated, setQuestionsGenerated] = useState(false);
  const recognitionRef = useRef(null);

  const [labReportFile, setLabReportFile] = useState(null);
  const [labExtracted, setLabExtracted] = useState(null);
  const [labFileHistory, setLabFileHistory] = useState([]);
  const [imageFile, setImageFile] = useState(null);
  const [imageObservations, setImageObservations] = useState(null);
  const [imageFileHistory, setImageFileHistory] = useState([]);
  const [isProcessingFile, setIsProcessingFile] = useState(false);

  const [result, setResult] = useState(null);
  const [patientToken, setPatientToken] = useState(null);
  const [showQR, setShowQR] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [showDoctorChange, setShowDoctorChange] = useState(false);
  const [showDoctorReview, setShowDoctorReview] = useState(false);
  const [showReferralNote, setShowReferralNote] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    const MOCK_USERS = [
      { username: 'nurse', password: 'nurse123' },
      { username: 'doctor', password: 'doctor123' },
      { username: 'admin', password: 'admin' },
    ];
    const matched = MOCK_USERS.find(u => u.username === username && u.password === password);
    if (matched) {
      setIsLoggedIn(true);
      return;
    }
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    formData.append('grant_type', 'password');
    try {
      await axios.post(API_BASE + '/api/login', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setIsLoggedIn(true);
    } catch (err) {
      setLoginError(err.response?.data?.detail || 'Login failed.');
    }
  };

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const activateBypass = () => {
    if (!bypassReason) {
      alert('Please select emergency reason');
      return;
    }
    const today = new Date();
    const dateStr = today.toISOString().slice(0, 10).replace(/-/g, '');
    const randomNum = Math.floor(Math.random() * 999).toString().padStart(3, '0');
    const bypassToken = `PAT-EMG-${dateStr}-${randomNum}`;
    setPatientToken(bypassToken);
    setBypassActivated(true);
    setShowEmergencyBypass(false);
    setEmergencyLog(prev => [...prev, {
      token: bypassToken,
      reason: bypassReason,
      location: bypassLocation,
      time: new Date().toLocaleTimeString(),
      nurse: username || 'nurse',
    }]);
    alert(`🚨 EMERGENCY ALERT SENT!\n\nToken: ${bypassToken}\nReason: ${bypassReason}\nLocation: ${bypassLocation}`);
  };

  const startRecording = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { alert('Please use Chrome or Edge.'); return; }
    const recognition = new SR();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = language === 'English' ? 'en-IN' : 'hi-IN';
    recognition.onstart = () => { setIsRecording(true); setLiveTranscript(''); };
    recognition.onresult = (event) => {
      let interim = '', final = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) final += t + ' ';
        else interim += t;
      }
      if (final) setForm(prev => ({ ...prev, symptoms: (prev.symptoms + ' ' + final).trim() }));
      setLiveTranscript(interim);
    };
    recognition.onerror = () => setIsRecording(false);
    recognition.onend = () => { setIsRecording(false); setLiveTranscript(''); };
    recognitionRef.current = recognition;
    recognition.start();
  };

  const stopRecording = () => {
    if (recognitionRef.current) { recognitionRef.current.stop(); setIsRecording(false); }
  };

  const QUESTION_BANK = {
    chest: [
      { id: 'chest_radiating', q: 'Is chest pain radiating to left arm or jaw?', type: 'yesno' },
      { id: 'chest_sweating', q: 'Associated with sweating?', type: 'yesno' },
    ],
    fever: [
      { id: 'fever_duration', q: 'Fever since how many days?', type: 'text' },
      { id: 'fever_rash', q: 'Any rash along with fever?', type: 'yesno' },
    ],
    leg: [
      { id: 'leg_weight', q: 'Can patient bear weight on leg?', type: 'yesno' },
      { id: 'leg_deformity', q: 'Any visible deformity?', type: 'yesno' },
    ],
    head: [
      { id: 'head_vision', q: 'Any vision changes?', type: 'yesno' },
      { id: 'head_injury', q: 'Was helmet worn?', type: 'yesno' },
    ],
    breathing: [
      { id: 'breath_rest', q: 'Difficulty breathing at rest?', type: 'yesno' },
    ],
    default: [
      { id: 'gen_duration', q: 'How long have symptoms lasted?', type: 'text' },
      { id: 'gen_severity', q: 'Severity of symptoms?', type: 'severity' },
      { id: 'gen_allergy', q: 'Any known allergies?', type: 'text' },
    ],
  };

  const generateQuestions = () => {
    const s = (form.symptoms || '').toLowerCase();
    let selected = [];
    const used = new Set();
    const add = (key) => {
      if (used.has(key)) return;
      used.add(key);
      QUESTION_BANK[key].forEach(q => { if (!selected.find(x => x.id === q.id)) selected.push(q); });
    };
    if (s.includes('chest') || s.includes('heart')) add('chest');
    if (s.includes('breathing') || s.includes('shortness')) add('breathing');
    if (s.includes('leg') || s.includes('fracture')) add('leg');
    if (s.includes('head') || s.includes('accident')) add('head');
    if (s.includes('fever')) add('fever');
    QUESTION_BANK.default.forEach(q => { if (!selected.find(x => x.id === q.id)) selected.push(q); });
    selected = selected.slice(0, 5);
    setDynamicQuestions(selected);
    setFollowupAnswers({});
    setQuestionsGenerated(true);
  };

  const handleFollowupAnswer = (id, value) => {
    setFollowupAnswers(prev => ({ ...prev, [id]: value }));
  };

  const buildTimeline = () => {
    const events = [];
    if (form.symptom_onset) events.push({ date: form.symptom_onset, label: 'Symptom Onset', description: form.symptoms?.substring(0, 80), icon: '🩺', color: 'amber' });
    if (form.prior_visit_date) events.push({ date: form.prior_visit_date, label: 'Prior Visit', description: 'Previous consultation', icon: '🏥', color: 'slate' });
    if (form.report_date && labExtracted) events.push({ date: form.report_date, label: 'Lab Report', description: `Hb: ${labExtracted.hemoglobin}`, icon: '📄', color: 'teal' });
    if (imageObservations) events.push({ date: new Date().toISOString().slice(0, 10), label: 'Visual Capture', description: imageObservations.findings.substring(0, 60), icon: '📷', color: 'blue' });
    if (form.current_medicines) events.push({ date: new Date().toISOString().slice(0, 10), label: 'Current Medicines', description: form.current_medicines, icon: '💊', color: 'purple' });
    events.push({ date: new Date().toISOString().slice(0, 10), label: 'Present Visit', description: `Vitals: BP ${form.bpSystolic}/${form.bpDiastolic}`, icon: '🚨', color: 'red' });
    events.sort((a, b) => new Date(a.date) - new Date(b.date));
    return events;
  };

  const handleLabUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (labReportFile) {
      setLabFileHistory(prev => [...prev, { name: labReportFile.name, replacedAt: new Date().toLocaleTimeString() }]);
    }
    setLabReportFile(file);
    setIsProcessingFile(true);
    setTimeout(() => {
      setLabExtracted({ hemoglobin: '11.2 g/dL', wbc: '8,500 /µL', platelets: '42,000 /µL', glucose: '110 mg/dL' });
      setIsProcessingFile(false);
    }, 1200);
  };

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (imageFile) {
      setImageFileHistory(prev => [...prev, { name: imageFile.name, replacedAt: new Date().toLocaleTimeString() }]);
    }
    setImageFile(file);
    setIsProcessingFile(true);
    setTimeout(() => {
      setImageObservations({ findings: 'Visible head wound, blood present.', confidence: '0.92' });
      setIsProcessingFile(false);
    }, 1200);
  };

  const autoSelectDepartment = () => {
    const s = (form.symptoms || '').toLowerCase();
    const bp = parseInt(form.bpSystolic) || 0;
    const spo2 = parseInt(form.spo2) || 100;
    const temp = parseFloat(form.temperature) || 98.6;
    const age = parseInt(form.patient_age) || 0;
    if (bypassActivated || s.includes('unconscious') || s.includes('accident') || spo2 < 90) return { dept: 'Emergency', reason: 'Critical - Trauma/Emergency' };
    if (s.includes('chest pain') || bp > 160) return { dept: 'Cardiology', reason: 'Chest pain / High BP' };
    if (form.patient_category === 'Pregnancy') return { dept: 'Obstetrics & Gynecology', reason: 'Pregnancy case' };
    if (form.patient_category === 'Child' || age < 12) return { dept: 'Pediatrics', reason: 'Pediatric patient' };
    if (s.includes('fracture') || s.includes('leg') || s.includes('arm')) return { dept: 'Orthopedics', reason: 'Bone/joint injury' };
    if (temp > 102 || s.includes('fever')) return { dept: 'General Medicine', reason: 'Fever/General symptoms' };
    return { dept: 'General Medicine', reason: 'General symptoms' };
  };

  const autoAssignDoctor = (department) => {
    const docs = DOCTORS.filter(d => d.dept === department && d.available);
    if (docs.length > 0) {
      const sorted = docs.sort((a, b) => b.experience - a.experience);
      return { name: sorted[0].name, available: true, reason: 'Available' };
    }
    return { name: 'Duty Medical Officer', available: true, reason: 'Backup Assigned' };
  };

  const calculatePriority = () => {
    const spo2 = parseInt(form.spo2) || 100;
    const bp = parseInt(form.bpSystolic) || 0;
    const temp = parseFloat(form.temperature) || 98.6;
    const sev = followupAnswers['gen_severity'];
    const s = (form.symptoms || '').toLowerCase();
    if (bypassActivated) return 'P1';
    if (s.includes('unconscious') || spo2 < 90 || bp > 180 || temp > 104 || sev === 'Severe') return 'P1';
    if (spo2 < 94 || bp > 160 || temp > 102) return 'P2';
    if (bp > 140 || temp > 100) return 'P3';
    return 'P4';
  };

  const handleDoctorChange = (newDoc) => {
    setResult(prev => ({ ...prev, assigned_doctor: newDoc, doctor_status: 'Manually Assigned' }));
    setShowDoctorChange(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');
    setResult(null);
    setTimeout(() => {
      const analysis = autoSelectDepartment();
      const doctor = autoAssignDoctor(analysis.dept);
      const priority = calculatePriority();
      const today = new Date();
      const dateStr = today.toISOString().slice(0, 10).replace(/-/g, '');
      const token = patientToken || form.patient_id.trim() || `PAT-${dateStr}-001`;
      setPatientToken(token);
      setResult({
        priority_tier: priority,
        recommended_department: analysis.dept,
        department_reason: analysis.reason,
        assigned_doctor: doctor.name,
        doctor_available: doctor.available,
        doctor_status: doctor.reason,
        summary: `${form.patient_name} (${form.patient_age}y/${form.patient_sex}) presenting with ${form.symptoms.substring(0, 100)}.`,
        vitals_summary: {
          bp: `${form.bpSystolic}/${form.bpDiastolic} mmHg`,
          hr: `${form.heartRate} bpm`,
          spo2: `${form.spo2}%`,
          temp: `${form.temperature}°F`,
          mews: priority === 'P1' ? 7 : 1,
        },
        timeline: buildTimeline(),
        followup_answers: followupAnswers,
        is_bypass: bypassActivated,
      });
      setIsSubmitting(false);
    }, 1200);
  };

  const handlePrint = () => window.print();

  const inputClass = "w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 text-sm";
  const inputLight = "w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-teal-500 text-sm";
  const labelClass = "block text-slate-400 text-xs mb-1";
  const labelLight = "block text-slate-600 text-xs mb-1";
  const cardClass = "bg-white rounded-xl border border-slate-200 p-5 shadow-sm";
  const Req = () => <span className="text-red-500 font-bold"> *</span>;

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-slate-800 rounded-xl border border-slate-700 p-6 shadow-xl">
          <h1 className="text-2xl font-bold text-white mb-2 text-center">🩺 AarogyaTriage</h1>
          <p className="text-slate-400 text-center mb-6 text-sm">Medical Officer Login</p>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className={labelClass}>Username</label>
              <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required className={inputClass} placeholder="admin" />
            </div>
            <div>
              <label className={labelClass}>Password</label>
              <div className="relative">
                <input type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} required className={inputClass + " pr-10"} placeholder="Password" />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">
                  {showPassword ? "🙈" : "👁"}
                </button>
              </div>
            </div>
            {loginError && <div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">⚠️ {loginError}</div>}
            <button type="submit" className="w-full py-3 rounded-lg font-semibold bg-teal-500 hover:bg-teal-400 text-slate-900">Login</button>
            <p className="text-xs text-slate-500 text-center">Demo: admin/admin · nurse/nurse123</p>
          </form>
        </div>
      </div>
    );
  }

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
            <option value="PHC">Primary Health Centre (PHC)</option>
            <option value="CHC">Community Health Centre (CHC)</option>
            <option value="DH">District Hospital (DH)</option>
          </select>
          <select value={language} onChange={(e) => setLanguage(e.target.value)} className="bg-slate-800 border border-slate-700 text-white text-xs rounded-lg px-3 py-2">
            <option>English</option>
            <option>हिन्दी (Hindi)</option>
            <option>ଓଡ଼ିଆ (Odia)</option>
          </select>
          <button onClick={() => { setIsLoggedIn(false); setUsername(''); setPassword(''); }} className="text-xs text-slate-400 border border-slate-700 rounded-lg px-3 py-2 hover:text-white">Logout</button>
        </div>
      </div>

      <div className="bg-amber-50 border-b border-amber-200 px-6 py-2 text-xs text-amber-800">
        ⚠️ <strong>Govt / Institutional Healthcare Prototype</strong> · Strictly Non-Diagnostic Triage Decision Support
      </div>

      {/* BYPASS BANNER */}
      {!bypassActivated && (
        <div className="bg-red-600 border-b-2 border-red-800 px-6 py-3 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <span className="text-2xl animate-pulse">🚨</span>
            <div>
              <p className="text-white font-bold text-sm">EMERGENCY SITUATION?</p>
              <p className="text-red-100 text-[10px]">Skip form → Alert doctor immediately</p>
            </div>
          </div>
          <button onClick={() => setShowEmergencyBypass(true)} className="bg-white text-red-600 font-bold px-4 py-2 rounded-lg hover:bg-red-50 text-sm">⚡ ACTIVATE EMERGENCY BYPASS</button>
        </div>
      )}

      {bypassActivated && (
        <div className="bg-red-600 border-b-2 border-red-800 px-6 py-3 animate-pulse">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🚨</span>
              <div>
                <p className="text-white font-bold text-sm">EMERGENCY BYPASS ACTIVE</p>
                <p className="text-red-100 text-[10px]">Token: {patientToken} · {emergencyLog[0]?.reason}</p>
              </div>
            </div>
            <button onClick={() => setBypassActivated(false)} className="bg-white text-red-600 text-xs font-bold px-3 py-1.5 rounded">Deactivate</button>
          </div>
        </div>
      )}

      <div className="p-6 mx-auto space-y-4 max-w-6xl">
        <div className={cardClass}>
          <h2 className="text-slate-800 font-semibold mb-4">Patient Intake Form</h2>

          <form onSubmit={handleSubmit} className="space-y-5">

            {/* PATIENT BASIC DETAILS */}
            <div>
              <h3 className="text-xs font-semibold text-teal-600 uppercase mb-2">1. Patient Basic Details</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className={labelLight}>Patient Name <Req /></label>
                  <input type="text" name="patient_name" value={form.patient_name} onChange={handleChange} required className={inputLight} placeholder="Full name" />
                </div>
                <div>
                  <label className={labelLight}>Sex <Req /></label>
                  <select name="patient_sex" value={form.patient_sex} onChange={handleChange} className={inputLight} required>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Others">Others</option>
                  </select>
                </div>
                <div>
                  <label className={labelLight}>Age <Req /></label>
                  <input type="number" name="patient_age" value={form.patient_age} onChange={handleChange} required className={inputLight} placeholder="35" />
                </div>
                <div>
                  <label className={labelLight}>Mobile Number <Req /></label>
                  <input type="tel" name="patient_mobile" value={form.patient_mobile} onChange={handleChange} required className={inputLight} placeholder="98765 43210" />
                </div>
                <div>
                  <label className={labelLight}>Email (optional)</label>
                  <input type="email" name="patient_email" value={form.patient_email} onChange={handleChange} className={inputLight} placeholder="patient@email.com" />
                </div>
                <div>
                  <label className={labelLight}>Patient Category <Req /></label>
                  <div className="flex items-center gap-4 mt-2 flex-wrap">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="radio" name="patient_category" value="Pregnancy" checked={form.patient_category === 'Pregnancy'} onChange={handleChange} className="w-4 h-4 accent-teal-500" />
                      <span className="text-sm text-slate-700">Pregnancy</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="radio" name="patient_category" value="Child" checked={form.patient_category === 'Child'} onChange={handleChange} className="w-4 h-4 accent-teal-500" />
                      <span className="text-sm text-slate-700">Child</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="radio" name="patient_category" value="None" checked={form.patient_category === 'None'} onChange={handleChange} className="w-4 h-4 accent-teal-500" />
                      <span className="text-sm text-slate-700">None</span>
                    </label>
                  </div>
                </div>
              </div>
            </div>

            <div>
              <label className={labelLight}>ABHA ID / Patient ID <Req /></label>
              <input type="text" name="patient_id" value={form.patient_id} onChange={handleChange} className={inputLight} placeholder="Leave blank for auto-token" />
            </div>

            {/* SYMPTOMS */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className={labelLight}>2. Symptom Narrative (Text or Live Voice) <Req /></label>
                <span className="text-xs text-slate-400">Spoken in: {language}</span>
              </div>
              <textarea name="symptoms" value={form.symptoms} onChange={handleChange} required rows="3" className={inputLight + " resize-none"} placeholder="Describe symptoms..." />
              <div className="mt-2 flex items-center gap-2 flex-wrap">
                {!isRecording && (
                  <button type="button" onClick={startRecording} className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-teal-500 text-teal-600 text-xs font-medium hover:bg-teal-50">🎤 Record Voice</button>
                )}
                {isRecording && (
                  <>
                    <button type="button" onClick={stopRecording} className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500 text-white text-xs font-medium animate-pulse">⏹ Stop Recording</button>
                    <span className="text-xs text-red-500 flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>Listening...</span>
                  </>
                )}
              </div>
              {liveTranscript && <p className="text-xs text-teal-600 italic mt-1">👂 Hearing: "{liveTranscript}"</p>}
            </div>

            {/* FOLLOW-UP */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className={labelLight}>3. Follow-up Questions</label>
                {form.symptoms && !questionsGenerated && (
                  <button type="button" onClick={generateQuestions} className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500 hover:bg-green-600 text-white text-xs font-semibold">🤖 Generate Follow-up Questions</button>
                )}
                {questionsGenerated && (
                  <button type="button" onClick={generateQuestions} className="text-xs text-teal-600 hover:text-teal-700 underline">🔄 Refresh</button>
                )}
              </div>
              {!questionsGenerated && !form.symptoms && (
                <p className="text-xs text-slate-400 italic mt-1">Enter symptoms above, then click "Generate Follow-up Questions"</p>
              )}
              {questionsGenerated && dynamicQuestions.length > 0 && (
                <div className="space-y-3 mt-2">
                  {dynamicQuestions.map((q, idx) => (
                    <div key={q.id} className="border border-slate-200 rounded-lg p-3">
                      <p className="text-sm text-slate-700 mb-2">{idx + 1}. {q.q} <Req /></p>
                      {q.type === 'yesno' && (
                        <div className="flex gap-4">
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input type="radio" name={q.id} value="Yes" checked={followupAnswers[q.id] === 'Yes'} onChange={(e) => handleFollowupAnswer(q.id, e.target.value)} className="w-4 h-4 accent-teal-500" />
                            <span className="text-sm text-slate-600">Yes</span>
                          </label>
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input type="radio" name={q.id} value="No" checked={followupAnswers[q.id] === 'No'} onChange={(e) => handleFollowupAnswer(q.id, e.target.value)} className="w-4 h-4 accent-teal-500" />
                            <span className="text-sm text-slate-600">No</span>
                          </label>
                        </div>
                      )}
                      {q.type === 'severity' && (
                        <div className="flex gap-4 flex-wrap">
                          {['Mild', 'Moderate', 'Severe'].map(level => (
                            <label key={level} className="flex items-center gap-2 cursor-pointer">
                              <input type="radio" name={q.id} value={level} checked={followupAnswers[q.id] === level} onChange={(e) => handleFollowupAnswer(q.id, e.target.value)} className="w-4 h-4 accent-teal-500" />
                              <span className={`text-sm ${level === 'Severe' ? 'text-red-600 font-semibold' : level === 'Moderate' ? 'text-amber-600 font-semibold' : 'text-green-600 font-semibold'}`}>{level}</span>
                            </label>
                          ))}
                        </div>
                      )}
                      {q.type === 'text' && (
                        <input type="text" value={followupAnswers[q.id] || ''} onChange={(e) => handleFollowupAnswer(q.id, e.target.value)} className={inputLight} placeholder="Enter answer..." />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* MULTIMODAL */}
            <div>
              <label className={labelLight}>4. Multimodal Inputs: Lab Report OCR & Visual Inspection</label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-2">
                <div className={`border-2 border-dashed rounded-lg p-4 text-center transition ${labReportFile ? 'border-teal-500 bg-teal-50/30' : 'border-slate-300 hover:border-teal-500'}`}>
                  <div className="text-2xl mb-1">📄</div>
                  <p className="text-xs font-semibold text-slate-700 mb-1">Lab Report / Prescription (OCR)</p>
                  <p className="text-[10px] text-slate-500 mb-2">Upload PDF or image</p>
                  {!labReportFile ? (
                    <label className="inline-block cursor-pointer text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded">
                      📎 Choose File
                      <input type="file" accept="image/*,application/pdf" onChange={handleLabUpload} className="hidden" />
                    </label>
                  ) : (
                    <div className="space-y-2">
                      <p className="text-[10px] text-teal-700 font-medium truncate">✓ {labReportFile.name}</p>
                      <div className="flex gap-2 justify-center">
                        <label className="cursor-pointer text-[10px] bg-amber-100 hover:bg-amber-200 text-amber-800 font-semibold px-3 py-1.5 rounded">
                          🔄 Replace
                          <input type="file" accept="image/*,application/pdf" onChange={handleLabUpload} className="hidden" />
                        </label>
                        <button type="button" onClick={() => { setLabReportFile(null); setLabExtracted(null); }} className="text-[10px] bg-red-100 hover:bg-red-200 text-red-800 font-semibold px-3 py-1.5 rounded">🗑 Delete</button>
                      </div>
                      {labFileHistory.length > 0 && <p className="text-[9px] text-slate-500">🔄 Replaced {labFileHistory.length} time(s)</p>}
                    </div>
                  )}
                </div>
                <div className={`border-2 border-dashed rounded-lg p-4 text-center transition ${imageFile ? 'border-teal-500 bg-teal-50/30' : 'border-slate-300 hover:border-teal-500'}`}>
                  <div className="text-2xl mb-1">📷</div>
                  <p className="text-xs font-semibold text-slate-700 mb-1">Visual Symptom Photo</p>
                  <p className="text-[10px] text-slate-500 mb-2">Wound / skin / swelling</p>
                  {!imageFile ? (
                    <label className="inline-block cursor-pointer text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded">
                      📎 Choose File
                      <input type="file" accept="image/*" onChange={handleImageUpload} className="hidden" />
                    </label>
                  ) : (
                    <div className="space-y-2">
                      <p className="text-[10px] text-teal-700 font-medium truncate">✓ {imageFile.name}</p>
                      <div className="flex gap-2 justify-center">
                        <label className="cursor-pointer text-[10px] bg-amber-100 hover:bg-amber-200 text-amber-800 font-semibold px-3 py-1.5 rounded">
                          🔄 Replace
                          <input type="file" accept="image/*" onChange={handleImageUpload} className="hidden" />
                        </label>
                        <button type="button" onClick={() => { setImageFile(null); setImageObservations(null); }} className="text-[10px] bg-red-100 hover:bg-red-200 text-red-800 font-semibold px-3 py-1.5 rounded">🗑 Delete</button>
                      </div>
                      {imageFileHistory.length > 0 && <p className="text-[9px] text-slate-500">🔄 Replaced {imageFileHistory.length} time(s)</p>}
                    </div>
                  )}
                </div>
              </div>
              {isProcessingFile && <p className="text-xs text-teal-600 mt-2 animate-pulse">⏳ Processing file...</p>}
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
                  <p className="text-[10px] text-amber-600 mt-1">Confidence: {imageObservations.confidence}</p>
                </div>
              )}
            </div>

            {/* MEDICAL HISTORY */}
            <div>
              <h3 className="text-xs font-semibold text-teal-600 uppercase mb-3">5. Medical History</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                <div>
                  <label className={labelLight}>Blood Group <Req /></label>
                  <select name="blood_group" value={form.blood_group} onChange={handleChange} required className={inputLight}>
  <option value="">-- Select --</option>
  <option value="A+">A+</option>
  <option value="A-">A-</option>
  <option value="B+">B+</option>
  <option value="B-">B-</option>
  <option value="O+">O+</option>
  <option value="O-">O-</option>
  <option value="AB+">AB+</option>
  <option value="AB-">AB-</option>
  <option value="Unknown">Unknown</option>
</select>
                </div>
                <div>
                  <label className={labelLight}>Known Allergies</label>
                  <input type="text" name="known_allergies" value={form.known_allergies} onChange={handleChange} className={inputLight} placeholder="e.g., Penicillin" />
                </div>
              </div>
              <div className="mb-3">
                <label className={labelLight}>Chronic Conditions (Tick all that apply)</label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2">
                  {['Diabetes', 'Hypertension', 'Asthma', 'Heart Disease', 'Kidney Disease', 'Thyroid', 'TB', 'Cancer'].map(cond => (
                    <label key={cond} className="flex items-center gap-2 cursor-pointer border border-slate-300 rounded-lg px-3 py-2 hover:bg-slate-50">
                      <input type="checkbox" checked={form.chronic_conditions.includes(cond)}
                        onChange={(e) => {
                          const conds = form.chronic_conditions;
                          if (e.target.checked) setForm({ ...form, chronic_conditions: [...conds, cond] });
                          else setForm({ ...form, chronic_conditions: conds.filter(c => c !== cond) });
                        }} className="w-4 h-4 accent-teal-500" />
                      <span className="text-xs text-slate-700">{cond}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="md:col-span-2">
                  <label className={labelLight}>Past Surgeries (if any)</label>
                  <input type="text" name="past_surgeries" value={form.past_surgeries} onChange={handleChange} className={inputLight} placeholder="e.g., Appendectomy (2020)" />
                </div>
                <div className="md:col-span-2">
                  <label className={labelLight}>Family History</label>
                  <input type="text" name="family_history" value={form.family_history} onChange={handleChange} className={inputLight} placeholder="e.g., Father - Diabetes" />
                </div>
              </div>
            </div>

            {/* TIMELINE */}
            <div>
              <h3 className="text-xs font-semibold text-teal-600 uppercase mb-2">6. Medical Timeline Details</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className={labelLight}>Symptom Onset Date <Req /></label>
                  <input type="date" name="symptom_onset" value={form.symptom_onset} onChange={handleChange} required className={inputLight} />
                </div>
                <div>
                  <label className={labelLight}>Report Date <Req /></label>
                  <input type="date" name="report_date" value={form.report_date} onChange={handleChange} required className={inputLight} />
                </div>
                <div>
                  <label className={labelLight}>Prior Visit Date (if any)</label>
                  <input type="date" name="prior_visit_date" value={form.prior_visit_date} onChange={handleChange} className={inputLight} />
                </div>
                <div>
                  <label className={labelLight}>Current Medicines</label>
                  <input type="text" name="current_medicines" value={form.current_medicines} onChange={handleChange} className={inputLight} placeholder="e.g., Paracetamol 500mg" />
                </div>
              </div>
            </div>

            {/* VITALS */}
            <div>
              <h3 className="text-xs font-semibold text-teal-600 uppercase mb-2">7. Vital Signs</h3>
              <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                <div><label className={labelLight}>BP Sys <Req /></label><input type="number" name="bpSystolic" value={form.bpSystolic} onChange={handleChange} required className={inputLight} placeholder="124" /></div>
                <div><label className={labelLight}>BP Dia <Req /></label><input type="number" name="bpDiastolic" value={form.bpDiastolic} onChange={handleChange} required className={inputLight} placeholder="82" /></div>
                <div><label className={labelLight}>HR <Req /></label><input type="number" name="heartRate" value={form.heartRate} onChange={handleChange} required className={inputLight} placeholder="88" /></div>
                <div><label className={labelLight}>SpO2 <Req /></label><input type="number" name="spo2" value={form.spo2} onChange={handleChange} required className={inputLight} placeholder="97" /></div>
                <div><label className={labelLight}>Temp °F <Req /></label><input type="number" step="0.1" name="temperature" value={form.temperature} onChange={handleChange} required className={inputLight} placeholder="101.4" /></div>
                <div><label className={labelLight}>RR <Req /></label><input type="number" name="respiratoryRate" value={form.respiratoryRate} onChange={handleChange} required className={inputLight} placeholder="18" /></div>
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
          <div className={`rounded-xl p-4 flex items-center justify-between flex-wrap gap-2 ${
            result.priority_tier === 'P1' ? 'bg-red-500' :
            result.priority_tier === 'P2' ? 'bg-orange-500' :
            result.priority_tier === 'P3' ? 'bg-amber-400' : 'bg-green-500'
          }`}>
            <div className="flex items-center gap-4 flex-wrap">
              <span className="bg-slate-900/40 text-white text-xs font-bold px-3 py-1 rounded">{result.priority_tier} PRIORITY</span>
              <span className="text-white text-xs font-semibold">{form.patient_name} ({form.patient_age}y/{form.patient_sex[0]})</span>
              <span className="text-white text-xs font-mono">Token: {patientToken}</span>
              {result.is_bypass && <span className="bg-white text-red-600 text-[10px] font-bold px-2 py-1 rounded animate-pulse">🚨 BYPASS</span>}
            </div>
            <div className="flex items-center gap-3">
              <button onClick={handlePrint} className="bg-white text-slate-900 text-xs font-semibold px-3 py-2 rounded-lg">🖨 Print</button>
              <button onClick={() => setShowQR(!showQR)} className="bg-slate-900 text-white text-xs font-semibold px-3 py-2 rounded-lg">📱 {showQR ? 'Hide QR' : 'Show QR'}</button>
            </div>
          </div>
        )}

        {result && (() => {
          const info = PRIORITY_INFO[result.priority_tier] || PRIORITY_INFO.P3;
          const bg = result.priority_tier === 'P1' ? 'bg-red-500' : result.priority_tier === 'P2' ? 'bg-orange-500' : result.priority_tier === 'P3' ? 'bg-amber-400' : 'bg-green-500';
          const txt = result.priority_tier === 'P3' ? 'text-amber-900' : 'text-white';
          return (
            <div className={`${bg} rounded-xl px-4 pb-3 -mt-2`}>
              <h3 className={`${txt} text-lg font-bold`}>{result.priority_tier} – {info.urgency}</h3>
              <p className={`${txt} text-xs opacity-90`}>⏱ Target Queue Window: {info.wait}</p>
            </div>
          );
        })()}

        {result && (
          <div className="bg-teal-50 border border-teal-200 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-teal-800 mb-3">🏥 AI-Assigned Department & Doctor</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-slate-500 mb-1">Department</p>
                <p className="text-lg font-bold text-teal-700">{result.recommended_department}</p>
                <p className="text-[10px] text-slate-400 mt-1">{result.department_reason}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500 mb-1">Assigned Doctor</p>
                <div className="flex items-center gap-2">
                  <p className="text-lg font-bold text-slate-800">{result.assigned_doctor}</p>
                  <button onClick={() => setShowDoctorChange(!showDoctorChange)} className="text-[10px] text-teal-600 border border-teal-500 rounded px-2 py-0.5">Change</button>
                </div>
                <p className="text-[10px] text-teal-600 mt-1">✓ {result.doctor_status}</p>
              </div>
            </div>
            {showDoctorChange && (
              <div className="mt-3 pt-3 border-t border-teal-200">
                <select value={result.assigned_doctor} onChange={(e) => handleDoctorChange(e.target.value)} className="w-full bg-white border border-teal-300 rounded-lg px-3 py-2 text-sm">
                  <option value="">-- Select Doctor --</option>
                  {DOCTORS.filter(d => d.dept === result.recommended_department).map(d => (
                    <option key={d.id} value={d.name} disabled={!d.available}>{d.name} {d.available ? '✓' : `🔴 ${d.reason}`}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
        )}

        {result && result.priority_tier === 'P1' && (
          <div className="bg-red-50 border-2 border-red-300 rounded-xl p-4">
            <h3 className="text-sm font-bold text-red-800 mb-3">🚨 EMERGENCY ACTIONS</h3>
            <div className="grid grid-cols-2 gap-3">
              <button onClick={() => setShowDoctorReview(true)} className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-3 rounded-lg text-sm">👨‍⚕️ Doctor Review</button>
              <button onClick={() => setShowReferralNote(true)} className="bg-red-500 hover:bg-red-600 text-white font-semibold py-3 rounded-lg text-sm">🚑 Referral Note</button>
            </div>
          </div>
        )}

        {showQR && patientToken && (
          <div className={`${cardClass} flex flex-col items-center`}>
            <p className="text-slate-600 text-sm mb-3">📱 Scan to view live queue status</p>
            <div className="bg-white p-3 rounded-lg border border-slate-200">
              <QRCodeSVG value={`https://arogya-triage-eyyp.vercel.app/patient/${patientToken}`} size={180} />
            </div>
            <p className="text-slate-500 text-xs mt-3 font-mono">/patient/{patientToken}</p>
          </div>
        )}

        {result && Object.keys(followupAnswers).length > 0 && (
          <div className={cardClass}>
            <h3 className="text-slate-800 font-semibold text-sm mb-3">📝 Follow-up Answers</h3>
            <div className="space-y-2">
              {dynamicQuestions.map(q => (
                <div key={q.id} className="flex justify-between text-xs border-b border-slate-100 pb-2">
                  <span className="text-slate-600 flex-1">{q.q}</span>
                  <span className={`font-semibold ml-3 ${
                    followupAnswers[q.id] === 'Yes' || followupAnswers[q.id] === 'Severe' ? 'text-red-600' :
                    followupAnswers[q.id] === 'No' || followupAnswers[q.id] === 'Mild' ? 'text-green-600' :
                    followupAnswers[q.id] === 'Moderate' ? 'text-amber-600' : 'text-slate-700'
                  }`}>{followupAnswers[q.id] || '-'}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {result && (
          <div className={cardClass}>
            <h3 className="text-slate-800 font-semibold text-sm mb-3">📋 Medical History</h3>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {form.blood_group && (
                <div className="border border-slate-200 rounded-lg p-2">
                  <p className="text-slate-500 text-[10px] uppercase">Blood Group</p>
                  <p className="text-slate-900 font-bold">{form.blood_group}</p>
                </div>
              )}
              {form.known_allergies && (
                <div className="border border-red-200 bg-red-50 rounded-lg p-2">
                  <p className="text-red-500 text-[10px] uppercase">⚠️ Allergies</p>
                  <p className="text-red-700 font-semibold text-xs">{form.known_allergies}</p>
                </div>
              )}
              {form.chronic_conditions.length > 0 && (
                <div className="border border-amber-200 bg-amber-50 rounded-lg p-2 col-span-2">
                  <p className="text-amber-600 text-[10px] uppercase">Chronic Conditions</p>
                  <p className="text-amber-800 font-semibold text-xs">{form.chronic_conditions.join(' · ')}</p>
                </div>
              )}
              {form.past_surgeries && (
                <div className="border border-slate-200 rounded-lg p-2 col-span-2">
                  <p className="text-slate-500 text-[10px] uppercase">Past Surgeries</p>
                  <p className="text-slate-900 text-xs">{form.past_surgeries}</p>
                </div>
              )}
              {form.family_history && (
                <div className="border border-slate-200 rounded-lg p-2 col-span-2">
                  <p className="text-slate-500 text-[10px] uppercase">Family History</p>
                  <p className="text-slate-900 text-xs">{form.family_history}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {result && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex gap-3">
            <span className="text-amber-600 text-xl">⚠️</span>
            <div>
              <h4 className="text-amber-900 font-bold text-xs uppercase mb-1">Statutory Non-Diagnostic Notice:</h4>
              <p className="text-amber-800 text-xs leading-relaxed">CLINICAL ADVISORY ONLY. Must be verified by a licensed Medical Officer.</p>
            </div>
          </div>
        )}

        {result && result.timeline && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className={cardClass}>
              <h3 className="text-slate-800 font-semibold text-sm mb-4">📅 Clinical Timeline</h3>
              <div className="space-y-3">
                {result.timeline.map((event, i) => (
                  <div key={i} className="flex gap-3">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs shrink-0 ${
                      event.color === 'red' ? 'bg-red-100 border-2 border-red-500' :
                      event.color === 'teal' ? 'bg-teal-100 border-2 border-teal-500' :
                      event.color === 'amber' ? 'bg-amber-100 border-2 border-amber-500' :
                      event.color === 'purple' ? 'bg-purple-100 border-2 border-purple-500' :
                      event.color === 'blue' ? 'bg-blue-100 border-2 border-blue-500' :
                      'bg-slate-100 border-2 border-slate-400'
                    }`}>{event.icon}</div>
                    <div className="flex-1">
                      <div className="flex items-baseline gap-2">
                        <span className="text-xs font-bold text-slate-800">{event.label}</span>
                        <span className="text-[10px] text-slate-400 font-mono">{event.date}</span>
                      </div>
                      <p className="text-xs text-slate-600">{event.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className={cardClass}>
              <h3 className="text-slate-800 font-semibold text-sm mb-4">🩺 Vitals & Physiological State</h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="border border-slate-200 rounded-lg p-3"><p className="text-slate-500 text-[10px] uppercase">BP</p><p className="text-slate-900 font-semibold text-sm">{result.vitals_summary?.bp}</p></div>
                <div className="border border-slate-200 rounded-lg p-3"><p className="text-slate-500 text-[10px] uppercase">HR</p><p className="text-slate-900 font-semibold text-sm">{result.vitals_summary?.hr}</p></div>
                <div className="border border-slate-200 rounded-lg p-3"><p className="text-slate-500 text-[10px] uppercase">SpO2</p><p className="text-slate-900 font-semibold text-sm">{result.vitals_summary?.spo2}</p></div>
                <div className="border border-slate-200 rounded-lg p-3"><p className="text-slate-500 text-[10px] uppercase">Temp</p><p className="text-slate-900 font-semibold text-sm">{result.vitals_summary?.temp}</p></div>
              </div>
            </div>
          </div>
        )}

        {emergencyLog.length > 0 && (
          <div className="bg-red-50 border-2 border-red-300 rounded-xl p-4">
            <h3 className="text-sm font-bold text-red-800 mb-3">🚨 Emergency Bypass Audit Log</h3>
            {emergencyLog.map((log, i) => (
              <div key={i} className="bg-white border border-red-200 rounded-lg p-3 mb-2 last:mb-0">
                <div className="flex justify-between items-start flex-wrap gap-2">
                  <div>
                    <p className="text-xs font-bold text-red-700 font-mono">{log.token}</p>
                    <p className="text-xs text-slate-600 mt-1"><strong>Reason:</strong> {log.reason}</p>
                    <p className="text-xs text-slate-600"><strong>Location:</strong> {log.location}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-slate-500">{log.time}</p>
                    <p className="text-[10px] text-slate-500">By: {log.nurse}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {showDoctorReview && result && (
          <DoctorReview
            patient={{
              name: form.patient_name, age: form.patient_age, sex: form.patient_sex,
              token: patientToken, priority: result.priority_tier, symptoms: form.symptoms,
              bp: `${form.bpSystolic}/${form.bpDiastolic}`, hr: form.heartRate, spo2: form.spo2,
              temp: form.temperature, rr: form.respiratoryRate, mews: result.vitals_summary?.mews || 0,
              followup: followupAnswers, labReport: labExtracted, imageAnalysis: imageObservations,
              timeline: result.timeline.map(t => ({ time: t.date, event: t.description })),
            }}
            onClose={() => setShowDoctorReview(false)}
          />
        )}

        {showReferralNote && result && (
          <ReferralNote
            patient={{
              name: form.patient_name, age: form.patient_age, sex: form.patient_sex,
              token: patientToken, bp: `${form.bpSystolic}/${form.bpDiastolic}`,
              hr: form.heartRate, spo2: form.spo2,
              timeline: result.timeline.map(t => ({ time: t.date, event: t.description })),
            }}
            onClose={() => setShowReferralNote(false)}
          />
        )}

      </div>

      {/* BYPASS MODAL */}
      {showEmergencyBypass && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border-4 border-red-500">
            <div className="text-center mb-4">
              <div className="text-5xl mb-2">🚨</div>
              <h2 className="text-xl font-bold text-red-600">EMERGENCY BYPASS</h2>
              <p className="text-xs text-slate-500 mt-1">Ye action immediately doctor ko alert karega</p>
            </div>
            <div className="mb-4">
              <label className="text-xs font-semibold text-slate-700 mb-2 block">Emergency Reason <span className="text-red-500">*</span></label>
              <select value={bypassReason} onChange={(e) => setBypassReason(e.target.value)} className="w-full border-2 border-red-300 rounded-lg px-3 py-2 text-sm focus:border-red-500 focus:outline-none">
                <option value="">-- Select Reason --</option>
                {BYPASS_REASONS.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div className="mb-4">
              <label className="text-xs font-semibold text-slate-700 mb-2 block">Patient Location</label>
              <input type="text" value={bypassLocation} onChange={(e) => setBypassLocation(e.target.value)} placeholder="e.g., Casualty Room 1" className="w-full border-2 border-red-300 rounded-lg px-3 py-2 text-sm focus:border-red-500 focus:outline-none" />
            </div>
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
              <p className="text-xs text-red-700">⚠️ <strong>Confirm karein:</strong> Ye action:</p>
              <ul className="text-[10px] text-red-600 mt-1 space-y-0.5">
                <li>• Duty doctor ko INSTANT alert bhejega</li>
                <li>• Patient ko queue me TOP priority dega</li>
                <li>• Audit log me record hoga</li>
              </ul>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setShowEmergencyBypass(false)} className="flex-1 py-3 rounded-lg bg-slate-200 text-slate-700 font-semibold text-sm">Cancel</button>
              <button onClick={activateBypass} className="flex-1 py-3 rounded-lg bg-red-600 text-white font-bold text-sm hover:bg-red-700">🚨 ACTIVATE BYPASS</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
