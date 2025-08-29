import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import PrivateRoute from './PrivateRoute';
import { PageRoutes } from './Routes';
import { ScrollToTop, Toster } from '../components/wrapper';
import { ActionAdd, ActionList, BasicTables, Calendar, ContactAdd, ContactList, FormElements, Home, SignIn, SignUp, UserProfiles } from '../pages/wrapperPage';
import { Provider } from 'react-redux';
import { store } from '../store';
import Test from '../pages/test/Test';



const Router: React.FC = () => {
  return (
    // <Provider store={store}>
        <BrowserRouter>
          <ScrollToTop />
          <Toster/>
          <Routes>
                    
            {/* Public routes */}
            <Route path={PageRoutes.login} element={<SignIn />} />       
            <Route path={PageRoutes.register} element={<SignUp />} />
            <Route path="/test" element={<Test />} />
            {/* Protected routes */}
            <Route element={<PrivateRoute />}>
              <Route path={PageRoutes.dashboard} element={<Home />} />   
              <Route path={PageRoutes.profile} element={<UserProfiles />} />   
              <Route path={PageRoutes.actionList} element={<ActionList />} />
              <Route path={PageRoutes.actionAdd} element={<ActionAdd />} />  
              <Route path={PageRoutes.actionAdd + '/:id'} element={<ActionAdd />} /> 
              <Route path={PageRoutes.contactList} element={<ContactList />} /> 
              <Route path={PageRoutes.contactAdd} element={<ContactAdd />} />
          
              <Route path="/calendar" element={<Calendar />} />
              <Route path="/form-elements" element={<FormElements />} />
              <Route path="/basic-tables" element={<BasicTables />} />   
            </Route>
            
            {/* 404 page */}
            <Route path="*" element={<div>404 Not Found</div>} />
          </Routes>
        </BrowserRouter>
    // </Provider>    
  );
};

export default Router;