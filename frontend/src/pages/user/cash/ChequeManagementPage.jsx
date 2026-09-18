import React, { useState, useEffect } from 'react';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Receipt, CheckCircle, AlertTriangle } from 'lucide-react';
import { cashApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';

export const ChequeManagementPage = () => {
  const { success, error } = useToast();
  const [cheques, setCheques] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchCheques = async () => {
      setIsLoading(true);
      try {
        const data = await cashApi.getCheques();
        if (isMounted && data && Array.isArray(data)) {
          const normalized = data.map((ch) => ({
            id: ch.id_cheque || ch.idcheque || ch.id,
            numero: ch.numero_cheque || ch.numerocheque || ch.numero || 'CHQ-0000',
            banque: ch.nom_banque || ch.banque || 'Banque Partenaire',
            tireur: ch.tireur || ch.emetteur || ch.nom_emetteur || 'Assuré LE PHARE',
            montant: Number(ch.montant_initial || ch.montant || 0),
            date_reception: ch.date_saisie ? ch.date_saisie.split('T')[0] : (ch.date_reception || new Date().toISOString().split('T')[0]),
            statut: Number(ch.solde_disponible) === 0 ? 'Encaissé' : 'En attente compensation',
            statut_badge: Number(ch.solde_disponible) === 0 ? 'emerald' : 'amber',
          }));
          setCheques(normalized);
        }
      } catch (err) {
        console.error('Erreur chargement chèques Django:', err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };
    fetchCheques();
    return () => { isMounted = false; };
  }, []);

  const validerEncaissement = (id) => {
    setCheques(cheques.map((c) => (c.id === id ? { ...c, statut: 'Encaissé', statut_badge: 'emerald' } : c)));
    success('Chèque marqué comme encaissé en banque.');
  };

  const declarerImpaye = (id) => {
    setCheques(cheques.map((c) => (c.id === id ? { ...c, statut: 'Rejeté / Impayé', statut_badge: 'rose' } : c)));
    error('Alerte : Chèque marqué comme impayé !');
  };

  const columns = [
    { header: 'N° Chèque', accessor: 'numero', render: (row) => <strong style={{ color: '#fff', fontFamily: 'var(--font-mono)' }}>{row.numero}</strong> },
    { header: 'Banque', accessor: 'banque' },
    { header: 'Tireur / Émetteur', accessor: 'tireur' },
    { header: 'Date Dépôt', accessor: 'date_reception' },
    {
      header: 'Montant',
      accessor: 'montant',
      render: (row) => <strong style={{ color: '#34d399' }}>{row.montant.toLocaleString()} FCFA</strong>,
    },
    {
      header: 'Statut Bancaire',
      accessor: 'statut',
      render: (row) => <StatusBadge label={row.statut} color={row.statut_badge} />,
    },
    {
      header: 'Actions',
      render: (row) => (
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          {row.statut === 'En attente compensation' && (
            <>
              <button
                className="btn btn-secondary"
                style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', color: '#34d399' }}
                onClick={() => validerEncaissement(row.id)}
              >
                <CheckCircle size={14} /> Encaisser
              </button>
              <button
                className="btn btn-danger"
                style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                onClick={() => declarerImpaye(row.id)}
              >
                <AlertTriangle size={14} /> Impayé
              </button>
            </>
          )}
        </div>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div>
        <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <Receipt size={26} color="#fbbf24" />
          Portefeuille des Chèques & Rapprochement Bancaire
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          Suivi du statut de compensation, encaissements certifiés et gestion des rejets pour provisions insuffisantes.
        </p>
      </div>

      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <DataTable columns={columns} data={cheques} searchPlaceholder="Rechercher par n° de chèque, tireur ou banque..." />
      </div>
    </div>
  );
};

export default ChequeManagementPage;
