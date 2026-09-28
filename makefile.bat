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
echo       setLoginError(err.response?.data?.detail || 'Login failed.');
echo     }
echo   };
echo.
echo   const handleChange = (e) =^> setForm({ ...form, [e.target.name]: e.target.value });
echo.
echo   const handleSubmit = async (e) =^> {
echo     e.preventDefault(); setIsSubmitting(true); setError(''); setResult(null);
echo     const payload = { symptoms: form.symptoms, vitals: { bp_systolic: parseInt(form.bpSystolic), bp_diastolic: parseInt(form.bpDiastolic), heart_rate: parseInt(form.heartRate), spo2: parseInt(form.spo2), temperature: parseFloat(form.temperature), respiratory_rate: parseInt(form.respiratoryRate) } };
echo     try {
echo       const response = await axios.post(API_BASE + '/api/triage', payload);
echo       setResult(response.data);
echo     } catch (err) {
echo       setError(err.response?.data?.message || 'Failed to submit triage request.');
echo     } finally { setIsSubmitting(false); }
echo   };
echo.
echo   const inputClass = "w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-teal-500";
echo   const labelClass = "block text-slate-400 text-sm mb-1";
echo   const cardClass = "w-full max-w-2xl bg-slate-800 rounded-xl border border-slate-700 p-6 shadow-xl";
echo.
echo   if (!isLoggedIn) {
echo     return (
echo       ^<div className="min-h-screen bg-slate-900 flex items-center justify-center p-4"^>
echo         ^<div className={cardClass}^>
echo           ^<h1 className="text-2xl font-bold text-white mb-2 text-center"^>AarogyaTriage^</h1^>
echo           ^<p className="text-slate-400 text-center mb-6"^>Medical Officer Login^</p^>
echo           ^<form onSubmit={handleLogin} className="space-y-4"^>
echo             ^<input type="text" value={username} onChange={(e) =^> setUsername(e.target.value)} required className={inputClass} placeholder="Username" /^>
echo             ^<input type="password" value={password} onChange={(e) =^> setPassword(e.target.value)} required className={inputClass} placeholder="Password" /^>
echo             {loginError ^&^& ^<div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm"^>{loginError}^</div^>}
echo             ^<button type="submit" className="w-full py-3 rounded-lg font-semibold bg-teal-500 hover:bg-teal-400 text-slate-900"^>Login^</button^>
echo           ^</form^>
echo         ^</div^>
echo       ^</div^>
echo     );
echo   }
echo.
echo   return (
echo     ^<div className="min-h-screen bg-slate-900 p-6 flex flex-col items-center"^>
echo       ^<div className="w-full max-w-2xl flex justify-between items-center mb-6"^>
echo         ^<h1 className="text-xl font-bold text-white"^>Nurse Intake ^& Triage^</h1^>
echo         ^<button onClick={() =^> setIsLoggedIn(false)} className="text-sm text-slate-400 hover:text-white"^>Logout^</button^>
echo       ^</div^>
echo       ^<div className={cardClass}^>
echo         ^<form onSubmit={handleSubmit} className="space-y-6"^>
echo           ^<textarea name="symptoms" value={form.symptoms} onChange={handleChange} required rows="4" className={inputClass + " resize-none"} placeholder="Patient symptoms..." /^>
echo           ^<div className="pt-4 border-t border-slate-700"^>
echo             ^<h2 className="text-teal-400 text-sm font-semibold uppercase mb-4"^>Vital Signs^</h2^>
echo             ^<div className="grid grid-cols-2 md:grid-cols-3 gap-4"^>
echo               ^<input type="number" name="bpSystolic" value={form.bpSystolic} onChange={handleChange} required className={inputClass} placeholder="BP Systolic" /^>
echo               ^<input type="number" name="bpDiastolic" value={form.bpDiastolic} onChange={handleChange} required className={inputClass} placeholder="BP Diastolic" /^>
echo               ^<input type="number" name="heartRate" value={form.heartRate} onChange={handleChange} required className={inputClass} placeholder="Heart Rate" /^>
echo               ^<input type="number" name="spo2" value={form.spo2} onChange={handleChange} required className={inputClass} placeholder="SpO2" /^>
echo               ^<input type="number" step="0.1" name="temperature" value={form.temperature} onChange={handleChange} required className={inputClass} placeholder="Temperature" /^>
echo               ^<input type="number" name="respiratoryRate" value={form.respiratoryRate} onChange={handleChange} required className={inputClass} placeholder="Respiratory Rate" /^>
echo             ^</div^>
echo           ^</div^>
echo           {error ^&^& ^<div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm"^>{error}^</div^>}
echo           ^<button type="submit" disabled={isSubmitting} className="w-full py-4 rounded-xl font-bold text-lg bg-teal-500 hover:bg-teal-400 text-slate-900 disabled:bg-slate-600"^>{isSubmitting ? 'ANALYZING...' : 'SUBMIT TRIAGE'}^</button^>
echo         ^</form^>
echo       ^</div^>
echo       {result ^&^& (
echo         ^<div className="w-full max-w-2xl mt-6 bg-slate-800 rounded-xl border border-slate-700 p-6 space-y-4"^>
echo           ^<h2 className="text-lg font-semibold text-teal-400"^>Triage Result^</h2^>
echo           {result.priority_tier ^&^& ^<span className="inline-block px-3 py-1 rounded-full text-xs font-bold bg-teal-500 text-slate-900"^>{result.priority_tier}^</span^>}
echo           {result.summary ^&^& ^<p className="text-slate-400 text-sm"^>{result.summary}^</p^>}
echo           {result.timeline ^&^& result.timeline.map((event, i) =^> (
echo             ^<div key={i} className="flex gap-3 text-sm text-slate-300"^>
echo               ^<span className="text-slate-500 font-mono w-20"^>{event.time}^</span^>
echo               ^<span^>{event.description}^</span^>
echo             ^</div^>
echo           ))}
echo         ^</div^>
echo       )}
echo     ^</div^>
echo   );
echo }
) > src\NurseIntake.jsx
echo Done!
pause
