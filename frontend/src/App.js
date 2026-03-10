import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ChatInterface from './components/ChatInterface';
import LandingPage from './components/LandingPage';
import PatientTriage from './components/PatientTriage';
import FacilityDashboard from './components/FacilityDashboard';
import Header from './components/Header';
import './index.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/chat" element={
          <div className="min-h-screen bg-gray-50">
            <Header />
            <main className="container mx-auto px-4 py-8">
              <ChatInterface />
            </main>
          </div>
        } />
        <Route path="/patient" element={
          <div className="min-h-screen bg-gray-50">
            <Header />
            <main className="container mx-auto px-4 py-8">
              <PatientTriage />
            </main>
          </div>
        } />
        <Route path="/facility" element={
          <div className="min-h-screen bg-gray-50">
            <Header />
            <main className="container mx-auto px-4 py-8">
              <FacilityDashboard />
            </main>
          </div>
        } />
      </Routes>
    </Router>
  );
}

export default App;
