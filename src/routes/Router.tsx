import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import PrivateRoute from './PrivateRoute';
import { PageRoutes } from './Routes';
import { ScrollToTop, Toster } from '../components/wrapper';
import { BasicTables, Calendar, FormElements, Home, SignIn, SignUp, UserProfiles } from '../pages/wrapperPage';


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
          <Route path={PageRoutes.profile} element={<UserProfiles />} />      
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/form-elements" element={<FormElements />} />
          <Route path="/basic-tables" element={<BasicTables />} />   
        </Route>
        
        {/* 404 page */}
        <Route path="*" element={<div>404 Not Found</div>} />
      </Routes>
    </BrowserRouter>
  );
};

export default Router;