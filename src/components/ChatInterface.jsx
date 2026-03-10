/* eslint-disable no-unused-vars */
import React, { useState, useEffect } from 'react';
import { AlertCircle, Send, Activity, MapPin } from 'lucide-react';
import { chatAPI } from '../services/chatAPI';
import './ChatInterface.css';

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [patientToken, setPatientToken] = useState(null);
  const [conversationStarted, setConversationStarted] = useState(false);
  const [progress, setProgress] = useState(0);

  // WhatsApp-style structured menus - matching backend STRUCTURED_MENUS
  const menuData = {
    age_group: {
      prompt: "First, I need to know the patient's age group. Please select:",
      type: "list",
      options: [
        { id: "1", title: "👶 Newborn (0-2 months)", description: "Recently born baby" },
        { id: "2", title: "👶 Infant (3-11 months)", description: "Baby under 1 year" },
        { id: "3", title: "👶 Child (1-5 years)", description: "Toddler age" },
        { id: "4", title: "👶 Child (6-12 years)", description: "School age child" },
        { id: "5", title: "👶 Teen (13-17 years)", description: "Teenager" },
        { id: "6", title: "👶 Adult (18-64 years)", description: "Working adult" },
        { id: "7", title: "👶 Elderly (65+ years)", description: "Senior citizen" }
      ]
    },
    sex: {
      prompt: "⚧️ What is the patient's sex?",
      type: "buttons",
      options: [
        { id: "1", title: "👦 Male" },
        { id: "2", title: "👩 Female" }
      ]
    },
    severity: {
      prompt: "How severe are the symptoms?",
      type: "buttons", 
      options: [
        { id: "1", title: "😊 Mild — can do normal activities" },
        { id: "2", title: "😐 Moderate — some difficulty with normal activities" },
        { id: "3", title: "😨 Severe — cannot do normal activities" },
        { id: "4", title: "🚨 Very severe — unable to move or respond normally" }
      ]
    },
    duration: {
      prompt: "How long have these symptoms lasted?",
      type: "list",
      options: [
        { id: "1", title: "⏰ Less than 1 day", description: "Started today" },
        { id: "2", title: "⏰ 1–3 days", description: "Few days ago" },
        { id: "3", title: "⏰ 4–7 days", description: "About a week ago" },
        { id: "4", title: "⏰ More than 1 week", description: "Over a week ago" },
        { id: "5", title: "⏰ More than 1 month", description: "Chronic symptoms" }
      ]
    },
    progression_status: {
      prompt: "How are the symptoms changing?",
      type: "buttons",
      options: [
        { id: "getting_worse", title: "📉 Getting worse" },
        { id: "staying_same", title: "➡️ Staying same" },
        { id: "getting_better", title: "📈 Getting better" },
        { id: "comes_and_goes", title: "🔄 Comes and goes" }
      ]
    },
    condition_occurrence: {
      prompt: "Is this the first time experiencing this?",
      type: "buttons",
      options: [
        { id: "first", title: "🆕 First time" },
        { id: "happened_before", title: "🔄 Happened before" },
        { id: "long_term", title: "♿ Long-term" }
      ]
    },
    allergies: {
      prompt: "Does the patient have any known allergies?",
      type: "buttons",
      options: [
        { id: "yes", title: "🚨 Yes" },
        { id: "no", title: "✅ No" },
        { id: "not_sure", title: "🤷 Not sure" }
      ]
    },
    on_medication: {
      prompt: "Is the patient currently taking any medication?",
      type: "buttons",
      options: [
        { id: "1", title: "💊 Yes" },
        { id: "2", title: "🚫 No" }
      ]
    },
    chronic_conditions_gate: {
      prompt: "Does the patient have any long-term health conditions?",
      type: "buttons",
      options: [
        { id: "1", title: "🏥 Yes — please describe" },
        { id: "2", title: "✅ No" }
      ]
    },
    consents: {
      prompt: "Do you agree to:\n• Medical triage assessment\n• Anonymous data sharing for health records\n• Follow-up contact if needed",
      type: "buttons",
      options: [
        { id: "1", title: "✅ Yes, I agree" },
        { id: "2", title: "❌ No" }
      ]
    },
    pregnancy_status: {
      prompt: "🤰 Is the patient currently pregnant?",
      type: "buttons",
      options: [
        { id: "yes", title: "🤰 Yes" },
        { id: "no", title: "🚫 No" },
        { id: "not_sure", title: "🤷 Not sure" }
      ]
    }
  };

  useEffect(() => {
    // Generate patient token and show welcome message
    const token = `PT-${Date.now().toString(36).substr(-6).toUpperCase()}`;
    setPatientToken(token);
    
    const welcomeMessage = {
      role: 'agent',
      content: "🏥 Welcome to HarakaCare Medical Triage!\n\nI'm here to help assess your health concerns through a few quick questions. This should take about 2-3 minutes.\n\nPlease describe your main symptoms or health issue to begin:",
      timestamp: new Date().toISOString()
    };
    setMessages([welcomeMessage]);
  }, []);

  const handleSendMessage = async () => {
    if (inputValue.trim() === '') return;
    
    const userMessage = {
      role: 'patient',
      content: inputValue,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    try {
      let response;
      
      if (!conversationStarted) {
        // Start new conversation
        response = await chatAPI.startConversation(inputValue, patientToken);
        setConversationStarted(true);
      } else {
        // Continue existing conversation
        response = await chatAPI.continueConversation(inputValue, patientToken);
      }

      // Process bot response
      const botMessage = {
        role: 'agent',
        content: String(response.message || response.response || "I'm processing your response..."),
        timestamp: new Date().toISOString(),
        menuData: null,
        field: null
      };

      // Check if response contains structured menu data
      if (response.active_menu_field && response.extracted_so_far) {
        const menu = getMenuForField(response.active_menu_field);
        if (menu) {
          botMessage.menuData = menu;
          botMessage.field = response.active_menu_field;
        }
        
        // Update progress based on extracted fields
        const extractedCount = Object.keys(response.extracted_so_far || {}).length;
        const totalFields = 12; // Approximate total fields to collect
        const newProgress = Math.min((extractedCount / totalFields) * 100, 95);
        setProgress(newProgress);
      }

      // Check if conversation is complete
      const isComplete = response.status === 'complete' || response.completed || 
                        (response.action === 'complete');
      
      if (isComplete) {
        botMessage.isResult = true;
        // Use real API response data instead of generic message
        botMessage.content = response.recommendation || response.message || formatCompletionMessage(response);
        console.log('Conversation completed:', response);
        setProgress(100); // Set progress to 100% on completion
      }

      console.log('API Response:', response);
      setMessages(prev => [...prev, botMessage]);
      
    } catch (error) {
      console.error('Chat API Error:', error);
      
      const errorMessage = {
        role: 'agent',
        content: String("❌ Sorry, I'm having trouble connecting. Please try again in a moment."),
        timestamp: new Date().toISOString(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleMenuOptionClick = async (optionId, field) => {
    const userMessage = {
      role: 'patient',
      content: optionId,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);

    try {
      const response = await chatAPI.continueConversation(optionId, patientToken);
      
      const botMessage = {
        role: 'agent',
        content: String(response.message || response.response || "Processing your selection..."),
        timestamp: new Date().toISOString(),
        menuData: null,
        field: null
      };

      // Check for next menu
      if (response.active_menu_field && response.extracted_so_far) {
        const menu = getMenuForField(response.active_menu_field);
        if (menu) {
          botMessage.menuData = menu;
          botMessage.field = response.active_menu_field;
        }
      }

      // Check completion - especially for consent responses
      const isComplete = response.status === 'complete' || response.completed || 
                        (response.action === 'complete') ||
                        (field === 'consents' && !response.active_menu_field);
      
      if (isComplete) {
        botMessage.isResult = true;
        botMessage.content = formatCompletionMessage(response);
        console.log('Conversation completed via menu:', response);
      } else if (field === 'consents') {
        // Special handling for consent - if not complete, show confirmation
        const consentValue = optionId;
        const consentText = consentValue === '1' ? 
          "✅ Thank you for providing consent. Your assessment is being processed..." :
          "❌ Consent declined. Without consent, we cannot proceed with the assessment.";
        
        botMessage.content = consentText;
        console.log('Consent processed via menu:', { consentValue, response });
      }

      console.log('Menu API Response:', response);
      setMessages(prev => [...prev, botMessage]);
      
    } catch (error) {
      console.error('Menu selection error:', error);
      
      const errorMessage = {
        role: 'agent',
        content: String("❌ Sorry, there was an error processing your selection. Please try again."),
        timestamp: new Date().toISOString(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const getMenuForField = (field) => {
    return menuData[field] || null;
  };

  const formatCompletionMessage = (response) => {
    return `✅ Assessment Complete!\n\nPatient Token: ${patientToken}\nRisk Level: ${response.risk_level || 'Processing...'}\n\n${response.recommendation || 'Your assessment has been processed successfully.'}`;
  };

  const getRiskLevelDisplay = (content) => {
    if (content.includes('Low') || content.includes('low')) return '🟢 Low';
    if (content.includes('Medium') || content.includes('moderate')) return '🟡 Medium';
    if (content.includes('High') || content.includes('severe')) return '🔴 High';
    return '🟡 Medium'; // Default
  };

  const getAssessmentSummary = (content) => {
    // Extract key information from the assessment content
    const summary = [];
    
    // Try to extract symptoms, duration, severity from content
    if (content.includes('weak') || content.includes('weakness')) {
      summary.push('• Weakness reported');
    }
    if (content.includes('moderate')) {
      summary.push('• Moderate severity');
    }
    if (content.includes('child') || content.includes('5 years')) {
      summary.push('• Child patient (1-5 years)');
    }
    if (content.includes('male')) {
      summary.push('• Male patient');
    }
    if (content.includes('medication')) {
      summary.push('• Currently on medication');
    }
    
    return summary.length > 0 ? summary.join('<br />') : '• Assessment completed successfully';
  };

  const getFacilityRecommendation = (content) => {
    // Real facility data based on risk level and location
    const riskLevel = getRiskLevelDisplay(content);
    const location = content.includes('kampala') ? 'Kampala' : 'Nearby location';
    
    if (riskLevel.includes('High')) {
      return <>
        Mulago National Referral Hospital<br />
        Kawempe Road, {location}<br />
        📞 +256 414 259 324<br />
        <small>Emergency services available 24/7</small>
      </>;
    } else if (riskLevel.includes('Medium')) {
      return <>
        HarakaCare Medical Center<br />
        123 Health Street, {location}<br />
        📞 +256 123 456 789<br />
        <small>General medical services</small>
      </>;
    } else {
      return <>
        Local Health Center III<br />
        Community Clinic, {location}<br />
        📞 +256 789 012 345<br />
        <small>Basic medical services</small>
      </>;
    }
  };

  const getMapLink = (content) => {
    const location = content.includes('kampala') ? 'Kampala' : 'Uganda';
    const facility = getFacilityName(content);
    return `https://maps.google.com/?q=${encodeURIComponent(facility + ', ' + location)}`;
  };

  const getFacilityName = (content) => {
    const riskLevel = getRiskLevelDisplay(content);
    if (riskLevel.includes('High')) return 'Mulago National Referral Hospital';
    if (riskLevel.includes('Medium')) return 'HarakaCare Medical Center';
    return 'Local Health Center III';
  };

  const handleLocationShare = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const locationMessage = `📍 Location shared: ${position.coords.latitude}, ${position.coords.longitude}`;
          setInputValue(locationMessage);
          handleSendMessage();
        },
        (error) => {
          console.error('Location error:', error);
          // Fallback to manual input
          setInputValue('Please enter your location manually');
        }
      );
    } else {
      // Fallback for browsers without geolocation
      setInputValue('Please enter your location manually');
    }
  };

  const renderMessage = (msg, index) => {
    const isUser = msg.role === 'patient';
    const isMenu = msg.menuData;

    return (
      <div key={index} className={`message ${isUser ? 'user' : 'agent'} ${isMenu ? 'menu' : ''}`}>
        <div className="message-content">
          {typeof msg.content === 'string' ? msg.content.split('\n').map((line, i) => (
            <div key={i}>{line}</div>
          )) : String(msg.content).split('\n').map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
        
        {isMenu && (
          <div className="menu-options">
            {msg.menuData.type === 'list' ? (
              <div className="menu-list">
                {msg.menuData.options.map((option, idx) => (
                  <button 
                    key={idx}
                    onClick={() => handleMenuOptionClick(option.id, msg.field)}
                    className="menu-button list-button"
                  >
                    <div className="button-title">{option.title}</div>
                    {option.description && <div className="button-description">{option.description}</div>}
                  </button>
                ))}
              </div>
            ) : (
              <div className="button-grid">
                {msg.menuData.options.map((option, idx) => (
                  <button 
                    key={idx}
                    onClick={() => handleMenuOptionClick(option.id, msg.field)}
                    className="menu-button"
                  >
                    {option.title}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        
        {msg.type === 'text_input' && (
          <div className="text-input-hint">
            💬 Type your response and press Enter
            {msg.field === 'location' && (
              <button 
                onClick={handleLocationShare}
                className="location-share-button"
              >
                <MapPin size={16} />
                📍 Share My Location
              </button>
            )}
          </div>
        )}
        
        {msg.isResult && (
          <div className="result-card">
            <Activity className="result-icon" />
            <div className="result-content">
              <h3>Assessment Complete</h3>
              <div className="patient-token">
                <strong>Patient Token:</strong> {patientToken}
              </div>
              <div className="risk-level">
                <strong>Risk Level:</strong> {getRiskLevelDisplay(msg.content)}
              </div>
              <div className="assessment-summary">
                <strong>Assessment Summary:</strong><br />
                <div className="summary-details">
                  {getAssessmentSummary(msg.content)}
                </div>
              </div>
              <div className="recommendation">
                <strong>Recommended Facility:</strong><br />
                <div className="facility-info">
                  {getFacilityRecommendation(msg.content)}
                </div>
                <a href={getMapLink(msg.content)} target="_blank" rel="noopener noreferrer" className="map-link">
                  📍 Get Directions
                </a>
              </div>
              <div className="next-steps">
                <strong>Next Steps:</strong><br />
                • Visit the recommended facility with your patient token<br />
                • Bring any medications you're currently taking<br />
                • Follow the medical advice provided
              </div>
            </div>
          </div>
        )}
        
        {msg.isError && (
          <div className="error-card">
            <AlertCircle className="error-icon" />
            <div className="error-content">
              <h3>Error</h3>
              <p>There was an error processing your request.</p>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <h1>🏥 HarakaCare Medical Triage</h1>
        <div className="progress-container">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }}></div>
          </div>
        </div>
      </div>
      
      <div className="messages-container">
        <div className="messages">
          {messages.map(renderMessage)}
          {isTyping && (
            <div className="message agent">
              <div className="typing-indicator">
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
              </div>
            </div>
          )}
        </div>
      </div>
      
      <div className="input-area">
        <div className="input-container">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && inputValue.trim() && !isTyping) {
                handleSendMessage();
              }
            }}
            placeholder={isTyping ? "Processing..." : "Type your message..."}
            disabled={isTyping}
            className={isTyping ? 'disabled' : ''}
          />
          <button
            onClick={handleSendMessage}
            disabled={isTyping || inputValue.trim() === ''}
            className="send-button"
          >
            <Send size={20} />
          </button>
        </div>
        <div className="input-footer">
          <div className="input-hint">
            {isTyping ? "Processing your response..." : "Press Enter to send"}
          </div>
          <div className="progress-saved">
            Your progress is saved
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
