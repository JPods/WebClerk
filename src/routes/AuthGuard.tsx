/* Auth guard — wraps a component with auth check + AppLayout */
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import type { RootState } from '@/store';
import { SidebarProvider } from '@/context/SidebarContext';
import AppLayout from '@/layout/AppLayout';

const RippleLoader = () => <div style={{display:'flex',justifyContent:'center',alignItems:'center',height:'100vh'}}>Loading...</div>;

const AuthGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isLoading, isAuthenticated } = useSelector((state: RootState) => state.auth);

  if (isLoading) return <RippleLoader />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return (
    <SidebarProvider>
      <AppLayout>{children}</AppLayout>
    </SidebarProvider>
  );
};

export default AuthGuard;
