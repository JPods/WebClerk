import React from 'react';
import { useParams } from 'react-router-dom';
import { CustomerDashboard } from '../CustomerDashboard';

// This page expects a customerId param in the route
const CustomerDashboardPage: React.FC = () => {
  const { customerId } = useParams<{ customerId: string }>();
  return (
    <div>
      <CustomerDashboard customerId={customerId} />
    </div>
  );
};

export default CustomerDashboardPage;
