import React, { useState, useEffect } from 'react';
import { DataTable } from '../../../components/common/DataTable';
import { Modal } from '../../../components/common/Modal';
import { TrendingUp, Download, Calendar, FileText, Printer, Check, Filter, Loader2, RefreshCw } from 'lucide-react';
import { useToast } from '../../../context/ToastContext';
import { exportToCsv, exportToExcel, exportToPdf } from '../../../utils/exportUtils';
import { reportingApi } from '../../../api/endpoints';

export const EmissionSummaryPage = () => {
  const { success, error: toastError } = useToast();
  const [showExportModal, setShowExportModal] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState(null);
  const [exportFormat, setExportFormat] = useState('PDF');
  const [exportScope, setExportScope] = useState('ALL');

  const [dateDebut, setDateDebut] = useState('2020-01-01');
  const [dateFin, setDateFin] = useState('2026-12-31');
  const [loading, setLoading] = useState(true);
  const [emissions, setEmissions] = useState([]);
  const [rawRecords, setRawRecords] = useState([]);

  const fetchEmissions = async () => {
    try {
      setLoading(true);
      const data = await reportingApi.getBordereauRecapEmission({
        date_debut: dateDebut,
        date_fin: dateFin,
        type_etat: 1,
      });

      if (Array.isArray(data)) {
        setRawRecords(data);
        const groups = {};
        data.forEach((item) => {
          const d = item.date_emission ? new Date(item.date_emission) : new Date();
          const monthKey = !isNaN(d.getTime())
            ? d.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })
            : 'Période 2026';
          const capitalizedMonth = monthKey.charAt(0).toUpperCase() + monthKey.slice(1);

          if (!groups[capitalizedMonth]) {
            groups[capitalizedMonth] = {
              id: capitalizedMonth,
              mois: capitalizedMonth,
              nombre_polices: 0,
              prime_nette: 0,
              accessoires: 0,
              taxes: 0,
              prime_totale: 0,
              branches: {},
            };
          }
          const pNette = parseFloat(item.prime_nette || 0);
          const pAcc = parseFloat(item.accessoire || 0);
          const pTaxe = parseFloat(item.taxe || 0);
          const pTtc = parseFloat(item.prime_ttc || 0);

          groups[capitalizedMonth].nombre_polices += 1;
          groups[capitalizedMonth].prime_nette += pNette;
          groups[capitalizedMonth].accessoires += pAcc;
          groups[capitalizedMonth].taxes += pTaxe;
          groups[capitalizedMonth].prime_totale += pTtc;

          const prod = item.libelle_produit || 'Automobile';
          groups[capitalizedMonth].branches[prod] = (groups[capitalizedMonth].branches[prod] || 0) + 1;
        });

        const list = Object.values(groups);
        setEmissions(list);
      }
    } catch (err) {
      console.error('Erreur chargement bordereau recap emission:', err);
      toastError?.('Erreur lors du chargement des émissions réelles.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmissions();
  }, [dateDebut, dateFin]);

  const handleExecuteExport = (e) => {
    e.preventDefault();

    let filteredData = [...emissions];
    let scopeLabel = `Exercice Réel (${dateDebut} au ${dateFin})`;
    if (exportScope === 'S1') {
      filteredData = emissions.slice(0, 6);
      scopeLabel = 'Semestre 1';
    } else if (exportScope === 'T1') {
      filteredData = emissions.slice(0, 3);
      scopeLabel = 'Premier Trimestre (T1)';
    } else if (exportScope === 'LAST') {
      filteredData = emissions.slice(-1);
      scopeLabel = 'Dernier Mois Clôturé';
    }

    const headers = [
      'Période / Mois',
      'Polices Émises',
      'Prime Nette (FCFA)',
      'Accessoires (FCFA)',
      'Taxes d’Assurance (FCFA)',
      'Prime Totale TTC (FCFA)',
    ];

    const rows = filteredData.map((r) => [
      r.mois,
      r.nombre_polices,
      `${Math.round(r.prime_nette).toLocaleString()} FCFA`,
      `${Math.round(r.accessoires).toLocaleString()} FCFA`,
      `${Math.round(r.taxes).toLocaleString()} FCFA`,
      `${Math.round(r.prime_totale).toLocaleString()} FCFA`,
    ]);

    const totPolices = filteredData.reduce((acc, r) => acc + (r.nombre_polices || 0), 0);
    const totNette = filteredData.reduce((acc, r) => acc + (r.prime_nette || 0), 0);
    const totAccessoires = filteredData.reduce((acc, r) => acc + (r.accessoires || 0), 0);
    const totTaxes = filteredData.reduce((acc, r) => acc + (r.taxes || 0), 0);
    const totTtc = filteredData.reduce((acc, r) => acc + (r.prime_totale || 0), 0);

    const totals = [
      'TOTAL CONSOLIDÉ',
      totPolices,
      `${Math.round(totNette).toLocaleString()} FCFA`,
      `${Math.round(totAccessoires).toLocaleString()} FCFA`,
      `${Math.round(totTaxes).toLocaleString()} FCFA`,
      `${Math.round(totTtc).toLocaleString()} FCFA`,
    ];

    const filename = `Bordereau_Emissions_${exportScope}`;
    const title = 'BORDEREAU RÉCAPITULATIF DES ÉMISSIONS';
    const subtitle = `Synthèse périodique certifiée conforme - ${scopeLabel}`;
    const metadata = {
      'Organisme Émetteur': 'LE PHARE COURTAGE & GESTION D\'ASSURANCES',
      'Exercice Fiscal': '2026',
      'Périmètre de l\'État': scopeLabel,
      'Conformité Réglementaire': 'Code CIMA - Articles 13 et suivants (CRCA)',
      'Date d\'Édition': new Date().toLocaleDateString('fr-FR'),
      'Polices Consolidées': `${totPolices} polices`,
    };

    if (exportFormat === 'CSV') {
      exportToCsv({ filename, title, metadata, headers, rows, totals });
    } else if (exportFormat === 'XLSX') {
      exportToExcel({ filename, title, subtitle, metadata, headers, rows, totals });
    } else {
      exportToPdf({ filename, title, subtitle, metadata, headers, rows, totals });
    }

    success(`Bordereau des émissions (${exportFormat}) téléchargé avec succès.`);
    setShowExportModal(false);
  };

  const columns = [
    { header: 'Période / Mois', accessor: 'mois', render: (r) => <strong style={{ color: '#fff' }}>{r.mois}</strong> },
    { header: 'Polices Émises', accessor: 'nombre_polices', render: (r) => <span style={{ color: '#60a5fa', fontWeight: 600 }}>{r.nombre_polices}</span> },
    { header: 'Prime Nette (FCFA)', render: (r) => <span>{Math.round(r.prime_nette || 0).toLocaleString()} F</span> },
    { header: 'Accessoires (FCFA)', render: (r) => <span style={{ color: '#fbbf24' }}>{Math.round(r.accessoires || 0).toLocaleString()} F</span> },
    { header: 'Taxes d’Assurance (FCFA)', render: (r) => <span style={{ color: '#c084fc' }}>{Math.round(r.taxes || 0).toLocaleString()} F</span> },
    {
      header: 'Prime Totale TTC (FCFA)',
      render: (r) => <strong style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>{Math.round(r.prime_totale || 0).toLocaleString()} F</strong>,
    },
    {
      header: 'Actions',
      render: (r) => (
        <button
          className="btn btn-secondary"
          style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
          onClick={() => setSelectedPeriod(r)}
        >
          <FileText size={13} />
          <span>Ventilation</span>
        </button>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <span className="badge badge-success">Production & Émissions Réelles</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Conformité Fiscale & CIMA (Django Backend)</span>
          </div>
          <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <TrendingUp size={26} color="#34d399" />
            Bordereau Récapitulatif des Émissions
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Synthèse consolidée en temps réel depuis les contrats et quittances enregistrés dans Uranus.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button
            className="btn btn-secondary"
            onClick={fetchEmissions}
            disabled={loading}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            <span>Actualiser</span>
          </button>
          <button className="btn btn-primary" onClick={() => setShowExportModal(true)} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Download size={16} />
            <span>Exporter le Bordereau</span>
          </button>
        </div>
      </div>

      {/* Barre de filtres de dates */}
      <div className="glass-panel" style={{ padding: '1rem 1.5rem', display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Calendar size={16} color="var(--text-muted)" />
          <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Du :</span>
          <input
            type="date"
            className="form-control"
            style={{ padding: '0.35rem 0.6rem', fontSize: '0.85rem', width: 'auto' }}
            value={dateDebut}
            onChange={(e) => setDateDebut(e.target.value)}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Au :</span>
          <input
            type="date"
            className="form-control"
            style={{ padding: '0.35rem 0.6rem', fontSize: '0.85rem', width: 'auto' }}
            value={dateFin}
            onChange={(e) => setDateFin(e.target.value)}
          />
        </div>

        <div style={{ marginLeft: 'auto', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Total contrats consolidés : <strong style={{ color: '#60a5fa' }}>{rawRecords.length}</strong>
        </div>
      </div>

      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '3rem', gap: '0.75rem', color: 'var(--text-muted)' }}>
            <Loader2 size={24} className="animate-spin" />
            <span>Calcul du bordereau des émissions en direct...</span>
          </div>
        ) : (
          <DataTable columns={columns} data={emissions} searchPlaceholder="Filtrer un mois..." />
        )}
      </div>

      {/* Modal Ventilation par Branche */}
      <Modal
        isOpen={Boolean(selectedPeriod)}
        onClose={() => setSelectedPeriod(null)}
        title={`Bordereau Détaillé d'Émission : ${selectedPeriod?.mois}`}
        subtitle="Décomposition de la production par branche d'assurance et quote-part fiscale."
        maxWidth="620px"
      >
        {selectedPeriod && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div style={{ background: 'var(--bg-surface)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.85rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Nombre total de contrats émis :</span>
                <strong style={{ color: '#60a5fa' }}>{selectedPeriod.nombre_polices} polices</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Primes Nettes Hors Taxes :</span>
                <strong>{Math.round(selectedPeriod.prime_nette || 0).toLocaleString()} FCFA</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Accessoires de Compagnie & Frais :</span>
                <span style={{ color: '#fbbf24' }}>{Math.round(selectedPeriod.accessoires || 0).toLocaleString()} FCFA</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Taxes sur Contrats d'Assurances (TCA + FGA) :</span>
                <span style={{ color: '#c084fc' }}>{Math.round(selectedPeriod.taxes || 0).toLocaleString()} FCFA</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '2px solid var(--border-color)', paddingTop: '0.5rem', fontSize: '1.05rem' }}>
                <span style={{ fontWeight: 700 }}>Total Primes TTC Émises :</span>
                <strong style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>{Math.round(selectedPeriod.prime_totale || 0).toLocaleString()} FCFA</strong>
              </div>
            </div>

            <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.02)', padding: '0.85rem', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
              <strong>Ventilation par Branche & Produit :</strong>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginTop: '0.5rem' }}>
                {Object.entries(selectedPeriod.branches || {}).map(([branche, count]) => (
                  <div key={branche}>
                    • {branche} : <strong>{count} polices ({Math.round((count / selectedPeriod.nombre_polices) * 100)}%)</strong>
                  </div>
                ))}
              </div>
            </div>

            <div className="no-print" style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
              <button className="btn btn-secondary" onClick={() => setSelectedPeriod(null)}>
                Fermer
              </button>
              <button className="btn btn-primary" onClick={() => window.print()} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Printer size={15} />
                <span>Imprimer l'État Mensuel</span>
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Modal Exportation du Bordereau */}
      <Modal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        title="Exporter le Bordereau Récapitulatif des Émissions"
        subtitle="Génération d'un état certifié conforme pour la comptabilité et la tutelle CIMA."
        maxWidth="520px"
      >
        <form onSubmit={handleExecuteExport} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="form-group">
            <label className="form-label">Format de Sortie *</label>
            <select
              className="form-control"
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value)}
            >
              <option value="PDF">Document PDF Officiel Certifié</option>
              <option value="XLSX">Classeur Microsoft Excel (.xlsx)</option>
              <option value="CSV">Format CSV Délimité (Export Comptable)</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Périmètre de l'État</label>
            <select
              className="form-control"
              value={exportScope}
              onChange={(e) => setExportScope(e.target.value)}
            >
              <option value="ALL">Période Complète ({dateDebut} au {dateFin})</option>
              <option value="S1">Semestre 1 (Janvier à Juin)</option>
              <option value="T1">Premier Trimestre (T1)</option>
              <option value="LAST">Dernier Mois Clôturé</option>
            </select>
          </div>

          <div style={{ background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.2)', padding: '0.85rem', borderRadius: '6px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Le document intègre l'ensemble des polices validées, les quittances émises et la décomposition de la taxe sur la valeur ajoutée et TCA exigibles.
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setShowExportModal(false)}>
              Annuler
            </button>
            <button type="submit" className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Download size={15} />
              <span>Télécharger l'Export</span>
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default EmissionSummaryPage;
