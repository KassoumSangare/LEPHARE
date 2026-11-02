import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Car, CalendarRange, Loader2, AlertTriangle } from 'lucide-react';
import { contractApi } from '../../../api/endpoints';
import { messageErreurApi } from '../../../utils/financeUtils';
import { useToast } from '../../../context/ToastContext';

const aujourdhui = () => {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
};
const dateFr = (valeur) => (valeur ? String(valeur).slice(0, 10).split('-').reverse().join('/') : '-');
const joursInclusifs = (debut, fin) => (
  debut && fin ? Math.max(0, Math.round((new Date(`${fin}T00:00:00`) - new Date(`${debut}T00:00:00`)) / 86400000) + 1) : 0
);
// Jours de l'année qui commence à la date d'incorporation (365 ou 366), base du prorata (fn_get_duree_annuelle_contrat)
const joursAnnee = (debut) => {
  if (!debut) return 365;
  const depart = new Date(`${debut}T00:00:00`);
  const fin = new Date(depart);
  fin.setFullYear(depart.getFullYear() + 1);
  return Math.round((fin - depart) / 86400000);
};
const pourcentage = (valeur) => (valeur * 100).toLocaleString('fr-FR', { maximumFractionDigits: 2 });

export const IncorporationFlottePage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();
  const [donnees, setDonnees] = useState(null);
  const [dateEffet, setDateEffet] = useState('');
  // Affaire à tarif forfaitaire : primes du fichier Excel reprises telles quelles, aucun prorata
  const [forfaitaire, setForfaitaire] = useState(false);
  const [erreur, setErreur] = useState('');
  const [chargement, setChargement] = useState(true);
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    let actif = true;
    contractApi.preparerIncorporation(id)
      .then((reponse) => {
        if (!actif) return;
        setDonnees(reponse);
        const minimum = aujourdhui() > reponse.Contrat.DateEffet ? aujourdhui() : reponse.Contrat.DateEffet;
        setDateEffet(minimum);
      })
      .catch((err) => { if (actif) setErreur(messageErreurApi(err)); })
      .finally(() => { if (actif) setChargement(false); });
    return () => { actif = false; };
  }, [id]);

  const contrat = donnees?.Contrat;
  const restant = joursInclusifs(dateEffet, contrat?.DateExpiration);
  const annee = joursAnnee(dateEffet);
  const prorata = Math.min(1, restant / annee);
  const enCours = donnees?.DevisEnCours?.[0];

  const creer = async () => {
    if (!dateEffet) {
      toastError("Choisissez la date à laquelle le véhicule doit être assuré.");
      return;
    }
    setEnvoi(true);
    try {
      const devis = await contractApi.creerIncorporation(id, { DateEffet: dateEffet, Forfaitaire: forfaitaire });
      success(forfaitaire
        ? `Devis d'incorporation ${devis.NumeroDevis} créé (affaire forfaitaire). Importez le fichier Excel ou ajoutez le véhicule, puis enregistrez.`
        : `Devis d'incorporation ${devis.NumeroDevis} créé. Ajoutez le véhicule puis enregistrez-le pour calculer la prime.`);
      navigate(`/user/quotes/auto?edit=${devis.IdDevis}&incorporation=1`);
    } catch (err) {
      toastError(messageErreurApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <main className="page-container" style={{ maxWidth: 1000, margin: '0 auto' }}>
      <button type="button" className="btn btn-secondary" onClick={() => navigate(`/user/contracts/${id}`)}
        style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', marginBottom: '1rem' }}>
        <ArrowLeft size={15} /> Retour au contrat
      </button>
      <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
        <Car size={22} /> Incorporer un véhicule à la flotte
      </h1>
      {chargement && <p role="status"><Loader2 size={15} className="spin" /> Lecture du contrat…</p>}
      {erreur && <div role="alert" style={{ color: 'var(--accent-rose)', display: 'flex', gap: '0.5rem' }}><AlertTriangle size={18} />{erreur}</div>}
      {contrat && (
        <section className="glass-panel" style={{ padding: '1.25rem', marginTop: '1rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '0.8rem', marginBottom: '1rem' }}>
            <div><span className="text-muted">Police</span><strong style={{ display: 'block' }}>{contrat.NumeroPolice}</strong></div>
            <div><span className="text-muted">Client</span><strong style={{ display: 'block' }}>{contrat.Client}</strong></div>
            <div><span className="text-muted">Échéance du contrat principal</span><strong style={{ display: 'block' }}>{dateFr(contrat.DateExpiration)}</strong></div>
          </div>

          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            Le véhicule sera assuré à partir de la date d’incorporation choisie et jusqu’à l’échéance initiale de la police.
            La période du contrat principal ne sera pas modifiée.
          </p>

          {enCours ? (
            <div style={{ padding: '0.9rem', border: '1px solid rgba(245, 158, 11, 0.45)', borderRadius: 8, background: 'rgba(245, 158, 11, 0.08)' }}>
              Un devis d’incorporation est déjà en cours : <strong>{enCours.NumeroDevis}</strong>, du {dateFr(enCours.DateEffet)} au {dateFr(enCours.DateExpiration)}
              {enCours.Forfaitaire ? ' (affaire forfaitaire, sans prorata).' : ' (prime au prorata de la durée restante).'}
              <div style={{ marginTop: '0.65rem' }}>
                <Link className="btn btn-primary" to={`/user/quotes/auto?edit=${enCours.IdDevis}&incorporation=1`}>Ouvrir le devis</Link>
              </div>
            </div>
          ) : (
            <>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxWidth: 340, margin: '1rem 0' }}>
                <span style={{ fontWeight: 700 }}><CalendarRange size={15} style={{ verticalAlign: 'text-bottom' }} /> Date d’incorporation</span>
                <input type="date" className="form-control" value={dateEffet}
                  min={aujourdhui() > contrat.DateEffet ? aujourdhui() : contrat.DateEffet}
                  max={contrat.DateExpiration} onChange={(event) => setDateEffet(event.target.value)} />
              </label>
              <fieldset style={{ border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '0.75rem 1rem', margin: '0 0 1rem' }}>
                <legend style={{ fontWeight: 700, padding: '0 0.35rem' }}>Tarification de l’affaire</legend>
                <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', marginBottom: '0.55rem', cursor: 'pointer' }}>
                  <input type="radio" name="tarification" checked={!forfaitaire} onChange={() => setForfaitaire(false)} style={{ marginTop: '0.25rem' }} />
                  <span>
                    <strong>Au prorata de la durée restante</strong>
                    <span style={{ display: 'block', fontSize: '0.83rem', color: 'var(--text-muted)' }}>
                      Prime annuelle du tarif × {restant}/{annee} jours ({pourcentage(prorata)} %), du {dateFr(dateEffet)} au {dateFr(contrat.DateExpiration)}.
                    </span>
                  </span>
                </label>
                <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', cursor: 'pointer' }}>
                  <input type="radio" name="tarification" checked={forfaitaire} onChange={() => setForfaitaire(true)} style={{ marginTop: '0.25rem' }} />
                  <span>
                    <strong>Affaire à tarif forfaitaire</strong>
                    <span style={{ display: 'block', fontSize: '0.83rem', color: 'var(--text-muted)' }}>
                      Aucun prorata : la prime nette indiquée dans le fichier Excel importé est reprise telle quelle
                      (sans fichier, prime annuelle du barème).
                    </span>
                  </span>
                </label>
              </fieldset>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                Durée couverte : {restant} jour{restant > 1 ? 's' : ''}. Échéance maintenue au {dateFr(contrat.DateExpiration)}.
              </div>
              <button type="button" className="btn btn-primary" disabled={envoi || !dateEffet || dateEffet > contrat.DateExpiration}
                onClick={creer} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
                {envoi ? <Loader2 size={15} className="spin" /> : <Car size={15} />}
                {envoi ? 'Création du devis…' : 'Continuer et ajouter le véhicule'}
              </button>
            </>
          )}
        </section>
      )}
    </main>
  );
};

export default IncorporationFlottePage;
