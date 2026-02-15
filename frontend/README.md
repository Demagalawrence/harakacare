# HarakaCare Frontend

A modern React-based frontend for the HarakaCare healthcare triage and facility management system.

## Features

### Patient + Triage Agent
- **Step-by-step symptom assessment** with intuitive UI
- **Conditional logic** for dynamic field display
- **Red flag symptom detection** with emergency alerts
- **Comprehensive validation** and error handling
- **Mobile-responsive design** for accessibility

### Facility Agent Dashboard
- **Real-time case monitoring** with live updates
- **Risk level categorization** (High/Medium/Low)
- **Case management** (Confirm/Reject/Acknowledge)
- **Advanced filtering** and search capabilities
- **Detailed case views** with full patient information

## Technology Stack

- **React 18** - Modern UI framework
- **Tailwind CSS** - Utility-first styling
- **React Router** - Navigation and routing
- **Axios** - HTTP client for API calls
- **Lucide React** - Beautiful icons

## Getting Started

### Prerequisites
- Node.js 16+ 
- npm or yarn

### Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Set up environment variables:**
   Create a `.env` file in the frontend directory:
   ```
   REACT_APP_API_URL=http://127.0.0.1:8000/api
   ```

3. **Start the development server:**
   ```bash
   npm start
   ```

4. **Open your browser:**
   Navigate to `http://localhost:3000`

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── Header.js              # Navigation header
│   │   ├── PatientTriage.js       # Patient assessment form
│   │   └── FacilityDashboard.js    # Facility management dashboard
│   ├── services/
│   │   └── api.js                 # API service layer
│   ├── App.js                     # Main application component
│   ├── index.js                   # Application entry point
│   └── index.css                  # Global styles
├── package.json
├── tailwind.config.js
└── README.md
```

## Key Features

### Patient Triage Flow
1. **Basic Information** - Age, sex, location
2. **Symptom Reporting** - Primary and secondary symptoms
3. **Symptom Details** - Severity, duration, pattern
4. **Health History** - Chronic conditions, medications, allergies
5. **Consent & Confirmation** - Review and submit

### Facility Dashboard
- **Statistics Overview** - Total cases, risk distribution
- **Case Management** - Filter, search, and manage cases
- **Real-time Updates** - Live case status changes
- **Detailed Views** - Comprehensive patient information

## API Integration

The frontend is designed to integrate with the Django backend through REST APIs:

### Patient Endpoints
- `POST /api/triage/` - Submit triage assessment
- `GET /api/triage/{id}/` - Get case status
- `GET /api/patients/{token}/history/` - Patient history

### Facility Endpoints
- `GET /api/facilities/cases/` - Get facility cases
- `POST /api/facilities/cases/{id}/confirm/` - Confirm case
- `POST /api/facilities/cases/{id}/reject/` - Reject case
- `GET /api/facilities/stats/` - Facility statistics

## Design Principles

- **Accessibility First** - WCAG compliant design
- **Mobile Responsive** - Works on all device sizes
- **Intuitive UX** - Clear navigation and user flows
- **Real-time Feedback** - Immediate validation and updates
- **Professional Healthcare UI** - Clean, trustworthy interface

## Development

### Building for Production
```bash
npm run build
```

### Running Tests
```bash
npm test
```

### Code Style
The project uses ESLint for code consistency. Run:
```bash
npm run lint
```

## Demo Features

The frontend includes mock data for demonstration purposes:
- Sample patient cases with various risk levels
- Interactive dashboard with filtering and search
- Complete triage workflow with validation
- Emergency alert system for red flag symptoms

## Contributing

1. Follow the existing code style and patterns
2. Ensure responsive design for all new components
3. Add proper error handling and loading states
4. Test with mock data before API integration
5. Maintain accessibility standards

## Support

For questions or issues related to the frontend implementation, please refer to the project documentation or contact the development team.
