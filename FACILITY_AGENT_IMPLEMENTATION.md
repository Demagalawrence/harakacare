# HarakaCare Facility Agent Implementation

## Overview
Complete implementation of the HarakaCare Facility Agent based on the provided specification. The Facility Agent manages routing of patient cases to healthcare facilities based on triage outputs, facility availability, and risk levels using a hybrid booking model.

## Architecture Components

### 1. Enhanced Facility Model (`apps/facilities/models.py`)
- **Capacity Management**: total_beds, available_beds, staff_count
- **Services**: JSON field for offered services (emergency, general_medicine, etc.)
- **Real-time Info**: average_wait_time_minutes, ambulance_available
- **Communication**: notification_endpoint for facility API integration
- **Utility Methods**: distance calculation, capacity checking, service validation

### 2. Facility Agent Models (`apps/facilities/models_facility_agent.py`)

#### FacilityRouting
- Main routing record with patient case data from Triage Agent
- Supports hybrid booking: automatic for emergencies, manual for routine cases
- Tracks complete routing workflow with timestamps
- Priority scoring and risk level handling

#### FacilityCandidate
- Stores all considered facilities with match scores
- Distance, capacity, and service compatibility tracking
- Selection reasoning for audit trail

#### FacilityNotification
- Complete notification tracking to facilities
- Multiple notification types: new_case, confirmation, cancellation
- Response handling and acknowledgment tracking
- Retry mechanism with error handling

#### FacilityCapacityLog
- Audit trail of capacity changes
- Change tracking with reasons and sources
- Performance monitoring data

### 3. Internal Tools

#### Facility Matching Tool (`apps/facilities/tools/facility_matching.py`)
- **Location-based matching**: District preference + distance calculation
- **Capacity filtering**: Real-time bed availability checking
- **Service matching**: Symptom-to-service mapping
- **Scoring algorithm**: Distance (30%) + Capacity (25%) + Services (25%) + Type (10%) + Emergency (10%)
- **Validation**: Comprehensive facility capability validation

#### Prioritization Tool (`apps/facilities/tools/prioritization.py`)
- **Urgency scoring**: Emergency (1000) > High (500) > Medium (100) > Low (10)
- **Capability assessment**: Emergency handling, service matching, facility type
- **Availability scoring**: Bed ratios, staff levels, ambulance access
- **Hybrid booking logic**: Automatic for emergencies, manual for routine cases
- **Alternative facility selection**: Fallback mechanism for rejections

#### Notification/Dispatch Tool (`apps/facilities/tools/notification_dispatch.py`)
- **Multi-channel delivery**: API endpoint → SMS fallback
- **HTTP session management**: Retry strategy with exponential backoff
- **Payload formatting**: Structured JSON for facility APIs
- **Response tracking**: Acknowledgment and confirmation handling
- **Performance monitoring**: Response time analytics

#### Logging & Monitoring Tool (`apps/facilities/tools/logging_monitoring.py`)
- **Comprehensive audit trail**: All routing decisions and responses
- **Compliance reporting**: Emergency response rates, acknowledgment rates
- **Performance dashboard**: Daily statistics, facility rankings
- **Export capabilities**: JSON, CSV, XML formats
- **System event logging**: Error tracking and monitoring

### 4. API Endpoints (`apps/facilities/views_facility_agent.py`)

