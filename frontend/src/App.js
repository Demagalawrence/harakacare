import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import PatientTriage from './components/PatientTriage';
import FacilityDashboard from './components/FacilityDashboard';
import Header from './components/Header';
import './index.css';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Navigate to="/patient" replace />} />
            <Route path="/patient" element={<PatientTriage />} />
            <Route path="/facility" element={<FacilityDashboard />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
