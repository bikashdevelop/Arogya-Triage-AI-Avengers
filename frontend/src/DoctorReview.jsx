import React, { useState, useEffect } from 'react';
import api from './api/client';

const TRIAGE_META = {
  P1: { label: 'Emergency', wait: '0–5 min', color: 'bg-red-500', border: 'border-red-500', bg: 'bg-red-50', text: 'text-red-700' },
  P2: { label: 'Very Urgent', wait: '10–30 min', color: 'bg-orange-500', border: 'border-orange-500', bg: 'bg-orange-50', text: 'text-orange-700' },
  P3: { label: 'Urgent', wait: '30–60 min', color: 'bg-amber-400', border: 'border-amber-400', bg: 'bg-amber-50', text: 'text-amber-800' },
  P4: { label: 'Standard', wait: '120 min', color: 'bg-green-500', border: 'border-green-500', bg: 'bg-green-50', text: 'text-green-700' },
};

const getVitalColor = (type, value) => {
  const val = parseFloat(value);
  if (isNaN(val)) return 'bg-slate-50 border-slate-200 text-slate-700';
  switch(type) {
    case 'bp_sys': return (val > 140 || val < 90) ? 'bg-red-50 border-red-200 text-red-700' : 'bg-green-50 border-green-200 text-green-700';
    case 'bp_dia': return (val > 90 || val < 60) ? 'bg-red-50 border-red-200 text-red-700' : 'bg-green-50 border-green-200 text-green-700';
    case 'hr': return (val > 100 || val < 60) ? 'bg-red-50 border-red-200 text-red-700' : 'bg-green-50 border-green-200 text-green-700';
    case 'spo2': return (val < 95) ? 'bg-red-50 border-red-200 text-red-700' : 'bg-green-50 border-green-200 text-green-700';
    case 'temp': return (val > 100.4 || val < 97) ? 'bg-amber-50 border-amber-200 text-amber-700' : 'bg-green-50 border-green-200 text-green-700';
    case 'rr': return (val > 20 || val < 12) ? 'bg-amber-50 border-amber-200 text-amber-700' : 'bg-green-50 border-green-200 text-green-700';
    case 'mews': return (val > 0) ? 'bg-red-50 border-red-200 text-red-700' : 'bg-green-50 border-green-200 text-green-700';
    default: return 'bg-slate-50 border-slate-200 text-slate-700';
  }
};

// 👈 NEW: format ISO timestamp for display in header
const fmtDateTime = (iso) => {
  if (!iso) return null;
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return null;
    return d.toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: true,
    });
  } catch {
    return null;
  }
};

