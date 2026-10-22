import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { authApi, securiteApi } from '../api/endpoints';
import { CLE_JETON, CLE_SESSION, EVENEMENT_SESSION_EXPIREE } from '../api/apiClient';
import { definirDroits, aLeDroit } from '../utils/droits';
import { ADMIN_MENU } from '../components/layout/adminMenu';
import { chargerParametrage } from '../utils/parametrage';

// Session de l'utilisateur : jeton Knox (POST /api/users/login) et droits effectifs
// (GET /api/securite/moi/). Aucune session locale de secours : sans jeton accepté par le serveur,
// retour à la page de connexion.
const AuthContext = createContext(null);

const lireSession = () => {
  try {
    const jeton = localStorage.getItem(CLE_JETON);
    const session = JSON.parse(localStorage.getItem(CLE_SESSION) || 'null');
    return jeton && session?.user ? session : null;
  } catch {
    return null;
  }
};

// Utilisateur affiché à partir de GET /api/securite/moi/
const utilisateurDepuis = (moi) => {
  const nom = (moi.nom || moi.email || '').trim();
  const roles = moi.roles || [];
  return {
    id: moi.id,
    email: moi.email,
    username: moi.email,
    name: nom,
    first_name: nom,
    is_admin: Boolean(moi.administrateur),
    roles,
    role_label: moi.administrateur
      ? 'Administrateur'
      : (roles.filter((r) => r.actif).map((r) => r.libelle).join(', ') || 'Aucun rôle'),
    avatar: (nom || 'LP').split(/\s+/).map((m) => m[0]).join('').slice(0, 2).toUpperCase(),
  };
};

// Écrans de l'administration accessibles (hors guide) : l'espace Administration est proposé s'il y en a un
const ECRANS_ADMIN = ADMIN_MENU.flatMap((g) => g.items).filter((i) => i.to !== '/admin/guide');

export const AuthProvider = ({ children }) => {
  const [session, setSession] = useState(lireSession);
  const [verification, setVerification] = useState(Boolean(lireSession()));
  const [versionDroits, setVersionDroits] = useState(0);
  const [activeSpace, setActiveSpace] = useState(() => localStorage.getItem('uranus_active_space') || 'user');

  const enregistrer = useCallback((nouvelle) => {
    setSession(nouvelle);
    definirDroits(nouvelle?.droits || []);
    setVersionDroits((v) => v + 1);
    try {
      if (nouvelle) localStorage.setItem(CLE_SESSION, JSON.stringify(nouvelle));
      else localStorage.removeItem(CLE_SESSION);
    } catch {
      // stockage indisponible : la session reste en mémoire
    }
  }, []);

  const fermer = useCallback(() => {
    try {
      localStorage.removeItem(CLE_JETON);
      localStorage.removeItem(CLE_SESSION);
    } catch {
      // rien à faire
    }
    enregistrer(null);
  }, [enregistrer]);

  // Droits relus auprès du serveur (au démarrage, après un changement de rôles ou de mot de passe)
  const rafraichir = useCallback(async () => {
    const moi = await securiteApi.moi();
    const nouvelle = {
      user: utilisateurDepuis(moi),
      droits: moi.droits || [],
      doitChangerMotDePasse: Boolean(moi.doit_changer_mot_de_passe),
    };
    enregistrer(nouvelle);
    return nouvelle;
  }, [enregistrer]);

  useEffect(() => {
    definirDroits(session?.droits || []);
    if (!session) return;
    rafraichir().catch(() => {}).finally(() => setVerification(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Jeton refusé par le serveur (expiré, compte désactivé) : fin de session
  useEffect(() => {
    const surExpiration = () => {
      if (!localStorage.getItem(CLE_JETON)) return;
      fermer();
      if (!window.location.pathname.startsWith('/login')) window.location.assign('/login?session=expiree');
    };
    window.addEventListener(EVENEMENT_SESSION_EXPIREE, surExpiration);
    return () => window.removeEventListener(EVENEMENT_SESSION_EXPIREE, surExpiration);
  }, [fermer]);

  const peut = useCallback((exigence) => aLeDroit(exigence), [versionDroits]); // eslint-disable-line react-hooks/exhaustive-deps
  const accesAdministration = useMemo(
    () => Boolean(session) && ECRANS_ADMIN.some((i) => aLeDroit(i.droit)),
    [session, versionDroits], // eslint-disable-line react-hooks/exhaustive-deps
  );

  useEffect(() => {
    // Droits encore en cours de vérification (rechargement de la page) : l'espace choisi est gardé jusqu'à la réponse
    if (verification) return;
    const espace = accesAdministration ? activeSpace : 'user';
    if (espace !== activeSpace) setActiveSpace(espace);
    localStorage.setItem('uranus_active_space', espace);
  }, [accesAdministration, activeSpace, verification]);

  /** Connexion : erreurs du serveur remontées telles quelles (mot de passe, compte verrouillé ou expiré). */
  const login = async (email, password) => {
    try {
      localStorage.removeItem(CLE_JETON);
    } catch {
      // rien
    }
    const res = await authApi.login({ email: (email || '').trim().toLowerCase(), password });
    const jeton = res?.data?.token;
    if (!jeton) throw new Error('Réponse du serveur sans jeton de session.');
    localStorage.setItem(CLE_JETON, jeton);
    const nouvelle = await rafraichir();
    chargerParametrage(true);
    setActiveSpace('user');
    return nouvelle.user;
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch {
      // session déjà fermée côté serveur
    }
    fermer();
  };

  const switchSpace = (space) => {
    if (space === 'admin' && !accesAdministration) return;
    setActiveSpace(space);
  };

  return (
    <AuthContext.Provider
      value={{
        user: session?.user || null,
        token: session ? localStorage.getItem(CLE_JETON) : null,
        droits: session?.droits || [],
        doitChangerMotDePasse: Boolean(session?.doitChangerMotDePasse),
        verificationSession: verification,
        activeSpace,
        isAuthenticated: Boolean(session),
        // Noms gardés pour les écrans existants : « accès à l'espace Administration »
        isAdmin: accesAdministration,
        isDirectorOrAdmin: accesAdministration,
        canSwitchSpace: accesAdministration,
        accesAdministration,
        peut,
        login,
        logout,
        switchSpace,
        rafraichirSession: rafraichir,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    return {
      user: null,
      token: null,
      droits: [],
      activeSpace: 'user',
      isAuthenticated: false,
      isAdmin: false,
      isDirectorOrAdmin: false,
      canSwitchSpace: false,
      accesAdministration: false,
      peut: () => false,
      login: async () => null,
      logout: () => {},
      switchSpace: () => {},
      rafraichirSession: async () => null,
    };
  }
  return context;
};
