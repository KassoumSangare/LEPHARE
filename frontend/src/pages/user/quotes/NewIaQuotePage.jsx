import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { dataStore } from '../../../api/dataStore';
import { quoteApi, customerApi, settingsApi, contractApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { UserPlus, ArrowLeft, Check, Shield, Plus } from 'lucide-react';
import { ViewQuoteModal } from './ViewQuoteModal';
import { QuickAddClientModal } from '../clients/QuickAddClientModal';
import { sortUniqueBy } from '../../../utils/sortUtils';
import { AmountInput } from '../../../components/common/AmountInput';

export const NewIaQuotePage = () => {
  const navigate = useNavigate();
  const { success } = useToast();

  const [createdQuote, setCreatedQuote] = useState(null);
  const [isQuickAddClientOpen, setIsQuickAddClientOpen] = useState(false);
  const [clients, setClients] = useState([]);
  const [companies, setCompanies] = useState(() => dataStore.getActiveCompanies('IA'));

  useEffect(() => {
    let isMounted = true;
    const loadRealRefs = async () => {
      try {
        const [cls, cies] = await Promise.all([
          customerApi.getClients().catch(() => []),
          settingsApi.getCompanies().catch(() => []),
        ]);
        if (isMounted) {
          if (cls && cls.length > 0) {
            setClients(cls);
            setClientId(cls[0].id);
          }
          if (cies && cies.length > 0) {
            const mappedCies = cies.map((c) => ({ id: c.id || c.IdCompagnie, nom: c.RaisonSociale || c.nom }));
            setCompanies(mappedCies);
            setCompagnie(mappedCies[0].nom);
          }
        }
      } catch (err) {
        console.error('Erreur chargement clients/compagnies Django:', err);
      }
    };
    loadRealRefs();
    return () => { isMounted = false; };
  }, []);

  const [clientId, setClientId] = useState(() => clients[0]?.id || 1);
  const [compagnie, setCompagnie] = useState(() => companies[0]?.nom || 'NSIA Assurances Côte d’Ivoire');
  const [classeProfessionnelle, setClasseProfessionnelle] = useState('Classe 1 (Sédentaire/Bureautique)');
  const [capitalDeces, setCapitalDeces] = useState(10000000);
  const [capitalIpt, setCapitalIpt] = useState(10000000);
  const [fraisMedicaux, setFraisMedicaux] = useState(1000000);

  const calculatePrime = () => {
    let tauxBase = 0.0025; // Classe 1
    if (classeProfessionnelle.includes('Classe 2')) tauxBase = 0.004;
    if (classeProfessionnelle.includes('Classe 3')) tauxBase = 0.007;

    const primeDeces = capitalDeces * tauxBase;
    const primeIpt = capitalIpt * tauxBase;
    const primeFrais = fraisMedicaux * 0.05;
    const primeNette = Math.round(primeDeces + primeIpt + primeFrais);
    const tarif = dataStore.getTarifForBranch('IA');
    const accessoires = tarif.accessoires;
    const taxes = Math.round(primeNette * tarif.taxRate);
    const primeTotale = primeNette + accessoires + taxes;

    return { primeNette, accessoires, taxes, primeTotale };
  };

  const totals = calculatePrime();

  const handleSave = async () => {
    const selectedClient = clients.find((c) => c.id === clientId) || clients[0];
    const newQuote = {
      client_nom: selectedClient?.nomcomplet || 'Assuré LE PHARE',
      client_id: selectedClient?.id,
      produit: `Individuelle Accident (${classeProfessionnelle.split(' ')[0]})`,
      branche: 'IA',
      compagnie: compagnie,
      prime_nette: totals.primeNette,
      accessoires: totals.accessoires,
      taxes: totals.taxes,
      prime_totale: totals.primeTotale,
      date_emission: new Date().toISOString().split('T')[0],
      statut: 'En attente',
      statut_badge: 'amber',
      details: {
        classeProfessionnelle,
        capitalDeces,
        capitalIpt,
        fraisMedicaux,
      },
    };

    const saved = dataStore.saveQuote(newQuote);
    try {
      await quoteApi.createIaQuote(saved);
    } catch (e) {
      console.warn('API IA fallback to dataStore');
    }

    success(`Devis Individuelle Accident ${saved.numerodevis} créé avec succès !`);
    setCreatedQuote(saved);
  };

  const handleConvertToContract = async (quoteToConvert) => {
    try {
      await contractApi.createContractFromQuote(quoteToConvert.id);
    } catch (e) {
      console.warn('Fallback contract creation');
    }
    const newContract = dataStore.convertQuoteToContract(quoteToConvert);
    success(`Devis ${quoteToConvert.numerodevis} transformé en police d'assurance avec succès !`);
    setCreatedQuote(null);
    navigate(`/user/contracts/${newContract.id || newContract.numeropolice}`);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '900px', margin: '0 auto' }}>
      <div>
        <button className="btn btn-secondary" onClick={() => navigate('/user/quotes')} style={{ padding: '0.35rem 0.75rem', marginBottom: '0.5rem' }}>
          <ArrowLeft size={16} /> Retour aux devis
        </button>
        <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <UserPlus size={26} color="#8b5cf6" />
          Nouveau Devis Individuelle Accident (IA)
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          Garanties Décès accidentel, Invalidité Permanente Partielle ou Totale, et Frais de Traitement.
        </p>
      </div>

      <div className="glass-panel" style={{ padding: '1.75rem' }}>
          <div className="responsive-form-row">
            <div className="form-group">
              <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Souscripteur / Assuré</span>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Nouveau ? Cliquez sur +</span>
              </label>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <select className="form-control" value={clientId} onChange={(e) => setClientId(parseInt(e.target.value))} style={{ flex: 1 }}>
                  {sortUniqueBy(clients, (c) => c.nomcomplet).map((c) => (
                    <option key={c.id} value={c.id}>{c.nomcomplet} ({c.profession})</option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setIsQuickAddClientOpen(true)}
                  style={{
                    padding: '0.6rem 0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.35rem',
                    background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
                    borderRadius: 'var(--radius-md)',
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                  title="Enregistrer un nouveau client souscripteur"
                >
                  <Plus size={18} />
                  <span style={{ fontSize: '0.85rem' }}>Nouveau</span>
                </button>
              </div>
            </div>
          <div className="form-group">
            <label className="form-label">Compagnie d'Assurance</label>
            <select className="form-control" value={compagnie} onChange={(e) => setCompagnie(e.target.value)}>
              {sortUniqueBy(companies, (c) => c.nom).map((c) => (
                <option key={c.id || c.code} value={c.nom}>
                  {c.nom}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Classe de Risque Professionnel</label>
          <select className="form-control" value={classeProfessionnelle} onChange={(e) => setClasseProfessionnelle(e.target.value)}>
            <option value="Classe 1 (Sédentaire/Bureautique)">Classe 1 : Travail de bureau, administratif, enseignement</option>
            <option value="Classe 2 (Commercial/Déplacement)">Classe 2 : Commerciaux, chauffeurs VP, techniciens légers</option>
            <option value="Classe 3 (Manuel/Chantier)">Classe 3 : Ouvriers BTP, dockers, manutention lourde</option>
          </select>
        </div>

        <div className="responsive-form-row-3" style={{ marginTop: '1rem' }}>
          <div className="form-group">
            <label className="form-label">Capital Décès Accidentel</label>
            <AmountInput value={capitalDeces} onChange={setCapitalDeces} />
          </div>
          <div className="form-group">
            <label className="form-label">Capital Invalidité (IPT)</label>
            <AmountInput value={capitalIpt} onChange={setCapitalIpt} />
          </div>
          <div className="form-group">
            <label className="form-label">Remboursement Frais Médicaux</label>
            <AmountInput value={fraisMedicaux} onChange={setFraisMedicaux} />
          </div>
        </div>

        {/* Breakdown box */}
        <div style={{ marginTop: '1.5rem', padding: '1.25rem', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
            <span className="text-muted">Prime Nette :</span>
            <strong style={{ color: '#60a5fa' }}>{totals.primeNette.toLocaleString('fr-FR')} FCFA</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
            <span className="text-muted">Accessoires & Taxes :</span>
            <span>{(totals.accessoires + totals.taxes).toLocaleString('fr-FR')} FCFA</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '1.1rem', fontWeight: 800, color: '#34d399', paddingTop: '0.5rem', borderTop: '1px solid var(--border-subtle)' }}>
            <span>Prime Globale TTC :</span>
            <span>{totals.primeTotale.toLocaleString('fr-FR')} FCFA</span>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
          <button className="btn btn-primary" onClick={handleSave} style={{ padding: '0.75rem 1.5rem' }}>
            <Check size={18} />
            Enregistrer le Devis IA
          </button>
        </div>
      </div>

      {createdQuote && (
        <ViewQuoteModal
          isOpen={Boolean(createdQuote)}
          quote={createdQuote}
          onClose={() => {
            setCreatedQuote(null);
            navigate('/user/quotes');
          }}
          onConvertToContract={handleConvertToContract}
        />
      )}

      {/* Modal d'ajout complet de client */}
      <QuickAddClientModal
        isOpen={isQuickAddClientOpen}
        onClose={() => setIsQuickAddClientOpen(false)}
        onClientCreated={(newClient) => {
          setClients((prev) => [newClient, ...prev]);
          setClientId(newClient.id || newClient.IdClient);
        }}
      />
    </div>
  );
};

export default NewIaQuotePage;
