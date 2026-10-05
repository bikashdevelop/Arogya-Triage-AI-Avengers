import React, { useState } from 'react';

export default function DoctorReview({ patient, onClose }) {
  const [showReferral, setShowReferral] = useState(false);
  const [notes, setNotes] = useState('');

  const [referralDetails, setReferralDetails] = useState({
    currentLocation: 'Casualty Room 1',
    currentFacility: 'CHC Sundargarh',
    currentFacilityId: 'CHC-OD-SNG-001',
    destinationFacility: 'District Hospital, Rourkela',
    destinationFacilityId: 'DH-OD-RKL-001',
    ambulanceNumber: 'OD-14-AB-1234',
    transferETA: '45',
    attendingTeam: 'Emergency + Neurosurgery',
    bedNumber: 'ICU Bed 3 (Reserved)',
  });

  if (!patient) return null;

  const handleSendReferral = () => {
    // Save to localStorage — PatientQueue will read this
    localStorage.setItem(`referral_${patient.token}`, JSON.stringify({
      ...referralDetails,
      transferStatus: 'En Route',
      referredAt: new Date().toLocaleTimeString(),
      referredBy: 'Dr. R. Mohanty',
    }));

    alert(`✅ Referral Generated!\n\nLocation: ${referralDetails.currentLocation}\nDestination: ${referralDetails.destinationFacility}\n\nPatient Queue pe family ko ye info dikhegi.`);
    setShowReferral(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-start justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl max-w-3xl w-full my-8 shadow-2xl">

        {/* HEADER */}
        <div className="bg-slate-900 text-white px-6 py-4 rounded-t-2xl flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold">🩺 Patient Review</h2>
            <p className="text-xs text-slate-300">{patient.name} ({patient.age}y/{patient.sex})</p>
          </div>
          <button onClick={onClose} className="text-white text-2xl hover:text-red-400">×</button>
        </div>

        <div className="p-6 space-y-5">

          {/* PATIENT INFO */}
          <div className="flex items-center gap-3 pb-3 border-b border-slate-200">
            <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center text-2xl">🚨</div>
            <div>
              <p className="font-bold text-slate-800">{patient.name}</p>
              <p className="text-xs font-mono text-slate-500">{patient.token}</p>
            </div>
            <span className="ml-auto bg-red-500 text-white text-xs font-bold px-3 py-1 rounded">
              {patient.priority}
            </span>
          </div>

          {/* SYMPTOMS */}
          <div>
            <h3 className="text-xs font-semibold text-slate-600 uppercase mb-2">📋 Symptoms</h3>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
              <p className="text-sm text-slate-700 italic">"{patient.symptoms}"</p>
            </div>
          </div>

          {/* VITALS */}
          <div>
            <h3 className="text-xs font-semibold text-slate-600 uppercase mb-2">🩺 Vitals</h3>
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-red-50 border border-red-200 rounded-lg p-2">
                <p className="text-[10px] text-red-600 uppercase">BP</p>
                <p className="text-sm font-bold text-red-700">{patient.bp}</p>
              </div>
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-2">
                <p className="text-[10px] text-amber-600 uppercase">HR</p>
                <p className="text-sm font-bold text-amber-700">{patient.hr}</p>
              </div>
              <div className="bg-red-50 border border-red-200 rounded-lg p-2">
                <p className="text-[10px] text-red-600 uppercase">SpO2</p>
                <p className="text-sm font-bold text-red-700">{patient.spo2}</p>
              </div>
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-2">
                <p className="text-[10px] text-slate-500 uppercase">Temp</p>
                <p className="text-sm font-bold text-slate-700">{patient.temp}</p>
              </div>
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-2">
                <p className="text-[10px] text-slate-500 uppercase">RR</p>
                <p className="text-sm font-bold text-slate-700">{patient.rr}</p>
              </div>
              <div className="bg-red-50 border border-red-200 rounded-lg p-2">
                <p className="text-[10px] text-red-600 uppercase">MEWS</p>
                <p className="text-sm font-bold text-red-700">{patient.mews}</p>
              </div>
            </div>
          </div>

          {/* FOLLOW-UP */}
          {patient.followup && Object.keys(patient.followup).length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-slate-600 uppercase mb-2">📝 Follow-up Answers</h3>
              <div className="space-y-2">
                {Object.entries(patient.followup).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs border-b border-slate-100 pb-1">
                    <span className="text-slate-600">{k}</span>
                    <span className="font-semibold text-red-600">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* LAB REPORT */}
          {patient.labReport && (
            <div>
              <h3 className="text-xs font-semibold text-slate-600 uppercase mb-2">📄 Lab Report</h3>
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(patient.labReport).map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-slate-600 capitalize">{k}:</span>
                      <span className="font-semibold text-slate-700">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* AI RECOMMENDATION */}
          <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
            <h3 className="text-sm font-bold text-teal-800 mb-2">🤖 AI Recommendation</h3>
            <ul className="text-xs text-teal-900 space-y-1">
              <li>• IMMEDIATE neurosurgical evaluation</li>
              <li>• Consider CT scan</li>
              <li>• Transfer to DH if needed</li>
            </ul>
          </div>

          {/* DOCTOR NOTES */}
          <div>
            <h3 className="text-xs font-semibold text-slate-600 uppercase mb-2">Doctor Notes</h3>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows="3"
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-teal-500"
              placeholder="Enter clinical notes..."
            />
          </div>

          {/* ACTIONS */}
          <div className="grid grid-cols-3 gap-3 pt-3 border-t border-slate-200">
            <button
              onClick={() => alert('✅ CT Scan ordered')}
              className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-3 rounded-lg text-sm"
            >
              📷 Order CT
            </button>
            <button
              onClick={() => setShowReferral(true)}
              className="bg-red-500 hover:bg-red-600 text-white font-semibold py-3 rounded-lg text-sm"
            >
              🚑 Refer to DH
            </button>
            <button
              onClick={() => alert('✅ Treatment started')}
              className="bg-teal-500 hover:bg-teal-600 text-white font-semibold py-3 rounded-lg text-sm"
            >
              💊 Treat
            </button>
          </div>
        </div>

        {/* REFERRAL FORM MODAL */}
        {showReferral && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-60 p-4 overflow-y-auto">
            <div className="bg-white rounded-2xl max-w-2xl w-full my-8 p-6">
              
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-red-600">🚑 Referral to Higher Facility</h2>
                <button onClick={() => setShowReferral(false)} className="text-2xl text-slate-400 hover:text-red-500">×</button>
              </div>

              <p className="text-xs text-slate-500 mb-4">
                Fill referral details. Ye info patient queue pe family ko dikhegi.
              </p>

              {/* FORM */}
              <div className="space-y-3 mb-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold text-slate-700 mb-1 block">📍 Current Location</label>
                    <select
                      value={referralDetails.currentLocation}
                      onChange={(e) => setReferralDetails({...referralDetails, currentLocation: e.target.value})}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-teal-500"
                    >
                      <option>Casualty Room 1</option>
                      <option>Casualty Room 2</option>
                      <option>Emergency Ward</option>
                      <option>ICU</option>
                      <option>General Ward</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-700 mb-1 block">🎯 Destination</label>
                    <select
                      value={referralDetails.destinationFacility}
                      onChange={(e) => setReferralDetails({...referralDetails, destinationFacility: e.target.value})}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-teal-500"
                    >
                      <option>District Hospital, Rourkela</option>
                      <option>District Hospital, Sambalpur</option>
                      <option>Medical College, Cuttack</option>
                      <option>AIIMS, Bhubaneswar</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold text-slate-700 mb-1 block">🚑 Ambulance Number</label>
                    <input
                      type="text"
                      value={referralDetails.ambulanceNumber}
                      onChange={(e) => setReferralDetails({...referralDetails, ambulanceNumber: e.target.value})}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-teal-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-700 mb-1 block">⏱ ETA (minutes)</label>
                    <input
                      type="number"
                      value={referralDetails.transferETA}
                      onChange={(e) => setReferralDetails({...referralDetails, transferETA: e.target.value})}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-teal-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold text-slate-700 mb-1 block">👥 Attending Team</label>
                    <input
                      type="text"
                      value={referralDetails.attendingTeam}
                      onChange={(e) => setReferralDetails({...referralDetails, attendingTeam: e.target.value})}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-teal-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-700 mb-1 block">🛏 Bed Number</label>
                    <input
                      type="text"
                      value={referralDetails.bedNumber}
                      onChange={(e) => setReferralDetails({...referralDetails, bedNumber: e.target.value})}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-teal-500"
                    />
                  </div>
                </div>
              </div>

              {/* PREVIEW */}
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 mb-4">
                <p className="text-[10px] uppercase text-slate-500 mb-2">Preview</p>
                <div className="text-xs space-y-1">
                  <p><strong>From:</strong> {referralDetails.currentFacility} — {referralDetails.currentLocation}</p>
                  <p><strong>To:</strong> {referralDetails.destinationFacility} — {referralDetails.bedNumber}</p>
                  <p><strong>Ambulance:</strong> {referralDetails.ambulanceNumber} | <strong>ETA:</strong> {referralDetails.transferETA} min</p>
                  <p><strong>Team:</strong> {referralDetails.attendingTeam}</p>
                </div>
              </div>

              {/* BUTTONS */}
              <div className="flex gap-3">
                <button
                  onClick={() => setShowReferral(false)}
                  className="flex-1 bg-slate-200 text-slate-700 font-semibold py-3 rounded-lg text-sm"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSendReferral}
                  className="flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold py-3 rounded-lg text-sm"
                >
                  ✅ Send Referral
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}