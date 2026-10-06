import React, { useState, useEffect } from 'react';

export default function PatientQueue({ patientId }) {
  const [queueInfo, setQueueInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const isEmergency = patientId?.includes('EMG');

  // ===== FETCH QUEUE INFO =====
  const fetchQueueInfo = () => {
    if (isEmergency) {
      setQueueInfo({
        token: patientId,
        status: 'REFERRED TO DH',
        statusColor: 'red',
        position: 1,
        totalInQueue: 8,
        waitTime: '0 min (Immediate)',
        nowServing: patientId,
        priority: 'P1',
        urgency: 'Immediate / Emergent',

        // Location & Facility
        currentFacility: 'CHC Sundargarh',
        currentFacilityId: 'CHC-OD-SNG-001',
        currentLocation: 'Casualty Room 1',
        destinationFacility: 'District Hospital, Rourkela',
        destinationFacilityId: 'DH-OD-RKL-001',
        transferStatus: 'En Route',
        transferETA: '45 minutes',
        ambulanceNumber: 'OD-14-AB-1234',
        attendingTeam: 'Emergency + Neurosurgery',
        bedNumber: 'ICU Bed 3 (Reserved)',

        // Doctor
        doctor: {
          name: 'Dr. R. Mohanty',
          dept: 'Emergency',
          number: '+91 98765 43210',
          available: true,
          shift: 'On-duty',
          isEmergencyLine: true,
        },

        // Timeline
        timeline: [
          { done: true, text: 'Emergency Attended', time: '10:31 AM', location: 'CHC Casualty Room 1' },
          { done: true, text: 'Vitals Recorded', time: '10:33 AM', location: 'CHC Casualty Room 1' },
          { done: true, text: 'Triage Complete', time: '10:34 AM', location: 'System' },
          { done: true, text: 'Doctor Consultation', time: '10:35 AM', location: 'CHC Casualty Room 1' },
          { done: true, text: 'Referral Generated', time: '10:41 AM', location: 'CHC' },
          { done: false, text: 'Transfer to DH', time: '10:45 AM', location: 'En Route' },
          { done: false, text: 'DH Reception', time: '~11:30 AM', location: 'District Hospital' },
          { done: false, text: 'ICU Admission', time: '~11:45 AM', location: 'DH ICU' },
        ],

        showTransfer: true,
        emergencyContact: '108',
        hospitalHelpdesk: '+91 661 240 1000',
        dhContact: '+91 661 250 2000',
      });
    } else {
      setQueueInfo({
        token: patientId,
        status: 'WAITING',
        statusColor: 'amber',
        position: 3,
        totalInQueue: 8,
        waitTime: '~24 minutes',
        nowServing: 'PAT-20261004-039',
        priority: 'P3',
        urgency: 'Urgent',

        currentFacility: 'CHC Sundargarh',
        currentFacilityId: 'CHC-OD-SNG-001',
        currentLocation: 'Waiting Area - Bay 3',

        doctor: {
          name: 'Dr. S. Patnaik',
          dept: 'Pediatrics',
          number: '+91 661 240 1234',
          available: true,
          shift: 'Morning (9 AM - 2 PM)',
          isEmergencyLine: false,
        },

        timeline: [
          { done: true, text: 'Registered', time: '10:46 AM', location: 'Reception' },
          { done: true, text: 'AI Triage Complete', time: '10:47 AM', location: 'System' },
          { done: false, text: 'Waiting for Doctor', time: '', location: 'Waiting Area' },
          { done: false, text: 'Consultation', time: '', location: 'Room 3' },
        ],

        showTransfer: false,
        emergencyContact: '108',
        hospitalHelpdesk: '+91 661 240 1000',
      });
    }

    setLastRefresh(new Date());
    setLoading(false);
  };

  useEffect(() => {
    fetchQueueInfo();
    const interval = setInterval(fetchQueueInfo, 10000);
    return () => clearInterval(interval);
  }, [patientId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-pulse text-teal-400 text-2xl mb-2">🩺</div>
          <p className="text-teal-400 text-sm">Loading your queue status...</p>
        </div>
      </div>
    );
  }

  const statusColorClass =
    queueInfo.statusColor === 'red' ? 'bg-red-500' :
    queueInfo.statusColor === 'orange' ? 'bg-orange-500' :
    queueInfo.statusColor === 'amber' ? 'bg-amber-500' :
    queueInfo.statusColor === 'green' ? 'bg-green-500' :
    'bg-teal-500';

  const priorityColorClass =
    queueInfo.priority === 'P1' ? 'bg-red-500 text-white' :
    queueInfo.priority === 'P2' ? 'bg-orange-500 text-white' :
    queueInfo.priority === 'P3' ? 'bg-yellow-500 text-slate-900' :
    'bg-green-500 text-white';

  const urgencyMsg =
    queueInfo.priority === 'P1' ? '🚨 IMMEDIATE ATTENTION' :
    queueInfo.priority === 'P2' ? '⚡ VERY URGENT — Within 10 min' :
    queueInfo.priority === 'P3' ? '⏰ PLEASE WAIT — Within 60 min' :
    '✓ ROUTINE — Within 2 hours';

  const urgencyColor =
    queueInfo.priority === 'P1' ? 'text-red-400' :
    queueInfo.priority === 'P2' ? 'text-orange-400' :
    queueInfo.priority === 'P3' ? 'text-amber-400' :
    'text-green-400';

  return (
    <div className="min-h-screen bg-slate-900 p-4 flex flex-col items-center">

      {/* HEADER */}
      <div className="w-full max-w-md mb-4 text-center">
        <div className="inline-flex items-center gap-2 text-white">
          <div className="w-8 h-8 rounded-lg bg-teal-500 flex items-center justify-center font-bold text-slate-900">A</div>
          <span className="font-bold">AarogyaTriage</span>
        </div>
        <p className="text-[10px] text-slate-500 mt-1 uppercase tracking-widest">India-Wide AI</p>
      </div>

      {/* MAIN CARD */}
      <div className="w-full max-w-md bg-slate-800 rounded-2xl border border-slate-700 p-6 shadow-2xl">

        {/* TOKEN + PRIORITY */}
        <div className="text-center mb-4">
          <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Your Token</p>
          <p className="text-xl font-bold text-teal-400 font-mono break-all">{queueInfo.token}</p>
          <span className={`inline-block mt-2 px-3 py-1 rounded-full text-xs font-bold ${priorityColorClass}`}>
            {queueInfo.priority} Priority
          </span>
        </div>

        {/* STATUS BANNER */}
        <div className={`${statusColorClass} rounded-xl p-4 mb-3 text-center`}>
          <p className="text-white/80 text-xs uppercase tracking-wider mb-1">Status</p>
          <p className="text-lg font-bold text-white">{queueInfo.status}</p>
        </div>

        {/* URGENCY MESSAGE */}
        <div className={`text-center text-xs font-semibold mb-4 ${urgencyColor}`}>
          {urgencyMsg}
        </div>

        {/* POSITION + WAIT TIME — Same for all */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-gradient-to-br from-teal-500 to-teal-700 rounded-xl p-4 text-center">
            <p className="text-teal-100 text-[10px] uppercase tracking-wider mb-1">Position</p>
            <p className="text-4xl font-extrabold text-white leading-none">{queueInfo.position}</p>
            <p className="text-teal-100 text-[10px] mt-1">of {queueInfo.totalInQueue}</p>
          </div>
          <div className="bg-slate-900 rounded-xl p-4 border border-slate-700 text-center flex flex-col justify-center">
            <p className="text-slate-400 text-[10px] uppercase tracking-wider mb-1">Wait Time</p>
            <p className="text-sm font-bold text-white">{queueInfo.waitTime}</p>
          </div>
        </div>

        {/* NOW SERVING */}
        <div className="bg-slate-900 rounded-xl p-4 mb-4 border border-slate-700 text-center">
          <p className="text-slate-400 text-[10px] uppercase tracking-wider mb-1">Now Serving</p>
          <p className="text-sm font-bold text-teal-400 font-mono break-all">{queueInfo.nowServing}</p>
        </div>

        {/* DOCTOR CARD */}
        <div className="bg-slate-900 rounded-xl p-4 mb-4 border border-slate-700">
          <p className="text-slate-400 text-[10px] uppercase tracking-wider mb-3">👨‍⚕️ Assigned Doctor</p>

          <div className="flex items-center gap-3 mb-3">
            <div className="w-12 h-12 rounded-full bg-teal-500/20 border-2 border-teal-500 flex items-center justify-center text-2xl">
              👨‍⚕️
            </div>
            <div className="flex-1">
              <p className="text-base font-bold text-white">{queueInfo.doctor.name}</p>
              <p className="text-[10px] text-slate-400">{queueInfo.doctor.dept}</p>
            </div>
            <div className={`w-3 h-3 rounded-full ${queueInfo.doctor.available ? 'bg-green-500' : 'bg-red-500'} animate-pulse`}></div>
          </div>

          <div className="flex items-center gap-2 text-[10px] text-slate-400 mb-3">
            <span>🕐</span>
            <span>{queueInfo.doctor.shift}</span>
          </div>

          <a
            href={`tel:${queueInfo.doctor.number.replace(/\s/g, '')}`}
            className="block bg-teal-500 hover:bg-teal-600 text-white text-center font-bold py-3 rounded-lg text-sm transition active:scale-95"
          >
            📞 Call Doctor
            <span className="block text-[10px] font-normal text-teal-100 mt-0.5">
              {queueInfo.doctor.number}
            </span>
          </a>

          <p className="text-[9px] text-slate-500 text-center mt-2">
            {queueInfo.doctor.isEmergencyLine
              ? '⚠️ Emergency — Direct doctor line'
              : '⏰ Available during shift hours only'}
          </p>
        </div>

        {/* TRANSFER STATUS (Emergency only) */}
        {queueInfo.showTransfer && (
          <div className="bg-slate-900 rounded-xl p-4 mb-4 border border-amber-500/50">
            <p className="text-slate-400 text-[10px] uppercase tracking-wider mb-3">
              🚑 Transfer Status
            </p>

            {/* Status Header */}
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="text-sm font-bold text-amber-400">🚑 {queueInfo.transferStatus}</p>
              </div>
              <div className="text-right">
                <p className="text-[10px] text-slate-400 uppercase mb-1">ETA</p>
                <p className="text-sm font-bold text-white">{queueInfo.transferETA}</p>
              </div>
            </div>

            {/* FROM */}
            <div className="bg-slate-950/50 rounded-lg p-3 mb-2 border-l-4 border-teal-500">
              <p className="text-[9px] text-teal-400 uppercase tracking-wider mb-1">From</p>
              <p className="text-xs font-bold text-white">{queueInfo.currentFacility}</p>
              <p className="text-[10px] font-mono text-teal-300 mt-0.5">🆔 {queueInfo.currentFacilityId}</p>
              <p className="text-[10px] text-slate-400 mt-1">📍 {queueInfo.currentLocation}</p>
            </div>

            {/* TO */}
            <div className="bg-slate-950/50 rounded-lg p-3 mb-2 border-l-4 border-red-500">
              <p className="text-[9px] text-red-400 uppercase tracking-wider mb-1">To</p>
              <p className="text-xs font-bold text-white">{queueInfo.destinationFacility}</p>
              <p className="text-[10px] font-mono text-red-300 mt-0.5">🆔 {queueInfo.destinationFacilityId}</p>
              <p className="text-[10px] text-slate-400 mt-1">🛏 {queueInfo.bedNumber}</p>
            </div>

            {/* AMBULANCE */}
            <div className="bg-slate-950/50 rounded-lg p-3 border-l-4 border-amber-500">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[9px] text-amber-400 uppercase tracking-wider mb-1">Ambulance</p>
                  <p className="text-xs font-mono font-bold text-white">{queueInfo.ambulanceNumber}</p>
                </div>
                <div className="text-right">
                  <p className="text-[9px] text-amber-400 uppercase tracking-wider mb-1">Team</p>
                  <p className="text-[10px] text-white">{queueInfo.attendingTeam}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TIMELINE */}
        <div className="bg-slate-900 rounded-xl p-4 mb-4 border border-slate-700">
          <p className="text-slate-400 text-[10px] uppercase tracking-wider mb-3">Your Timeline</p>
          <div className="space-y-3">
            {queueInfo.timeline.map((t, i) => (
              <div key={i} className="flex items-start gap-3">
                <span className={`text-lg ${t.done ? 'text-green-400' : 'text-amber-400'}`}>
                  {t.done ? '✅' : '⏳'}
                </span>
                <div className="flex-1">
                  <p className={`text-sm ${t.done ? 'text-slate-300' : 'text-white font-semibold'}`}>
                    {t.text}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                    {t.time && <p className="text-[10px] text-slate-500 font-mono">{t.time}</p>}
                    {t.location && (
                      <>
                        <span className="text-slate-600 text-[10px]">•</span>
                        <p className="text-[10px] text-teal-400">📍 {t.location}</p>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CONTACTS */}
        <div className="grid grid-cols-2 gap-2 mb-4">
          <a
            href={`tel:${queueInfo.emergencyContact}`}
            className="bg-red-500/10 border border-red-500/50 rounded-xl p-3 text-center hover:bg-red-500/20 transition"
          >
            <p className="text-red-400 text-[10px] uppercase tracking-wider mb-1">Ambulance</p>
            <p className="text-sm font-bold text-white">🚑 {queueInfo.emergencyContact}</p>
          </a>
          <a
            href={`tel:${queueInfo.hospitalHelpdesk.replace(/\s/g, '')}`}
            className="bg-teal-500/10 border border-teal-500/50 rounded-xl p-3 text-center hover:bg-teal-500/20 transition"
          >
            <p className="text-teal-400 text-[10px] uppercase tracking-wider mb-1">Helpdesk</p>
            <p className="text-xs font-bold text-white">📞 Hospital</p>
          </a>
          {queueInfo.dhContact && (
            <a
              href={`tel:${queueInfo.dhContact.replace(/\s/g, '')}`}
              className="col-span-2 bg-purple-500/10 border border-purple-500/50 rounded-xl p-3 text-center hover:bg-purple-500/20 transition"
            >
              <p className="text-purple-400 text-[10px] uppercase tracking-wider mb-1">District Hospital</p>
              <p className="text-sm font-bold text-white">🏥 {queueInfo.dhContact}</p>
            </a>
          )}
        </div>

        {/* LIVE INDICATOR */}
        <div className="flex items-center justify-center gap-2 text-teal-400 text-xs mt-4">
          <div className="w-2 h-2 rounded-full bg-teal-400 animate-pulse"></div>
          <span>Auto-refreshing every 10 seconds</span>
        </div>

        <p className="text-center text-slate-500 text-[10px] mt-1">
          Last updated: {lastRefresh.toLocaleTimeString()}
        </p>
      </div>

      <p className="text-slate-500 text-xs mt-4 text-center max-w-md">
        AarogyaTriage · Non-Diagnostic Triage Support
      </p>
      <p className="text-slate-600 text-[10px] mt-1 text-center max-w-md">
        ⚠️ Please wait nearby. You will be notified when called.
      </p>
    </div>
  );
}
