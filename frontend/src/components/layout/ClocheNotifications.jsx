import React, { useEffect, useId, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Bell, CheckCircle2, Info, Landmark, XCircle } from 'lucide-react';
import { useJournalMessages } from '../../context/ToastContext';

/* =========================================================================
   CLOCHE DE LA BARRE DU HAUT
   Badge = messages non lus de la session (chaque notification affichée l'incrémente, voir
   ToastContext) + chèques de l'échéancier à déposer pour les utilisateurs de la caisse.
   Le panneau liste les messages récents (les ouvrir les marque comme lus) et l'alerte des chèques.
   Animations (cloche qui s'agite à un nouveau message, badge, panneau) : index.css « CLOCHE ».
   ========================================================================= */

const ICONES = { success: CheckCircle2, error: XCircle, warning: AlertTriangle, info: Info };
const CLASSES = { success: 'succes', error: 'erreur', warning: 'attention', info: 'info' };

const depuis = (instant) => {
  const secondes = Math.round((Date.now() - instant) / 1000);
  if (secondes < 45) return "à l'instant";
  const minutes = Math.round(secondes / 60);
  if (minutes < 60) return `il y a ${minutes} min`;
  const heures = Math.round(minutes / 60);
  if (heures < 24) return `il y a ${heures} h`;
  return new Date(instant).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
};

export const ClocheNotifications = ({ alertesCheques = 0, voitCaisse = false }) => {
  const navigate = useNavigate();
  const { messages, nonLus, marquerLus, effacer } = useJournalMessages();
  const [ouvert, setOuvert] = useState(false);
  const idPanneau = useId();
  const zone = useRef(null);
  const total = nonLus + (voitCaisse ? alertesCheques : 0);

  // La cloche s'agite quand le nombre de messages non lus augmente
  const [agite, setAgite] = useState(false);
  const precedent = useRef(nonLus);
  useEffect(() => {
    if (nonLus > precedent.current) {
      setAgite(true);
      const minuterie = setTimeout(() => setAgite(false), 700);
      precedent.current = nonLus;
      return () => clearTimeout(minuterie);
    }
    precedent.current = nonLus;
    return undefined;
  }, [nonLus]);

  // Panneau ouvert : les messages non lus sont mis en évidence (nouveaux) puis marqués comme lus
  const [nouveaux, setNouveaux] = useState(() => new Set());
  useEffect(() => {
    if (!ouvert) {
      setNouveaux(new Set());
      return;
    }
    if (nonLus === 0) return;
    const ids = messages.filter((m) => !m.lu).map((m) => m.id);
    setNouveaux((avant) => new Set([...avant, ...ids]));
    marquerLus();
  }, [ouvert, nonLus]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fermeture au clic extérieur et avec Échap
  useEffect(() => {
    if (!ouvert) return undefined;
    const surClic = (e) => { if (zone.current && !zone.current.contains(e.target)) setOuvert(false); };
    const surTouche = (e) => { if (e.key === 'Escape') setOuvert(false); };
    document.addEventListener('mousedown', surClic);
    document.addEventListener('keydown', surTouche);
    return () => {
      document.removeEventListener('mousedown', surClic);
      document.removeEventListener('keydown', surTouche);
    };
  }, [ouvert]);

  const libelle = total > 0 ? `Notifications : ${total} non lue${total > 1 ? 's' : ''}` : 'Notifications';

  return (
    <div className="cloche" ref={zone}>
      <button
        type="button"
        className={`cloche-bouton${agite ? ' agite' : ''}`}
        onClick={() => setOuvert((o) => !o)}
        aria-label={libelle}
        aria-expanded={ouvert}
        aria-controls={idPanneau}
        title={libelle}
      >
        <Bell size={15} />
        {total > 0 && <span key={total} className="cloche-badge" aria-hidden="true">{total > 99 ? '99+' : total}</span>}
      </button>

      {ouvert && (
        <div id={idPanneau} className="cloche-panneau" role="dialog" aria-label="Notifications">
          <div className="cloche-entete">
            <strong>Notifications</strong>
            {messages.length > 0 && (
              <button type="button" className="cloche-lien" onClick={effacer}>Effacer</button>
            )}
          </div>

          {voitCaisse && alertesCheques > 0 && (
            <button type="button" className="cloche-element cloche-cheques" onClick={() => { setOuvert(false); navigate('/user/cheques'); }}>
              <span className="cloche-icone attention"><Landmark size={15} /></span>
              <span className="cloche-texte">
                <span className="cloche-titre">Échéancier des chèques</span>
                <span className="cloche-message">
                  {alertesCheques} chèque{alertesCheques > 1 ? 's' : ''} à déposer (un mois avant l'échéance ou échu).
                </span>
              </span>
            </button>
          )}

          {messages.length === 0 ? (
            <p className="cloche-vide">Aucun message pour le moment. Les confirmations, alertes et erreurs de vos opérations s'afficheront ici.</p>
          ) : (
            <ul className="cloche-liste">
              {messages.map((m) => {
                const Icone = ICONES[m.type] || Info;
                return (
                  <li key={m.id} className={`cloche-element${nouveaux.has(m.id) ? ' non-lu' : ''}`}>
                    <span className={`cloche-icone ${CLASSES[m.type] || 'info'}`} aria-hidden="true"><Icone size={15} /></span>
                    <span className="cloche-texte">
                      <span className="cloche-titre">
                        {m.titre}
                        {m.compte > 1 && <span className="cloche-compte">×{m.compte}</span>}
                      </span>
                      <span className="cloche-message">{m.texte}</span>
                      <span className="cloche-heure">{depuis(m.instant)}</span>
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};

export default ClocheNotifications;
