import React from 'react';
import './index-simple.css';

function App() {
  return (
    <div className="container" style={{ padding: '40px 16px' }}>
      <h1 style={{ color: '#2563eb', marginBottom: '20px', textAlign: 'center' }}>
        🏥 HarakaCare - Healthcare Management System
      </h1>
      
      <div className="card" style={{ padding: '30px', marginBottom: '30px', textAlign: 'center' }}>
        <h2 style={{ color: '#059669', marginBottom: '15px' }}>
          ✅ System Status: Working
        </h2>
        <p style={{ fontSize: '18px', color: '#374151', marginBottom: '25px' }}>
          The frontend is running successfully! This is a simplified version to test basic functionality.
        </p>
        
        <div style={{ display: 'flex', gap: '20px', justifyContent: 'center', flexWrap: 'wrap' }}>
          <button className="btn btn-primary" style={{ fontSize: '16px', padding: '12px 24px' }}>
            🧑‍⚕️ Patient Triage
          </button>
          <button className="btn btn-secondary" style={{ fontSize: '16px', padding: '12px 24px' }}>
            🏢 Facility Dashboard
          </button>
        </div>
      </div>

      <div className="card" style={{ padding: '25px', marginBottom: '30px' }}>
        <h3 style={{ color: '#1f2937', marginBottom: '15px' }}>🎯 Features Implemented:</h3>
        <ul style={{ lineHeight: '1.8', color: '#4b5563' }}>
          <li>✅ React 18 with modern hooks</li>
          <li>✅ Responsive design system</li>
          <li>✅ Patient symptom assessment workflow</li>
          <li>✅ Facility case management dashboard</li>
          <li>✅ Real-time validation and error handling</li>
          <li>✅ Mobile-first accessibility</li>
          <li>✅ Professional healthcare UI/UX</li>
        </ul>
      </div>

      <div className="card" style={{ padding: '25px', textAlign: 'center' }}>
        <h3 style={{ color: '#1f2937', marginBottom: '15px' }}>🚀 Next Steps:</h3>
        <p style={{ color: '#4b5563', lineHeight: '1.6' }}>
          Once we confirm this basic version works, we'll restore the full Tailwind CSS version 
          with all the advanced features including:
        </p>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
          gap: '15px', 
          marginTop: '20px' 
        }}>
          <div style={{ padding: '15px', backgroundColor: '#f0fdf4', borderRadius: '6px' }}>
            <strong>📱 Mobile Responsive</strong>
            <p style={{ fontSize: '14px', margin: '5px 0 0 0' }}>Perfect on all devices</p>
          </div>
          <div style={{ padding: '15px', backgroundColor: '#fef3c7', borderRadius: '6px' }}>
            <strong>⚡ Real-time Updates</strong>
            <p style={{ fontSize: '14px', margin: '5px 0 0 0' }}>Live case management</p>
          </div>
          <div style={{ padding: '15px', backgroundColor: '#dbeafe', borderRadius: '6px' }}>
            <strong>🎨 Beautiful UI</strong>
            <p style={{ fontSize: '14px', margin: '5px 0 0 0' }}>Professional healthcare design</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
