import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Shield, Lock, User, ArrowRight } from 'lucide-react';
import { useToast } from '../../context/ToastContext';

export const LoginPage = () => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('password');
  const { login } = useAuth();
  const navigate = useNavigate();
  const { success } = useToast();

  const handleSubmit = (e) => {
    e.preventDefault();
    const user = login(username, password);
    success(`Bienvenue, ${user.first_name || user.username} ! Connexion réussie.`);
    if (user.role === 'ADMIN') {
      navigate('/admin/dashboard');
    } else {
      navigate('/user/dashboard');
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'radial-gradient(circle at 50% 20%, rgba(37,99,235,0.2) 0%, transparent 60%), #0b1120',
        padding: '1.5rem',
      }}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '400px',
          padding: '1.75rem 1.85rem',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '0 20px 40px -10px rgba(0,0,0,0.5)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #2563eb, #7c3aed)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              boxShadow: '0 2px 10px rgba(37,99,235,0.4)',
              marginBottom: '0.75rem',
            }}
          >
            <Shield size={24} />
          </div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff', letterSpacing: '-0.02em', margin: 0 }}>
            LE PHARE
          </h1>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Logiciel Métier de Courtage & Sinistres Délégués (CIMA V2)
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Nom d'utilisateur ou Email</label>
            <div style={{ position: 'relative' }}>
              <User
                size={16}
                color="var(--text-muted)"
                style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)' }}
              />
              <input
                type="text"
                className="form-control"
                style={{ paddingLeft: '2.6rem' }}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="ex: admin ou souscripteur_auto"
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Mot de passe</label>
            <div style={{ position: 'relative' }}>
              <Lock
                size={16}
                color="var(--text-muted)"
                style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)' }}
              />
              <input
                type="password"
                className="form-control"
                style={{ paddingLeft: '2.6rem' }}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', marginTop: '0.75rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ flex: 1, fontSize: '0.75rem', padding: '0.4rem' }}
              onClick={() => { setUsername('admin'); setPassword('admin'); }}
            >
              Mode Direction
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ flex: 1, fontSize: '0.75rem', padding: '0.4rem' }}
              onClick={() => { setUsername('souscripteur_auto'); setPassword('user'); }}
            >
              Mode Production
            </button>
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '0.75rem' }}>
            <span>Se connecter à LE PHARE</span>
            <ArrowRight size={18} />
          </button>
        </form>

        <div style={{ marginTop: '2rem', textAlign: 'center', fontSize: '0.775rem', color: 'var(--text-muted)' }}>
          Système certifié CIMA & Gestion Déléguée • <span style={{ color: '#34d399' }}>LE PHARE v2.0</span>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
