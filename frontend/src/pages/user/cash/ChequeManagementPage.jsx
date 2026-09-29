import React, { useState, useEffect } from 'react';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { Receipt } from 'lucide-react';
import { cashApi } from '../../../api/endpoints';
import { formatDate } from '../../../utils/dateUtils';

const fcfa = (v) => `${Math.round(Number(v) || 0).toLocaleString('fr-FR')} F`;

// Chèques reçus en caisse (stdcheque) : un chèque peut régler plusieurs quittances, son solde
// disponible est la part pas encore affectée. La base ne suit pas la remise en banque ni les
// impayés : pas de statut bancaire ici.
export const ChequeManagementPage = () => {
  const [cheques, setCheques] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchCheques = async () => {
      setIsLoading(true);
      try {
        const data = await cashApi.getCheques();
        if (isMounted && Array.isArray(data)) {
          setCheques(data.map((ch) => {
            const montant = Number(ch.montant_initial) || 0;
            const solde = Number(ch.solde_disponible) || 0;
            const affecte = montant - solde;
            return {
              id: ch.id_cheque,
              numero: ch.numero_cheque,
              banque: ch.nom_banque,
              date_saisie: ch.date_saisie,
              montant,
              affecte,
              solde,
              quittances: ch.quittances_reglees || '',
              clients: ch.clients || '',
              utilisation: solde === 0 ? 'Épuisé' : affecte > 0 ? 'Partiellement affecté' : 'Non affecté',
              utilisation_badge: solde === 0 ? 'emerald' : affecte > 0 ? 'amber' : 'rose',
              // Clés lues par la recherche du DataTable : client puis n° de chèque
              client_nom: ch.clients || '',
              police: ch.numero_cheque,
            };
          }));
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

  const soldeTotal = cheques.reduce((s, c) => s + c.solde, 0);

  const columns = [
    { header: 'N° Chèque', accessor: 'numero', render: (row) => <strong style={{ fontFamily: 'var(--font-mono)' }}>{row.numero}</strong> },
    { header: 'Banque', accessor: 'banque' },
    { header: 'Client(s)', accessor: 'clients' },
    { header: 'Date de saisie', render: (row) => formatDate(row.date_saisie) },
    { header: 'Montant du chèque', render: (row) => <strong>{fcfa(row.montant)}</strong> },
    { header: 'Affecté', render: (row) => <span style={{ color: '#34d399' }}>{fcfa(row.affecte)}</span> },
    { header: 'Solde disponible', render: (row) => <span style={{ color: row.solde > 0 ? '#fbbf24' : 'var(--text-muted)' }}>{fcfa(row.solde)}</span> },
    { header: 'Quittance(s) réglée(s)', accessor: 'quittances', render: (row) => <span style={{ fontFamily: 'var(--font-mono)' }}>{row.quittances || '—'}</span> },
    {
      header: 'Utilisation',
      accessor: 'utilisation',
      render: (row) => <StatusBadge label={row.utilisation} color={row.utilisation_badge} />,
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
          Chèques reçus en caisse, quittances qu'ils ont réglées et solde encore disponible sur chaque chèque.
        </p>
      </div>

      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        {!isLoading && (
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>
            <strong>{cheques.length}</strong> chèque{cheques.length > 1 ? 's' : ''} enregistré{cheques.length > 1 ? 's' : ''} ·
            solde disponible total <strong>{fcfa(soldeTotal)}</strong>
          </p>
        )}
        <DataTable columns={columns} data={cheques} loading={isLoading} searchPlaceholder="Rechercher par client ou n° de chèque..." />
      </div>
    </div>
  );
};

export default ChequeManagementPage;
