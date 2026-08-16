/* Auth guard — wraps a component with auth check + AppLayout */
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import type { RootState } from '@/store';
import { SidebarProvider } from '@/context/SidebarContext';
import AppLayout from '@/layout/AppLayout';
import LoadingSpinner from '@/components/common/LoadingSpinner';

const AuthGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isLoading, isAuthenticated } = useSelector((state: RootState) => state.auth);

  if (isLoading) return <div className="flex justify-center items-center h-screen"><LoadingSpinner size="lg" label="Loading..." /></div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return (
    <SidebarProvider>
      <AppLayout>{children}</AppLayout>
    </SidebarProvider>
  );
};

export default AuthGuard;
