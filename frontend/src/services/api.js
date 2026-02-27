import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Patient/Triage API endpoints
export const patientAPI = {
  // Submit patient triage data
  submitTriage: async (patientData) => {
    const response = await api.post('/triage/', patientData);
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
