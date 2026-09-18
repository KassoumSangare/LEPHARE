import React, { useState, useEffect } from 'react';
import { Modal } from '../../../components/common/Modal';
import { DataTable } from '../../../components/common/DataTable';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { reportingApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { exportToPdf, exportToExcel } from '../../../utils/exportUtils';
import { GitBranch, Plus, Edit2, Trash2, RefreshCw, CheckCircle2, XCircle, Download, Eye, Printer, Calendar, Loader2 } from 'lucide-react';

const URL_OPTIONS = ['DETAIL', 'LISTE', 'VALIDATION', 'REJET', 'CLOTURE'];

const emptyForm = { code_etat: '', libelle_etat: '', url: 'DETAIL', actif: true };

const defaultDateDebut = '2020-01-01';
const defaultDateFin = new Date().toISOString().slice(0, 10);

export const DecisionalStatesPage = () => {
  const { success, error: toastError } = useToast();

  const [etats, setEtats] = useState([]);
  const [loading, setLoading] = useState(true);

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState(emptyForm);
  const [isSaving, setIsSaving] = useState(false);

  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [editForm, setEditForm] = useState(emptyForm);

  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const [isExportOpen, setIsExportOpen] = useState(false);
  const [exportFormat, setExportFormat] = useState('PDF');
  const [exportScope, setExportScope] = useState('ALL');

  // Modal Contenu (dossiers rattachés à un état, sur une période)
  const [isContenuOpen, setIsContenuOpen] = useState(false);
  const [contenuTarget, setContenuTarget] = useState(null);
  const [contenuDateDebut, setContenuDateDebut] = useState(defaultDateDebut);
  const [contenuDateFin, setContenuDateFin] = useState(defaultDateFin);
  const [contenuLoading, setContenuLoading] = useState(false);
  const [contenuDossiers, setContenuDossiers] = useState([]);
  const [contenuFormat, setContenuFormat] = useState('PDF');

  const loadEtats = async () => {
    setLoading(true);
    try {
      const data = await reportingApi.getDecisionnel();
      setEtats(Array.isArray(data) ? data : []);
    } catch (err) {
      toastError('Erreur lors du chargement des états décisionnels.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEtats();
  }, []);

  const totalEtats = etats.length;
  const actifsCount = etats.filter((e) => e.actif).length;
  const inactifsCount = totalEtats - actifsCount;

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!createForm.code_etat.trim() || !createForm.libelle_etat.trim()) return;
    setIsSaving(true);
    try {
      await reportingApi.createDecisionnel({
        code_etat: createForm.code_etat.trim().toUpperCase(),
        libelle_etat: createForm.libelle_etat.trim(),
        url: createForm.url,
        actif: createForm.actif,
      });
      setIsCreateOpen(false);
      setCreateForm(emptyForm);
      success('État décisionnel créé avec succès.');
      loadEtats();
    } catch (err) {
      toastError(err?.response?.data?.code_etat?.[0] || err?.response?.data?.error || 'Erreur lors de la création.');
    } finally {
      setIsSaving(false);
    }
  };

  const openEdit = (etat) => {
    setEditTarget(etat);
    setEditForm({
      code_etat: etat.code_etat || '',
      libelle_etat: etat.libelle_etat || '',
      url: etat.url || 'DETAIL',
      actif: Boolean(etat.actif),
    });
    setIsEditOpen(true);
  };

  const handleEdit = async (e) => {
    e.preventDefault();
    if (!editTarget || !editForm.code_etat.trim() || !editForm.libelle_etat.trim()) return;
    setIsSaving(true);
    try {
      await reportingApi.updateDecisionnel(editTarget.id_etat, {
        code_etat: editForm.code_etat.trim().toUpperCase(),
        libelle_etat: editForm.libelle_etat.trim(),
        url: editForm.url,
        actif: editForm.actif,
      });
      setIsEditOpen(false);
      setEditTarget(null);
      success('État décisionnel modifié avec succès.');
      loadEtats();
    } catch (err) {
      toastError(err?.response?.data?.code_etat?.[0] || err?.response?.data?.error || 'Erreur lors de la modification.');
    } finally {
      setIsSaving(false);
    }
  };

  const openDelete = (etat) => {
    setDeleteTarget(etat);
    setIsDeleteOpen(true);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await reportingApi.deleteDecisionnel(deleteTarget.id_etat);
      setIsDeleteOpen(false);
      setDeleteTarget(null);
      success('État décisionnel supprimé avec succès.');
      loadEtats();
    } catch (err) {
      toastError(err?.response?.data?.error || 'Erreur lors de la suppression.');
      setIsDeleteOpen(false);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleExport = (e) => {
    e.preventDefault();

    const filteredData =
      exportScope === 'ACTIFS' ? etats.filter((r) => r.actif) :
      exportScope === 'INACTIFS' ? etats.filter((r) => !r.actif) :
      etats;

    const headers = ['Code', 'Libellé de l\'État Décisionnel', 'Destination / Action', 'Statut'];
    const rows = filteredData.map((r) => [
      r.code_etat || '-',
      r.libelle_etat || '-',
      r.url || '-',
      r.actif ? 'Actif' : 'Inactif',
    ]);

    const filename = `Etats_Decisionnels_${exportScope}`;
    const title = 'RÉFÉRENTIEL DES ÉTATS DÉCISIONNELS';
    const subtitle = 'Table stdetatdecisionnel — Cycle décisionnel souscription, contrats et sinistres';
    const metadata = {
      'Organisme': 'LE PHARE COURTAGE & GESTION D\'ASSURANCES',
      'Périmètre': exportScope === 'ACTIFS' ? 'États actifs uniquement' : exportScope === 'INACTIFS' ? 'États inactifs uniquement' : 'Tous les états',
      'Total États': String(filteredData.length),
      'Date d\'Édition': new Date().toLocaleDateString('fr-FR'),
    };

    if (exportFormat === 'XLSX') {
      exportToExcel({ filename, title, subtitle, metadata, headers, rows });
    } else {
      exportToPdf({ filename, title, subtitle, metadata, headers, rows });
    }

    success(`États décisionnels (${exportFormat}) téléchargés avec succès.`);
    setIsExportOpen(false);
  };

  const openContenu = (etat) => {
    setContenuTarget(etat);
    setContenuDateDebut(defaultDateDebut);
    setContenuDateFin(defaultDateFin);
    setContenuDossiers([]);
    setIsContenuOpen(true);
  };

  const loadContenu = async (etat, dateDebut, dateFin) => {
    if (!etat) return;
    setContenuLoading(true);
    try {
      const result = await reportingApi.getDecisionnelContenu(etat.id_etat, dateDebut, dateFin);
      const dossiers = Array.isArray(result?.Data) ? result.Data : [];
      setContenuDossiers(dossiers);
      if (result?.Status && result.Status !== 'Succès') {
        toastError(result?.Data || 'Erreur lors du chargement du contenu.');
      }
    } catch (err) {
      toastError(err?.response?.data?.Data || 'Erreur lors du chargement du contenu de cet état.');
      setContenuDossiers([]);
    } finally {
      setContenuLoading(false);
    }
  };

  useEffect(() => {
    if (isContenuOpen && contenuTarget) {
      loadContenu(contenuTarget, contenuDateDebut, contenuDateFin);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isContenuOpen, contenuTarget, contenuDateDebut, contenuDateFin]);

  const buildContenuDoc = () => {
    const headers = ['N° Devis', 'Client', 'Produit', 'Statut', 'Date Émission', 'Prime TTC (FCFA)'];
    const rows = contenuDossiers.map((d) => [
      d.numero_devis || '-',
      d.nom_client || '-',
      d.produit || '-',
      d.statut || '-',
      d.date_emission ? new Date(d.date_emission).toLocaleDateString('fr-FR') : '-',
      `${Number(d.prime_ttc || 0).toLocaleString()} FCFA`,
    ]);
    const totPrime = contenuDossiers.reduce((acc, d) => acc + Number(d.prime_ttc || 0), 0);
    const totals = ['TOTAL', `${contenuDossiers.length} dossier(s)`, '', '', '', `${totPrime.toLocaleString()} FCFA`];
    const filename = `Etat_Decisionnel_${contenuTarget?.code_etat}_${contenuDateDebut}_${contenuDateFin}`;
    const title = `CONTENU DE L'ÉTAT DÉCISIONNEL : ${contenuTarget?.libelle_etat || ''}`;
    const subtitle = `Code ${contenuTarget?.code_etat || ''} — Période du ${contenuDateDebut} au ${contenuDateFin}`;
    const metadata = {
      'Organisme': 'LE PHARE COURTAGE & GESTION D\'ASSURANCES',
      'État Décisionnel': `${contenuTarget?.code_etat} — ${contenuTarget?.libelle_etat}`,
      'Période': `${contenuDateDebut} au ${contenuDateFin}`,
      'Total Dossiers': String(contenuDossiers.length),
      'Date d\'Édition': new Date().toLocaleDateString('fr-FR'),
    };
    return { filename, title, subtitle, metadata, headers, rows, totals };
  };

  const handlePrintContenu = () => {
    window.print();
  };

  const handleExportContenu = (e) => {
    e.preventDefault();
    const doc = buildContenuDoc();
    if (contenuFormat === 'XLSX') {
      exportToExcel(doc);
    } else {
      exportToPdf(doc);
    }
    success(`Contenu de l'état "${contenuTarget?.libelle_etat}" (${contenuFormat}) téléchargé avec succès.`);
  };

  const columns = [
    {
      header: 'Code',
      accessor: 'code_etat',
      render: (r) => (
        <span style={{ fontFamily: 'var(--font-mono)', color: '#60a5fa', fontWeight: 700, fontSize: '0.82rem' }}>
          {r.code_etat}
        </span>
      ),
    },
    {
      header: 'Libellé de l\'État Décisionnel',
      accessor: 'libelle_etat',
      render: (r) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <GitBranch size={14} style={{ color: '#a78bfa', flexShrink: 0 }} />
          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{r.libelle_etat}</span>
        </div>
      ),
    },
    {
      header: 'Destination / Action',
      accessor: 'url',
      render: (r) => (
        <span style={{ fontSize: '0.75rem', padding: '0.15rem 0.5rem', borderRadius: '6px', background: 'rgba(99,102,241,0.12)', color: '#a5b4fc' }}>
          {r.url}
        </span>
      ),
    },
    {
      header: 'Statut',
      accessor: 'actif',
      render: (r) =>
        r.actif ? (
          <StatusBadge label="Actif" color="emerald" />
        ) : (
          <StatusBadge label="Inactif" color="gray" />
        ),
    },
    {
      header: 'Actions',
      render: (r) => (
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '0.75rem', padding: '0.25rem 0.55rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}
            onClick={() => openContenu(r)}
          >
            <Eye size={13} /> Contenu
          </button>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '0.75rem', padding: '0.25rem 0.55rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}
            onClick={() => openEdit(r)}
          >
            <Edit2 size={13} /> Modifier
          </button>
          <button
            className="btn"
            style={{
              fontSize: '0.75rem', padding: '0.25rem 0.55rem',
              display: 'flex', alignItems: 'center', gap: '0.3rem',
              background: 'rgba(239,68,68,0.12)', color: '#f87171',
              border: '1px solid rgba(239,68,68,0.3)',
            }}
            onClick={() => openDelete(r)}
          >
            <Trash2 size={13} /> Supprimer
          </button>
        </div>
      ),
    },
  ];

  return (
    <div style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <GitBranch size={22} color="#a78bfa" />
            États Décisionnels
          </h1>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.3rem', margin: '0.3rem 0 0 0' }}>
            Table{' '}
            <code style={{ background: 'rgba(99,102,241,0.12)', padding: '0.1rem 0.35rem', borderRadius: '4px', fontSize: '0.75rem' }}>
              stdetatdecisionnel
            </code>{' '}
            — Référentiel des états du cycle décisionnel (souscription, contrats, sinistres)
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.65rem' }}>
          <button
            className="btn btn-secondary"
            onClick={loadEtats}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem' }}
          >
            <RefreshCw size={14} /> Actualiser
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => setIsExportOpen(true)}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem' }}
          >
            <Download size={14} /> Exporter
          </button>
          <button
            className="btn btn-primary"
            onClick={() => { setIsCreateOpen(true); setCreateForm(emptyForm); }}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem' }}
          >
            <Plus size={14} /> Nouvel État Décisionnel
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        {[
          { label: 'Total États', value: totalEtats, color: '#a78bfa' },
          { label: 'États Actifs', value: actifsCount, color: '#34d399' },
          { label: 'États Inactifs', value: inactifsCount, color: '#94a3b8' },
        ].map((kpi) => (
          <div key={kpi.label} style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '10px', padding: '1rem 1.25rem' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {kpi.label}
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: kpi.color, marginTop: '0.25rem' }}>{kpi.value}</div>
          </div>
        ))}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          Chargement des états décisionnels…
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={etats}
          searchable
          searchPlaceholder="Rechercher un état décisionnel…"
          emptyMessage="Aucun état décisionnel enregistré. Cliquez sur «+ Nouveau» pour commencer."
        />
      )}

      {/* Modal Création */}
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Nouvel État Décisionnel" maxWidth="480px">
        <form onSubmit={handleCreate}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
              Code de l'état * (3 caractères max)
            </label>
            <input
              type="text"
              className="form-control"
              placeholder="Ex: ATT, VAL, REJ…"
              value={createForm.code_etat}
              maxLength={3}
              onChange={(e) => setCreateForm({ ...createForm, code_etat: e.target.value.toUpperCase() })}
              autoFocus
              required
              style={{ textTransform: 'uppercase' }}
            />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
              Libellé de l'état *
            </label>
            <input
              type="text"
              className="form-control"
              placeholder="Ex: En attente de validation"
              value={createForm.libelle_etat}
              onChange={(e) => setCreateForm({ ...createForm, libelle_etat: e.target.value })}
              required
            />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
              Destination / Action associée
            </label>
            <select
              className="form-control"
              value={createForm.url}
              onChange={(e) => setCreateForm({ ...createForm, url: e.target.value })}
            >
              {URL_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </div>
          <div style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              id="create-actif"
              checked={createForm.actif}
              onChange={(e) => setCreateForm({ ...createForm, actif: e.target.checked })}
            />
            <label htmlFor="create-actif" style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              État actif (visible dans les workflows)
            </label>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsCreateOpen(false)} disabled={isSaving}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={isSaving || !createForm.code_etat.trim() || !createForm.libelle_etat.trim()}
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              {isSaving ? 'Enregistrement…' : <><Plus size={14} /> Créer l'État</>}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Édition */}
      <Modal isOpen={isEditOpen} onClose={() => setIsEditOpen(false)} title={`Modifier — ${editTarget?.libelle_etat || ''}`} maxWidth="480px">
        <form onSubmit={handleEdit}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
              Code de l'état *
            </label>
            <input
              type="text"
              className="form-control"
              value={editForm.code_etat}
              maxLength={3}
              onChange={(e) => setEditForm({ ...editForm, code_etat: e.target.value.toUpperCase() })}
              required
              style={{ textTransform: 'uppercase' }}
            />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
              Libellé de l'état *
            </label>
            <input
              type="text"
              className="form-control"
              value={editForm.libelle_etat}
              onChange={(e) => setEditForm({ ...editForm, libelle_etat: e.target.value })}
              required
            />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
              Destination / Action associée
            </label>
            <select
              className="form-control"
              value={editForm.url}
              onChange={(e) => setEditForm({ ...editForm, url: e.target.value })}
            >
              {URL_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </div>
          <div style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              id="edit-actif"
              checked={editForm.actif}
              onChange={(e) => setEditForm({ ...editForm, actif: e.target.checked })}
            />
            <label htmlFor="edit-actif" style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
              {editForm.actif ? <CheckCircle2 size={13} color="#34d399" /> : <XCircle size={13} color="#94a3b8" />}
              État actif (visible dans les workflows)
            </label>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsEditOpen(false)} disabled={isSaving}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={isSaving || !editForm.code_etat.trim() || !editForm.libelle_etat.trim()}
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              {isSaving ? 'Enregistrement…' : <><Edit2 size={14} /> Enregistrer</>}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Contenu de l'état décisionnel (avec choix de période) */}
      <Modal
        isOpen={isContenuOpen}
        onClose={() => setIsContenuOpen(false)}
        title={`Contenu de l'État : ${contenuTarget?.libelle_etat || ''}`}
        subtitle={`Code ${contenuTarget?.code_etat || ''} — Dossiers rattachés sur la période sélectionnée`}
        maxWidth="820px"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Sélecteur de période */}
          <div className="no-print" style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', background: 'var(--bg-surface)', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Calendar size={15} color="var(--text-muted)" />
              <span style={{ fontSize: '0.82rem', fontWeight: 600 }}>Du :</span>
              <input
                type="date"
                className="form-control"
                style={{ padding: '0.3rem 0.55rem', fontSize: '0.82rem', width: 'auto' }}
                value={contenuDateDebut}
                onChange={(e) => setContenuDateDebut(e.target.value)}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.82rem', fontWeight: 600 }}>Au :</span>
              <input
                type="date"
                className="form-control"
                style={{ padding: '0.3rem 0.55rem', fontSize: '0.82rem', width: 'auto' }}
                value={contenuDateFin}
                onChange={(e) => setContenuDateFin(e.target.value)}
              />
            </div>
            <div style={{ marginLeft: 'auto', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Total : <strong style={{ color: '#60a5fa' }}>{contenuDossiers.length}</strong> dossier(s)
            </div>
          </div>

          {/* Liste des dossiers */}
          {contenuLoading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem', gap: '0.75rem', color: 'var(--text-muted)' }}>
              <Loader2 size={20} className="animate-spin" />
              <span>Chargement des dossiers rattachés à cet état…</span>
            </div>
          ) : (
            <DataTable
              columns={[
                { header: 'N° Devis', accessor: 'numero_devis', render: (d) => <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{d.numero_devis || '-'}</span> },
                { header: 'Client', accessor: 'nom_client' },
                { header: 'Produit', accessor: 'produit' },
                { header: 'Statut', accessor: 'statut' },
                { header: 'Date Émission', render: (d) => d.date_emission ? new Date(d.date_emission).toLocaleDateString('fr-FR') : '-' },
                { header: 'Prime TTC (FCFA)', render: (d) => <strong>{Number(d.prime_ttc || 0).toLocaleString()} F</strong> },
              ]}
              data={contenuDossiers}
              searchPlaceholder="Filtrer un dossier…"
              emptyMessage="Aucun dossier rattaché à cet état sur la période sélectionnée."
            />
          )}

          {/* Actions d'impression / export */}
          <div className="no-print" style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.75rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem' }}>
            <select
              className="form-control"
              style={{ width: 'auto', fontSize: '0.82rem', padding: '0.35rem 0.6rem' }}
              value={contenuFormat}
              onChange={(e) => setContenuFormat(e.target.value)}
            >
              <option value="PDF">PDF</option>
              <option value="XLSX">Excel (.xlsx)</option>
            </select>
            <button className="btn btn-secondary" onClick={handleExportContenu} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Download size={15} /> Télécharger
            </button>
            <button className="btn btn-primary" onClick={handlePrintContenu} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Printer size={15} /> Imprimer
            </button>
          </div>
        </div>
      </Modal>

      {/* Modal Export */}
      <Modal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        title="Exporter le Référentiel des États Décisionnels"
        subtitle="Génération d'un document PDF ou Excel pour archivage et contrôle."
        maxWidth="480px"
      >
        <form onSubmit={handleExport}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
              Format du Document *
            </label>
            <select
              className="form-control"
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value)}
            >
              <option value="PDF">Document PDF</option>
              <option value="XLSX">Classeur Microsoft Excel (.xlsx)</option>
            </select>
          </div>

          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
              Périmètre des États
            </label>
            <select
              className="form-control"
              value={exportScope}
              onChange={(e) => setExportScope(e.target.value)}
            >
              <option value="ALL">Tous les états ({etats.length})</option>
              <option value="ACTIFS">États actifs uniquement ({actifsCount})</option>
              <option value="INACTIFS">États inactifs uniquement ({inactifsCount})</option>
            </select>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsExportOpen(false)}>Annuler</button>
            <button type="submit" className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Download size={14} /> Télécharger
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Confirmation Suppression */}
      {isDeleteOpen && deleteTarget && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(4px)',
        }}>
          <div style={{
            background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
            borderRadius: '12px', padding: '1.75rem', maxWidth: '420px', width: '100%',
            boxShadow: '0 20px 60px rgba(0,0,0,0.45)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
              <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: 'rgba(239,68,68,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Trash2 size={18} style={{ color: '#f87171' }} />
              </div>
              <div>
                <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.95rem' }}>Supprimer l'état décisionnel ?</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Cette action est irréversible.</div>
              </div>
            </div>
            <div style={{ padding: '0.75rem', background: 'var(--bg-muted)', borderRadius: '8px', marginBottom: '1.25rem', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Vous êtes sur le point de supprimer <strong>« {deleteTarget.code_etat} — {deleteTarget.libelle_etat} »</strong>.
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setIsDeleteOpen(false)} disabled={isDeleting}>Annuler</button>
              <button
                className="btn"
                style={{ background: 'rgba(239,68,68,0.15)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                onClick={handleDelete}
                disabled={isDeleting}
              >
                <Trash2 size={14} />
                {isDeleting ? 'Suppression…' : 'Confirmer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DecisionalStatesPage;
