import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 
  (window.location.hostname.includes('vercel.app') 
    ? 'https://harakacare.onrender.com/api' 
    : (window.location.hostname === 'localhost' 
      ? 'https://harakacare.onrender.com/api'  // Use deployed backend even when testing locally
      : '/api'));

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// Chat API endpoints for conversational agent
export const chatAPI = {
  // Start a new conversation
  startConversation: async (message, patientToken = null) => {
    try {
      const payload = patientToken 
        ? { message, patient_token: patientToken }
        : { message };
      
      const response = await api.post('/v1/chat/start/', payload);
      return response.data;
    } catch (error) {
      console.error('Error starting conversation:', error);
      throw error;
    }
  },

  // Continue an existing conversation
  continueConversation: async (message, patientToken) => {
    try {
      const response = await api.post(`/v1/chat/continue/${patientToken}/`, { message });
      return response.data;
    } catch (error) {
      console.error('Error continuing conversation:', error);
      throw error;
    }
  },

  // Get conversation status
  getConversationStatus: async (patientToken) => {
    try {
      const response = await api.get(`/v1/chat/status/${patientToken}/`);
      return response.data;
    } catch (error) {
      console.error('Error getting conversation status:', error);
      throw error;
    }
  },

  // Submit final triage assessment
  submitTriage: async (patientData) => {
    try {
      const patientToken = patientData.patientToken || `PT-${Date.now().toString(36).substr(-6).toUpperCase()}`;
      
      // Map frontend form data to backend format
      const backendData = {
        patient_token: patientToken,
        complaint_text: patientData.primarySymptom,
        ...mapFormDataToBackend(patientData)
      };
      
      const response = await api.post(`/v1/triage/${patientToken}/submit/`, backendData);
      return response.data;
    } catch (error) {
      console.error('Error submitting triage:', error);
      throw error;
    }
  }
};

// Helper function to map frontend form data to backend format
const mapFormDataToBackend = (formData) => {
  return {
    age_group: formData.age_group,
    sex: formData.sex,
    district: formData.district,
    village: formData.subCounty,
    complaint_group: formData.primarySymptom,
    severity: formData.severity,
    duration: formData.duration,
    progression_status: formData.pattern || formData.progression_status,
    condition_occurrence: formData.condition_occurrence,
    allergies_status: formData.hasAllergies,
    allergy_types: formData.allergyType ? [formData.allergyType] : [],
    chronic_conditions: formData.chronicConditions ? [formData.chronicConditions] : [],
    has_chronic_conditions: !!formData.chronicConditions && formData.chronicConditions !== 'No',
    on_medication: formData.currentMedication === 'Yes' || formData.currentMedication === true,
    pregnancy_status: formData.isPregnant,
    consents_given: formData.consent_medical_triage,
    location: formData.district,
    // Additional fields
    patient_relation: 'self',
    symptom_indicators: {},
    red_flag_indicators: {},
    risk_modifiers: {},
    complaint_group_confidence: 0.8,
    severity_confidence: 0.8,
    duration_confidence: 0.8,
    age_group_confidence: 0.8
  };
};

export default chatAPI;
