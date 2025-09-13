import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import PrivateRoute from './PrivateRoute';
import { PageRoutes } from './Routes';
import { ScrollToTop, Toster } from '../components/wrapper';
import { ActionAdd, ActionList, BasicTables, Calendar, ContactAdd, ContactList, DomainAdd, DomainList, FormElements, Home, SettingAdd, SettingList, SignIn, SignUp, UserProfiles } from '../pages/wrapperPage';
import AdminWorkbench from '../pages/admin/AdminWorkbench';
import WhitelistTester from '../pages/tools/WhitelistTester';
import ProductsPage from '../pages/items/ProductsPage';
import OrdersListPage from '../pages/transactions/OrdersListPage';
import OrderDetailPage from '../pages/transactions/OrderDetailPage';
import InvoicesListPage from '../pages/transactions/InvoicesListPage';
import InvoiceDetailPage from '../pages/transactions/InvoiceDetailPage';
import PurchaseOrderDetailPage from '../pages/transactions/PurchaseOrderDetailPage';
import ProposalDetailPage from '../pages/transactions/ProposalDetailPage';
// Redux store is not used directly here; pages connect as needed.
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
              <Route path={PageRoutes.contactAdd + '/:id'} element={<ContactAdd />} />
              <Route path={PageRoutes.settingList} element={<SettingList />} /> 
              <Route path={PageRoutes.settingAdd} element={<SettingAdd />} />
              <Route path={PageRoutes.domainList} element={<DomainList />} /> 
              <Route path={PageRoutes.domainAdd} element={<DomainAdd />} />
    
              <Route path="/calendar" element={<Calendar />} />
              <Route path="/form-elements" element={<FormElements />} />
              <Route path="/basic-models" element={<BasicTables />} />   
              <Route path={PageRoutes.adminWorkbench} element={<AdminWorkbench />} />
              <Route path={PageRoutes.whitelist} element={<WhitelistTester />} />
              {/* Products */}
              <Route path={PageRoutes.products} element={<ProductsPage />} />
              {/* Transactions */}
              <Route path={PageRoutes.transactionsOrders} element={<OrdersListPage />} />
              <Route path={PageRoutes.transactionsOrderDetail} element={<OrderDetailPage />} />
              <Route path={PageRoutes.transactionsInvoices} element={<InvoicesListPage />} />
              <Route path={PageRoutes.transactionsInvoiceDetail} element={<InvoiceDetailPage />} />
              <Route path={PageRoutes.transactionsPurchaseOrderDetail} element={<PurchaseOrderDetailPage />} />
              <Route path={PageRoutes.transactionsProposalDetail} element={<ProposalDetailPage />} />
            </Route>
            
            {/* 404 page */}
            <Route path="*" element={<div>404 Not Found</div>} />
          </Routes>
        </BrowserRouter>
    // </Provider>    
  );
};

export default Router;