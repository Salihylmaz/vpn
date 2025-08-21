import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navigation from './components/Navigation';
import Dashboard from './components/Dashboard';
import SystemMonitor from './components/SystemMonitor';
import QueryInterface from './components/QueryInterface';
import DataHistory from './components/DataHistory';
import './App.css';

const App = () => {
  return (
    <Router>
      <div className="app-container flex">
        <Navigation />
        <main className="content-wrapper flex-1 p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/system" element={<SystemMonitor />} />
            <Route path="/query" element={<QueryInterface />} />
            <Route path="/history" element={<DataHistory />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App;
