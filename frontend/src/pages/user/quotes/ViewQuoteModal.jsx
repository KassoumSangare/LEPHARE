import React from 'react';
import { Modal } from '../../../components/common/Modal';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { printQuoteFacture, printConditionsParticulieres } from '../../../utils/exportUtils';
import {
  FileText,
  Printer,
  CheckCircle,
  Building2,
  Calendar,
  User,
  Shield,
  Car,
  Home,
  HeartPulse,
  Plane,
  Ship,
  DollarSign,
  Package,
  MapPin,
  Clock,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
} from 'lucide-react';

export const ViewQuoteModal = ({ isOpen, onClose, quote, onConvertToContract }) => {
  if (!isOpen || !quote) return null;

  const isConsolidated = quote.statut === 'Consolidé';
  const details = quote.details || {};

  const getBranchIcon = (branche) => {
    const b = String(branche || '').toLowerCase();
    if (b.includes('auto')) return <Car size={20} color="#3b82f6" />;
    if (b.includes('mrh') || b.includes('habit')) return <Home size={20} color="#0ea5e9" />;
    if (b.includes('sant')) return <HeartPulse size={20} color="#f43f5e" />;
    if (b.includes('voyag')) return <Plane size={20} color="#38bdf8" />;
    if (b.includes('transp')) return <Ship size={20} color="#0284c7" />;
    return <Shield size={20} color="#8b5cf6" />;
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Fiche Proposition & Devis [${quote.numerodevis}]`}
      size="large"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {/* Header Ribbon */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1rem 1.25rem',
            background: 'var(--surface-sunken)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
            flexWrap: 'wrap',
            gap: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '8px',
                background: 'rgba(59, 130, 246, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {getBranchIcon(quote.branche)}
            </div>
            <div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                {quote.numerodevis}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Branche : <strong>{quote.branche || 'Général'}</strong> • Émis le {quote.date_emission}
                {(quote.date_derniere_modification || quote.DateMaj || quote.date_maj) && (
                  <span style={{ marginLeft: '0.5rem', color: '#93c5fd' }}>
                    • Modifié le : <strong>{quote.date_derniere_modification || quote.DateMaj || quote.date_maj}</strong>
                  </span>
                )}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <StatusBadge label={quote.statut} color={quote.statut_badge} />
            {quote.date_expiration && (
              <span
                style={{
                  fontSize: '0.75rem',
                  padding: '0.2rem 0.5rem',
                  borderRadius: '4px',
                  background: new Date(quote.date_expiration) < new Date() ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.15)',
                  color: new Date(quote.date_expiration) < new Date() ? '#fca5a5' : '#34d399',
                  border: `1px solid ${new Date(quote.date_expiration) < new Date() ? '#ef4444' : '#10b981'}`,
                  fontWeight: 600,
                }}
              >
                {new Date(quote.date_expiration) < new Date()
                  ? `Expiré le ${quote.date_expiration}`
                  : `Valide jusqu'au ${quote.date_expiration}`}
              </span>
            )}
            {isConsolidated && quote.police_associee && (
              <span style={{ fontSize: '0.75rem', color: '#34d399', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                Contrat lié : {quote.police_associee}
              </span>
            )}
          </div>
        </div>

        {/* Alerte si dérogation en attente (CA-07.4) */}
        {quote.circuit_approbation && quote.circuit_approbation.statut_validation === 'EN_ATTENTE_DIRECTION' && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              padding: '0.75rem 1rem',
              borderRadius: '8px',
              background: 'rgba(168, 85, 247, 0.15)',
              border: '1px solid #a855f7',
              color: '#d8b4fe',
              fontSize: '0.85rem',
            }}
          >
            <ShieldAlert size={18} color="#c084fc" />
            <div>
              <strong>Dérogation tarifaire en attente de visa (CA-07.4) :</strong> Remise de {quote.taux_remise || 0}% accordée. Motif : <em>"{quote.motif_derogation || quote.circuit_approbation.motif}"</em>.
            </div>
          </div>
        )}

        {/* Client, Intermédiaire & Partner Details */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          <div className="glass-panel" style={{ padding: '1rem' }}>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <User size={14} color="#60a5fa" />
              Souscripteur / Assuré
            </div>
            <div style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>
              {quote.client_nom}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <MapPin size={13} color="#94a3b8" />
              <span>{quote.adresse || quote.details?.adresse || 'Abidjan, Côte d\'Ivoire'}</span>
            </div>
            {quote.client_id && (
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                ID Client : CLI-{String(quote.client_id).padStart(3, '0')}
              </div>
            )}
          </div>

          <div className="glass-panel" style={{ padding: '1rem' }}>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Building2 size={14} color="#34d399" />
              Compagnie Porteuse & Intermédiaire
            </div>
            <div style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>
              {quote.compagnie}
            </div>
            <div style={{ fontSize: '0.8rem', color: '#60a5fa', marginTop: '0.35rem' }}>
              Intermédiaire : <strong>{quote.intermediaire || 'LE PHARE - Courtage & Sinistres Délégués'}</strong>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              Produit : {quote.produit}
            </div>
          </div>
        </div>

        {/* Actuarial Financial Breakdown */}
        <div className="glass-panel" style={{ padding: '1.25rem', background: 'rgba(255,255,255,0.02)' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.75rem', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <DollarSign size={15} color="#38bdf8" />
            Décompte Actuariel CIMA & Quittance
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem' }}>
            <div style={{ padding: '0.75rem', borderRadius: '6px', background: 'var(--surface-sunken)' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Prime Nette</div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: '#60a5fa', fontFamily: 'var(--font-mono)' }}>
                {Number(quote.prime_nette || 0).toLocaleString()} FCFA
              </div>
            </div>

            <div style={{ padding: '0.75rem', borderRadius: '6px', background: 'var(--surface-sunken)' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Frais Accessoires</div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', fontFamily: 'var(--font-mono)' }}>
                {Number(quote.accessoires || 0).toLocaleString()} FCFA
              </div>
            </div>

            <div style={{ padding: '0.75rem', borderRadius: '6px', background: 'var(--surface-sunken)' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Taxes d'Assurance (TCA)</div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', fontFamily: 'var(--font-mono)' }}>
                {Number(quote.taxes || 0).toLocaleString()} FCFA
              </div>
            </div>

            <div style={{ padding: '0.75rem', borderRadius: '6px', background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
              <div style={{ fontSize: '0.7rem', color: '#34d399', textTransform: 'uppercase', fontWeight: 700 }}>Total TTC à Payer</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#34d399', fontFamily: 'var(--font-mono)' }}>
                {Number(quote.prime_totale || 0).toLocaleString()} FCFA
              </div>
            </div>
          </div>

          {/* CIMA Regulatory Breakdown: FGA, CEDEAO, Commission & Dates */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem', marginTop: '0.75rem', fontSize: '0.8rem', borderTop: '1px dashed var(--border-subtle)', paddingTop: '0.75rem' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Date d'Effet :</span>{' '}
              <strong style={{ color: '#fff' }}>{quote.date_effet || 'N/A'}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Date d'Expiration :</span>{' '}
              <strong style={{ color: '#fff' }}>{quote.date_expiration || 'N/A'}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>FGA + CEDEAO :</span>{' '}
              <strong style={{ color: '#fff' }}>{(Number(quote.fga || 0) + Number(quote.cedeao || 0)).toLocaleString()} FCFA</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Commission Apporteur :</span>{' '}
              <strong style={{ color: '#38bdf8' }}>{Number(quote.commission || 0).toLocaleString()} FCFA</strong>
            </div>
          </div>
        </div>

        {/* Branch Specific Technical Details */}
        {Object.keys(details).length > 0 && (
          <div className="glass-panel" style={{ padding: '1.25rem' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.75rem', textTransform: 'uppercase' }}>
              Détails & Paramètres Techniques ({quote.branche})
            </div>

            {/* Automobile Details */}
            {quote.branche === 'Auto' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.85rem' }}>
                <div><strong>Immatriculation :</strong> {details.immatriculation || 'Non renseignée'}</div>
                <div><strong>Genre / Usage :</strong> {details.genre || 'Véhicule Particulier'}</div>
                <div><strong>Marque & Modèle :</strong> {details.marque} {details.modele}</div>
                <div><strong>Puissance Fiscale :</strong> {details.puissanceFiscale} CV ({details.energie})</div>
                <div><strong>Valeur Vénale :</strong> {Number(details.valeurVenale || 0).toLocaleString()} FCFA</div>
                <div><strong>Durée de contrat :</strong> {details.dureeMois || 12} Mois</div>
                {details.guarantees && (
                  <div style={{ gridColumn: 'span 2', marginTop: '0.5rem' }}>
                    <strong style={{ display: 'block', marginBottom: '0.35rem' }}>Garanties souscrites :</strong>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                      {Object.entries(details.guarantees)
                        .filter(([_, active]) => active)
                        .map(([key]) => (
                          <span key={key} style={{ padding: '0.2rem 0.5rem', borderRadius: '4px', background: 'rgba(59,130,246,0.15)', color: '#60a5fa', fontSize: '0.75rem' }}>
                            {key.replace(/_/g, ' ').toUpperCase()}
                          </span>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* MRH Details */}
            {quote.branche === 'MRH' && details.maisons && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.85rem' }}>
                {details.maisons.map((m, idx) => (
                  <div key={idx} style={{ padding: '0.65rem', borderRadius: '6px', background: 'var(--surface-sunken)' }}>
                    <strong>Logement #{idx + 1} - {m.description}</strong> ({m.code_usage}) :
                    Bâtiment : {Number(m.valeur_batiment || 0).toLocaleString()} FCFA •
                    Contenu : {Number(m.valeur_contenu || 0).toLocaleString()} FCFA
                    {m.presence_gardien && ' • Gardiennage (-5%)'}
                  </div>
                ))}
              </div>
            )}

            {/* Santé Details */}
            {quote.branche === 'Santé' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.85rem' }}>
                <div><strong>Nombre total de bénéficiaires :</strong> {details.totalAssures || 0} personnes</div>
                {details.colleges && details.colleges.map((c, idx) => (
                  <div key={idx} style={{ padding: '0.6rem', borderRadius: '6px', background: 'var(--surface-sunken)' }}>
                    <strong>{c.nom}</strong> : {c.effectif} assurés • Taux de couverture : {c.taux_couverture} • Prime/tête : {Number(c.prime_par_tete || 0).toLocaleString()} FCFA
                  </div>
                ))}
              </div>
            )}

            {/* IA Details */}
            {quote.branche === 'IA' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.85rem' }}>
                <div><strong>Classe Professionnelle :</strong> {details.classeProfessionnelle}</div>
                <div><strong>Capital Décès :</strong> {Number(details.capitalDeces || 0).toLocaleString()} FCFA</div>
                <div><strong>Capital Invalidité (IPT) :</strong> {Number(details.capitalIpt || 0).toLocaleString()} FCFA</div>
                <div><strong>Frais Médicaux :</strong> {Number(details.fraisMedicaux || 0).toLocaleString()} FCFA</div>
              </div>
            )}

            {/* Voyage Details */}
            {quote.branche === 'Voyage' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.85rem' }}>
                <div><strong>Destination :</strong> {details.paysDestination || 'Espace Schengen'} ({details.zone})</div>
                <div><strong>Formule :</strong> {details.formule}</div>
                <div><strong>Période :</strong> Du {details.dateDepart} au {details.dateRetour} ({details.daysCount} jours)</div>
                <div><strong>Plafond Médical :</strong> {details.plafondFraisMedicaux || '30 000 €'}</div>
                {details.voyageurs && (
                  <div style={{ gridColumn: 'span 2', marginTop: '0.5rem' }}>
                    <strong>Voyageurs assurés ({details.voyageurs.length}) :</strong>
                    <ul style={{ margin: '0.3rem 0 0 1.25rem', padding: 0 }}>
                      {details.voyageurs.map((v, i) => (
                        <li key={i}>{v.nom} {v.prenom} (Né(e) le {v.dateNaissance}, Pass: {v.passeport || 'N/A'})</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Transport Details */}
            {quote.branche === 'Transport' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.85rem' }}>
                <div><strong>Mode de Transport :</strong> {details.modeTransport}</div>
                <div><strong>Catégorie de Marchandise :</strong> {details.natureMarchandise}</div>
                <div><strong>Incoterm :</strong> {details.incoterm}</div>
                <div><strong>Garantie :</strong> {details.typeGarantie}</div>
                <div><strong>Trajet :</strong> De {details.portDepart} à {details.portArrivee}</div>
                <div><strong>N° Connaissement / B/L :</strong> {details.numeroBlLta || 'En cours'}</div>
                <div><strong>Navire / Vol :</strong> {details.nomNavireVol}</div>
                <div><strong>Somme Totale Assurée :</strong> {Number(details.sommeAssuree || 0).toLocaleString()} FCFA</div>
              </div>
            )}
          </div>
        )}

        {/* Modal Actions */}
        <div
          className="no-print"
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            paddingTop: '1rem',
            borderTop: '1px solid var(--border-subtle)',
            flexWrap: 'wrap',
            gap: '0.75rem',
          }}
        >
          <button className="btn btn-secondary" onClick={onClose}>
            Fermer
          </button>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => printQuoteFacture(quote)}
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <Printer size={15} />
              <span>Imprimer Facture Proforma</span>
            </button>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => printConditionsParticulieres(quote)}
              title="Échéancier de police détaillé (véhicule + tableau des garanties)"
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <FileText size={15} />
              <span>Imprimer Conditions Particulières</span>
            </button>

            {!isConsolidated && onConvertToContract && (
              (() => {
                const todayStr = new Date().toISOString().split('T')[0];
                const isExpired = quote.date_expiration ? new Date(quote.date_expiration) < new Date(todayStr) : false;
                const isPendingApproval = quote.circuit_approbation && quote.circuit_approbation.statut_validation === 'EN_ATTENTE_DIRECTION';

                return (
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={isExpired || isPendingApproval}
                    onClick={() => {
                      onClose();
                      onConvertToContract(quote);
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.4rem',
                      backgroundColor: (isExpired || isPendingApproval) ? '#475569' : '#059669',
                      cursor: (isExpired || isPendingApproval) ? 'not-allowed' : 'pointer',
                    }}
                    title={
                      isExpired
                        ? 'Devis expiré : conversion bloquée (CA-07.3)'
                        : isPendingApproval
                        ? 'En attente d\'approbation de la dérogation (CA-07.4)'
                        : 'Transformer en police d\'assurance (E08)'
                    }
                  >
                    <CheckCircle size={15} />
                    <span>
                      {isExpired
                        ? 'Devis Expiré (Non transformable)'
                        : isPendingApproval
                        ? 'Visa Direction Requis'
                        : 'Transformer en Police CIMA'}
                    </span>
                  </button>
                );
              })()
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
};

export default ViewQuoteModal;
