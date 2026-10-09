import axios from 'axios';
import { demanderMotif } from '../utils/motif';

// Client de l'API : jeton de la session ouverte par POST /api/users/login (aucun jeton par défaut :
// sans connexion, le serveur répond 401 et l'écran revient à la page de connexion).
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 45000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

export const CLE_JETON = 'uranus_auth_token';
export const CLE_SESSION = 'lephare_session';

// Émis quand le serveur refuse le jeton (session expirée, compte désactivé) : AuthContext ferme la session
export const EVENEMENT_SESSION_EXPIREE = 'lephare:session-expiree';
// Émis sur une requête sans réponse ou en erreur 5xx : le bandeau d'état du serveur vérifie alors
// si Django ou la base de données est indisponible.
export const EVENEMENT_ERREUR_API = 'lephare:erreur-api';
// Émis quand la garde du serveur refuse une opération d'écriture (droit manquant, séparation des
// tâches) : AppLayout affiche le motif du refus, même si l'écran n'affiche qu'un message générique.
export const EVENEMENT_ACCES_REFUSE = 'lephare:acces-refuse';

const lireJeton = () => {
  try {
    return localStorage.getItem(CLE_JETON);
  } catch {
    return null;
  }
};

apiClient.interceptors.request.use(
  (config) => {
    const jeton = lireJeton();
    if (jeton) config.headers.Authorization = `Token ${jeton}`;
    else delete config.headers.Authorization;
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const requete = error.config || {};
    const statut = error.response?.status;
    if (!requete.sansSignalement && !axios.isCancel(error) && (!error.response || statut >= 500)) {
      window.dispatchEvent(new Event(EVENEMENT_ERREUR_API));
    }
    // Session refusée par le serveur : retour à la connexion (sauf pendant la connexion elle-même)
    if (statut === 401 && !String(requete.url || '').includes('/users/login')) {
      window.dispatchEvent(new Event(EVENEMENT_SESSION_EXPIREE));
    }
    const methode = String(requete.method || 'get').toLowerCase();
    if (statut === 403 && !['get', 'head', 'options'].includes(methode)) {
      const detail = error.response?.data?.detail || error.response?.data?.error;
      if (typeof detail === 'string' && detail) {
        window.dispatchEvent(new CustomEvent(EVENEMENT_ACCES_REFUSE, { detail }));
      }
    }
    // Opération sensible : le serveur exige un motif (garde centrale) ; saisie puis nouvel envoi
    if (statut === 428 && error.response?.data?.code === 'motif_requis' && !requete.motifEnvoye) {
      const motif = await demanderMotif(error.response.data.libelle);
      if (motif) {
        requete.motifEnvoye = true;
        requete.headers = { ...(requete.headers || {}), 'X-Motif': encodeURIComponent(motif) };
        return apiClient(requete);
      }
      error.response.data = { ...error.response.data, error: 'Opération annulée : motif non saisi.' };
    }
    return Promise.reject(error);
  }
);

export default apiClient;
