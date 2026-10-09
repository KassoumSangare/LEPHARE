import React from 'react';
import { Link } from 'react-router-dom';
import { Lock } from 'lucide-react';

// Écran affiché à la place d'une page dont l'utilisateur n'a pas le droit (le serveur refuserait
// de toute façon les appels correspondants)
export const AccesRefuse = ({ droit }) => (
  <div className="glass-panel" style={{ maxWidth: 560, margin: '3rem auto', padding: '2rem', textAlign: 'center', borderRadius: 14 }}>
    <Lock size={32} style={{ color: 'var(--accent-amber)' }} />
    <h1 style={{ fontSize: '1.15rem', fontWeight: 800, margin: '0.75rem 0 0.4rem' }}>Accès non autorisé</h1>
    <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', margin: 0 }}>
      Vos rôles ne donnent pas accès à cet écran
      {droit ? <> (droit requis : <code>{Array.isArray(droit) ? droit.join(' ou ') : droit}</code>)</> : null}.
      Adressez-vous à un administrateur si vous en avez besoin.
    </p>
    <Link to="/user/dashboard" className="btn btn-secondary" style={{ marginTop: '1.25rem', display: 'inline-flex' }}>Retour au tableau de bord</Link>
  </div>
);

export default AccesRefuse;
