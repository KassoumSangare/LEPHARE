import { isRegistryQuote } from '../../../utils/quoteRegistry';
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { customerApi, contractApi, quoteApi } from '../../../api/endpoints';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { ArrowLeft, User, Phone, Mail, MapPin, Building, Shield, FileText, CreditCard } from 'lucide-react';
import { formatDate } from '../../../utils/dateUtils';

export const ClientDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [clientData, setClientData] = useState(null);
  const [contracts, setContracts] = useState([]);
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchClientData = async () => {
      setLoading(true);
      try {
        const [cData, cList, qList] = await Promise.all([
          customerApi.getClientDetail(id),
          contractApi.getContracts(),
          quoteApi.getQuotes(),
        ]);
        if (isMounted) {
          setClientData(cData);
          const clientNameLower = String(cData?.nom || cData?.nomcomplet || '').toLowerCase();
          setContracts(cList.filter((c) => (clientNameLower && String(c.client_nom || '').toLowerCase().includes(clientNameLower)) || String(c.client_id) === String(cData?.id)));
          setQuotes(qList.filter(isRegistryQuote).filter((q) => String(q.client_id) === String(cData?.id) || (clientNameLower && String(q.client_nom || '').toLowerCase().includes(clientNameLower))));
        }
      } catch (err) {
        console.error('Erreur chargement détail client:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    if (id) {
      fetchClientData();
    }
    return () => { isMounted = false; };
  }, [id]);

  const client = clientData || {};
  const clientContracts = contracts;
  const clientQuotes = quotes;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Back button & Page Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <button className="btn btn-secondary" onClick={() => navigate('/user/clients')} style={{ padding: '0.4rem 0.8rem' }}>
          <ArrowLeft size={16} />
          Retour
        </button>
        <div>
          <h1 className="title-xl">{client.nomcomplet || (loading ? '' : 'Client non trouvé')}</h1>
          <span style={{ fontSize: '0.8rem', color: '#60a5fa', fontFamily: 'var(--font-mono)' }}>
            Code: {client.codeclient || id} • {client.typeclient || ''}
          </span>
        </div>
      </div>

      {/* Overview Cards Exhaustives stdclient */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
        {/* 1. Identité & Conformité CIMA */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <h3 className="title-md" style={{ color: '#fff', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <User size={18} color="#3b82f6" />
            Identité & Conformité CIMA
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-muted">Type de Personne :</span>
              <strong>{client.typeclient} {client.civilite ? `(${client.civilite})` : ''}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-muted">N° Assuré CIMA :</span>
              <strong style={{ color: '#60a5fa', fontFamily: 'var(--font-mono)' }}>{client.numero_assure || 'N/A'}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-muted">Matricule Interne :</span>
              <strong style={{ fontFamily: 'var(--font-mono)' }}>{client.codeclient || client.Matricule || 'N/A'}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-muted">{client.typeclient === 'Entreprise' ? 'RCCM / Patente :' : 'N° Pièce / CNI :'}</span>
              <strong style={{ color: '#fbbf24' }}>{client.CniPat || 'Non renseigné'}</strong>
            </div>
            {client.typeclient === 'Particulier' && (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="text-muted">Date de Naissance :</span>
                  <span>{client.DateNaissance || 'Non renseignée'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="text-muted">Lieu de Naissance :</span>
                  <span>{client.LieuNaissance || 'Non renseigné'}</span>
                </div>
              </>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '0.25rem' }}>
              <span className="text-muted">Statut VIP :</span>
              <span className={`badge ${client.Vip === 'V' || client.is_vip ? 'badge-warning' : 'badge-neutral'}`} style={{ fontSize: '0.7rem' }}>
                {client.Vip === 'V' || client.is_vip ? 'VIP Prioritaire' : 'Standard'}
              </span>
            </div>
          </div>
        </div>

        {/* 2. Coordonnées & Localisation */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <h3 className="title-md" style={{ color: '#fff', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Phone size={18} color="#60a5fa" />
            Coordonnées & Localisation
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
              <Phone size={14} color="var(--text-muted)" />
              <span>Mobile : <strong>{client.mobile || client.telephone || 'Non renseigné'}</strong></span>
            </div>
            {client.fixe && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
                <Phone size={14} color="var(--text-muted)" />
                <span>Fixe : {client.fixe}</span>
              </div>
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
              <Mail size={14} color="var(--text-muted)" />
              <span>Email : {client.email || client.Email || 'Non renseigné'}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
              <MapPin size={14} color="var(--text-muted)" />
              <span>Adresse : {client.adresse || client.Adresse1 || 'Abidjan'}</span>
            </div>
            {client.Adresse2 && (
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', paddingLeft: '1.4rem' }}>
                Complément : {client.Adresse2}
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: '0.25rem' }}>
              <span className="text-muted">Ville :</span>
              <strong>{client.ville || 'Abidjan'}</strong>
            </div>
            {client.CodePostal && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-muted">Boîte Postale :</span>
                <span>{client.CodePostal}</span>
              </div>
            )}
          </div>
        </div>

        {/* 3. Activité & Données Entreprise */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <h3 className="title-md" style={{ color: '#fff', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Building size={18} color="#a855f7" />
            Activité & Profil Courtage
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-muted">Profession :</span>
              <strong>{client.profession || client.libelleprofession || 'Non renseignée'}</strong>
            </div>
            {client.secteur_activite && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-muted">Secteur d'Activité :</span>
                <span>{client.secteur_activite}</span>
              </div>
            )}
            {client.typeclient === 'Entreprise' && client.Responsable && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-muted">Représentant Légal :</span>
                <strong>{client.Responsable}</strong>
              </div>
            )}
            {client.Fonction && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-muted">Fonction Contact :</span>
                <span>{client.Fonction}</span>
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-muted">Type Souscripteur :</span>
              <span>{client.type_souscripteur || (client.typeclient === 'Entreprise' ? 'Personne Morale' : 'Personne Physique')}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-muted">Type Assuré :</span>
              <span>{client.type_assure || (client.typeclient === 'Entreprise' ? 'Personne Morale' : 'Personne Physique')}</span>
            </div>
          </div>
        </div>

        {/* 4. Banque & Données Fiscales */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <h3 className="title-md" style={{ color: '#fff', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <CreditCard size={18} color="#10b981" />
            Banque & Fiscalité
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.85rem' }}>
            <div>
              <span className="text-muted" style={{ fontSize: '0.75rem' }}>RIB Bancaire (24 car.) :</span>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: client.Rib ? '#34d399' : 'var(--text-muted)', fontSize: '0.8rem', wordBreak: 'break-all' }}>
                {client.Rib || 'Non renseigné'}
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-muted">N° Compte Client :</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{client.NumeroCompte || 'Non assigné'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-muted">Exonéré de Taxes :</span>
              <strong style={{ color: client.ExonereDeTaxes ? '#34d399' : '#94a3b8' }}>
                {client.ExonereDeTaxes ? 'Oui (Exonération Légale)' : 'Non (Soumis)'}
              </strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-muted">Exonéré d'Accessoires :</span>
              <strong style={{ color: client.ExonereDeAccess ? '#34d399' : '#94a3b8' }}>
                {client.ExonereDeAccess ? 'Oui' : 'Non'}
              </strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.4rem', marginTop: '0.2rem' }}>
              <span className="text-muted">Total Primes Émises :</span>
              <strong style={{ color: '#fff', fontFamily: 'var(--font-mono)' }}>{client.total_primes || '0 FCFA'}</strong>
            </div>
          </div>
        </div>
      </div>

      {/* Policies section */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <h3 className="title-md" style={{ color: '#fff', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Shield size={18} color="#8b5cf6" />
          Contrats d'Assurance du Client ({clientContracts.length})
        </h3>
        {clientContracts.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {clientContracts.map((ctr) => (
              <div
                key={ctr.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '1rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, color: '#fff' }}>{ctr.numeropolice} - {ctr.produit}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {ctr.compagnie} • Du {formatDate(ctr.date_effet)} au {formatDate(ctr.date_expiration)}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
                    {ctr.prime_totale.toLocaleString('fr-FR')} FCFA
                  </div>
                  <StatusBadge label={ctr.statut_encaissement} color={ctr.statut_encaissement === 'Soldé' ? 'emerald' : 'amber'} />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Aucun contrat actif pour ce client.</p>
        )}
      </div>

      {/* Quotes section */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <h3 className="title-md" style={{ color: '#fff', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <FileText size={18} color="#0ea5e9" />
          Devis & Propositions Récentes ({clientQuotes.length})
        </h3>
        {clientQuotes.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {clientQuotes.map((q) => (
              <div
                key={q.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '1rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, color: '#fff' }}>{q.numerodevis} - {q.produit}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Émis le {formatDate(q.date_emission)} • {q.compagnie}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
                    {Number(q.prime_totale || 0).toLocaleString('fr-FR')} FCFA
                  </div>
                  <StatusBadge label={q.statut} color={q.statut_badge} />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Aucun devis en cours pour ce client.</p>
        )}
      </div>
    </div>
  );
};

export default ClientDetailPage;
