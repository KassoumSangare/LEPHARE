import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../api/endpoints';

const AuthContext = createContext(null);

const DEFAULT_DJANGO_USER = {
  id: 1,
  email: 'franckdelord@hotmail.com',
  username: 'franckdelord@hotmail.com',
  name: 'Franck Delord',
  is_admin: true,
  role: 'ADMIN',
  role_label: 'Directeur Général & Administrateur',
  avatar: 'FD',
};

const DEFAULT_DJANGO_TOKEN = '7adb48b906a8d68c79d22dfa120c72119ca6da9ca7ce6b5b53ff4a8d2e10e988';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('uranus_user');
    return saved ? JSON.parse(saved) : DEFAULT_DJANGO_USER;
  });

  // Helper to determine if a user has Director or Administrator privileges
  const checkIsDirectorOrAdmin = (u) => {
    if (!u) return false;
    if (u.is_admin === true || u.is_superuser === true || u.is_staff === true) return true;
    const roleStr = (u.role || '').toUpperCase();
    if (roleStr === 'ADMIN' || roleStr === 'DIRECTEUR' || roleStr === 'DIR_GEN') return true;
    const labelStr = (u.role_label || '').toLowerCase();
    if (labelStr.includes('directeur') || labelStr.includes('administrateur') || labelStr.includes('admin')) return true;
    const usernameStr = (u.username || u.email || '').toLowerCase();
    if (usernameStr.includes('admin') || usernameStr.includes('directeur') || usernameStr.includes('franckdelord')) return true;
    return false;
  };

  const isDirectorOrAdmin = checkIsDirectorOrAdmin(user);

  // Current active workspace: 'user' (Opérateur) or 'admin' (Direction & Paramétrage)
  const [activeSpace, setActiveSpace] = useState(() => {
    const saved = localStorage.getItem('uranus_active_space');
    if (!checkIsDirectorOrAdmin(user ? user : DEFAULT_DJANGO_USER)) {
      return 'user';
    }
    return saved || 'user';
  });

  const [token, setToken] = useState(() => {
    const saved = localStorage.getItem('uranus_auth_token');
    if (!saved) {
      localStorage.setItem('uranus_auth_token', DEFAULT_DJANGO_TOKEN);
      return DEFAULT_DJANGO_TOKEN;
    }
    return saved;
  });

  useEffect(() => {
    if (token) {
      localStorage.setItem('uranus_auth_token', token);
    } else {
      localStorage.removeItem('uranus_auth_token');
    }
  }, [token]);

  useEffect(() => {
    if (user) {
      localStorage.setItem('uranus_user', JSON.stringify(user));
      if (!isDirectorOrAdmin && activeSpace !== 'user') {
        setActiveSpace('user');
      }
    } else {
      localStorage.removeItem('uranus_user');
    }
  }, [user, isDirectorOrAdmin, activeSpace]);

  useEffect(() => {
    localStorage.setItem('uranus_active_space', activeSpace);
  }, [activeSpace]);

  const login = async (username, password) => {
    try {
      const res = await authApi.login({ email: username, password });
      if (res && res.data && res.data.token) {
        const u = res.data.user || {};
        const mappedUser = {
          id: u.id || 1,
          email: u.email || username,
          username: u.email || username,
          name: u.name || (u.email ? u.email.split('@')[0] : username),
          is_admin: Boolean(u.is_admin),
          role: u.is_admin ? 'ADMIN' : 'USER',
          role_label: u.is_admin ? 'Directeur Général & Administrateur' : 'Opérateur Guichet',
          avatar: (u.name || u.email || username).substring(0, 2).toUpperCase(),
        };
        setUser(mappedUser);
        setToken(res.data.token);
        localStorage.setItem('uranus_auth_token', res.data.token);
        localStorage.setItem('uranus_user', JSON.stringify(mappedUser));
        if (mappedUser.is_admin) {
          setActiveSpace('admin');
        } else {
          setActiveSpace('user');
        }
        return mappedUser;
      }
    } catch (err) {
      console.warn('Échec de connexion API Django:', err.response?.data || err.message);
      throw err;
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('uranus_auth_token');
    localStorage.removeItem('uranus_user');
  };

  const switchSpace = (space) => {
    // Seul le directeur ou administrateur a le droit de basculer vers l'espace admin
    if (space === 'admin' && !isDirectorOrAdmin) {
      return;
    }
    setActiveSpace(space);
  };

  const switchUser = (newUser) => {
    if (!newUser) return;
    const isAdmin = Boolean(
      newUser.is_admin ||
      newUser.role === 'ADMIN' ||
      newUser.role_code === 'ADMIN' ||
      (newUser.username || '').toLowerCase().includes('admin') ||
      (newUser.username || '').toLowerCase().includes('franckdelord') ||
      (newUser.role_label || '').toLowerCase().includes('directeur') ||
      (newUser.role_label || '').toLowerCase().includes('admin')
    );
    const mapped = {
      id: newUser.id || 1,
      email: newUser.email || `${newUser.username || 'user'}@uranus.ci`,
      username: newUser.username || newUser.email,
      name: newUser.name || newUser.first_name || (newUser.email ? newUser.email.split('@')[0] : 'Utilisateur'),
      is_admin: isAdmin,
      role: isAdmin ? 'ADMIN' : 'USER',
      role_label: newUser.role_label || (isAdmin ? 'Directeur Général & Administrateur' : 'Opérateur Guichet'),
      avatar: (newUser.first_name || newUser.name || newUser.username || 'U').substring(0, 2).toUpperCase(),
    };
    setUser(mapped);
    localStorage.setItem('uranus_user', JSON.stringify(mapped));
    if (isAdmin) {
      setActiveSpace('admin');
    } else {
      setActiveSpace('user');
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        activeSpace,
        isAuthenticated: !!user,
        isAdmin: isDirectorOrAdmin,
        isDirectorOrAdmin,
        canSwitchSpace: isDirectorOrAdmin,
        login,
        logout,
        switchSpace,
        switchUser,
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
      activeSpace: 'user',
      isAuthenticated: false,
      isAdmin: false,
      isDirectorOrAdmin: false,
      canSwitchSpace: false,
      login: () => {},
      logout: () => {},
      switchSpace: () => {},
    };
  }
  return context;
};
