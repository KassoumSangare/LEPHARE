import React, { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  LayoutDashboard,
  Users,
  FileText,
  Shield,
  ShieldCheck,
  RefreshCw,
  CreditCard,
  Car,
  KeyRound,
  BarChart3,
  FileSpreadsheet,
  CheckCheck,
  Building2,
  Coins,
  UserCheck,
  ChevronDown,
  TrendingUp,
  AlertTriangle,
  FolderOpen,
  Layers,
  Compass,
  Settings,
  X,
} from 'lucide-react';

export const Sidebar = ({ isOpen, onClose }) => {
  const { user, activeSpace } = useAuth();
  const location = useLocation();

  // Collapsible accordion states
  const [openSubmenus, setOpenSubmenus] = useState({
    crm: true,
    quotes: true,
    cash: true,
    conventions: true,
    compliance: true,
    users: true,
  });

  useEffect(() => {
    if (location.pathname.includes('/user/crm') || location.pathname.includes('/user/clients')) {
      setOpenSubmenus((prev) => ({ ...prev, crm: true }));
    }
    if (location.pathname.includes('/user/quotes')) {
      setOpenSubmenus((prev) => ({ ...prev, quotes: true }));
    }
    if (location.pathname.includes('/user/cash') || location.pathname.includes('/user/cheques')) {
      setOpenSubmenus((prev) => ({ ...prev, cash: true }));
    }
    if (location.pathname.includes('/admin/conventions') || location.pathname.includes('/admin/settings')) {
      setOpenSubmenus((prev) => ({ ...prev, conventions: true }));
    }
    if (location.pathname.includes('/admin/compliance') || location.pathname.includes('/admin/reporting')) {
      setOpenSubmenus((prev) => ({ ...prev, compliance: true }));
    }
    if (
      location.pathname.includes('/admin/users') ||
      location.pathname.includes('/admin/profiles') ||
      location.pathname.includes('/admin/roles-permissions')
    ) {
      setOpenSubmenus((prev) => ({ ...prev, users: true }));
    }
  }, [location.pathname]);

  const toggleSubmenu = (menu) => {
    setOpenSubmenus((prev) => ({ ...prev, [menu]: !prev[menu] }));
  };

  const handleLinkClick = () => {
    if (window.innerWidth <= 1024 && onClose) {
      onClose();
    }
  };

  return (
    <aside
      className={`sidebar-drawer ${isOpen ? 'open' : ''}`}
      style={{
        width: 'var(--sidebar-width)',
        background: 'var(--bg-surface)',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - var(--navbar-height))',
        position: 'sticky',
        top: 'var(--navbar-height)',
        overflowY: 'auto',
        padding: '0.85rem 0.65rem 1.5rem 0.65rem',
        userSelect: 'none',
      }}
    >
      {/* Workspace Indicator Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.45rem 0.65rem',
          marginBottom: '0.65rem',
          borderRadius: 'var(--radius-sm)',
          background: activeSpace === 'admin' ? 'rgba(139,92,246,0.06)' : 'rgba(37,99,235,0.06)',
          border: `1px solid ${activeSpace === 'admin' ? 'rgba(139,92,246,0.18)' : 'rgba(37,99,235,0.18)'}`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {activeSpace === 'admin' ? (
            <Settings size={14} style={{ color: '#c084fc' }} />
          ) : (
            <Compass size={14} style={{ color: '#60a5fa' }} />
          )}
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
            {activeSpace === 'admin' ? 'Direction & Pilotage' : 'Production & Courtage'}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span
            style={{
              fontSize: '0.62rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              padding: '0.15rem 0.45rem',
              borderRadius: '9999px',
              background: activeSpace === 'admin' ? 'rgba(139,92,246,0.2)' : 'rgba(37,99,235,0.2)',
              color: activeSpace === 'admin' ? '#c084fc' : '#60a5fa',
            }}
          >
            {activeSpace === 'admin' ? 'ADMIN' : 'MÉTIER'}
          </span>

          {onClose && (
            <button
              onClick={onClose}
              className="mobile-toggle-btn"
              style={{ padding: '0.15rem', color: 'var(--text-muted)', border: 'none', background: 'transparent' }}
              title="Fermer le menu"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {/* Navigation Tree */}
      <nav
        onClick={(e) => {
          if (e.target.closest('a')) handleLinkClick();
        }}
        style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}
      >
        {activeSpace === 'admin' ? (
          /* =========================================================================
             ESPACE DIRECTION & ADMINISTRATION
             ========================================================================= */
          <>
            {/* 1. PILOTAGE & STRATÉGIE */}
            <div className="sidebar-section-header">
              <span>Pilotage & Stratégie</span>
            </div>

            <NavLink to="/admin/dashboard" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
              <LayoutDashboard size={16} className="nav-icon" />
              <span>Tableau de Bord Direction</span>
            </NavLink>

            <NavLink to="/user/crm" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
              <TrendingUp size={16} className="nav-icon" />
              <span>Pipeline Commercial</span>
            </NavLink>

            <NavLink to="/user/crm/360" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
              <Users size={16} className="nav-icon" />
              <span>Fiche Client 360°</span>
            </NavLink>

            {/* 2. FINANCE & RÈGLEMENTS */}
            <div className="sidebar-section-header">
              <span>Finance & Règlements (CIMA)</span>
            </div>

            <NavLink to="/admin/remittances" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
              <Building2 size={16} className="nav-icon" />
              <span>Reversements Compagnies (30j)</span>
            </NavLink>

            <NavLink to="/admin/commissions" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
              <Coins size={16} className="nav-icon" />
              <span>Commissions & Rétrocessions</span>
            </NavLink>

            <NavLink to="/admin/approvals" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
              <CheckCheck size={16} className="nav-icon" />
              <span>Centre d'Approbation</span>
            </NavLink>

            {/* 3. GESTION MÉTIER & CONVENTIONS */}
            <div className="sidebar-section-header">
              <span>Métier & Conventions</span>
            </div>

            <NavLink to="/user/claims" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
              <AlertTriangle size={16} className="nav-icon" />
              <span>Supervision Sinistres Délégués</span>
            </NavLink>

            <div>
              <div
                onClick={() => toggleSubmenu('conventions')}
                className={`sidebar-nav-item ${location.pathname.includes('/admin/conventions') || location.pathname.includes('/admin/settings') ? 'active' : ''}`}
                style={{ justifyContent: 'space-between' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                  <Layers size={16} className="nav-icon" />
                  <span>Conventions & Catalogue</span>
                </div>
                <ChevronDown
                  size={14}
                  style={{
                    transform: openSubmenus.conventions ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s',
                    color: 'var(--text-muted)',
                  }}
                />
              </div>

              {openSubmenus.conventions && (
                <div className="sidebar-submenu-tree">
                  <NavLink to="/admin/conventions" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Moteur des Conventions
                  </NavLink>
                  <NavLink to="/admin/settings/products" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Branches & Produits
                  </NavLink>
                  <NavLink to="/admin/settings/guarantees" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Référentiel Garanties
                  </NavLink>
                  <NavLink to="/admin/settings/tarifs" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Grilles Tarifaires & Taxes
                  </NavLink>
                  <NavLink to="/admin/settings/companies" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Compagnies Partenaires
                  </NavLink>
                  <NavLink to="/admin/settings/vehicle-geo" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Référentiels Auto & Géo
                  </NavLink>
                  <NavLink to="/admin/settings/secteurs-activite" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Secteurs d'Activité Éco.
                  </NavLink>
                  <NavLink to="/admin/settings/professions" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Professions & Métiers
                  </NavLink>
                  <NavLink to="/admin/settings/types-souscripteur" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Types de Souscripteur
                  </NavLink>
                  <NavLink to="/admin/settings/types-assure" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Types d'Assuré
                  </NavLink>
                </div>
              )}
            </div>

            {/* SECTION PARAMÉTRAGE OREOLE */}
            <div>
              <div
                onClick={() => toggleSubmenu('oreole')}
                className={`sidebar-nav-item ${
                  location.pathname.includes('/admin/settings/offres') ||
                  location.pathname.includes('/admin/settings/garanties-oreole') ||
                  location.pathname.includes('/admin/settings/taxes') ||
                  location.pathname.includes('/admin/settings/commissions-baremes') ||
                  location.pathname.includes('/admin/settings/flotte') ||
                  location.pathname.includes('/admin/settings/securite-routiere') ||
                  location.pathname.includes('/admin/settings/marques') ||
                  location.pathname.includes('/parametrage/')
                    ? 'active'
                    : ''
                }`}
                style={{ justifyContent: 'space-between' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                  <Settings size={16} className="nav-icon" style={{ color: 'var(--brand-primary, #60a5fa)' }} />
                  <span>Paramétrage OREOLE</span>
                </div>
                <ChevronDown
                  size={14}
                  style={{
                    transform: openSubmenus.oreole ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s',
                    color: 'var(--text-muted)',
                  }}
                />
              </div>

              {openSubmenus.oreole && (
                <div className="sidebar-submenu-tree">
                  <NavLink to="/admin/settings/offres" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Catalogue Offres & Packages
                  </NavLink>
                  <NavLink to="/admin/settings/garanties-oreole" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Garanties & Sous-Garanties
                  </NavLink>
                  <NavLink to="/admin/settings/taxes" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Taxes CIMA / Fiscalité
                  </NavLink>
                  <NavLink to="/admin/settings/commissions-baremes" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Barèmes Commissions
                  </NavLink>
                  <NavLink to="/admin/settings/flotte" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Réductions Flotte Auto
                  </NavLink>
                  <NavLink to="/admin/settings/securite-routiere" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Sécurité Routière
                  </NavLink>
                  <NavLink to="/admin/settings/marques" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Marques Véhicules
                  </NavLink>
                </div>
              )}
            </div>

            {/* 4. CONFORMITÉ & AUDIT CRCA */}
            <div className="sidebar-section-header">
              <span>Conformité & Contrôle (CRCA)</span>
            </div>

            <NavLink to="/user/documents" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
              <FolderOpen size={16} className="nav-icon" />
              <span>GED & Pièces Probantes</span>
            </NavLink>

            <div>
              <div
                onClick={() => toggleSubmenu('compliance')}
                className={`sidebar-nav-item ${location.pathname.includes('/admin/compliance') || location.pathname.includes('/admin/reporting') ? 'active' : ''}`}
                style={{ justifyContent: 'space-between' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                  <ShieldCheck size={16} className="nav-icon" />
                  <span>Audit & États Réglementaires</span>
                </div>
                <ChevronDown
                  size={14}
                  style={{
                    transform: openSubmenus.compliance ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s',
                    color: 'var(--text-muted)',
                  }}
                />
              </div>

              {openSubmenus.compliance && (
                <div className="sidebar-submenu-tree">
                  <NavLink to="/admin/compliance" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Agrément, Caution & Audit
                  </NavLink>
                  <NavLink to="/admin/reporting/cima" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    États CIMA E1 & E2
                  </NavLink>
                  <NavLink to="/admin/reporting/emissions" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Bordereau des Émissions
                  </NavLink>
                  <NavLink to="/admin/reporting/etats-decisionnels" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    États Décisionnels
                  </NavLink>
                </div>
              )}
            </div>

            {/* 5. SYSTÈME & HABILITATIONS */}
            <div className="sidebar-section-header">
              <span>Système & Habilitations</span>
            </div>

            <div>
              <div
                onClick={() => toggleSubmenu('users')}
                className={`sidebar-nav-item ${
                  location.pathname.includes('/admin/users') ||
                  location.pathname.includes('/admin/profiles') ||
                  location.pathname.includes('/admin/roles-permissions')
                    ? 'active'
                    : ''
                }`}
                style={{ justifyContent: 'space-between' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                  <UserCheck size={16} className="nav-icon" />
                  <span>Utilisateurs & Droits</span>
                </div>
                <ChevronDown
                  size={14}
                  style={{
                    transform: openSubmenus.users ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s',
                    color: 'var(--text-muted)',
                  }}
                />
              </div>

              {openSubmenus.users && (
                <div className="sidebar-submenu-tree">
                  <NavLink to="/admin/users" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Comptes Collaborateurs
                  </NavLink>
                  <NavLink to="/admin/profiles" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    8 Profils CIMA & Droits
                  </NavLink>
                  <NavLink to="/admin/roles-permissions" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Matrice des Habilitations
                  </NavLink>
                </div>
              )}
            </div>
          </>
        ) : (
          /* =========================================================================
             ESPACE PRODUCTION & EXPLOITATION (OPÉRATEUR)
             ========================================================================= */
          <>
            {/* 1. GESTION OPÉRATIONNELLE */}
            <div className="sidebar-section-header">
              <span>Gestion Opérationnelle</span>
            </div>

            <NavLink to="/user/dashboard" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
              <LayoutDashboard size={16} className="nav-icon" />
              <span>Cockpit Opérationnel</span>
            </NavLink>

            <div>
              <div
                onClick={() => toggleSubmenu('crm')}
                className={`sidebar-nav-item ${location.pathname.includes('/user/crm') || location.pathname.includes('/user/clients') ? 'active' : ''}`}
                style={{ justifyContent: 'space-between' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                  <Users size={16} className="nav-icon" />
                  <span>CRM & Relations Clients</span>
                </div>
                <ChevronDown
                  size={14}
                  style={{
                    transform: openSubmenus.crm ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s',
                    color: 'var(--text-muted)',
                  }}
                />
              </div>

              {openSubmenus.crm && (
                <div className="sidebar-submenu-tree">
                  <NavLink to="/user/crm" end className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Pipeline Commercial
                  </NavLink>
                  <NavLink to="/user/crm/360" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Fiche Client 360°
                  </NavLink>
                  <NavLink to="/user/clients" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Clientèle
                  </NavLink>
                </div>
              )}
            </div>

            {/* 2. PRODUCTION & SOUSCRIPTION */}
            <div className="sidebar-section-header">
              <span>Production & Souscription</span>
            </div>

            <div>
              <div
                onClick={() => toggleSubmenu('quotes')}
                className={`sidebar-nav-item ${location.pathname.includes('/user/quotes') ? 'active' : ''}`}
                style={{ justifyContent: 'space-between' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                  <FileText size={16} className="nav-icon" />
                  <span>Devis & Tarification</span>
                </div>
                <ChevronDown
                  size={14}
                  style={{
                    transform: openSubmenus.quotes ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s',
                    color: 'var(--text-muted)',
                  }}
                />
              </div>

              {openSubmenus.quotes && (
                <div className="sidebar-submenu-tree">
                  <NavLink to="/user/quotes" end className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Registre des Devis
                  </NavLink>
                  <NavLink to="/user/quotes/auto" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Automobile
                  </NavLink>
                  <NavLink to="/user/quotes/mrh" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Habitation (MRH)
                  </NavLink>
                  <NavLink to="/user/quotes/sante" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Santé
                  </NavLink>
                  <NavLink to="/user/quotes/ia" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Accidents Corporels
                  </NavLink>
                  <NavLink to="/user/quotes/voyage" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Voyage & Schengen
                  </NavLink>
                  <NavLink to="/user/quotes/transport" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Transport (Facultés)
                  </NavLink>
                </div>
              )}
            </div>

            <NavLink to="/user/contracts" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
              <ShieldCheck size={16} className="nav-icon" />
              <span>Polices & Contrats</span>
            </NavLink>

            <NavLink to="/user/endorsements" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
              <RefreshCw size={16} className="nav-icon" />
              <span>Avenants & Mouvements</span>
            </NavLink>

            <NavLink to="/user/asaci" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
              <Car size={16} className="nav-icon" />
              <span>e-Attestations ASACI Auto</span>
            </NavLink>

            {/* 3. FINANCE & CAISSE (ART. 13) */}
            <div className="sidebar-section-header">
              <span>Caisse & Encaissements (Art. 13)</span>
            </div>

            <div>
              <div
                onClick={() => toggleSubmenu('cash')}
                className={`sidebar-nav-item ${location.pathname.includes('/user/cash') || location.pathname.includes('/user/cheques') ? 'active' : ''}`}
                style={{ justifyContent: 'space-between' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                  <CreditCard size={16} className="nav-icon" />
                  <span>Caisse & Règlements</span>
                </div>
                <ChevronDown
                  size={14}
                  style={{
                    transform: openSubmenus.cash ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s',
                    color: 'var(--text-muted)',
                  }}
                />
              </div>

              {openSubmenus.cash && (
                <div className="sidebar-submenu-tree">
                  <NavLink to="/user/cash" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Encaisser Primes (Quittances)
                  </NavLink>
                  <NavLink to="/user/cheques" className={({ isActive }) => `sidebar-sublink-item ${isActive ? 'active' : ''}`}>
                    Portefeuille Chèques
                  </NavLink>
                </div>
              )}
            </div>

            {/* 4. INDEMNISATION & GED */}
            <div className="sidebar-section-header">
              <span>Indemnisation & Pièces</span>
            </div>

            <NavLink to="/user/claims" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
              <AlertTriangle size={16} className="nav-icon" />
              <span>Gestion Déléguée Sinistres</span>
            </NavLink>

            <NavLink to="/user/documents" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
              <FolderOpen size={16} className="nav-icon" />
              <span>GED & Pièces Probantes</span>
            </NavLink>

            <NavLink to="/user/derogations" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
              <KeyRound size={16} className="nav-icon" />
              <span>Workflows & Dérogations</span>
            </NavLink>
          </>
        )}
      </nav>
    </aside>
  );
};

export default Sidebar;
