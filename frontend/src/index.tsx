import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

// Monta la aplicacion React en el contenedor del HTML.
const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
