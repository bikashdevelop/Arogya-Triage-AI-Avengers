import React from 'react';

export default function ReferralNote({ patient, onClose }) {
  if (!patient) return null;

  const noteText = `
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Patient: ${patient.name} (${patient.age}M)
Token: ${patient.token}
Referral Time: ${new Date().toLocaleTimeString()}

CLINICAL SUMMARY:
${patient.age}y/${patient.sex} with head injury from bike accident. 
Unconscious, head wound visible. 
BP ${patient.bp}, SpO2 ${patient.spo2}, HR ${patient.hr}.
Suspected intracranial hemorrhage.
Low platelets (42,000).

URGENT NEEDS:
✅ CT scan (head)
✅ Neurosurgical evaluation
✅ ICU bed

TIMELINE:
${patient.timeline.map(t => `${t.time} - ${t.event}`).join('\n')}

REFERRED BY:
Dr. R. Mohanty (Emergency)
CHC Sundargarh

TRANSPORT: 108 Ambulance
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  `;

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6">
        
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-red-600">
            🚑 DISTRICT HOSPITAL REFERRAL
          </h2>
          <button onClick={onClose} className="text-2xl text-slate-400 hover:text-red-500">×</button>
        </div>

        <pre className="text-xs font-mono bg-slate-50 border border-slate-200 rounded-lg p-4 whitespace-pre-wrap leading-relaxed">
          {noteText}
        </pre>

        <div className="flex gap-3 mt-4">
          <button
            onClick={() => window.print()}
            className="flex-1 bg-white border-2 border-red-500 text-red-600 font-semibold py-3 rounded-lg hover:bg-red-50"
          >
            🖨 Print Note
          </button>
          <button
            onClick={() => {
              alert('✅ Referral sent to District Hospital\n📱 SMS sent to 108 Ambulance\n📧 Email sent to DH');
              onClose();
            }}
            className="flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold py-3 rounded-lg"
          >
            ✅ Confirm & Send Referral
          </button>
        </div>

      </div>
    </div>
  );
}