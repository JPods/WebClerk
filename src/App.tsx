import React, { useEffect } from 'react';
import { Provider, useDispatch } from 'react-redux';
import { store } from './store';
import Router from './routes/Router';

const App: React.FC = () => {


  return (
    <Provider store={store}>
      <div className="min-h-screen bg-[#F5F5F5] dark:bg-gray-900">
        <Router />
      </div>
    </Provider>
  );
};

export default App;