import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import PrivateRoute from './PrivateRoute';
import { PageRoutes } from './Routes';
import { ScrollToTop, Toster } from '../components/wrapper';
import { Home, SignIn, SignUp } from '../pages/wrapperPage';


const Router: React.FC = () => {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <Toster/>
      <Routes>
                
        {/* Public routes */}
        <Route path={PageRoutes.login} element={<SignIn />} />       
        <Route path={PageRoutes.register} element={<SignUp />} />

        {/* Protected routes */}
        <Route element={<PrivateRoute />}>
          <Route path={PageRoutes.dashboard} element={<Home />} />         
        </Route>
        
        {/* 404 page */}
        <Route path="*" element={<div>404 Not Found</div>} />
      </Routes>
    </BrowserRouter>
  );
};

export default Router;