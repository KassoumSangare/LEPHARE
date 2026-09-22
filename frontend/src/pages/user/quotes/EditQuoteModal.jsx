import React, { useState, useEffect } from 'react';
import { Modal } from '../../../components/common/Modal';
import { dataStore } from '../../../api/dataStore';
import { FileText, DollarSign, Building2, Save, Clock } from 'lucide-react';
import { sortUniqueBy } from '../../../utils/sortUtils';

export const EditQuoteModal = ({ isOpen, onClose, quote, onSave }) => {
  const [formData, setFormData] = useState({
    client_nom: '',
    produit: '',
    compagnie: '',
    prime_nette: 0,
    accessoires: 15000,
    taxes: 0,
    prime_totale: 0,
  });

  const [activeCompanies, setActiveCompanies] = useState([]);
  const [taxRate, setTaxRate] = useState(0.145);

  useEffect(() => {
    if (quote) {
      const tarif = dataStore.getTarifForBranch(quote.branche);
      const companies = dataStore.getActiveCompanies(quote.branche);
      setActiveCompanies(companies);
      setTaxRate(tarif.taxRate || 0.145);

      const pNette = Number(quote.prime_nette || 0);
      const acc = Number(quote.accessoires ?? tarif.accessoires ?? 15000);
      const taxes = Number(quote.taxes ?? Math.round(pNette * (tarif.taxRate || 0.145)));
      const pTotale = Number(quote.prime_totale || pNette + acc + taxes);

      setFormData({
        client_nom: quote.client_nom || '',
        produit: quote.produit || 'Automobile Tous Risques',
        compagnie: quote.compagnie || (companies[0]?.nom || 'NSIA Assurances'),
        prime_nette: pNette,
        accessoires: acc,
        taxes: taxes,
        prime_totale: pTotale,
      });
    }
  }, [quote]);

  if (!isOpen || !quote) return null;

  const handlePrimeNetteChange = (val) => {
    const pNette = Number(val) || 0;
    const taxes = Math.round(pNette * taxRate);
    const pTotale = pNette + formData.accessoires + taxes;
    setFormData({
      ...formData,
      prime_nette: pNette,
      taxes,
      prime_totale: pTotale,
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(quote.id, formData);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Ajuster le Devis [${quote.numerodevis}]`}
      size="medium"
    >
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {/* Bandeau de traçabilité CIMA & Horodatage */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '0.5rem',
            padding: '0.6rem 0.85rem',
            backgroundColor: 'rgba(59, 130, 246, 0.08)',
            border: '1px solid rgba(59, 130, 246, 0.2)',
            borderRadius: '6px',
            fontSize: '0.78rem',
            color: 'var(--text-secondary)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Clock size={14} color="#60a5fa" />
            <span>Émis le : <strong style={{ color: '#fff' }}>{quote.date_emission || quote.date_creation || '-'}</strong></span>
          </div>
          <div>
            <span>Dernière modification : <strong style={{ color: '#38bdf8' }}>{quote.date_derniere_modification || quote.DateMaj || quote.date_maj || 'Enregistrement initial'}</strong></span>
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
          <div>
            <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Souscripteur / Assuré</label>
            <input
              type="text"
              className="form-control"
              value={formData.client_nom}
              onChange={(e) => setFormData({ ...formData, client_nom: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Compagnie Partenaire</label>
            <select
              className="form-control"
              value={formData.compagnie}
              onChange={(e) => setFormData({ ...formData, compagnie: e.target.value })}
            >
              {sortUniqueBy(activeCompanies, (c) => c.nom).map((c) => (
                <option key={c.id || c.nom} value={c.nom}>{c.nom}</option>
              ))}
              {!activeCompanies.some((c) => c.nom === formData.compagnie) && formData.compagnie && (
                <option value={formData.compagnie}>{formData.compagnie}</option>
              )}
            </select>
          </div>
        </div>

        <div>
          <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Produit / Formule</label>
          <input
            type="text"
            className="form-control"
            value={formData.produit}
            onChange={(e) => setFormData({ ...formData, produit: e.target.value })}
            required
          />
        </div>

        <div style={{ backgroundColor: 'var(--surface-sunken)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.6rem', textTransform: 'uppercase' }}>
            Décomposition Actuarielle CIMA ({quote.branche || 'Général'})
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
            <div>
              <label className="form-label" style={{ fontSize: '0.75rem' }}>Prime Nette (FCFA)</label>
              <input
                type="number"
                className="form-control"
                value={formData.prime_nette}
                onChange={(e) => handlePrimeNetteChange(e.target.value)}
                min="0"
                step="5000"
                required
              />
            </div>
            <div>
              <label className="form-label" style={{ fontSize: '0.75rem' }}>Accessoires (FCFA)</label>
              <input
                type="number"
                className="form-control"
                value={formData.accessoires}
                onChange={(e) => {
                  const acc = Number(e.target.value) || 0;
                  setFormData({
                    ...formData,
                    accessoires: acc,
                    prime_totale: formData.prime_nette + acc + formData.taxes,
                  });
                }}
                min="0"
              />
            </div>
            <div>
              <label className="form-label" style={{ fontSize: '0.75rem' }}>
                Taxes ({(taxRate * 100).toFixed(1)}%)
              </label>
              <input
                type="text"
                className="form-control"
                value={`${formData.taxes.toLocaleString('fr-FR')} FCFA`}
                readOnly
                disabled
              />
            </div>
          </div>
          <div style={{ marginTop: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '0.5rem', borderTop: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>Prime Totale TTC :</span>
            <strong style={{ fontSize: '1.1rem', color: '#60a5fa', fontFamily: 'var(--font-mono)' }}>
              {formData.prime_totale.toLocaleString('fr-FR')} FCFA
            </strong>
          </div>
        </div>

        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '0.75rem',
            paddingTop: '0.75rem',
            borderTop: '1px solid var(--border-subtle)',
          }}
        >
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Annuler
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', backgroundColor: '#2563eb' }}
          >
            <Save size={15} />
            <span>Mettre à Jour la Proposition</span>
          </button>
        </div>
      </form>
    </Modal>
  );
};
