import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Package, Save, Loader2, RotateCcw, Shield, Boxes, LayoutList } from 'lucide-react';
import { EnTeteParametrage, SectionParametrage } from '../../../components/admin/EnTeteParametrage';
import { parametrageApi } from '../../../api/endpoints';
import { messageErreurApi } from '../../../utils/financeUtils';
import { chargerParametrage, codeOnglet } from '../../../utils/parametrage';
import { useToast } from '../../../context/ToastContext';
import { Interrupteur } from '../../../components/admin/Interrupteur';

// Produits (stdproduit) et leur place dans LE PHARE (lephare_produit_parametre) : onglet du
// registre des devis, formulaire de saisie, saisie ouverte. configuration_api/parametrage.py

const CHAMPS = ['Libelle', 'Actif', 'Onglet', 'ModuleSaisie', 'SaisieOuverte', 'ArrondiTtc', 'IdCompagnieDefaut', 'Ordre'];
const identique = (a, b) => CHAMPS.every((c) => String(a[c] ?? '') === String(b[c] ?? ''));

export const CatalogProductsPage = () => {
  const { success, error: toastError } = useToast();
  const [origine, setOrigine] = useState([]);
  const [saisie, setSaisie] = useState({});
  const [modules, setModules] = useState([]);
  const [compagnies, setCompagnies] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [envoi, setEnvoi] = useState(null);

  const charger = async () => {
    setChargement(true);
    try {
      const [d, cies] = await Promise.all([parametrageApi.getProduits(), parametrageApi.getCompagnies().catch(() => [])]);
      setCompagnies((cies || []).filter((c) => c.Active).map((c) => ({ id: Number(c.IdCompagnie), nom: c.RaisonSociale }))
        .sort((a, b) => a.nom.localeCompare(b.nom, 'fr')));
      setOrigine(d.Produits);
      setSaisie(Object.fromEntries(d.Produits.map((p) => [p.IdProduit, { ...p }])));
      setModules(d.Modules);
    } catch (err) {
      toastError(`Produits non chargés : ${messageErreurApi(err)}`);
    } finally {
      setChargement(false);
    }
  };
  useEffect(() => { charger(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const changer = (id, cle, valeur) => setSaisie((s) => {
    const ligne = { ...s[id], [cle]: valeur };
    if (cle === 'ModuleSaisie' && !valeur) ligne.SaisieOuverte = false;
    return { ...s, [id]: ligne };
  });

  const enregistrer = async (p) => {
    setEnvoi(p.IdProduit);
    try {
      const l = saisie[p.IdProduit];
      const maj = await parametrageApi.modifierProduit(p.IdProduit, Object.fromEntries(CHAMPS.map((c) => [c, l[c]])));
      setOrigine((liste) => liste.map((x) => (x.IdProduit === maj.IdProduit ? maj : x)));
      setSaisie((s) => ({ ...s, [maj.IdProduit]: { ...maj } }));
      chargerParametrage(true);
      success(`${maj.Libelle} enregistré : registre des devis et boutons de création mis à jour.`);
    } catch (err) {
      toastError(messageErreurApi(err));
    } finally {
      setEnvoi(null);
    }
  };

  const lignes = useMemo(() => [...origine].sort((a, b) => (saisie[a.IdProduit]?.Ordre ?? 99) - (saisie[b.IdProduit]?.Ordre ?? 99) || a.IdProduit - b.IdProduit), [origine, saisie]);
  const onglets = useMemo(() => {
    const vus = new Map();
    lignes.forEach((p) => {
      const l = saisie[p.IdProduit];
      if (!l?.Onglet) return;
      const code = codeOnglet(l.Onglet);
      if (!vus.has(code)) vus.set(code, { libelle: l.Onglet, produits: [] });
      vus.get(code).produits.push(l.Libelle);
    });
    return [...vus.values()];
  }, [lignes, saisie]);
  const libellesOnglets = [...new Set(Object.values(saisie).map((l) => l.Onglet).filter(Boolean))];

  return (
    <div style={{ padding: '1.5rem' }}>
      <EnTeteParametrage
        icone={Package}
        titre="Produits"
        description="Les produits d'assurance de la base (Automobile, Santé, IA…) et leur place dans LE PHARE : onglet du registre des devis, formulaire de saisie, saisie ouverte ou non."
        usage="« Saisie ouverte » active les boutons de création et le bouton « Modifier » du registre pour ce formulaire. « Compagnie proposée » : compagnie sélectionnée à l'ouverture d'un nouveau devis. Les produits d'un même onglet sont regroupés dans le Registre des devis."
        actions={(
          <>
            <Link to="/admin/settings/garanties-oreole" className="btn btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}><Shield size={15} /> Garanties</Link>
            <Link to="/admin/settings/offres" className="btn btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}><Boxes size={15} /> Offres</Link>
          </>
        )}
      />

      <SectionParametrage icone={LayoutList} titre="Aperçu du Registre des devis" description="Onglets affichés au-dessus de la liste des devis, dans l'ordre des produits.">
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
          <span className="badge badge-blue">Tous</span>
          {onglets.map((o) => <span key={o.libelle} className="badge badge-slate" title={o.produits.join(', ')}>{o.libelle} <span style={{ opacity: 0.7 }}>({o.produits.length})</span></span>)}
        </div>
      </SectionParametrage>

      <div className="glass-panel" style={{ padding: '0.5rem 1.25rem 1rem', overflowX: 'auto' }}>
        {chargement ? <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}><Loader2 className="spin" /> Chargement…</div> : (
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 1160 }}>
            <thead>
              <tr style={{ textAlign: 'left', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)' }}>
                <th style={{ padding: '0.75rem 0.4rem', width: 60 }}>Ordre</th>
                <th style={{ padding: '0.75rem 0.4rem' }}>Produit</th>
                <th style={{ padding: '0.75rem 0.4rem', width: 70 }} title="Produit utilisable dans la base">Actif</th>
                <th style={{ padding: '0.75rem 0.4rem', width: 150 }}>Onglet du registre</th>
                <th style={{ padding: '0.75rem 0.4rem', width: 210 }}>Formulaire de saisie</th>
                <th style={{ padding: '0.75rem 0.4rem', width: 100 }}>Saisie ouverte</th>
                <th style={{ padding: '0.75rem 0.4rem', width: 100 }} title="Prime TTC arrondie à la pièce (Paramètres du cabinet > Règles de gestion > Arrondi des montants)">Arrondi TTC</th>
                <th style={{ padding: '0.75rem 0.4rem', width: 200 }} title="Compagnie sélectionnée à l'ouverture d'un nouveau devis du produit">Compagnie proposée</th>
                <th style={{ padding: '0.75rem 0.4rem', width: 190 }} />
              </tr>
            </thead>
            <tbody>
              {lignes.map((p) => {
                const l = saisie[p.IdProduit];
                const modifie = !identique(l, p);
                return (
                  <tr key={p.IdProduit} style={{ borderTop: '1px solid var(--border-subtle)', background: modifie ? 'rgba(245,158,11,0.06)' : undefined }}>
                    <td style={{ padding: '0.55rem 0.4rem' }}>
                      <input type="number" className="form-control" min={0} max={999} value={l.Ordre} onChange={(e) => changer(p.IdProduit, 'Ordre', e.target.value)} style={{ width: 58 }} />
                    </td>
                    <td style={{ padding: '0.55rem 0.4rem' }}>
                      <input className="form-control" maxLength={60} value={l.Libelle} onChange={(e) => changer(p.IdProduit, 'Libelle', e.target.value.toUpperCase())} />
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Produit n° {p.IdProduit}</span>
                    </td>
                    <td style={{ padding: '0.55rem 0.4rem' }}><Interrupteur actif={!!l.Actif} onChange={(v) => changer(p.IdProduit, 'Actif', v)} titre="Produit actif dans la base" /></td>
                    <td style={{ padding: '0.55rem 0.4rem' }}>
                      <input className="form-control" list="onglets-registre" maxLength={40} value={l.Onglet} onChange={(e) => changer(p.IdProduit, 'Onglet', e.target.value)} />
                    </td>
                    <td style={{ padding: '0.55rem 0.4rem' }}>
                      <select className="form-control" value={l.ModuleSaisie} onChange={(e) => changer(p.IdProduit, 'ModuleSaisie', e.target.value)}>
                        <option value="">Aucun formulaire</option>
                        {modules.map((m) => <option key={m.Code} value={m.Code}>{m.Libelle}</option>)}
                      </select>
                    </td>
                    <td style={{ padding: '0.55rem 0.4rem' }}>
                      <Interrupteur actif={!!l.SaisieOuverte} desactive={!l.ModuleSaisie} onChange={(v) => changer(p.IdProduit, 'SaisieOuverte', v)}
                        titre={l.ModuleSaisie ? 'Ouvrir ou fermer la saisie de ce formulaire' : 'Choisissez d\'abord un formulaire'} />
                    </td>
                    <td style={{ padding: '0.55rem 0.4rem' }}>
                      <Interrupteur actif={l.ArrondiTtc !== false} onChange={(v) => changer(p.IdProduit, 'ArrondiTtc', v)}
                        titre={l.ArrondiTtc !== false ? 'Prime TTC arrondie à la pièce : cliquer pour garder la TTC calculée (ex. grilles Voyage des compagnies)' : 'TTC calculée gardée telle quelle : cliquer pour l\'arrondir à la pièce'} />
                    </td>
                    <td style={{ padding: '0.55rem 0.4rem' }}>
                      <select className="form-control" value={l.IdCompagnieDefaut || ''} disabled={!l.ModuleSaisie}
                        onChange={(e) => changer(p.IdProduit, 'IdCompagnieDefaut', e.target.value ? Number(e.target.value) : null)}
                        title={l.ModuleSaisie ? "Compagnie sélectionnée à l'ouverture d'un nouveau devis" : "Choisissez d'abord un formulaire"}>
                        <option value="">Première de la liste</option>
                        {l.IdCompagnieDefaut && !compagnies.some((c) => c.id === Number(l.IdCompagnieDefaut)) && <option value={l.IdCompagnieDefaut}>Compagnie n° {l.IdCompagnieDefaut}</option>}
                        {compagnies.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
                      </select>
                    </td>
                    <td style={{ padding: '0.55rem 0.4rem' }}>
                      {modifie && (
                        <div style={{ display: 'flex', gap: '0.35rem', justifyContent: 'flex-end' }}>
                          <button type="button" className="btn btn-secondary" title="Annuler les changements" onClick={() => setSaisie((s) => ({ ...s, [p.IdProduit]: { ...p } }))} style={{ padding: '0.3rem 0.5rem' }}><RotateCcw size={14} /></button>
                          <button type="button" className="btn btn-primary" disabled={envoi === p.IdProduit} onClick={() => enregistrer(p)} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem' }}>
                            {envoi === p.IdProduit ? <Loader2 size={14} className="spin" /> : <Save size={14} />} Enregistrer
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        <datalist id="onglets-registre">{libellesOnglets.map((o) => <option key={o} value={o} />)}</datalist>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '0.85rem 0 0' }}>
          Un formulaire utilisé par plusieurs produits (ex. Santé) est ouvert dès qu'un de ces produits a la saisie ouverte.
          « Arrondi TTC » : prime TTC arrondie à la pièce selon Paramètres du cabinet &gt; Règles de gestion &gt; Arrondi des montants (montants déjà enregistrés inchangés).
          Les formulaires eux-mêmes (écrans de saisie) font partie de l'application : un nouveau produit se rattache à l'un d'eux.
        </p>
      </div>
    </div>
  );
};

export default CatalogProductsPage;
