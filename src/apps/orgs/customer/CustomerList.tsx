import React from 'react';
import { useNavigate } from 'react-router-dom';

// Standard list view for customers
export const CustomerList: React.FC = () => {
  const navigate = useNavigate();
  // TODO: Replace with real customer data
  const demoCustomerId = '1';
  return (
    <div>
      <h2>Customer List</h2>
      {/* Render customer list here */}
      <div style={{ margin: '1em 0' }}>
        <button onClick={() => navigate(`/org/customer/dashboard/${demoCustomerId}`)}>
          Go to Customer Dashboard
        </button>
      </div>
    </div>
  );
};
