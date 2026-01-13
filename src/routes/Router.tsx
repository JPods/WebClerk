import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import PrivateRoute from "./PrivateRoute";
import { PageRoutes } from "./Routes";
import { ScrollToTop, Toster } from "../components/wrapper";
import Test from "../pages/test/Test";
import { protectedRoutesConfig } from "./protectedRoutesConfig";
import NotFoundPage from "../pages/NotFoundPage";
import { SignIn, SignUp } from "../pages/wrapperPage";

const Router: React.FC = () => {
  return (
    // <Provider store={store}>
    <BrowserRouter>
      <ScrollToTop />
      <Toster />
      <Routes>
        {/* Public routes */}
        <Route path={PageRoutes.login} element={<SignIn />} />
        <Route path={PageRoutes.register} element={<SignUp />} />
        <Route path="/test" element={<Test />} />
        {/* Protected routes */}
        <Route element={<PrivateRoute />}>
          {protectedRoutesConfig.map((r) => (
            <Route key={r.path} path={r.path} element={r.element} />
          ))}
        </Route>

        {/* 404 page */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
    // </Provider>
  );
};

export default Router;
