import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Modal } from '../../../components/common/Modal';
import { dataStore } from '../../../api/dataStore';
import { UserCheck, Plus, Key, Shield, ShieldCheck } from 'lucide-react';
import { useToast } from '../../../context/ToastContext';
import { getProfiles, updateProfile } from '../../../api/profileService';
import { settingsApi } from '../../../api/endpoints';
import { sortUniqueBy } from '../../../utils/sortUtils';

export const UserManagementPage = () => {
  const [users, setUsers] = useState(() => dataStore.getUsers());
  const [profiles, setProfiles] = useState(getProfiles());
  const [isModalOpen, setIsModalOpen] = useState(false);
  const { success } = useToast();

  useEffect(() => {
    let isMounted = true;
    const loadUsers = async () => {
      try {
        const data = await settingsApi.getUsers();
        if (isMounted && data && Array.isArray(data) && data.length > 0) {
          const mapped = data.map((u) => {
            const fullName = u.nom || `${u.first_name || ''} ${u.last_name || ''}`.trim();
            const parts = fullName ? fullName.split(' ') : ['Utilisateur', ''];
            const fName = u.first_name || u.Prenom || parts[0] || 'Utilisateur';
            const lName = u.last_name || u.Nom || parts.slice(1).join(' ') || '';
            const isAdmin = Boolean(u.is_superuser || u.is_admin);
            return {
              id: u.id || u.IdUtilisateur,
              username: u.username || u.NomConnexion || u.email,
              email: u.email || `${u.NomConnexion || 'user'}@uranus.ci`,
              first_name: fName,
              last_name: lName,
              avatar: (fName[0] || 'U').toUpperCase() + (lName[0] || '').toUpperCase(),
              role: isAdmin ? 'ADMIN' : 'USER',
              role_label: isAdmin ? 'Directeur Général / Administrateur' : 'Opérateur / Souscripteur',
              status: u.is_active !== false ? 'Actif' : 'Inactif',
              status_badge: u.is_active !== false ? 'emerald' : 'rose',
              last_login: u.last_login || 'Récemment',
            };
          });
          setUsers(mapped);
        }
      } catch (e) {
        console.error('Erreur chargement utilisateurs Django:', e);
      }
    };
    loadUsers();
    return () => { isMounted = false; };
  }, []);

  const [formData, setFormData] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    role: 'USER',
    profile_code: 'SOUSCRIPTEUR_GUICHET',
    role_label: 'Opérateur / Souscripteur Guichet',
  });

  const [userToReset, setUserToReset] = useState(null);
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);
  const [tempPassword, setTempPassword] = useState('Phare@2026!');
  const [forceChangeOnLogin, setForceChangeOnLogin] = useState(true);

  const handleCreateUser = (e) => {
    e.preventDefault();
    const newUser = dataStore.saveUser({
      username: formData.username,
      email: formData.email,
      first_name: formData.first_name,
      last_name: formData.last_name,
      role: formData.role,
      role_label: formData.role_label,
      profile_code: formData.profile_code,
    });
    const targetProfile = profiles.find((p) => p.code === formData.profile_code);
    if (targetProfile) {
      updateProfile(targetProfile.id, { user_count: (targetProfile.user_count || 0) + 1 });
    }
    setUsers(dataStore.getUsers());
    setIsModalOpen(false);
    success(`Compte utilisateur pour ${newUser.first_name} ${newUser.last_name} (${newUser.role_label}) créé !`);
  };

  const columns = [
    {
      header: 'Utilisateur',
      render: (r) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              background: r.role === 'ADMIN' ? 'linear-gradient(135deg, #8b5cf6, #3b82f6)' : 'linear-gradient(135deg, #059669, #0ea5e9)',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '0.75rem',
            }}
          >
            {r.avatar}
          </div>
          <div>
            <div style={{ fontWeight: 700, color: '#fff' }}>{r.first_name} {r.last_name}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>@{r.username}</div>
          </div>
        </div>
      ),
    },
    { header: 'Email Professionnel', accessor: 'email' },
    {
      header: 'Rôle & Habilitation',
      render: (r) => (
        <span
          style={{
            fontSize: '0.75rem',
            padding: '2px 8px',
            borderRadius: '9999px',
            background: r.role === 'ADMIN' ? 'rgba(139,92,246,0.15)' : 'rgba(59,130,246,0.15)',
            color: r.role === 'ADMIN' ? '#c084fc' : '#60a5fa',
            fontWeight: 700,
          }}
        >
          {r.role_label}
        </span>
      ),
    },
    {
      header: 'Statut',
      render: (r) => <StatusBadge label={r.is_active ? 'Actif' : 'Désactivé'} color={r.is_active ? 'emerald' : 'rose'} />,
    },
    {
      header: 'Action',
      render: (r) => (
        <button
          className="btn btn-secondary"
          style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
          onClick={() => {
            setUserToReset(r);
            setTempPassword(`Phare@${Math.floor(1000 + Math.random() * 9000)}!`);
            setIsResetModalOpen(true);
          }}
        >
          <Key size={13} /> Reset Pass
        </button>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <UserCheck size={26} color="#3b82f6" />
            Comptes utilisateurs
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Créer un compte, lui attribuer un profil, réinitialiser un mot de passe.
          </p>
        </div>

        <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
          <Plus size={16} />
          <span>Nouvel Utilisateur</span>
        </button>
      </div>

      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <DataTable columns={columns} data={users} searchPlaceholder="Filtrer un utilisateur..." />
      </div>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Création d'un Compte Utilisateur">
        <form onSubmit={handleCreateUser}>
          <div className="responsive-form-row">
            <div className="form-group">
              <label className="form-label">Prénom</label>
              <input type="text" className="form-control" required value={formData.first_name} onChange={(e) => setFormData({ ...formData, first_name: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Nom</label>
              <input type="text" className="form-control" required value={formData.last_name} onChange={(e) => setFormData({ ...formData, last_name: e.target.value })} />
            </div>
          </div>

          <div className="responsive-form-row">
            <div className="form-group">
              <label className="form-label">Identifiant (Username)</label>
              <input type="text" className="form-control" required value={formData.username} onChange={(e) => setFormData({ ...formData, username: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Email professionnel</label>
              <input type="email" className="form-control" required value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} />
            </div>
          </div>

          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <label className="form-label" style={{ marginBottom: 0 }}>Profil d'Habilitation Métier</label>
              <Link to="/admin/profiles" style={{ fontSize: '0.75rem', color: '#60a5fa', textDecoration: 'none', fontWeight: 600 }}>
                + Gérer les profils
              </Link>
            </div>
            <select
              className="form-control"
              value={formData.profile_code}
              onChange={(e) => {
                const selected = profiles.find((p) => p.code === e.target.value);
                setFormData({
                  ...formData,
                  profile_code: e.target.value,
                  role: selected?.space === 'ADMIN' ? 'ADMIN' : (selected?.space === 'ALL' ? 'ADMIN' : 'USER'),
                  role_label: selected?.name || e.target.value,
                });
              }}
            >
              {sortUniqueBy(profiles, (p) => p.name).map((p) => (
                <option key={p.id} value={p.code}>
                  {p.name} ({p.space === 'ALL' ? 'Accès Global' : p.space === 'ADMIN' ? 'Espace Admin' : 'Espace Opérateur'})
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>Annuler</button>
            <button type="submit" className="btn btn-primary">Créer le Compte</button>
          </div>
        </form>
      </Modal>

      {/* Modal Réinitialisation Mot de Passe */}
      <Modal
        isOpen={isResetModalOpen}
        onClose={() => setIsResetModalOpen(false)}
        title="Réinitialisation du Mot de Passe"
        subtitle={`Utilisateur : @${userToReset?.username} (${userToReset?.first_name} ${userToReset?.last_name})`}
        maxWidth="500px"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ background: 'var(--bg-surface)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Email de notification :</span>
              <strong style={{ color: 'var(--text-primary)' }}>{userToReset?.email}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Profil actuel :</span>
              <span className="badge badge-info">{userToReset?.role_label}</span>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Mot de passe temporaire généré</label>
            <input
              type="text"
              className="form-control"
              value={tempPassword}
              onChange={(e) => setTempPassword(e.target.value)}
              style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#34d399', letterSpacing: '1px' }}
            />
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.85rem', cursor: 'pointer', color: 'var(--text-secondary)' }}>
            <input
              type="checkbox"
              checked={forceChangeOnLogin}
              onChange={(e) => setForceChangeOnLogin(e.target.checked)}
            />
            <span>Exiger le changement de mot de passe à la prochaine connexion</span>
          </label>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsResetModalOpen(false)}>
              Annuler
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                success(`Mot de passe réinitialisé pour @${userToReset?.username}. Identifiants transmis.`);
                setIsResetModalOpen(false);
              }}
            >
              Confirmer Réinitialisation
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default UserManagementPage;
