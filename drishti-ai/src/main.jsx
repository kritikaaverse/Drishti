import React from 'react';import{createRoot}from'react-dom/client';import{BrowserRouter}from'react-router-dom';import{AppProvider}from'./context/AppContext';import App from './App';import './styles/index.css';
createRoot(document.getElementById('root')).render(<BrowserRouter><AppProvider><App/></AppProvider></BrowserRouter>);
import './styles/reference.css';
import './styles/landing.css';
