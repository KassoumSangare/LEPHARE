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
const dateFr = (valeur) => (valeur ? String(valeur).slice(0, 10).split('-').reverse().join('/') : '—');
const joursInclusifs = (debut, fin) => (
  debut && fin ? Math.max(0, Math.round((new Date(`${fin}T00:00:00`) - new Date(`${debut}T00:00:00`)) / 86400000) + 1) : 0
);

export const IncorporationFlottePage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();
  const [donnees, setDonnees] = useState(null);
  const [dateEffet, setDateEffet] = useState('');
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
  const total = joursInclusifs(contrat?.DateEffet, contrat?.DateExpiration);
  const enCours = donnees?.DevisEnCours?.[0];

  const creer = async () => {
    if (!dateEffet) {
      toastError("Choisissez la date à laquelle le véhicule doit être assuré.");
      return;
    }
    setEnvoi(true);
    try {
      const devis = await contractApi.creerIncorporation(id, { DateEffet: dateEffet });
      success(`Devis d'incorporation ${devis.NumeroDevis} créé. Ajoutez le véhicule puis enregistrez-le pour calculer la prime.`);
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
            La période du contrat principal ne sera pas modifiée. La prime sera calculée selon le tarif du véhicule et la durée restante.
          </p>

          {enCours ? (
            <div style={{ padding: '0.9rem', border: '1px solid rgba(245, 158, 11, 0.45)', borderRadius: 8, background: 'rgba(245, 158, 11, 0.08)' }}>
              Un devis d’incorporation est déjà en cours : <strong>{enCours.NumeroDevis}</strong>, du {dateFr(enCours.DateEffet)} au {dateFr(enCours.DateExpiration)}.
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
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                Durée couverte : {restant} jour{restant > 1 ? 's' : ''} sur {total} jours. Échéance maintenue au {dateFr(contrat.DateExpiration)}.
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