export default function DoctorReview({ recordId, labReport, imageAnalysis, onClose, onSaved }) {
  const [recordDetails, setRecordDetails] = useState(null);
  const [referral, setReferral] = useState(null);
  const [referralNote, setReferralNote] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showOriginal, setShowOriginal] = useState(false);

  const [decision, setDecision] = useState('approve');
  const [finalPriority, setFinalPriority] = useState('P3');
  const [action, setAction] = useState('opd');
  const [notes, setNotes] = useState('');
  const [medicines, setMedicines] = useState([]);
  const [newMedicine, setNewMedicine] = useState({ name: '', dosage: '', frequency: '', duration: '' });
  const [submitting, setSubmitting] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState('');

  const [showReferralForm, setShowReferralForm] = useState(false);
  const [referralDetails, setReferralDetails] = useState({
    currentLocation: 'Casualty Room 1',
    destinationFacility: 'District Hospital, Rourkela',
    ambulanceNumber: 'OD-14-AB-1234',
    transferETA: '45',
    attendingTeam: 'Emergency + Neurosurgery',
    bedNumber: 'ICU Bed 3',
  });

  useEffect(() => {
    if (!recordId) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError('');
      try {
        const res = await api.get(`/api/triage/${recordId}`);
        if (cancelled) return;
        const data = res.data.data;
        setRecordDetails(data);
        setFinalPriority(data.ai_priority || 'P3');

        try {
          const r = await api.get(`/api/referral/recommend/${recordId}`);
          if (!cancelled) setReferral(r.data.recommendation);
        } catch (e) {
          // referral optional
        }
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.detail || 'Failed to load record');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [recordId]);

  const addMedicine = () => {
    if (!newMedicine.name.trim()) return;
    setMedicines([...medicines, { ...newMedicine }]);
    setNewMedicine({ name: '', dosage: '', frequency: '', duration: '' });
  };
  const removeMedicine = (i) => setMedicines(medicines.filter((_, idx) => idx !== i));

  const generateReferralNote = async () => {
    try {
      const res = await api.get(`/api/triage/${recordId}/referral-note`);
      setReferralNote(res.data.referral_note);
    } catch (err) {
      alert('Failed to generate referral note');
    }
  };

  const handleSave = async () => {
    setSubmitting(true);
    setSaveSuccess('');
    try {
      const actionMap = { opd: 'Send to OPD', chemist: 'Send to Chemist', admit: 'Send to ICU', refer: 'Refer to DH' };
      const payload = {
        patient_id: parseInt(recordId),
        token: null,
        doctor_name: sessionStorage.getItem('full_name') || 'Doctor',
        decision,
        final_priority: finalPriority,
        action: actionMap[action] || action,
        clinical_notes: notes,
        medicines: action === 'chemist' ? medicines : [],
      };
      const res = await api.post('/api/doctor/decision-full', payload);
      setSaveSuccess(res.data?.message || 'Decision saved');
      if (onSaved) onSaved();
      setTimeout(() => onClose && onClose(), 1500);
    } catch (err) {
      alert('Failed to save: ' + (err.response?.data?.detail || 'Unknown error'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleSendReferral = async () => {
    try {
      setSubmitting(true);
      const payload = {
        patient_id: parseInt(recordId),
        token: null,
        doctor_name: sessionStorage.getItem('full_name') || 'Doctor',
        decision: 'override',
        final_priority: finalPriority,
        action: 'Refer to DH',
        clinical_notes: `Referral: ${referralDetails.currentLocation} → ${referralDetails.destinationFacility}. Ambulance: ${referralDetails.ambulanceNumber}. ETA: ${referralDetails.transferETA} min. Team: ${referralDetails.attendingTeam}. Bed: ${referralDetails.bedNumber}. Notes: ${notes}`,
        medicines: [],
      };
      const res = await api.post('/api/doctor/decision-full', payload);
      setSaveSuccess(res.data?.message || 'Referral sent');
      setShowReferralForm(false);
      if (onSaved) onSaved();
      setTimeout(() => onClose && onClose(), 1500);
    } catch (err) {
      alert('Failed to send referral: ' + (err.response?.data?.detail || 'Unknown error'));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"><div className="bg-white rounded-xl px-8 py-6 text-slate-600 text-sm">Loading record…</div></div>;
  if (error || !recordDetails) return <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"><div className="bg-white rounded-xl max-w-md w-full p-6 text-center"><p className="text-red-600 text-sm mb-4">{error || 'Record not found'}</p><button onClick={onClose} className="px-4 py-2 text-sm bg-slate-800 text-white rounded-lg">Close</button></div></div>;

  const meta = TRIAGE_META[recordDetails.ai_priority] || TRIAGE_META.P4;
  const vitals = recordDetails.vitals || {};
  const englishText = recordDetails.translated_text || recordDetails.symptoms_text;
  const originalText = recordDetails.original_transcript || recordDetails.symptoms_text;
  const createdAt = fmtDateTime(recordDetails.created_at);   // 👈 NEW
  const reviewedAt = fmtDateTime(recordDetails.reviewed_at); // 👈 NEW

  return (
    <div className="fixed inset-0 bg-black/70 flex items-start justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl max-w-3xl w-full my-8 shadow-2xl">

        <div className="bg-slate-900 text-white px-6 py-4 rounded-t-2xl flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold">🩺 Patient Review</h2>
            <p className="text-xs text-slate-300">{recordDetails.patient?.name || 'Unknown'} ({recordDetails.patient?.age}y/{recordDetails.patient?.sex})</p>
            {/* 👈 NEW: Visit date/time in the header */}
            {(createdAt || reviewedAt) && (
              <p className="text-[10px] text-slate-400 mt-1">
                {createdAt && <>🕒 Visit: {createdAt}</>}
                {createdAt && reviewedAt && <> · </>}
                {reviewedAt && <>✅ Reviewed: {reviewedAt}</>}
              </p>
            )}
          </div>
          <button onClick={onClose} className="text-white text-2xl hover:text-red-400">×</button>
        </div>

        <div className="p-6 space-y-5">

          <div className={`flex items-center gap-3 px-4 py-3 rounded-lg border-2 ${meta.border} ${meta.bg}`}>
            <span className={`${meta.color} text-white text-xs font-bold px-3 py-1 rounded`}>{recordDetails.ai_priority}</span>
            <div>
              <p className={`font-bold text-sm ${meta.text}`}>{meta.label}</p>
              <p className="text-[10px] text-slate-600">{recordDetails.patient_id || recordId} · Target: {meta.wait}</p>
            </div>
            <div className="ml-auto text-right">
              <p className="text-[10px] text-slate-500 uppercase">MEWS</p>
              <p className="text-2xl font-bold text-slate-900">{recordDetails.mews_score || 0}</p>
            </div>
          </div>

          {recordDetails.patient?.allergies && recordDetails.patient.allergies.toLowerCase() !== 'none' && (
            <div className="flex items-center gap-3 bg-red-100 border-2 border-red-500 rounded-lg px-4 py-3">
              <span className="text-2xl">⚠️</span>
              <div>
                <p className="text-red-800 font-bold text-sm">ALLERGY ALERT</p>
                <p className="text-red-700 text-xs">{recordDetails.patient.allergies}</p>
              </div>
            </div>
          )}

          <div>
            <div className="flex justify-between items-center mb-2">
              <h3 className="text-xs font-semibold text-slate-600 uppercase">📋 Symptoms</h3>
              <button
                onClick={() => setShowOriginal(!showOriginal)}
                className="text-[10px] bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-600 px-2 py-1 rounded"
              >
                {showOriginal ? '🌐 View English Translation' : '🌐 View Original Transcript'}
              </button>
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
              <p className="text-sm text-slate-700 italic">"{showOriginal ? originalText : englishText}"</p>
            </div>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-slate-600 uppercase mb-2">🩺 Vitals</h3>
            <div className="grid grid-cols-3 gap-2">
              <div className={`border rounded-lg p-2 ${getVitalColor('bp_sys', vitals.bp_systolic)}`}><p className="text-[10px] uppercase opacity-80">BP</p><p className="text-sm font-bold">{vitals.bp_systolic}/{vitals.bp_diastolic}</p></div>
              <div className={`border rounded-lg p-2 ${getVitalColor('hr', vitals.heart_rate)}`}><p className="text-[10px] uppercase opacity-80">HR</p><p className="text-sm font-bold">{vitals.heart_rate}</p></div>
              <div className={`border rounded-lg p-2 ${getVitalColor('spo2', vitals.spo2)}`}><p className="text-[10px] uppercase opacity-80">SpO2</p><p className="text-sm font-bold">{vitals.spo2}%</p></div>
              <div className={`border rounded-lg p-2 ${getVitalColor('temp', vitals.temperature_f)}`}><p className="text-[10px] uppercase opacity-80">Temp</p><p className="text-sm font-bold">{vitals.temperature_f}°F</p></div>
              <div className={`border rounded-lg p-2 ${getVitalColor('rr', vitals.respiratory_rate)}`}><p className="text-[10px] uppercase opacity-80">RR</p><p className="text-sm font-bold">{vitals.respiratory_rate}</p></div>
              <div className={`border rounded-lg p-2 ${getVitalColor('mews', recordDetails.mews_score)}`}><p className="text-[10px] uppercase opacity-80">MEWS</p><p className="text-sm font-bold">{recordDetails.mews_score || 0}</p></div>
            </div>
          </div>

          {recordDetails.summary && (
            <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
              <h3 className="text-sm font-bold text-teal-800 mb-2">🤖 AI Summary (Advisory)</h3>
              <p className="text-xs text-teal-900 whitespace-pre-wrap">{recordDetails.summary}</p>
            </div>
          )}

          {labReport && !labReport.error && labReport.extracted_values?.length > 0 && (
            <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
              <h3 className="text-sm font-bold text-teal-800 mb-2">📄 Lab Report (OCR Extracted)</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-teal-900">
                {labReport.extracted_values.map((item, i) => (
                  <div key={i} className="flex justify-between border-b border-teal-100 pb-1">
                    <span className="text-slate-600">{item.name}:</span>
                    <strong>{item.value} {item.unit}</strong>
                  </div>
                ))}
              </div>
            </div>
          )}

          {imageAnalysis && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <h3 className="text-sm font-bold text-amber-800 mb-2">👁 Vision AI Observations</h3>
              <p className="text-xs text-amber-900">{imageAnalysis.findings}</p>
              <p className="text-[10px] text-amber-600 mt-1">Confidence: {imageAnalysis.confidence}</p>
            </div>
          )}

          {recordDetails.ai_explanation && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="text-xs font-semibold text-blue-700 uppercase mb-2">Why this was flagged</h3>
              <p className="text-sm text-blue-900">{recordDetails.ai_explanation}</p>
            </div>
          )}

          {recordDetails.timeline?.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-slate-600 uppercase mb-2">📅 Timeline</h3>
              <ul className="space-y-1.5 text-sm">
                {recordDetails.timeline.map((t, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="text-slate-400 shrink-0 w-20">{typeof t === 'string' ? '' : (t.time || '')}</span>
                    <span className="text-slate-700">{typeof t === 'string' ? t : (t.event || JSON.stringify(t))}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {recordDetails.follow_up_questions?.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-slate-600 uppercase mb-2">📝 Follow-up Answers</h3>
              {Object.keys(recordDetails.follow_up_answers || {}).length === 0 ? (
                <p className="text-xs text-slate-500 italic bg-slate-50 p-3 rounded border border-slate-200">No follow-up answers were provided by the nurse.</p>
              ) : (
                <div className="space-y-2">
                  {recordDetails.follow_up_questions.map((q, i) => {
                    // 👈 FIXED: backend saves questions as {id, q, type} → read q.q first
                    const questionText = (typeof q === 'string') ? q : (q.q || q.text || JSON.stringify(q));
                    const answer = recordDetails.follow_up_answers?.[q.id] || recordDetails.follow_up_answers?.[q.text] || '-';
                    return (
                      <div key={i} className="flex justify-between text-xs border-b border-slate-100 pb-1">
                        <span className="text-slate-600">{questionText}</span>
                        <span className="font-semibold text-teal-700">{answer}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {recordDetails.identified_gaps?.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <h3 className="text-xs font-semibold text-amber-800 mb-2">⚠️ Missing Information</h3>
              <ul className="text-sm text-amber-700 space-y-1">
                {recordDetails.identified_gaps.map((g, i) => <li key={i}>— {typeof g === 'string' ? g : JSON.stringify(g)}</li>)}
              </ul>
            </div>
          )}

          {referral && (
            <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-teal-800 mb-3">🧭 Referral Suggestion</h3>
              <div className="grid grid-cols-2 gap-4 mb-3 text-sm">
                <div>
                  <p className="text-teal-600 text-[10px] uppercase">Suggested Service</p>
                  <p className="font-bold text-teal-900">{referral.suggested_service_name}</p>
                </div>
                <div>
                  <p className="text-teal-600 text-[10px] uppercase">Suggested Facility</p>
                  <p className="font-bold text-teal-900">{referral.suggested_facility_name || 'Nearest District Hospital (Default)'}</p>
                </div>
              </div>
              {referral.facility_reasons?.length > 0 && (
                <ul className="text-xs text-teal-700 list-disc ml-4 mb-2">
                  {referral.facility_reasons.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              )}
              {referral.fallback_facilities?.length > 0 && (
                <div className="mt-2 pt-2 border-t border-teal-200">
                  <p className="text-[10px] text-teal-600 uppercase mb-1">Fallback Options</p>
                  <div className="flex flex-wrap gap-2">
                    {referral.fallback_facilities.map((f, i) => (
                      <span key={i} className="text-[10px] bg-white border border-teal-300 text-teal-700 px-2 py-1 rounded">{f.name}</span>
                    ))}
                  </div>
                </div>
              )}
              <button onClick={generateReferralNote} className="mt-3 w-full bg-teal-500 hover:bg-teal-600 text-white text-xs font-semibold py-2 rounded-lg">📄 Generate Referral Note</button>
            </div>
          )}

          {referralNote && (
            <div className="bg-white border-2 border-teal-500 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-slate-800">Referral Note (Ready to Print)</h3>
                <button onClick={() => window.print()} className="text-xs bg-slate-800 text-white px-3 py-1 rounded">🖨 Print</button>
              </div>
              <pre className="text-[10px] text-slate-700 bg-slate-50 p-3 rounded whitespace-pre-wrap font-mono max-h-80 overflow-y-auto">{referralNote}</pre>
            </div>
          )}

          <div>
            <h3 className="text-xs font-semibold text-slate-600 uppercase mb-2">Doctor Notes</h3>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows="3" className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-teal-500" placeholder="Enter clinical notes..." />
          </div>

          <div className="border-t border-slate-200 pt-5">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Clinical Decision</h3>
            <div className="grid md:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Decision</label>
                <select value={decision} onChange={e => setDecision(e.target.value)} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
                  <option value="approve">Approve AI priority</option>
                  <option value="override">Override priority</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Final priority</label>
                <select value={finalPriority} onChange={e => setFinalPriority(e.target.value)} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
                  <option value="P1">P1 — Emergency</option>
                  <option value="P2">P2 — Very Urgent</option>
                  <option value="P3">P3 — Urgent</option>
                  <option value="P4">P4 — Standard</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Action</label>
                <select value={action} onChange={e => setAction(e.target.value)} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
                  <option value="opd">Send to OPD</option>
                  <option value="chemist">Send to Chemist (Prescribe)</option>
                  <option value="admit">Admit to ICU</option>
                  <option value="refer">Refer to District Hospital</option>
                </select>
              </div>
            </div>

            {action === 'chemist' && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mt-4">
                <p className="text-sm font-semibold text-amber-800 mb-3">💊 Prescription</p>
                <div className="grid grid-cols-4 gap-2 mb-2">
                  <input type="text" placeholder="Medicine name" value={newMedicine.name} onChange={e => setNewMedicine({ ...newMedicine, name: e.target.value })} className="col-span-2 border border-slate-300 rounded px-2 py-1.5 text-sm" />
                  <input type="text" placeholder="Dosage" value={newMedicine.dosage} onChange={e => setNewMedicine({ ...newMedicine, dosage: e.target.value })} className="border border-slate-300 rounded px-2 py-1.5 text-sm" />
                  <button onClick={addMedicine} className="bg-amber-500 hover:bg-amber-600 text-white text-sm rounded font-semibold">+ Add</button>
                </div>
                <div className="grid grid-cols-2 gap-2 mb-2">
                  <input type="text" placeholder="Frequency (e.g., 2× daily)" value={newMedicine.frequency} onChange={e => setNewMedicine({ ...newMedicine, frequency: e.target.value })} className="border border-slate-300 rounded px-2 py-1.5 text-sm" />
                  <input type="text" placeholder="Duration (e.g., 5 days)" value={newMedicine.duration} onChange={e => setNewMedicine({ ...newMedicine, duration: e.target.value })} className="border border-slate-300 rounded px-2 py-1.5 text-sm" />
                </div>
                {medicines.length > 0 && (
                  <div className="space-y-1 mt-3">
                    {medicines.map((m, i) => (
                      <div key={i} className="flex items-center justify-between bg-white border border-amber-200 rounded px-2 py-1 text-xs">
                        <span><strong>{m.name}</strong> — {m.dosage} · {m.frequency} · {m.duration}</span>
                        <button onClick={() => removeMedicine(i)} className="text-red-500 font-bold">✕</button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {saveSuccess && <div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2 mt-3">✅ {saveSuccess}</div>}

            <div className="flex justify-end gap-2 mt-5 flex-wrap">
              <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 border border-slate-300 rounded-lg hover:bg-slate-50">Cancel</button>
              <button onClick={() => setShowReferralForm(true)} className="px-4 py-2 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg">🚑 Refer to DH</button>
              <button onClick={handleSave} disabled={submitting} className="px-5 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-lg disabled:opacity-60">{submitting ? 'Saving…' : '💾 Save Decision'}</button>
            </div>
          </div>

        </div>
      </div>

      {showReferralForm && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[60] p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-2xl w-full my-8 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-red-600">🚑 Referral to Higher Facility</h2>
              <button onClick={() => setShowReferralForm(false)} className="text-2xl text-slate-400 hover:text-red-500">×</button>
            </div>
            <div className="space-y-3 mb-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-700 mb-1 block">📍 Current Location</label>
                  <select value={referralDetails.currentLocation} onChange={(e) => setReferralDetails({...referralDetails, currentLocation: e.target.value})} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
                    <option>Casualty Room 1</option><option>Casualty Room 2</option><option>Emergency Ward</option><option>ICU</option><option>General Ward</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700 mb-1 block">🎯 Destination</label>
                  <select value={referralDetails.destinationFacility} onChange={(e) => setReferralDetails({...referralDetails, destinationFacility: e.target.value})} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
                    <option>District Hospital, Rourkela</option><option>District Hospital, Sambalpur</option><option>Medical College, Cuttack</option><option>AIIMS, Bhubaneswar</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-700 mb-1 block">🚑 Ambulance Number</label>
                  <input type="text" value={referralDetails.ambulanceNumber} onChange={(e) => setReferralDetails({...referralDetails, ambulanceNumber: e.target.value})} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700 mb-1 block">⏱ ETA (minutes)</label>
                  <input type="number" value={referralDetails.transferETA} onChange={(e) => setReferralDetails({...referralDetails, transferETA: e.target.value})} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-700 mb-1 block">👥 Attending Team</label>
                  <input type="text" value={referralDetails.attendingTeam} onChange={(e) => setReferralDetails({...referralDetails, attendingTeam: e.target.value})} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700 mb-1 block">🛏 Bed Number</label>
                  <input type="text" value={referralDetails.bedNumber} onChange={(e) => setReferralDetails({...referralDetails, bedNumber: e.target.value})} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setShowReferralForm(false)} className="flex-1 bg-slate-200 text-slate-700 font-semibold py-3 rounded-lg text-sm">Cancel</button>
              <button onClick={handleSendReferral} disabled={submitting} className="flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold py-3 rounded-lg text-sm disabled:opacity-60">{submitting ? 'Sending…' : '✅ Send Referral'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}