import axios from 'axios';

// const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8001/api';

const API_BASE_URL = process.env.REACT_APP_API_URL || 
  (window.location.hostname.includes('vercel.app') 
    ? 'https://harakacare.onrender.com/api' 
    : (window.location.hostname === 'localhost' 
      ? 'http://localhost:8001/api' 
      : '/api'));

// Debug: Log the API URL being used
console.log('API Base URL:', API_BASE_URL);

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// NOTE: Facility dashboard uses session-based auth via withCredentials.

// Patient/Triage API endpoints
export const patientAPI = {
  // Submit patient triage data
  submitTriage: async (patientData) => {
    // Generate patient token if not provided
    const patientToken = patientData.patientToken || `PT-${Date.now().toString(36).substr(-6).toUpperCase()}`;
    
    // Use correct endpoint with patient token in URL
    const response = await api.post(`/v1/triage/${patientToken}/submit/`, patientData);
    return response.data;
  },

  // Get patient case status
  getCaseStatus: async (caseId) => {
    const response = await api.get(`/triage/${caseId}/`);
    return response.data;
  },

  // Get patient history
  getPatientHistory: async (patientToken) => {
    const response = await api.get(`/patients/${patientToken}/history/`);
    return response.data;
  },
};

// Facility dashboard auth endpoints (session-based)
export const facilityAuthAPI = {
  login: async (credentials) => {
    const response = await api.post('/facilities/auth/login/', credentials);
    return response.data;
  },

  logout: async () => {
    const response = await api.post('/facilities/auth/logout/');
    return response.data;
  },

  whoami: async () => {
    const response = await api.get('/facilities/auth/whoami/');
    return response.data;
  },
};

// Facility API endpoints
export const facilityAPI = {
  // Get all cases for a facility
  getCases: async (filters = {}) => {
    const response = await api.get('/facilities/cases/', { params: filters });
    return response.data;
  },

  // Get case details
  getCaseDetails: async (caseId) => {
    const response = await api.get(`/facilities/cases/${caseId}/`);
    return response.data;
  },

  // Confirm a case
  confirmCase: async (caseId, confirmationData) => {
    const response = await api.post(`/facilities/cases/${caseId}/confirm/`, confirmationData);
    return response.data;
  },

  // Reject a case
  rejectCase: async (caseId, reason) => {
    const response = await api.post(`/facilities/cases/${caseId}/reject/`, { reason });
    return response.data;
  },

  // Acknowledge auto-assigned case
  acknowledgeCase: async (caseId) => {
    const response = await api.post(`/facilities/cases/${caseId}/acknowledge/`);
    return response.data;
  },

  // Delete a case
  deleteCase: async (caseId) => {
    const response = await api.delete(`/facilities/cases/${caseId}/delete/`);
    return response.data;
  },

  // Get facility statistics
  getStats: async () => {
    const response = await api.get('/facilities/stats/');
    return response.data;
  },

  // Get facility capacity
  getCapacity: async () => {
    const response = await api.get('/facilities/capacity/');
    return response.data;
  },
};

// Authentication API endpoints
export const authAPI = {
  login: async (credentials) => {
    const response = await api.post('/auth/login/', credentials);
    return response.data;
  },

  logout: async () => {
    const response = await api.post('/auth/logout/');
    return response.data;
  },

  refreshToken: async () => {
    const response = await api.post('/auth/refresh/');
    return response.data;
  },
};

export default api;
