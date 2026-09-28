import React from 'react';
import NurseIntake from './NurseIntake';
import PatientQueue from './PatientQueue';

export default function App() {
  const path = window.location.pathname;
  const patientMatch = path.match(/^\/patient\/(.+)$/);

  if (patientMatch) {
    return <PatientQueue patientId={patientMatch[1]} />;
  }

  return <NurseIntake />;
}
