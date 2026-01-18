import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import ErrorBoundary from './components/ErrorBoundary/ErrorBoundary';
import HomePage from './pages/HomePage';

function App() {
  return (
    <ErrorBoundary>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            {/* Future routes can be added here */}
          </Routes>
        </Layout>
      </Router>
    </ErrorBoundary>
  );
}

export default App;