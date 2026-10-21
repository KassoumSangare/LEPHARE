import React from 'react';
import { FileImage, FileSpreadsheet, FileText } from 'lucide-react';
import { normaliserTexte } from '../../../utils/financeUtils';

// Étapes d'un questionnaire déposé (institutionnel/questionnaires.py)
export const ETAPES_QUESTIONNAIRE = [
  { id: 'Reçu', couleur: 'blue', aide: 'Déposé, à étudier' },
  { id: 'En étude', couleur: 'amber', aide: "En cours d'analyse pour le devis" },
  { id: 'À compléter', couleur: 'rose', aide: 'Renvoyé au client : informations manquantes' },
  { id: 'Devis établi', couleur: 'emerald', aide: 'Devis fait : le prospect passe à « Proposition »' },
];
export const etapeQuestionnaire = (statut) => ETAPES_QUESTIONNAIRE.find((e) => e.id === statut) || ETAPES_QUESTIONNAIRE[0];
export const A_TRAITER = ['Reçu', 'En étude'];

export const extensionDe = (nom) => (String(nom || '').includes('.') ? String(nom).split('.').pop().toLowerCase() : '');

export const tailleLisible = (octets) => {
  if (!octets && octets !== 0) return '';
  if (octets < 1024) return `${octets} o`;
  if (octets < 1024 * 1024) return `${Math.round(octets / 1024)} Ko`;
  return `${(octets / (1024 * 1024)).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} Mo`;
};

export const dateHeure = (iso) => (iso
  ? new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  : '');

// Message lisible d'une erreur de l'API (les noms de champs ne sont pas repris : les messages se suffisent)
export const messageErreur = (err) => {
  const donnees = err?.response?.data;
  if (donnees && typeof donnees === 'object' && !(donnees instanceof Blob)) {
    const messages = Object.values(donnees).flatMap((v) => [].concat(v)).filter((m) => typeof m === 'string');
    if (messages.length) return messages.join(' ');
  }
  if (err?.response?.status === 403) return "droit insuffisant (Administration > Rôles et droits).";
  if (err?.response?.status === 404) return 'fichier introuvable.';
  return err?.message || 'erreur du serveur';
};

// Pastille du format : Word en bleu, Excel en vert, PDF et photos en rouge
const FORMATS = {
  docx: { classe: 'word', icone: FileText, libelle: 'Word' },
  doc: { classe: 'word', icone: FileText, libelle: 'Word' },
  xlsx: { classe: 'excel', icone: FileSpreadsheet, libelle: 'Excel' },
  xls: { classe: 'excel', icone: FileSpreadsheet, libelle: 'Excel' },
  pdf: { classe: 'pdf', icone: FileText, libelle: 'PDF' },
  jpg: { classe: 'pdf', icone: FileImage, libelle: 'Photo' },
  jpeg: { classe: 'pdf', icone: FileImage, libelle: 'Photo' },
  png: { classe: 'pdf', icone: FileImage, libelle: 'Photo' },
};
export const formatDe = (extension) => FORMATS[extension] || FORMATS.pdf;

export const IconeFormat = ({ extension, taille = 42 }) => {
  const format = formatDe(extension);
  const Icone = format.icone;
  return (
    <span className={`qp-format ${format.classe}`} style={{ width: taille, height: taille }} aria-hidden="true">
      <Icone size={Math.round(taille * 0.45)} />
      <small>{(extension || '').toUpperCase()}</small>
    </span>
  );
};

// Questionnaire reconnu d'après le nom du fichier renvoyé par le client : le modèle est téléchargé sous son titre,
// le client garde en général ce nom (parfois suivi de « (1) » ou de son nom). Le titre le plus précis l'emporte.
const MOTS_VIDES = new Set(['de', 'des', 'du', 'la', 'le', 'les', 'par', 'pour', 'et', 'ou', 'en', 'a', 'l', 'd']);
const mots = (texte) => normaliserTexte(texte).replace(/\.[a-z0-9]{2,4}$/, '').split(/[^a-z0-9]+/).filter((m) => m.length > 1 && !MOTS_VIDES.has(m));

export const devinerModele = (nomFichier, modeles = []) => {
  const motsFichier = new Set(mots(nomFichier));
  const extension = extensionDe(nomFichier);
  let meilleur = null;
  modeles.forEach((m) => {
    const motsTitre = mots(m.titre);
    if (!motsTitre.length) return;
    const score = motsTitre.filter((w) => motsFichier.has(w)).length / motsTitre.length;
    const memeFamille = formatDe(extension).classe === formatDe(m.extension).classe ? 0.01 : 0;
    const cle = score + memeFamille + motsTitre.length / 1000;
    if (score >= 0.75 && (!meilleur || cle > meilleur.cle)) meilleur = { modele: m, cle };
  });
  return meilleur?.modele || null;
};
