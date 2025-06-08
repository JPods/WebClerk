import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import PrivateRoute from './PrivateRoute';
import LoginPage from '../pages/LoginPage';
import DashboardPage from '../pages/DashboardPage';
import { Toster } from '../components/wrapper';
import { PageRoutes } from './Routes';
import { ExamAdd, ExamList } from '../pages/wrapperPage';

const Router: React.FC = () => {
  return (
    <BrowserRouter>
      <Toster/>
      <Routes>
        {/* Public routes */}
        <Route path={PageRoutes.login} element={<LoginPage />} />       
        
        {/* Protected routes */}
        <Route element={<PrivateRoute />}>
          <Route path={PageRoutes.dashboard} element={<DashboardPage />} />
          <Route path={PageRoutes.examList} element={<ExamList />} />
          <Route path={PageRoutes.examAdd} element={<ExamAdd />} />
        </Route>
        
        {/* 404 page */}
        <Route path="*" element={<div>404 Not Found</div>} />
      </Routes>
    </BrowserRouter>
  );
};

export default Router;