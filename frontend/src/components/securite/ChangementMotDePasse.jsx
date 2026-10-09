import React, { useState } from 'react';
import { KeyRound, Loader2, ShieldAlert } from 'lucide-react';
import { securiteApi } from '../../api/endpoints';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';

// Changement de son propre mot de passe. « obligatoire » : après une réinitialisation par
// l'administrateur, la boîte ne se ferme qu'une fois le nouveau mot de passe enregistré.
export const ChangementMotDePasse = ({ obligatoire = false, onFermer }) => {
  const { rafraichirSession, logout } = useAuth();
  const { success } = useToast();
  const [ancien, setAncien] = useState('');
  const [nouveau, setNouveau] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [erreur, setErreur] = useState('');
  const [envoi, setEnvoi] = useState(false);

  const enregistrer = async (e) => {
    e.preventDefault();
    setErreur('');
    if (nouveau.length < 8) { setErreur('Le nouveau mot de passe doit contenir au moins 8 caractères.'); return; }
    if (nouveau !== confirmation) { setErreur('La confirmation ne correspond pas au nouveau mot de passe.'); return; }
    setEnvoi(true);
    try {
      await securiteApi.changerMonMotDePasse(ancien, nouveau);
      await rafraichirSession();
      success('Mot de passe modifié. Vos autres sessions ont été fermées.');
      if (onFermer) onFermer();
    } catch (err) {
      setErreur(err?.response?.data?.error || 'Le mot de passe n\'a pas pu être modifié.');
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, zIndex: 9000, background: 'rgba(15,23,42,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
      <form onSubmit={enregistrer} className="glass-panel" style={{ width: '100%', maxWidth: 430, padding: '1.4rem 1.5rem', borderRadius: 14, background: 'var(--bg-surface)' }}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: '0 0 0.4rem', fontSize: '1.05rem', fontWeight: 800 }}>
          <KeyRound size={18} style={{ color: 'var(--primary-500)' }} /> {obligatoire ? 'Choisissez votre mot de passe' : 'Changer mon mot de passe'}
        </h2>
        {obligatoire && (
          <p style={{ display: 'flex', gap: '0.45rem', fontSize: '0.82rem', color: 'var(--text-secondary)', margin: '0 0 0.9rem' }}>
            <ShieldAlert size={16} style={{ color: 'var(--accent-amber)', flexShrink: 0 }} />
            Votre mot de passe a été réinitialisé par un administrateur : remplacez-le par un mot de passe connu de vous seul.
          </p>
        )}
        {[
          ['Mot de passe actuel', ancien, setAncien, 'current-password'],
          ['Nouveau mot de passe', nouveau, setNouveau, 'new-password'],
          ['Confirmation', confirmation, setConfirmation, 'new-password'],
        ].map(([libelle, valeur, changer, auto]) => (
          <div className="form-group" key={libelle}>
            <label className="form-label">{libelle}</label>
            <input type="password" className="form-control" autoComplete={auto} value={valeur} onChange={(e) => changer(e.target.value)} required />
          </div>
        ))}
        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '0 0 0.5rem' }}>8 caractères au moins, ni trop courant ni uniquement des chiffres.</p>
        {erreur && <div role="alert" style={{ fontSize: '0.8rem', color: 'var(--accent-rose)', fontWeight: 600, marginBottom: '0.5rem' }}>{erreur}</div>}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.75rem' }}>
          {obligatoire
            ? <button type="button" className="btn btn-secondary" onClick={logout}>Se déconnecter</button>
            : <button type="button" className="btn btn-secondary" onClick={onFermer}>Annuler</button>}
          <button type="submit" className="btn btn-primary" disabled={envoi} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            {envoi && <Loader2 size={15} className="spin" />} Enregistrer
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChangementMotDePasse;
