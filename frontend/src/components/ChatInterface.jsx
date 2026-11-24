import React, { useState, useEffect, useRef } from 'react';
import { Activity, Send, RotateCcw, AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';
import { chatAPI } from '../services/api';

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [stage, setStage] = useState('consent');
  const [patientData, setPatientData] = useState({});
  const [suggestedAnswers, setSuggestedAnswers] = useState([]);
  const [progress, setProgress] = useState(5);
  const [assessment, setAssessment] = useState(null);
  const [safety, setSafety] = useState(null);
  const [conversationEnded, setConversationEnded] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    startConversation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const startConversation = async () => {
    setIsLoading(true);
    try {
      const response = await chatAPI.startChat();
      setMessages([{ id: Date.now(), text: response.message, sender: 'ai', timestamp: new Date() }]);
      setStage(response.stage || 'consent');
      setPatientData(response.patient_data || {});
      setConversationId(response.conversation_id);
      setSuggestedAnswers(response.suggested_answers || []);
      setProgress(response.progress || 5);
      setSafety(response.safety || null);
    } catch (error) {
      console.error('Start chat error:', error);
      setMessages([{ id: Date.now(), text: "Sorry, I'm having trouble connecting. Please make sure the backend is running.", sender: 'ai', timestamp: new Date() }]);
    } finally {
      setIsLoading(false);
    }
  };

  const restartAssessment = async () => {
    setMessages([]);
    setConversationId(null);
    setStage('consent');
    setPatientData({});
    setSuggestedAnswers([]);
    setProgress(5);
    setAssessment(null);
    setSafety(null);
    setConversationEnded(false);
    setInputValue('');
    await startConversation();
  };

  const sendMessage = async (text) => {
    const userMessage = (text || inputValue).trim();
    if (!userMessage || isLoading) return;

    setInputValue('');
    setIsLoading(true);
    setSuggestedAnswers([]);

    setMessages(prev => [...prev, { id: Date.now(), text: userMessage, sender: 'user', timestamp: new Date() }]);

    try {
      const response = await chatAPI.continueChat({
        message: userMessage,
        conversation_id: conversationId,
        context: { stage, patient_data: patientData }
      });

      setMessages(prev => [...prev, { id: Date.now() + 1, text: response.message, sender: 'ai', timestamp: new Date() }]);
      setStage(response.stage || stage);
      setPatientData(response.patient_data || patientData);
      setSuggestedAnswers(response.suggested_answers || []);
      setProgress(response.progress || progress);
      setSafety(response.safety || safety);

      if (response.stage === 'completed' || response.stage === 'emergency') {
        setConversationEnded(true);
        setAssessment(response.assessment || null);
      }
    } catch (error) {
      console.error('Continue chat error:', error);
      setMessages(prev => [...prev, { id: Date.now(), text: "Sorry, I'm having trouble connecting. Please try again.", sender: 'ai', timestamp: new Date() }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(inputValue);
  };

  const isEmergency = stage === 'emergency' || safety?.safety_level === 'emergency';
  const isCompleted = stage === 'completed' || conversationEnded;

  return (
    <div className="flex flex-col h-screen max-w-2xl mx-auto bg-gray-50">
      {/* Header */}
      <header className="bg-primary-600 text-white p-4 shadow-md flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Activity className="w-6 h-6" />
          <div>
            <h2 className="font-bold text-lg leading-tight">HarakaCare Triage</h2>
            <p className="text-xs opacity-90">AI Health Assessment Assistant</p>
          </div>
        </div>
        <button
          onClick={restartAssessment}
          className="flex items-center space-x-1 text-xs bg-white/20 hover:bg-white/30 px-3 py-1.5 rounded-lg transition-colors"
          aria-label="Restart assessment"
        >
          <RotateCcw className="w-4 h-4" />
          <span>Restart</span>
        </button>
      </header>

      {/* Progress bar */}
      <div className="bg-white px-4 py-2 border-b border-gray-200">
        <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
          <span>Assessment progress</span>
          <span>{progress}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            className={`h-2 rounded-full transition-all duration-500 ${isEmergency ? 'bg-red-500' : 'bg-primary-600'}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Emergency banner */}
      {isEmergency && (
        <div className="bg-red-600 text-white p-3 flex items-start space-x-2 animate-pulse">
          <ShieldAlert className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            <strong>EMERGENCY:</strong> Danger signs detected. Seek immediate medical attention. Do not wait — go to the nearest hospital or call emergency services.
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] px-4 py-3 rounded-2xl shadow-sm ${
              msg.sender === 'user'
                ? 'bg-primary-600 text-white rounded-br-sm'
                : isEmergency && msg.sender === 'ai'
                  ? 'bg-red-50 text-red-900 border border-red-200 rounded-bl-sm'
                  : 'bg-white text-gray-900 border border-gray-200 rounded-bl-sm'
            }`}>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
              <span className={`text-[10px] mt-1 block ${msg.sender === 'user' ? 'text-white/70' : 'text-gray-400'}`}>
                {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-bl-sm shadow-sm flex items-center space-x-2">
              <div className="flex space-x-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="text-xs text-gray-500">AI is thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested answer buttons */}
      {!conversationEnded && suggestedAnswers.length > 0 && !isLoading && (
        <div className="px-4 pb-2 flex flex-wrap gap-2">
          {suggestedAnswers.map((ans, idx) => (
            <button
              key={idx}
              onClick={() => sendMessage(ans)}
              className="text-xs px-3 py-1.5 rounded-full border border-primary-300 bg-primary-50 text-primary-700 hover:bg-primary-100 transition-colors"
            >
              {ans}
            </button>
          ))}
        </div>
      )}

      {/* Assessment completion card */}
      {isCompleted && assessment && (
        <div className={`mx-4 mb-2 p-4 rounded-xl border shadow-sm ${isEmergency ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'}`}>
          <div className="flex items-center space-x-2 mb-3">
            {isEmergency ? <AlertTriangle className="w-5 h-5 text-red-600" /> : <CheckCircle2 className="w-5 h-5 text-green-600" />}
            <h3 className={`font-bold ${isEmergency ? 'text-red-900' : 'text-green-900'}`}>
              {isEmergency ? 'Emergency Assessment' : 'Assessment Complete'}
            </h3>
          </div>
          <div className="space-y-2 text-sm">
            <div><strong>Case reference:</strong> {assessment.case_reference}</div>
            <div><strong>Main symptoms:</strong> {assessment.main_symptoms}</div>
            <div><strong>Duration:</strong> {assessment.duration} &nbsp;|&nbsp; <strong>Severity:</strong> {assessment.severity}</div>
            <div><strong>Urgency:</strong> <span className="font-semibold uppercase">{assessment.urgency?.level}</span></div>
            {assessment.important_findings?.warning_signs?.length > 0 && (
              <div><strong>Warning signs:</strong> {assessment.important_findings.warning_signs.join(', ')}</div>
            )}
            <div className="mt-2 text-gray-700">{assessment.recommended_next_steps}</div>
            {assessment.facility_assignment?.assigned_facility && (
              <div className="mt-3 p-3 bg-white rounded-lg border border-gray-200">
                <div className="font-semibold text-gray-900 mb-1">Recommended Health Center</div>
                <div className="text-sm text-gray-800">{assessment.facility_assignment.assigned_facility.name}</div>
                {assessment.facility_assignment.assigned_facility.address && (
                  <div className="text-xs text-gray-600 mt-1">Address: {assessment.facility_assignment.assigned_facility.address}</div>
                )}
                {assessment.facility_assignment.assigned_facility.district && (
                  <div className="text-xs text-gray-600">District: {assessment.facility_assignment.assigned_facility.district}</div>
                )}
                {assessment.facility_assignment.assigned_facility.phone_number && (
                  <div className="text-xs text-gray-600">Phone: {assessment.facility_assignment.assigned_facility.phone_number}</div>
                )}
                {assessment.facility_assignment.assigned_facility.latitude != null && assessment.facility_assignment.assigned_facility.longitude != null && (
                  <a href={`https://www.google.com/maps?q=${assessment.facility_assignment.assigned_facility.latitude},${assessment.facility_assignment.assigned_facility.longitude}`} target="_blank" rel="noopener noreferrer" className="inline-block mt-2 text-xs text-primary-600 hover:underline">
                    View on Google Maps
                  </a>
                )}
                {assessment.facility_assignment.assigned_facility.available_medications?.length > 0 && (
                  <div className="text-xs text-gray-600 mt-1">Medications: {assessment.facility_assignment.assigned_facility.available_medications.join(', ')}</div>
                )}
                {assessment.facility_assignment.distance_km != null && (
                  <div className="text-xs text-gray-600 mt-1">Distance: {assessment.facility_assignment.distance_km} km</div>
                )}
              </div>
            )}
            <div className="mt-2 text-xs text-gray-500 italic">{assessment.disclaimer}</div>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-gray-200 bg-white">
        {conversationEnded ? (
          <div className="text-center">
            <button
              onClick={restartAssessment}
              className="px-6 py-2 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 transition-colors"
            >
              Start New Assessment
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex space-x-2">
            <input
              ref={inputRef}
              type="text"
              placeholder="Describe your symptoms naturally..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 outline-none disabled:opacity-50"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !inputValue.trim()}
              className={`px-4 py-2 rounded-xl font-medium flex items-center ${
                isLoading || !inputValue.trim()
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-primary-600 text-white hover:bg-primary-700 transition-colors'
              }`}
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        )}
        {!conversationEnded && (
          <p className="text-xs text-gray-500 text-center mt-2">
            Describe your symptoms naturally. I'll ask follow-up questions. Your answers are kept private.
          </p>
        )}
      </div>
    </div>
  );
};

export default ChatInterface;
