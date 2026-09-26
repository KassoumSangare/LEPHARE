import React, { useState, useEffect } from 'react';
import { Modal } from '../../../components/common/Modal';
import { Users, Phone, Mail, Banknote, Calendar, Briefcase, Award, Save } from 'lucide-react';
import { trierParLibelle } from '../../../utils/sortUtils';

const BRANCHES = [
  'Automobile',
  'Flotte Auto',
  'Santé Groupe',
  'IARD',
  'Multirisque Habitation',
  'Multirisque Entreprise',
  'Vie',
  'Transport',
];

const STAGES = [
  { id: 'Nouveau', label: 'Prospects Entrants' },
  { id: 'Qualifié', label: 'Besoins Qualifiés' },
  { id: 'Proposition', label: 'Proposition Émise' },
  { id: 'Négociation', label: 'Négociation & Clôture' },
  { id: 'Gagné', label: 'Affaires Gagnées' },
];

export const EditLeadModal = ({ isOpen, onClose, lead, onSave }) => {
  const [formData, setFormData] = useState({
    nom_prospect: '',
    contact: '',
    telephone: '',
    email: '',
    branche: 'Automobile',
    prime_estimee: 0,
    statut: 'Nouveau',
    commercial_attribue: 'Koffi Serge',
    prochaine_action: '',
    date_action: '',
    probabilite: 50,
  });

  useEffect(() => {
    if (lead) {
      setFormData({
        nom_prospect: lead.nom_prospect || '',
        contact: lead.contact || '',
        telephone: lead.telephone || '',
        email: lead.email || '',
        branche: lead.branche || 'Automobile',
        prime_estimee: lead.prime_estimee || 0,
        statut: lead.statut || 'Nouveau',
        commercial_attribue: lead.commercial_attribue || 'Koffi Serge',
        prochaine_action: lead.prochaine_action || '',
        date_action: lead.date_action || '',
        probabilite: lead.probabilite || 50,
      });
    }
  }, [lead]);

  if (!isOpen || !lead) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(lead.id || lead.id_lead, {
      ...formData,
      prime_estimee: Number(formData.prime_estimee) || 0,
      probabilite: Number(formData.probabilite) || 50,
    });
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Modifier le Prospect [${lead.id_lead || lead.id}]`}
      size="medium"
    >
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
          <div>
            <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Nom Prospect / Entreprise *</label>
            <div style={{ position: 'relative' }}>
              <Briefcase size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="text"
                className="form-control"
                style={{ paddingLeft: '2.25rem' }}
                required
                value={formData.nom_prospect}
                onChange={(e) => setFormData({ ...formData, nom_prospect: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Contact Interlocuteur</label>
            <div style={{ position: 'relative' }}>
              <Users size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="text"
                className="form-control"
                style={{ paddingLeft: '2.25rem' }}
                value={formData.contact}
                onChange={(e) => setFormData({ ...formData, contact: e.target.value })}
              />
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
          <div>
            <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Téléphone Direct</label>
            <div style={{ position: 'relative' }}>
              <Phone size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="text"
                className="form-control"
                style={{ paddingLeft: '2.25rem' }}
                value={formData.telephone}
                onChange={(e) => setFormData({ ...formData, telephone: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Email Professionnel</label>
            <div style={{ position: 'relative' }}>
              <Mail size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="email"
                className="form-control"
                style={{ paddingLeft: '2.25rem' }}
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              />
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
          <div>
            <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Branche d'Assurance</label>
            <select
              className="form-control"
              value={formData.branche}
              onChange={(e) => setFormData({ ...formData, branche: e.target.value })}
            >
              {trierParLibelle(BRANCHES, (b) => b).map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Étape du Pipeline</label>
            <select
              className="form-control"
              value={formData.statut}
              onChange={(e) => setFormData({ ...formData, statut: e.target.value })}
            >
              {trierParLibelle(STAGES, (s) => s.label).map((s) => (
                <option key={s.id} value={s.id}>{s.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
          <div>
            <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Prime Estimée (FCFA)</label>
            <div style={{ position: 'relative' }}>
              <Banknote size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="number"
                min="0"
                step="5000"
                className="form-control"
                style={{ paddingLeft: '2.25rem', fontFamily: 'var(--font-mono)' }}
                value={formData.prime_estimee}
                onChange={(e) => setFormData({ ...formData, prime_estimee: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Probabilité (%)</label>
            <div style={{ position: 'relative' }}>
              <Award size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="number"
                min="0"
                max="100"
                className="form-control"
                style={{ paddingLeft: '2.25rem' }}
                value={formData.probabilite}
                onChange={(e) => setFormData({ ...formData, probabilite: e.target.value })}
              />
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
          <div>
            <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Commercial Assigné</label>
            <select
              className="form-control"
              value={formData.commercial_attribue}
              onChange={(e) => setFormData({ ...formData, commercial_attribue: e.target.value })}
            >
              <option value="Awa Kone">Awa Kone</option>
              <option value="Franck Gnogouri">Franck Gnogouri</option>
              <option value="Koffi Serge">Koffi Serge</option>
              <option value="Mamadou Diarra">Mamadou Diarra</option>
            </select>
          </div>
          <div>
            <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Date Prochaine Relance</label>
            <div style={{ position: 'relative' }}>
              <Calendar size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="date"
                className="form-control"
                style={{ paddingLeft: '2.25rem' }}
                value={formData.date_action}
                onChange={(e) => setFormData({ ...formData, date_action: e.target.value })}
              />
            </div>
          </div>
        </div>

        <div>
          <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Prochaine Action Commerciale</label>
          <input
            type="text"
            className="form-control"
            placeholder="ex: Relance téléphonique suite à présentation de l'offre technique"
            value={formData.prochaine_action}
            onChange={(e) => setFormData({ ...formData, prochaine_action: e.target.value })}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Annuler
          </button>
          <button type="submit" className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Save size={16} />
            <span>Enregistrer les modifications</span>
          </button>
        </div>
      </form>
    </Modal>
  );
};
