import React from 'react';
import { MessageCircle, Globe, Activity } from 'lucide-react';
import './LandingPage.css';


const LandingPage = () => {
  return (
    <div className="landing-page">
      {/* Navbar - Based on Frame 1 */}
      <nav className="navbar">
        <div className="nav-container">
          <div className="logo-brand">
              <Activity className="h-10 w-10 text-primary-600" />

            <span className="logo-text">HarakaCare</span>
          </div>
          
          <div className="nav-links">
            <a href="https://www.youtube.com/watch?v=kiFreigRrkQ">How it Works</a>
            <a href="/facility" className="nav-link-secondary">Facility Login</a>
            <a href="/chat" className="btn-primary">Web Assesment</a>
          </div>
        </div>
      </nav>

      {/* Hero Section - Based on Frame 1 Layout */}
      <main className="hero-container">
        <div className="hero-content">
          <h1 className="main-headline">
            Connecting Patients to the  <br />
            <span>Right Hospital Faster</span>
          </h1>
          
          
          <div className="access-options">
            <div className="ussd-badge">
              Dial <strong>*256#</strong>
            </div>
            <div className="platform-buttons">
              <a href="https://wa.me/15551572733" className="platform-btn">
                <MessageCircle size={20} /> WhatsApp
              </a>
              <a href="/chat" className="platform-btn">
                <Globe size={20} /> Web Assessment
              </a>
            </div>
          </div>
          
          <p className="social-proof">
            Helping patients quickly find the right hospital using AI, WhatsApp, and USSD.
             </p>
        </div>

        {/* Visual Column - The "Phone Mockup" side */}
        <div className="hero-visual">
          <div className="phone-mockup">
            <div className="mockup-screen">
              <div className="triage-active">
                <div className="triage-header">AI Assessment</div>
                <div className="triage-chat">
                  <div className="msg bot">What are your symptoms?</div>
                  <div className="msg user">I have a sharp fever...</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

    </div>
  );
};

export default LandingPage;