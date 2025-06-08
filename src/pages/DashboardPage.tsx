import React from 'react';
import { useAppSelector } from '../store/hooks';


const DashboardPage: React.FC = () => {
 const { user } = useAppSelector((state) => state.auth);

//   const handleLogout = () => {
//     dispatch(logout());
//   };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <button
          //onClick={handleLogout}
          className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
        >
          Logout
        </button>
      </div>
      <div className="p-6 bg-white rounded-lg shadow">
        <p className="text-lg">Welcome, {user?.id}!</p>
        <p className="text-gray-600">You are now logged in.</p>
      </div>
    </div>
  );
};

export default DashboardPage;