#### FacilityAgentViewSet
- **POST /**: Create new routing from Triage Agent
- **POST /{id}/confirm_facility**: Manual facility confirmation
- **POST /{id}/facility_response**: Handle facility responses
- **GET /statistics**: Performance and compliance metrics
- **GET /audit_trail**: Audit trail access
- **POST /update_capacity**: Facility capacity updates

#### FacilityNotificationViewSet
- **POST /{id}/retry**: Retry failed notifications
- **POST /{id}/acknowledge**: Manual acknowledgment

#### FacilityCapacityLogViewSet
- **GET /**: Read-only access to capacity logs

### 5. Main Orchestrator (`apps/facilities/services/facility_agent_orchestrator.py`)
- **Complete workflow coordination**: Intake → Matching → Prioritization → Notification
- **Transaction management**: Database consistency guarantees
- **Error handling**: Comprehensive exception management and logging
- **Maintenance tasks**: Retry failed notifications, performance monitoring
- **Inter-agent communication**: Follow-up Agent integration

## Key Features Implemented

### ✅ Hybrid Booking Model
- **Automatic booking**: High-risk and emergency cases
- **Manual confirmation**: Medium/low-risk cases
- **Emergency override**: Red flag detection bypasses manual approval

### ✅ Privacy-Preserving Design
- **No PII transmission**: Only patient tokens and clinical data
- **Anonymized routing**: Patient identities protected
- **Secure communication**: HTTPS with authentication

### ✅ Intelligent Matching
- **Multi-factor scoring**: Location, capacity, services, facility type
- **Emergency prioritization**: Automatic routing for critical cases
- **Alternative selection**: Fallback facilities for rejections

### ✅ Comprehensive Monitoring
- **Real-time tracking**: All routing steps logged
- **Performance metrics**: Response times, success rates
- **Compliance reporting**: Audit trails for regulatory requirements
- **Capacity monitoring**: Bed availability and utilization

### ✅ Robust Communication
- **Retry mechanisms**: Failed notification handling
- **Multiple channels**: API, SMS, email support
- **Response tracking**: Acknowledgment and confirmation monitoring
- **Error handling**: Comprehensive error logging and recovery

## API Integration Examples

### Receiving Triage Data
```json
POST /api/facilities/agent/
{
    "patient_token": "abc123def456",
    "triage_session_id": "session_789",
    "risk_level": "high",
    "primary_symptom": "chest_pain",
    "secondary_symptoms": ["difficulty_breathing"],
    "has_red_flags": true,
    "chronic_conditions": ["hypertension"],
    "patient_district": "Nairobi",
    "patient_location_lat": -1.2921,
    "patient_location_lng": 36.8219
}
```

### Facility Response
```json
POST /api/facilities/agent/{id}/facility_response/
{
    "facility_id": 123,
    "response_type": "confirm",
    "response_message": "Patient accepted, bed reserved",
    "beds_reserved": 1,
    "estimated_arrival": "2026-02-18T15:30:00Z",
    "capacity_confirmed": true
}
```

### Capacity Update
```json
POST /api/facilities/agent/update_capacity/
{
    "facility_id": 123,
    "capacity": {
        "available_beds": 45,
        "staff_count": 12,
        "average_wait_time_minutes": 45,
        "reason": "patient_admission",
        "source": "facility_system"
    }
}
```

## Database Schema

### New Tables Created
1. **facilities_facilityrouting** - Main routing records
2. **facilities_facilitycandidate** - Facility candidates with scores
3. **facilities_facilitynotification** - Notification tracking
4. **facilities_facilitycapacitylog** - Capacity change logs

### Enhanced Tables
1. **facilities_facility** - Added capacity and service fields

## Security & Compliance

### Data Protection
- **PII isolation**: No personal health information stored
- **Token-based identification**: Anonymous patient tokens only
- **Secure APIs**: Authentication required for all endpoints

### Audit Trail
- **Complete logging**: All actions and decisions recorded
- **Timestamp tracking**: Full chronological audit trail
- **Change tracking**: Capacity and status changes logged

### Performance Monitoring
- **Response time tracking**: Facility acknowledgment metrics
- **Success rate monitoring**: Booking and notification analytics
- **Capacity utilization**: Real-time facility usage tracking

## Future Enhancements Ready

### AI Integration Points
- **Facility Matching AI**: Placeholder for transformer-based matching
- **Predictive routing**: ML models for outcome prediction
- **Capacity forecasting**: Time-series analysis for bed availability

### Scalability Features
- **Real-time capacity APIs**: Webhook support for facilities
- **Geographic expansion**: Multi-region facility support
- **Load balancing**: Intelligent distribution across facilities

## Testing & Validation

### Unit Tests Coverage
- **Model validation**: All serializers and models tested
- **Tool functionality**: Matching, prioritization, notification tools
- **API endpoints**: Complete request/response validation

### Integration Testing
- **End-to-end workflows**: Triage → Facility → Follow-up
- **Error scenarios**: Network failures, facility rejections
- **Performance testing**: Load testing for high-volume scenarios

## Deployment Notes

### Environment Variables
```bash
FACILITY_API_KEY=your_api_key_here
DEBUG=True/False
DATABASE_URL=postgresql://...
```

### Dependencies
- **Django REST Framework**: API development
- **Requests**: HTTP client for facility communication
- **Django-Filters**: Query filtering and search
- **Logging**: Comprehensive audit trail system

## Summary

The HarakaCare Facility Agent implementation provides a complete, production-ready solution for:

1. **Intelligent patient routing** based on clinical urgency and facility capabilities
2. **Hybrid booking model** balancing automation with safety
3. **Comprehensive monitoring** for compliance and performance
4. **Scalable architecture** ready for AI enhancements and growth
5. **Privacy-preserving design** compliant with healthcare data requirements

The implementation follows all specifications from the requirements document and provides a solid foundation for the HarakaCare healthcare ecosystem.
