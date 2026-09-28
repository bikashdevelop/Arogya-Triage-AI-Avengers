@echo off
echo Creating NurseIntake.jsx...

(
echo import React, { useState } from 'react';
echo import axios from 'axios';
echo const API_BASE = 'http://localhost:8000';
echo.
echo export default function NurseIntake() {
echo   const [isLoggedIn, setIsLoggedIn] = useState(false);
echo   const [username, setUsername] = useState('');
echo   const [password, setPassword] = useState('');
echo   const [loginError, setLoginError] = useState('');
echo   const [form, setForm] = useState({ symptoms: '', bpSystolic: '', bpDiastolic: '', heartRate: '', spo2: '', temperature: '', respiratoryRate: '' });
echo   const [result, setResult] = useState(null);
echo   const [isSubmitting, setIsSubmitting] = useState(false);
echo   const [error, setError] = useState('');
echo.
echo   const handleLogin = async (e) =^> {
echo     e.preventDefault();
echo     setLoginError('');
echo     const formData = new FormData();
echo     formData.append('username', username);
echo     formData.append('password', password);
echo     formData.append('grant_type', 'password');
echo     try {
echo       await axios.post(API_BASE + '/api/login', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
echo       setIsLoggedIn(true);
echo     } catch (err) {
echo       setLoginError(err.response?.data?.detail || 'Login failed. Check credentials or backend.');
echo     }
echo   };
echo.
echo   const handleChange = (e) =^> setForm({ ...form, [e.target.name]: e.target.value });
echo.
echo   const handleSubmit = async (e) =^> {
echo     e.preventDefault();
echo     setIsSubmitting(true); setError(''); setResult(null);
echo     const payload = { symptoms: form.symptoms, vitals: { bp_systolic: parseInt(form.bpSystolic), bp_diastolic: parseInt(form.bpDiastolic), heart_rate: parseInt(form.heartRate), spo2: parseInt(form.spo2), temperature: parseFloat(form.temperature), respiratory_rate: parseInt(form.respiratoryRate) } };
echo     try {
echo       const response = await axios.post(API_BASE + '/api/triage', payload);
echo       setResult(response.data);
echo     } catch (err) {
echo       setError(err.response?.data?.message || 'Failed to submit triage request.');
echo     } finally { setIsSubmitting(false); }
echo   };
echo.
echo   const inputClass = "w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 transition-colors";
echo   const labelClass = "block text-slate-400 text-sm mb-1";
echo   const cardClass = "w-full max-w-2xl bg-slate-800 rounded-xl border border-slate-700 p-6 shadow-xl";
echo.
echo   if (!isLoggedIn) {
echo     return (
echo       ^<div className="min-h-screen bg-slate-900 flex items-center justify-center p-4"^>
echo         ^<div className={cardClass}^>
echo           ^<h1 className="text-2xl font-bold text-white mb-2 text-center"^>🩺 AarogyaTriage^</h1^>
echo           ^<p className="text-slate-400 text-center mb-6"^>Medical Officer Login^</p^>
echo           ^<form onSubmit={handleLogin} className="space-y-4"^>
echo             ^<div^>
echo               ^<label className={labelClass}^>Username^</label^>
echo               ^<input type="text" value={username} onChange={(e) =^> setUsername(e.target.value)} required className={inputClass} placeholder="Enter username" /^>
echo             ^</div^>
echo             ^<div^>
echo               ^<label className={labelClass}^>Password^</label^>
echo               ^<input type="password" value={password} onChange={(e) =^> setPassword(e.target.value)} required className={inputClass} placeholder="Enter password" /^>
echo             ^</div^>
echo             {loginError ^&^& ^<div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm"^>⚠️ {loginError}^</div^>}
echo             ^<button type="submit" className="w-full py-3 rounded-lg font-semibold bg-teal-500 hover:bg-teal-400 text-slate-900 transition-colors"^>Login^</button^>
echo           ^</form^>
echo         ^</div^>
echo       ^</div^>
echo     );
echo   }
echo.
echo   return (
echo     ^<div className="min-h-screen bg-slate-900 p-6 flex flex-col items-center font-sans"^>
echo       ^<div className="w-full max-w-2xl flex justify-between items-center mb-6"^>
echo         ^<h1 className="text-xl font-bold text-white"^>📋 Nurse Intake ^& Triage^</h1^>
echo         ^<button onClick={() =^> setIsLoggedIn(false)} className="text-sm text-slate-400 hover:text-white transition-colors"^>Logout^</button^>
echo       ^</div^>
echo       ^<div className={cardClass}^>
echo         ^<form onSubmit={handleSubmit} className="space-y-6"^>
echo           ^<div^>
echo             ^<label className={labelClass}^>Patient Symptoms^</label^>
echo             ^<textarea name="symptoms" value={form.symptoms} onChange={handleChange} required rows="4" className={inputClass + " resize-none"} placeholder="e.g., Crushing chest pain radiating to left jaw, dyspnea for 45 mins." /^>
echo           ^</div^>
echo           ^<div className="pt-4 border-t border-slate-700"^>
echo             ^<h2 className="text-teal-400 text-sm font-semibold uppercase tracking-wider mb-4"^>Vital Signs^</h2^>
echo             ^<div className="grid grid-cols-2 md:grid-cols-3 gap-4"^>
echo               ^<div^>^<label className={labelClass}^>BP Systolic^</label^>^<input type="number" name="bpSystolic" value={form.bpSystolic} onChange={handleChange} required className={inputClass} placeholder="120" /^>^</div^>
echo               ^<div^>^<label className={labelClass}^>BP Diastolic^</label^>^<input type="number" name="bpDiastolic" value={form.bpDiastolic} onChange={handleChange} required className={inputClass} placeholder="80" /^>^</div^>
echo               ^<div^>^<label className={labelClass}^>Heart Rate^</label^>^<input type="number" name="heartRate" value={form.heartRate} onChange={handleChange} required className={inputClass} placeholder="88" /^>^</div^>
echo               ^<div^>^<label className={labelClass}^>SpO2 (%^^)^</label^>^<input type="number" name="spo2" value={form.spo2} onChange={handleChange} required className={inputClass} placeholder="98" /^>^</div^>
echo               ^<div^>^<label className={labelClass}^>Temperature (°F)^</label^>^<input type="number" step="0.1" name="temperature" value={form.temperature} onChange={handleChange} required className={inputClass} placeholder="98.6" /^>^</div^>
echo               ^<div^>^<label className={labelClass}^>Respiratory Rate^</label^>^<input type="number" name="respiratoryRate" value={form.respiratoryRate} onChange={handleChange} required className={inputClass} placeholder="18" /^>^</div^>
echo             ^</div^>
echo           ^</div^>
echo           {error ^&^& ^<div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm"^>❌ {error}^</div^>}
echo           ^<button type="submit" disabled={isSubmitting} className={"w-full py-4 rounded-xl font-bold text-lg transition-all " + (isSubmitting ? 'bg-slate-600 text-slate-400 cursor-not-allowed' : 'bg-teal-500 hover:bg-teal-400 text-slate-900')}^>{isSubmitting ? 'ANALYZING...' : 'SUBMIT TRIAGE REQUEST'}^</button^>
echo         ^</form^>
echo       ^</div^>
echo       {result ^&^& (
echo         ^<div className="w-full max-w-2xl mt-6 bg-slate-800 rounded-xl border border-slate-700 p-6 space-y-5 shadow-xl"^>
echo           ^<div className="flex items-center justify-between border-b border-slate-700 pb-3"^>
echo             ^<h2 className="text-lg font-semibold text-teal-400"^>📊 Triage Assessment^</h2^>
echo             {result.priority_tier ^&^& (
echo               ^<span className="px-3 py-1 rounded-full text-xs font-bold bg-teal-500 text-slate-900"^>{result.priority_tier}^</span^>
echo             )}
echo           ^</div^>
echo           {result.summary ^&^& (
echo             ^<div^>
echo               ^<h3 className="text-sm font-semibold text-slate-300 mb-1"^>AI Summary^</h3^>
echo               ^<p className="text-slate-400 text-sm leading-relaxed"^>{result.summary}^</p^>
echo             ^</div^>
echo           )}
echo           {result.timeline ^&^& result.timeline.length ^> 0 ^&^& (
echo             ^<div^>
echo               ^<h3 className="text-sm font-semibold text-slate-300 mb-2"^>Clinical Timeline^</h3^>
echo               ^<div className="space-y-3"^>
echo                 {result.timeline.map((event, index) =^> (
echo                   ^<div key={index} className="flex gap-3 items-start"^>
echo                     ^<div className="w-20 text-xs text-slate-500 font-mono pt-0.5"^>{event.time}^</div^>
echo                     ^<div className="w-2 h-2 rounded-full bg-teal-500 mt-1.5 shrink-0"^>^</div^>
echo                     ^<div className="text-sm text-slate-300"^>{event.description}^</div^>
echo                   ^</div^>
echo                 ))}
echo               ^</div^>
echo             ^</div^>
echo           )}
echo         ^</div^>
echo       )}
echo     ^</div^>
echo   );
echo }
) > src\NurseIntake.jsx

echo Updating App.jsx...
(
echo import React from 'react';
echo import NurseIntake from './NurseIntake';
echo export default function App() { return ^<NurseIntake /^>; }
) > src\App.jsx

echo Updating tailwind.config.js...
(
echo export default {
echo   content: ["./index.html", "./src/**/*.{js,jsx}"],
echo   theme: { extend: {} },
echo   plugins: [],
echo }
) > tailwind.config.js

echo Updating src\index.css...
(
echo @tailwind base;
echo @tailwind components;
echo @tailwind utilities;
) > src\index.css

echo.
echo ================================
echo All files updated successfully!
echo ================================
pause
