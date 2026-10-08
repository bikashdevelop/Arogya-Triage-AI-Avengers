import React from 'react';
import NurseIntake from './NurseIntake';
import DoctorDashboard from './DoctorDashboard';
import PatientQueue from './PatientQueue';

export default function App() {
  const path = window.location.pathname;
  const role = sessionStorage.getItem('role');
  const token = sessionStorage.getItem('access_token');

  // ─── Patient queue view: /patient/{token} ───
  const patientMatch = path.match(/^\/patient\/(.+)$/);
  if (patientMatch) {
    return <PatientQueue patientId={patientMatch[1]} />;
  }

  // ─── Explicit /doctor path ───
  if (path.startsWith('/doctor')) {
    return <DoctorDashboard />;
  }

  // ─── Logged in as doctor → auto-redirect to dashboard ───
  if (role === 'doctor' && token) {
    window.location.href = '/doctor';
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center text-white">
        Redirecting to doctor dashboard...
      </div>
    );
  }

  // ─── Default: Nurse intake ───
  return <NurseIntake />;
}