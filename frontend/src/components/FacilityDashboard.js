import React, { useState, useEffect } from 'react';
import { 
  Building2, 
  Users, 
  AlertCircle, 
  CheckCircle, 
  Clock, 
  Filter,
  Search,
  Eye,
  UserCheck,
  Calendar,
  Activity,
  X
} from 'lucide-react';

const FacilityDashboard = () => {
  const [cases, setCases] = useState([]);
  const [filteredCases, setFilteredCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    high: 0,
    medium: 0,
    low: 0,
    pending: 0,
    confirmed: 0
  });


  useEffect(() => {
    let filtered = cases;

    // Apply filter
    if (filter !== 'all') {
      filtered = filtered.filter(c => {
        if (filter === 'high') return c.riskLevel === 'high';
        if (filter === 'medium') return c.riskLevel === 'medium';
        if (filter === 'low') return c.riskLevel === 'low';
        if (filter === 'pending') return c.status === 'pending';
        if (filter === 'confirmed') return c.status === 'confirmed';
        if (filter === 'auto_assigned') return c.status === 'auto_assigned';
        return true;
      });
    }

    // Apply search
    if (searchTerm) {
      filtered = filtered.filter(c => 
        c.patientToken.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.primarySymptom.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.district.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.facility.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    setFilteredCases(filtered);
  }, [filter, searchTerm, cases]);

  const handleCaseAction = (caseId, action) => {
    setCases(prev => prev.map(c => {
      if (c.id === caseId) {
        if (action === 'confirm') {
          return { ...c, status: 'confirmed', confirmedAt: new Date().toISOString() };
        }
        if (action === 'reject') {
          return { ...c, status: 'rejected' };
        }
        if (action === 'acknowledge') {
          return { ...c, acknowledged: true };
        }
      }
      return c;
    }));
  };

  const getRiskBadgeClass = (riskLevel) => {
    switch (riskLevel) {
      case 'high': return 'risk-high';
      case 'medium': return 'risk-medium';
      case 'low': return 'risk-low';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'pending': return 'bg-warning-100 text-warning-800';
      case 'confirmed': return 'bg-success-100 text-success-800';
      case 'auto_assigned': return 'bg-danger-100 text-danger-800';
      case 'rejected': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center">
            <Building2 className="w-8 h-8 mr-3 text-primary-600" />
            Facility Dashboard
          </h1>
          <p className="text-gray-600 mt-1">Monitor and manage patient triage cases</p>
        </div>
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <Clock className="w-4 h-4" />
          <span>Last updated: {formatTime(new Date().toISOString())}</span>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Cases</p>
              <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
            </div>
            <Users className="w-8 h-8 text-primary-600" />
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">High Risk</p>
              <p className="text-2xl font-bold text-danger-600">{stats.high}</p>
            </div>
            <AlertCircle className="w-8 h-8 text-danger-600" />
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Pending Review</p>
              <p className="text-2xl font-bold text-warning-600">{stats.pending}</p>
            </div>
            <Clock className="w-8 h-8 text-warning-600" />
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Confirmed</p>
              <p className="text-2xl font-bold text-success-600">{stats.confirmed}</p>
            </div>
            <CheckCircle className="w-8 h-8 text-success-600" />
          </div>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="card p-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
          <div className="flex flex-wrap items-center space-x-2">
            <Filter className="w-4 h-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Filter:</span>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="input-field w-auto"
            >
              <option value="all">All Cases</option>
              <option value="high">High Risk</option>
              <option value="medium">Medium Risk</option>
              <option value="low">Low Risk</option>
              <option value="pending">Pending</option>
              <option value="confirmed">Confirmed</option>
              <option value="auto_assigned">Auto Assigned</option>
            </select>
          </div>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by token, symptom, district..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input-field pl-10 w-full md:w-80"
            />
          </div>
        </div>
      </div>

      {/* Cases List */}
      <div className="card">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Incoming Cases</h2>
          <p className="text-sm text-gray-600 mt-1">
            Showing {filteredCases.length} of {cases.length} cases
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Case Details
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Risk Level
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredCases.map((caseItem) => (
                <tr key={caseItem.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-start space-x-3">
                      <div className="flex-shrink-0">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                          caseItem.riskLevel === 'high' ? 'bg-danger-100' :
                          caseItem.riskLevel === 'medium' ? 'bg-warning-100' : 'bg-success-100'
                        }`}>
                          <Activity className={`w-4 h-4 ${
                            caseItem.riskLevel === 'high' ? 'text-danger-600' :
                            caseItem.riskLevel === 'medium' ? 'text-warning-600' : 'text-success-600'
                          }`} />
                        </div>
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {caseItem.patientToken}
                        </div>
                        <div className="text-sm text-gray-500">
                          {caseItem.primarySymptom}
                          {caseItem.secondarySymptoms.length > 0 && (
                            <span> +{caseItem.secondarySymptoms.length}</span>
                          )}
                        </div>
                        <div className="text-xs text-gray-400">
                          {caseItem.district}, {caseItem.subCounty}
                        </div>
                      </div>
                    </div>
                  </td>

                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getRiskBadgeClass(caseItem.riskLevel)}`}>
                      {caseItem.riskLevel.toUpperCase()}
                    </span>
                  </td>

                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusBadgeClass(caseItem.status)}`}>
                      {caseItem.status.replace('_', ' ').toUpperCase()}
                    </span>
                    {caseItem.redFlagSymptoms.length > 0 && (
                      <div className="flex items-center mt-1 text-xs text-danger-600">
                        <AlertCircle className="w-3 h-3 mr-1" />
                        Red flags
                      </div>
                    )}
                  </td>

                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <div>{formatTime(caseItem.createdAt)}</div>
                    {caseItem.confirmedAt && (
                      <div className="text-xs text-success-600">Confirmed: {formatTime(caseItem.confirmedAt)}</div>
                    )}
                  </td>

                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => setSelectedCase(caseItem)}
                        className="text-primary-600 hover:text-primary-900"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      
                      {caseItem.status === 'pending' && (
                        <>
                          <button
                            onClick={() => handleCaseAction(caseItem.id, 'confirm')}
                            className="text-success-600 hover:text-success-900"
                            title="Confirm Case"
                          >
                            <UserCheck className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleCaseAction(caseItem.id, 'reject')}
                            className="text-danger-600 hover:text-danger-900"
                            title="Reject Case"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </>
                      )}
                      
                      {caseItem.status === 'auto_assigned' && !caseItem.acknowledged && (
                        <button
                          onClick={() => handleCaseAction(caseItem.id, 'acknowledge')}
                          className="btn btn-warning btn-sm"
                        >
                          Acknowledge
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredCases.length === 0 && (
          <div className="text-center py-12">
            <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No cases found</h3>
            <p className="text-gray-500">Try adjusting your filters or search terms</p>
          </div>
        )}
      </div>

      {/* Case Details Modal */}
      {selectedCase && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">
                  Case Details - {selectedCase.patientToken}
                </h3>
                <button
                  onClick={() => setSelectedCase(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Risk and Status */}
              <div className="flex items-center space-x-4">
                <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getRiskBadgeClass(selectedCase.riskLevel)}`}>
                  {selectedCase.riskLevel.toUpperCase()} RISK
                </span>
                <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getStatusBadgeClass(selectedCase.status)}`}>
                  {selectedCase.status.replace('_', ' ').toUpperCase()}
                </span>
              </div>

              {/* Patient Information */}
              <div>
                <h4 className="font-semibold text-gray-900 mb-3">Patient Information</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Token:</span>
                    <span className="ml-2 font-medium">{selectedCase.patientToken}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Age Range:</span>
                    <span className="ml-2 font-medium">{selectedCase.ageRange}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Sex:</span>
                    <span className="ml-2 font-medium capitalize">{selectedCase.sex}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Location:</span>
                    <span className="ml-2 font-medium">{selectedCase.district}, {selectedCase.subCounty}</span>
                  </div>
                </div>
              </div>

              {/* Symptoms */}
              <div>
                <h4 className="font-semibold text-gray-900 mb-3">Symptoms</h4>
                <div className="space-y-2">
                  <div>
                    <span className="text-gray-600">Primary:</span>
                    <span className="ml-2 font-medium">{selectedCase.primarySymptom}</span>
                  </div>
                  {selectedCase.secondarySymptoms.length > 0 && (
                    <div>
                      <span className="text-gray-600">Secondary:</span>
                      <span className="ml-2 font-medium">{selectedCase.secondarySymptoms.join(', ')}</span>
                    </div>
                  )}
                  <div>
                    <span className="text-gray-600">Severity:</span>
                    <span className="ml-2 font-medium capitalize">{selectedCase.severity.replace('_', ' ')}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Duration:</span>
                    <span className="ml-2 font-medium">{selectedCase.duration.replace(/_/g, ' ')}</span>
                  </div>
                </div>
              </div>

              {/* Red Flag Symptoms */}
              {selectedCase.redFlagSymptoms.length > 0 && (
                <div className="bg-danger-50 border border-danger-200 p-4 rounded-lg">
                  <h4 className="font-semibold text-danger-800 mb-2 flex items-center">
                    <AlertCircle className="w-4 h-4 mr-2" />
                    Red Flag Symptoms
                  </h4>
                  <ul className="list-disc list-inside text-sm text-danger-700">
                    {selectedCase.redFlagSymptoms.map((symptom, index) => (
                      <li key={index}>{symptom}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Facility Information */}
              <div>
                <h4 className="font-semibold text-gray-900 mb-3">Facility Information</h4>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-gray-600">Assigned Facility:</span>
                    <span className="ml-2 font-medium">{selectedCase.facility}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Recommendation:</span>
                    <span className="ml-2 font-medium">{selectedCase.recommendation}</span>
                  </div>
                </div>
              </div>

              {/* Timestamps */}
              <div>
                <h4 className="font-semibold text-gray-900 mb-3">Timeline</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center">
                    <Calendar className="w-4 h-4 text-gray-400 mr-2" />
                    <span className="text-gray-600">Created:</span>
                    <span className="ml-2">{formatTime(selectedCase.createdAt)}</span>
                  </div>
                  {selectedCase.confirmedAt && (
                    <div className="flex items-center">
                      <CheckCircle className="w-4 h-4 text-success-600 mr-2" />
                      <span className="text-gray-600">Confirmed:</span>
                      <span className="ml-2">{formatTime(selectedCase.confirmedAt)}</span>
                    </div>
                  )}
                  {selectedCase.appointmentDate && (
                    <div className="flex items-center">
                      <Calendar className="w-4 h-4 text-primary-600 mr-2" />
                      <span className="text-gray-600">Appointment:</span>
                      <span className="ml-2">{formatTime(selectedCase.appointmentDate)}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Actions */}
              {selectedCase.status === 'pending' && (
                <div className="flex space-x-3 pt-4 border-t border-gray-200">
                  <button
                    onClick={() => {
                      handleCaseAction(selectedCase.id, 'confirm');
                      setSelectedCase(null);
                    }}
                    className="btn btn-success flex-1"
                  >
                    <UserCheck className="w-4 h-4 mr-2" />
                    Confirm Case
                  </button>
                  <button
                    onClick={() => {
                      handleCaseAction(selectedCase.id, 'reject');
                      setSelectedCase(null);
                    }}
                    className="btn btn-danger flex-1"
                  >
                    <X className="w-4 h-4 mr-2" />
                    Reject Case
                  </button>
                </div>
              )}

              {selectedCase.status === 'auto_assigned' && !selectedCase.acknowledged && (
                <div className="pt-4 border-t border-gray-200">
                  <button
                    onClick={() => {
                      handleCaseAction(selectedCase.id, 'acknowledge');
                      setSelectedCase(null);
                    }}
                    className="btn btn-warning w-full"
                  >
                    Acknowledge Receipt
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FacilityDashboard;
