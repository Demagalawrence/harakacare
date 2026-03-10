import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Activity, Building2 } from 'lucide-react';

const Header = () => {
  const location = useLocation();
  
  const isActive = (path) => location.pathname === path;
  
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-2">
            <Activity className="h-8 w-8 text-primary-600" />
            <h1 className="text-xl font-bold text-gray-900">HarakaCare</h1>
          </div>
          
          <nav className="flex space-x-1">
            <Link
              to="/patient"
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                isActive('/patient')
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Activity className="h-4 w-4" />
              <span>Patient Triage</span>
            </Link>
            
            <Link
              to="/facility"
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                isActive('/facility')
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Building2 className="h-4 w-4" />
              <span>Facility Dashboard</span>
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
};

export default Header;
