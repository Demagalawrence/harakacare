import React, { useState, useEffect } from 'react';
import { AlertCircle, ChevronRight, ChevronLeft, Check, X, Activity } from 'lucide-react';
import { patientAPI } from '../services/api';

const PatientTriage = () => {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    age_group: '', // Changed from age_group
    sex: '',
    district: '',
    village: '', // Added missing village field
    subCounty: '',
    primarySymptom: '',
    secondarySymptoms: [],
    severity: '',
    duration: '',
    pattern: '',
    redFlagSymptoms: [],
    chronicConditions: '',
    currentMedication: '',
    hasAllergies: '',
    allergyType: '',
    isPregnant: '',
    additionalNotes: '',
    consent_medical_triage: false, // Changed from consent
    consent_data_sharing: false, // Changed from dataConsent
    consent_follow_up: false // Added new field
  });
  
  const [errors, setErrors] = useState({});
  const [showEmergencyAlert, setShowEmergencyAlert] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionResult, setSubmissionResult] = useState(null);

  const ageGroups = [ // Changed from age_groups
    { value: 'newborn', label: 'Newborn (0-2 months)' },
    { value: 'infant', label: 'Infant (2-12 months)' },
    { value: 'child_1_5', label: 'Child (1-5 years)' },
    { value: 'child_6_12', label: 'Child (6-12 years)' },
    { value: 'teen', label: 'Teen (13-17 years)' },
    { value: 'adult', label: 'Adult (18-64 years)' },
    { value: 'elderly', label: 'Elderly (65+ years)' }
  ];

  const sexOptions = [
    { value: 'male', label: 'Male' },
    { value: 'female', label: 'Female' },
    { value: 'other', label: 'Other / Prefer not to say' }
  ];

  const primarySymptoms = [
    { value: 'fever', label: 'Fever / feeling hot' },
    { value: 'breathing', label: 'Breathing or cough problem' },
    { value: 'injury', label: 'Injury or accident' },
    { value: 'abdominal', label: 'Abdominal pain / vomiting / diarrhea' },
    { value: 'headache', label: 'Headache / confusion / weakness' },
    { value: 'chest_pain', label: 'Chest pain' },
    { value: 'pregnancy', label: 'Pregnancy concern' },
    { value: 'skin', label: 'Skin problem' },
    { value: 'feeding', label: 'Feeding problem / general weakness' },
    { value: 'bleeding', label: 'Bleeding / blood loss' },
    { value: 'mental_health', label: 'Mental health / emotional crisis' },
    { value: 'other', label: 'Other' }
  ];

  const secondarySymptoms = [
    'Loss of appetite', 'Weight loss', 'Night sweats', 'Chills',
    'Runny nose', 'Sneezing', 'Watery eyes', 'Itching', 'Swelling',
    'Constipation', 'Bloating', 'Difficulty sleeping', 'Anxiety', 'Other'
  ];

  const redFlagSymptoms = [
    'Severe chest pain', 'Difficulty breathing', 'Severe headache',
    'Loss of consciousness', 'Seizures', 'Severe bleeding',
    'High fever (>39°C)', 'Confusion', 'Weakness on one side',
    'Vision changes', 'Difficulty speaking'
  ];

  const severityLevels = [
    { value: 'mild', label: 'Mild', description: 'Noticeable but not interfering with daily activities' },
    { value: 'moderate', label: 'Moderate', description: 'Interfering with some daily activities' },
    { value: 'severe', label: 'Severe', description: 'Interfering with most daily activities' },
    { value: 'very_severe', label: 'Very Severe', description: 'Unable to perform daily activities' }
  ];

  const durationOptions = [
    { value: 'today', label: 'Today' },
    { value: '1-3_days', label: '1–3 days' },
    { value: '4-7_days', label: '4–7 days' },
    { value: '1_week_1_month', label: '>1 week, <1 month' },
    { value: '1_month_plus', label: '>1 month' }
  ];

  const patternOptions = [
    { value: 'improving', label: 'Improving' },
    { value: 'same', label: 'Same' },
    { value: 'worse', label: 'Worse' },
    { value: 'intermittent', label: 'Intermittent (comes and goes)' }
  ];

  const districts = [
    'Kampala',
    'Wakiso', 
    'Mpigi',
    'Mukono',
    'Buikwe',
    'Luwero',
    'Nakasongola',
    'Kayunga'
  ];

  useEffect(() => {
    if (formData.redFlagSymptoms.length > 0) {
      setShowEmergencyAlert(true);
    } else {
      setShowEmergencyAlert(false);
    }
  }, [formData.redFlagSymptoms]);

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const handleMultiSelect = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: prev[field].includes(value)
        ? prev[field].filter(item => item !== value)
        : [...prev[field], value]
    }));
  };

  const validateStep = (step) => {
    const newErrors = {};

    switch (step) {
      case 1:
        if (!formData.age_group) newErrors.age_group = 'Age range is required';
        if (!formData.sex) newErrors.sex = 'Sex is required';
        if (!formData.district) newErrors.district = 'District is required';
        if (!formData.village) newErrors.village = 'Village is required';
        break;
      case 2:
        if (!formData.primarySymptom) newErrors.primarySymptom = 'Primary symptom is required';
        break;
      case 3:
        if (!formData.severity) newErrors.severity = 'Severity is required';
        if (!formData.duration) newErrors.duration = 'Duration is required';
        if (!formData.pattern) newErrors.pattern = 'Pattern is required';
        break;
      case 4:
        if (formData.hasAllergies === 'yes' && !formData.allergyType) {
          newErrors.allergyType = 'Please specify allergy type';
        }
        if (formData.sex === 'female' && (formData.age_group === 'teen' || formData.age_group === 'adult') && !formData.isPregnant) {
          newErrors.isPregnant = 'Pregnancy status is required';
        }
        break;
      case 5:
        if (!formData.consent_medical_triage) newErrors.consent_medical_triage = 'You must consent to medical triage to proceed';
        if (!formData.consent_data_sharing) newErrors.consent_data_sharing = 'You must consent to data processing to proceed';
        if (!formData.consent_follow_up) newErrors.consent_follow_up = 'You must consent to follow-up care to proceed';
        break;
      default:
        break;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, 5));
    }
  };

  const handlePrevious = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
  };

  const handleSubmit = async () => {
    if (!validateStep(5)) return;

    setIsSubmitting(true);
    try {
      // Map frontend form data to backend field names
      const backendData = {
        age_group: formData.age_group,
        sex: formData.sex,
        district: formData.district,
        village: formData.village || '', // Ensure empty string if not provided
        complaint_group: formData.primarySymptom, // Use the value directly
        patient_relation: 'self', // Default value
        consent_medical_triage: formData.consent_medical_triage,
        consent_data_sharing: formData.consent_data_sharing,
        consent_follow_up: formData.consent_follow_up,
        location_consent: false, // Default value
        // Add any other potentially required fields with defaults
        complaint_text: '', // Empty string since we're using complaint_group
        device_location_lat: null, // Optional field
        device_location_lng: null, // Optional field
      };

      console.log('Submitting data:', JSON.stringify(backendData, null, 2));

      // Use real API call with correct endpoint (token generated in API service)
      const response = await patientAPI.submitTriage(backendData);
      
      console.log('Backend response:', response);
      
      // Format response for frontend display
      setSubmissionResult({
        success: true,
        caseId: response.patient_token,
        riskLevel: response.risk_level,
        recommendation: response.recommended_action,
        followUpRequired: response.follow_up_required,
        followUpTimeframe: response.follow_up_timeframe
      });
    } catch (error) {
      console.error('Submission error:', error);
      console.error('Error response:', error.response?.data);
      console.error('Validation errors:', error.response?.data?.errors);
      
      // Show specific validation errors if available
      const errorData = error.response?.data;
      let errorMessage = 'Failed to submit your information. Please try again.';
      
      if (errorData?.errors) {
        // Show the first validation error
        const firstError = Object.values(errorData.errors)[0];
        if (Array.isArray(firstError) && firstError.length > 0) {
          errorMessage = firstError[0];
        } else if (typeof firstError === 'string') {
          errorMessage = firstError;
        }
      } else if (errorData?.error) {
        errorMessage = errorData.error;
      }
      
      setSubmissionResult({
        success: false,
        error: errorMessage
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setCurrentStep(1);
    setFormData({
      age_group: '',
      sex: '',
      district: '',
      village: '',
      primarySymptom: '',
      secondarySymptoms: [],
      severity: '',
      duration: '',
      pattern: '',
      redFlagSymptoms: [],
      chronicConditions: '',
      currentMedication: '',
      hasAllergies: '',
      allergyType: '',
      isPregnant: '',
      additionalNotes: '',
      consent: false,
      dataConsent: false
    });
    setSubmissionResult(null);
  };

  if (submissionResult) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className={`card p-8 ${submissionResult.success ? 'border-success-300' : 'border-danger-300'}`}>
          <div className="text-center">
            <div className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 ${
              submissionResult.success ? 'bg-success-100' : 'bg-danger-100'
            }`}>
              {submissionResult.success ? (
                <Check className="w-8 h-8 text-success-600" />
              ) : (
                <X className="w-8 h-8 text-danger-600" />
              )}
            </div>
            
            <h2 className={`text-2xl font-bold mb-2 ${
              submissionResult.success ? 'text-success-800' : 'text-danger-800'
            }`}>
              {submissionResult.success ? 'Assessment Complete' : 'Submission Failed'}
            </h2>
            
            {submissionResult.success ? (
              <div className="space-y-4">
                <div className={`inline-block px-4 py-2 rounded-full text-sm font-medium ${
                  submissionResult.riskLevel === 'high' ? 'risk-high' :
                  submissionResult.riskLevel === 'medium' ? 'risk-medium' : 'risk-low'
                }`}>
                  Risk Level: {submissionResult.riskLevel.toUpperCase()}
                </div>
                
                <p className="text-gray-600 mb-4">
                  Case ID: <span className="font-mono font-bold">{submissionResult.caseId}</span>
                </p>
                
                <div className="bg-gray-50 p-4 rounded-lg text-left">
                  <h3 className="font-semibold mb-2">Recommendation:</h3>
                  <p className="text-gray-700">{submissionResult.recommendation}</p>
                </div>
                
                <button onClick={resetForm} className="btn btn-primary">
                  Start New Assessment
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-gray-600">{submissionResult.error}</p>
                <button onClick={() => setSubmissionResult(null)} className="btn btn-primary">
                  Try Again
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Emergency Alert */}
      {showEmergencyAlert && (
        <div className="mb-6 p-4 bg-danger-100 border border-danger-300 rounded-lg flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-danger-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-danger-800">Emergency Warning</h3>
            <p className="text-danger-700 text-sm">
              You have selected red flag symptoms. Please seek immediate medical attention.
            </p>
          </div>
        </div>
      )}

      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          {[1, 2, 3, 4, 5].map((step) => (
            <div key={step} className="flex items-center">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                currentStep >= step ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-600'
              }`}>
                {currentStep > step ? <Check className="w-5 h-5" /> : step}
              </div>
              {step < 5 && (
                <div className={`w-full h-1 mx-2 ${
                  currentStep > step ? 'bg-primary-600' : 'bg-gray-200'
                }`} />
              )}
            </div>
          ))}
        </div>
        <div className="flex justify-between text-sm text-gray-600">
          <span>Basic Info</span>
          <span>Symptoms</span>
          <span>Details</span>
          <span>Health History</span>
          <span>Consent</span>
        </div>
      </div>

      <div className="card p-6">
        <h2 className="text-2xl font-bold mb-6 flex items-center">
          <Activity className="w-6 h-6 mr-2 text-primary-600" />
          Patient Symptom Assessment
        </h2>

        {/* Step 1: Basic Information */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold">Basic Information</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Age Range *
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {ageGroups.map((range) => (
                  <button
                    key={range.value}
                    type="button"
                    onClick={() => handleInputChange('age_group', range.value)}
                    className={`p-3 rounded-lg border-2 transition-colors ${
                      formData.age_group === range.value
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {range.label}
                  </button>
                ))}
              </div>
              {errors.age_group && <p className="text-danger-600 text-sm mt-1">{errors.age_group}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sex *
              </label>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {sexOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => handleInputChange('sex', option.value)}
                    className={`p-3 rounded-lg border-2 transition-colors ${
                      formData.sex === option.value
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              {errors.sex && <p className="text-danger-600 text-sm mt-1">{errors.sex}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                District *
              </label>
              <select
                value={formData.district}
                onChange={(e) => handleInputChange('district', e.target.value)}
                className="input-field"
              >
                <option value="">Select district</option>
                {districts.map((district) => (
                  <option key={district} value={district}>{district}</option>
                ))}
              </select>
              {errors.district && <p className="text-danger-600 text-sm mt-1">{errors.district}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Village *
              </label>
              <input
                type="text"
                value={formData.village}
                onChange={(e) => handleInputChange('village', e.target.value)}
                placeholder="Enter village"
                className="input-field"
              />
              {errors.village && <p className="text-danger-600 text-sm mt-1">{errors.village}</p>}
            </div>
          </div>
        )}

        {/* Step 2: Symptoms */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold">Symptoms</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Primary Symptom *
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {primarySymptoms.map((symptom) => (
                  <button
                    key={symptom.value}
                    type="button"
                    onClick={() => handleInputChange('primarySymptom', symptom.value)}
                    className={`p-3 rounded-lg border-2 transition-colors text-sm ${
                      formData.primarySymptom === symptom.value
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {symptom.label}
                  </button>
                ))}
              </div>
              {errors.primarySymptom && <p className="text-danger-600 text-sm mt-1">{errors.primarySymptom}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Secondary Symptoms (Select all that apply)
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {secondarySymptoms.map((symptom) => (
                  <button
                    key={symptom}
                    type="button"
                    onClick={() => handleMultiSelect('secondarySymptoms', symptom)}
                    className={`p-3 rounded-lg border-2 transition-colors text-sm ${
                      formData.secondarySymptoms.includes(symptom)
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center justify-center">
                      {formData.secondarySymptoms.includes(symptom) && (
                        <Check className="w-4 h-4 mr-1" />
                      )}
                      {symptom}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Red Flag Symptoms (Select all that apply)
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {redFlagSymptoms.map((symptom) => (
                  <button
                    key={symptom}
                    type="button"
                    onClick={() => handleMultiSelect('redFlagSymptoms', symptom)}
                    className={`p-3 rounded-lg border-2 transition-colors text-sm ${
                      formData.redFlagSymptoms.includes(symptom)
                        ? 'border-danger-500 bg-danger-50 text-danger-700'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center">
                      {formData.redFlagSymptoms.includes(symptom) && (
                        <Check className="w-4 h-4 mr-2" />
                      )}
                      <AlertCircle className="w-4 h-4 mr-2 text-danger-500" />
                      {symptom}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Symptom Details */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold">Symptom Details</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Severity *
              </label>
              <div className="space-y-3">
                {severityLevels.map((level) => (
                  <button
                    key={level.value}
                    type="button"
                    onClick={() => handleInputChange('severity', level.value)}
                    className={`w-full p-4 rounded-lg border-2 transition-colors text-left ${
                      formData.severity === level.value
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="font-medium">{level.label}</div>
                    <div className="text-sm text-gray-600">{level.description}</div>
                  </button>
                ))}
              </div>
              {errors.severity && <p className="text-danger-600 text-sm mt-1">{errors.severity}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Duration - "Since when?" *
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {durationOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => handleInputChange('duration', option.value)}
                    className={`p-3 rounded-lg border-2 transition-colors ${
                      formData.duration === option.value
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              {errors.duration && <p className="text-danger-600 text-sm mt-1">{errors.duration}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Symptom Pattern *
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {patternOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => handleInputChange('pattern', option.value)}
                    className={`p-3 rounded-lg border-2 transition-colors ${
                      formData.pattern === option.value
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              {errors.pattern && <p className="text-danger-600 text-sm mt-1">{errors.pattern}</p>}
            </div>
          </div>
        )}

        {/* Step 4: Health History */}
        {currentStep === 4 && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold">Health History</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Chronic/Continuous Conditions
              </label>
              <textarea
                value={formData.chronicConditions}
                onChange={(e) => handleInputChange('chronicConditions', e.target.value)}
                placeholder="List any chronic conditions (e.g., diabetes, hypertension, asthma)..."
                rows={3}
                className="input-field"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Current Medication
              </label>
              <textarea
                value={formData.currentMedication}
                onChange={(e) => handleInputChange('currentMedication', e.target.value)}
                placeholder="List any medications you are currently taking..."
                rows={3}
                className="input-field"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Do you have any allergies?
              </label>
              <div className="grid grid-cols-3 gap-3">
                {['yes', 'no', 'not_sure'].map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => handleInputChange('hasAllergies', option)}
                    className={`p-3 rounded-lg border-2 transition-colors capitalize ${
                      formData.hasAllergies === option
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {option.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            {formData.hasAllergies === 'yes' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Allergy Type *
                </label>
                <input
                  type="text"
                  value={formData.allergyType}
                  onChange={(e) => handleInputChange('allergyType', e.target.value)}
                  placeholder="Specify the type of allergy (e.g., penicillin, peanuts, etc.)"
                  className="input-field"
                />
                {errors.allergyType && <p className="text-danger-600 text-sm mt-1">{errors.allergyType}</p>}
              </div>
            )}

            {formData.sex === 'female' && (formData.age_group === '13-17' || formData.age_group === '18-30' || formData.age_group === '31-50') && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Are you currently pregnant? *
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {['yes', 'no', 'prefer_not_to_say'].map((option) => (
                    <button
                      key={option}
                      type="button"
                      onClick={() => handleInputChange('isPregnant', option)}
                      className={`p-3 rounded-lg border-2 transition-colors capitalize ${
                        formData.isPregnant === option
                          ? 'border-primary-500 bg-primary-50 text-primary-700'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      {option.replace('_', ' ')}
                    </button>
                  ))}
                </div>
                {errors.isPregnant && <p className="text-danger-600 text-sm mt-1">{errors.isPregnant}</p>}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Additional Notes (Optional)
              </label>
              <textarea
                value={formData.additionalNotes}
                onChange={(e) => handleInputChange('additionalNotes', e.target.value)}
                placeholder="Any additional information you think is important..."
                rows={3}
                className="input-field"
              />
            </div>
          </div>
        )}

        {/* Step 5: Consent */}
        {currentStep === 5 && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold">Consent & Confirmation</h3>
            
            <div className="bg-gray-50 p-6 rounded-lg">
              <h4 className="font-semibold mb-4">Review Your Information</h4>
              <div className="space-y-2 text-sm">
                <div><strong>Age Range:</strong> {ageGroups.find(r => r.value === formData.age_group)?.label}</div>
                <div><strong>Sex:</strong> {sexOptions.find(s => s.value === formData.sex)?.label}</div>
                <div><strong>Location:</strong> {formData.district}, {formData.village}</div>
                <div><strong>Primary Symptom:</strong> {primarySymptoms.find(s => s.value === formData.primarySymptom)?.label}</div>
                {formData.secondarySymptoms.length > 0 && (
                  <div><strong>Secondary Symptoms:</strong> {formData.secondarySymptoms.join(', ')}</div>
                )}
                {formData.redFlagSymptoms.length > 0 && (
                  <div className="text-danger-600">
                    <strong>Red Flag Symptoms:</strong> {formData.redFlagSymptoms.join(', ')}
                  </div>
                )}
                <div><strong>Severity:</strong> {severityLevels.find(s => s.value === formData.severity)?.label}</div>
                <div><strong>Duration:</strong> {durationOptions.find(d => d.value === formData.duration)?.label}</div>
                <div><strong>Pattern:</strong> {patternOptions.find(p => p.value === formData.pattern)?.label}</div>
              </div>
            </div>

            <div className="space-y-4">
              <label className="flex items-start space-x-3">
                <input
                  type="checkbox"
                  checked={formData.consent_medical_triage}
                  onChange={(e) => handleInputChange('consent_medical_triage', e.target.checked)}
                  className="mt-1 w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700">
                  I consent to participate in this health assessment and understand that this is not a substitute for professional medical advice.
                </span>
              </label>
              {errors.consent_medical_triage && <p className="text-danger-600 text-sm">{errors.consent_medical_triage}</p>}

              <label className="flex items-start space-x-3">
                <input
                  type="checkbox"
                  checked={formData.consent_data_sharing}
                  onChange={(e) => handleInputChange('consent_data_sharing', e.target.checked)}
                  className="mt-1 w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700">
                  I consent to the processing of my personal health information for the purpose of this assessment and subsequent healthcare coordination.
                </span>
              </label>
              {errors.consent_data_sharing && <p className="text-danger-600 text-sm">{errors.consent_data_sharing}</p>}

              <label className="flex items-start space-x-3">
                <input
                  type="checkbox"
                  checked={formData.consent_follow_up}
                  onChange={(e) => handleInputChange('consent_follow_up', e.target.checked)}
                  className="mt-1 w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700">
                  I consent to being contacted for follow-up care and additional health assessments as needed.
                </span>
              </label>
              {errors.consent_follow_up && <p className="text-danger-600 text-sm">{errors.consent_follow_up}</p>}
            </div>

            <div className="bg-warning-50 border border-warning-200 p-4 rounded-lg">
              <h4 className="font-semibold text-warning-800 mb-2">You are submitting a new case</h4>
              <p className="text-warning-700 text-sm">
                Once submitted, your information will be reviewed by healthcare professionals who will determine the appropriate level of care.
              </p>
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="flex justify-between mt-8">
          <button
            onClick={handlePrevious}
            disabled={currentStep === 1}
            className={`btn flex items-center space-x-2 ${
              currentStep === 1 ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'btn-secondary'
            }`}
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Previous</span>
          </button>

          {currentStep < 5 ? (
            <button onClick={handleNext} className="btn btn-primary flex items-center space-x-2">
              <span>Next</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="btn btn-primary flex items-center space-x-2"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Submitting...</span>
                </>
              ) : (
                <>
                  <span>Submit Assessment</span>
                  <Check className="w-4 h-4" />
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default PatientTriage;
