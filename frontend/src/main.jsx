import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { chargerParametrage } from './utils/parametrage';
import './index.css';

// Paramétrage de l'admin lu avant le premier affichage (3 s au plus : au-delà, les valeurs
// d'origine s'appliquent et l'application démarre quand même)
Promise.race([chargerParametrage(), new Promise((resolve) => setTimeout(resolve, 3000))]).finally(() => {
  ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
});
