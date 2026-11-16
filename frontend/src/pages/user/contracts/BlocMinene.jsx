import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { HeartPulse, Link2, Loader2, Plus, ShieldCheck, Umbrella, Wallet } from 'lucide-react';
import { mineneApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { aLeDroit } from '../../../utils/droits';
import { messageErreurApi } from '../../../utils/financeUtils';

/* =========================================================================
   Fiche contrat : package MINENE (production/minene_package.py), comme le bloc Oreole Santé. Les trois polices liées
   (Santé, Individuelle Accidents, RC chef de famille), ce qui reste à émettre (sans ressaisie, depuis les adhérents de
   la police Santé) et l'encaissement en un seul règlement. Affiché sur un contrat Santé, IA ou RC MINENE.
   ========================================================================= */
const PRODUITS = {
  Sante: { libelle: 'Santé MINENE', icone: HeartPulse, couleur: 'var(--accent-emerald, #10b981)' },
  IA: { libelle: 'Individuelle Accidents', icone: ShieldCheck, couleur: 'var(--primary-500, #3b82f6)' },
  RC: { libelle: 'RC chef de famille', icone: Umbrella, couleur: 'var(--accent-amber, #f59e0b)' },
};
const ETATS = {
  Emise: ['Émise', 'var(--accent-emerald, #10b981)'], Devis: ['En devis', 'var(--accent-amber, #f59e0b)'], 'A emettre': ['À émettre', 'var(--text-muted)'],
  'Non souscrite': ['Non souscrite', 'var(--text-muted)'],
};
const fcfa = (v) => Math.round(Number(v) || 0).toLocaleString('fr-FR');
const dateFr = (iso) => (iso ? String(iso).slice(0, 10).split('-').reverse().join('/') : '-');
const ligne = { display: 'flex', justifyContent: 'space-between', gap: '0.75rem', fontSize: '0.82rem', padding: '0.18rem 0' };

export default function BlocMinene({ idContrat }) {
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();
  const [donnees, setDonnees] = useState(null);
  const [emission, setEmission] = useState(false);

  useEffect(() => {
    let actif = true;
    mineneApi.contrat(idContrat)
      .then((d) => { if (actif) setDonnees(d?.Minene ? d : null); })
      .catch(() => { if (actif) setDonnees(null); });
    return () => { actif = false; };
  }, [idContrat]);

  if (!donnees) return null;

  const produits = donnees.Produits;
  // Assurances à émettre : celles du package qui n'ont pas encore de police (une case décochée à l'écran Santé n'en fait pas partie)
  const manquants = ['IA', 'RC'].filter((cle) => !produits[cle]?.IdContrat && produits[cle]?.Inclus !== false);
  const santeEmise = Boolean(produits.Sante?.IdContrat);
  const emisLies = ['IA', 'RC'].some((cle) => produits[cle]?.IdContrat);
  const totaux = donnees.Totaux;

  const emettre = async () => {
    setEmission(true);
    try {
      const r = await mineneApi.emettreContrat(idContrat);
      setDonnees(r);
      const libelles = (r.Emis || []).map((cle) => PRODUITS[cle]?.libelle || cle);
      success(libelles.length ? `${libelles.join(' et ')} émise${libelles.length > 1 ? 's' : ''} sur la police Santé, sans ressaisie.` : 'Le package MINENE est déjà complet.');
    } catch (err) {
      toastError(`Émission MINENE impossible : ${messageErreurApi(err)}`);
    } finally {
      setEmission(false);
    }
  };

  const carte = (cle) => {
    const p = PRODUITS[cle];
    const Icone = p.icone;
    const etat = produits[cle] || {};
    const [libelleEtat, couleurEtat] = ETATS[etat.Etat] || ETATS['A emettre'];
    return (
      <div key={cle} style={{ padding: '0.8rem 0.9rem', borderRadius: 12, border: '1px solid var(--border-medium)', borderTop: `3px solid ${p.couleur}`, display: 'flex', flexDirection: 'column', gap: '0.22rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', alignItems: 'center' }}>
          <b style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.88rem' }}><Icone size={15} color={p.couleur} /> {p.libelle}</b>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: couleurEtat }}>{libelleEtat}</span>
        </div>
        <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>{etat.Compagnie || 'NSIA ASSURANCES'}</span>
        <span style={{ fontSize: '1.05rem', fontWeight: 800 }}>{fcfa(etat.PrimeTtc)} F</span>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{etat.Etat === 'Non souscrite' ? 'Case décochée sur le devis Santé' : (etat.NumeroPolice || etat.NumeroDevis || (etat.Unitaire ? `${fcfa(etat.Unitaire)} F par adhérent` : '-'))}</span>
        {etat.IdContrat && String(etat.IdContrat) !== String(idContrat) && (
          <div style={{ marginTop: '0.3rem' }}>
            <button type="button" className="btn btn-secondary" style={{ fontSize: '0.76rem', padding: '0.25rem 0.6rem' }} onClick={() => navigate(`/user/contracts/${etat.IdContrat}`)}>Ouvrir le contrat</button>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="glass-panel" style={{ padding: '1.15rem 1.25rem', marginBottom: '1.5rem', border: '1px solid color-mix(in srgb, var(--accent-emerald, #10b981) 35%, transparent)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-start', marginBottom: '0.8rem' }}>
        <div>
          <div style={{ fontWeight: 800, color: 'var(--accent-emerald, #10b981)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}><Link2 size={16} /> MINENE : le package, police par police</div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Assurances du package, émises et réglées ensemble : {donnees.Adherents} adhérent{donnees.Adherents > 1 ? 's' : ''}, du {dateFr(donnees.DateEffet)} au {dateFr(donnees.DateExpiration)}.
            {' '}L&apos;IA et la RC reprennent le client, la période et les adhérents de la police Santé.
          </div>
        </div>
        {santeEmise && manquants.length > 0 && aLeDroit('devis.validate') && (
          <button type="button" className="btn btn-primary" disabled={emission} onClick={emettre} style={{ fontSize: '0.8rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
            {emission ? <Loader2 size={14} className="spin" /> : <Plus size={14} />}
            {`Émettre ${manquants.map((cle) => (cle === 'IA' ? "l'IA" : 'la RC')).join(' et ')} sans ressaisie`}
          </button>
        )}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: '0.7rem' }}>{['Sante', 'IA', 'RC'].map(carte)}</div>
      <div style={{ marginTop: '0.9rem', maxWidth: 460 }}>
        <b style={{ fontSize: '0.86rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}><Wallet size={15} /> Encaissement</b>
        <div style={ligne}><span style={{ color: 'var(--text-muted)' }}>Prime MINENE (trois polices)</span><b>{fcfa(totaux.PrimeTtc)} F</b></div>
        <div style={ligne}><span style={{ color: 'var(--text-muted)' }}>Déjà encaissé</span><b>{fcfa(totaux.Encaisse)} F</b></div>
        <div style={ligne}><span style={{ color: 'var(--text-muted)' }}>Reste à encaisser sur les polices émises</span><b style={{ color: totaux.ResteAEncaisser > 0 ? 'var(--accent-amber)' : 'var(--accent-emerald)' }}>{fcfa(totaux.ResteAEncaisser)} F</b></div>
        {santeEmise && emisLies && totaux.ResteAEncaisser > 0 && aLeDroit('encaissements.create') && (
          <button type="button" className="btn btn-primary" style={{ marginTop: '0.6rem', fontSize: '0.8rem' }} onClick={() => navigate(`/user/cash?minene=${donnees.IdDevis}`)}>Encaisser le package</button>
        )}
      </div>
    </div>
  );
}
