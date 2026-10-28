import React, { useEffect, useState } from 'react';
import { AlertTriangle, Download, Eye, FileText, Image as IconeImage, Loader2, Paperclip } from 'lucide-react';

import { piecesJointesApi } from '../../api/endpoints';
import { useToast } from '../../context/ToastContext';
import { formatDate } from '../../utils/dateUtils';
import { Modal } from './Modal';

// Pièce jointe d'un devis ou d'un contrat (type 'devis' ou 'contrat') : nom, taille, date, consultation dans
// l'application (PDF ou image) et téléchargement. `version` relance la lecture après un nouvel envoi.
const taille = (octets) => {
  const n = Number(octets) || 0;
  if (n >= 1024 * 1024) return `${(n / (1024 * 1024)).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} Mo`;
  return `${Math.max(1, Math.round(n / 1024)).toLocaleString('fr-FR')} Ko`;
};
const estImage = (type) => /^image\//.test(type || '');
// Formats affichés dans l'application ; le type du fichier en mémoire est imposé depuis cette liste, pour qu'un
// contenu d'un autre format (page HTML, SVG) ne soit jamais interprété : il est seulement proposé au téléchargement
const TYPES_AFFICHABLES = ['application/pdf', 'image/png', 'image/jpeg'];

export const PieceJointe = ({ type, id, version = 0, masquerSiAbsente = false, titre = 'Pièce jointe', className = '' }) => {
  const { error: toastError } = useToast();
  const [fiche, setFiche] = useState(null);
  const [apercu, setApercu] = useState(null); // { url, type, nom }
  const [ouverture, setOuverture] = useState(false);

  useEffect(() => {
    let actif = true;
    setFiche(null);
    if (!id) return undefined;
    piecesJointesApi.fiche(type, id)
      .then((f) => { if (actif) setFiche(f); })
      .catch(() => { if (actif) setFiche({ Presente: false, Erreur: true }); });
    return () => { actif = false; };
  }, [type, id, version]);

  // L'adresse du fichier en mémoire est libérée à la fermeture
  useEffect(() => () => { if (apercu?.url) URL.revokeObjectURL(apercu.url); }, [apercu]);

  if (!id || !fiche) return null;
  if (!fiche.Presente && masquerSiAbsente) return null;

  const consulter = async () => {
    setOuverture(true);
    try {
      const blob = await piecesJointesApi.fichier(type, id);
      const typeFichier = TYPES_AFFICHABLES.find((t) => t === blob.type);
      if (!typeFichier) {
        await telecharger();
        return;
      }
      setApercu({ url: URL.createObjectURL(new Blob([blob], { type: typeFichier })), type: typeFichier, nom: fiche.Nom });
    } catch {
      toastError(`La pièce jointe « ${fiche.Nom} » n'a pas pu être ouverte.`);
    } finally {
      setOuverture(false);
    }
  };
  const telecharger = () => piecesJointesApi.telecharger(type, id, fiche.Nom)
    .catch(() => toastError(`La pièce jointe « ${fiche.Nom} » n'a pas pu être téléchargée.`));

  const Icone = estImage(fiche.Type) ? IconeImage : FileText;
  return (
    <div className={`piece-jointe ${className}`.trim()}>
      <div className="piece-jointe-titre"><Paperclip size={14} aria-hidden="true" /> {titre}</div>
      {!fiche.Presente ? (
        <div className="piece-jointe-vide">{fiche.Erreur ? 'Pièce jointe indisponible pour le moment.' : 'Aucune pièce jointe.'}</div>
      ) : (
        <div className="piece-jointe-ligne">
          <Icone size={22} aria-hidden="true" className="piece-jointe-icone" />
          <div className="piece-jointe-infos">
            <strong title={fiche.Nom}>{fiche.Nom}</strong>
            <span>
              {[taille(fiche.Taille), fiche.Date && `déposée le ${formatDate(fiche.Date)}`, fiche.Origine === 'devis' && type === 'contrat' && 'jointe au devis']
                .filter(Boolean).join(' · ')}
            </span>
            {!fiche.Disponible && (
              <span className="piece-jointe-absente"><AlertTriangle size={13} aria-hidden="true" /> {fiche.Message}</span>
            )}
          </div>
          {fiche.Disponible && (
            <div className="piece-jointe-actions">
              {fiche.Affichable && (
                <button type="button" className="btn btn-secondary" onClick={consulter} disabled={ouverture} aria-busy={ouverture}>
                  {ouverture ? <Loader2 size={14} className="spin" /> : <Eye size={14} />} Consulter
                </button>
              )}
              <button type="button" className="btn btn-secondary" onClick={telecharger} title="Enregistrer le fichier sur le poste">
                <Download size={14} /> Télécharger
              </button>
            </div>
          )}
        </div>
      )}

      <Modal isOpen={Boolean(apercu)} onClose={() => setApercu(null)} title={apercu?.nom || fiche.Nom} maxWidth="min(1100px, 96vw)">
        {apercu && (estImage(apercu.type)
          ? <img src={apercu.url} alt={apercu.nom} className="piece-jointe-image" />
          : <iframe src={apercu.url} title={apercu.nom} className="piece-jointe-cadre" />)}
      </Modal>
    </div>
  );
};

export default PieceJointe;
