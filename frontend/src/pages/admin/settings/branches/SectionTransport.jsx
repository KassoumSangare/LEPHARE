import React, { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronUp, ListChecks, Loader2, Plus, Receipt, RotateCcw, Save, ShieldCheck, Ship } from 'lucide-react';
import { SectionParametrage } from '../../../../components/admin/EnTeteParametrage';
import { LigneParametre } from '../../../../components/admin/LigneParametre';
import { Interrupteur } from '../../../../components/admin/Interrupteur';
import { parametrageApi } from '../../../../api/endpoints';
import { useToast } from '../../../../context/ToastContext';
import { messageErreurApi } from '../../../../utils/financeUtils';
import { chargerParametrage } from '../../../../utils/parametrage';

// Réglages Transport hors GUCE (configuration_api/parametrage_transport.py) : garanties et taux proposés par mode,
// primes minimums et coûts, modes de transport, listes de saisie de la cotation.

const vide = (v) => v === null || v === undefined || String(v).trim() === '';
const texteTaux = (v) => (vide(v) ? '' : String(v).replace('.', ','));
const signature = (liste) => JSON.stringify(liste.map((g) => ({ ...g, Taux: Object.fromEntries(Object.entries(g.Taux || {}).map(([m, t]) => [m, texteTaux(t)])) })));

const ModeTransport = ({ mode, onEnregistre }) => {
  const { success, error: toastError } = useToast();
  const [saisie, setSaisie] = useState({ ...mode, Chargements: (mode.Chargements || []).join('\n') });
  const [envoi, setEnvoi] = useState(false);
  const modifie = saisie.Libelle !== mode.Libelle || saisie.Document !== mode.Document || saisie.Moyen !== mode.Moyen
    || saisie.Actif !== mode.Actif || saisie.Chargements !== (mode.Chargements || []).join('\n');
  const enregistrer = async () => {
    setEnvoi(true);
    try {
      const maj = await parametrageApi.modifierModeTransport(mode.Code, {
        Libelle: saisie.Libelle, Document: saisie.Document, Moyen: saisie.Moyen, Actif: saisie.Actif, Chargements: saisie.Chargements,
      });
      onEnregistre(maj);
      setSaisie({ ...maj, Chargements: maj.Chargements.join('\n') });
      success(`Mode « ${maj.Libelle} » enregistré.`);
    } catch (err) {
      toastError(messageErreurApi(err));
    } finally {
      setEnvoi(false);
    }
  };
  return (
    <div className={`rb-mode${saisie.Actif ? '' : ' inactif'}`}>
      <div className="rb-mode-entete">
        <strong>{mode.Libelle}</strong>
        <span className="rb-discret">Catégorie {mode.CodeCategorie}</span>
        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.8rem' }}>
          Proposé <Interrupteur actif={!!saisie.Actif} onChange={(v) => setSaisie((s) => ({ ...s, Actif: v }))} libelle={`Mode ${mode.Libelle} proposé à la cotation`} />
        </span>
      </div>
      <div className="rb-grille">
        <label className="rb-champ"><span className="rb-champ-libelle">Libellé</span>
          <input className="form-control" maxLength={60} value={saisie.Libelle} onChange={(e) => setSaisie((s) => ({ ...s, Libelle: e.target.value }))} /></label>
        <label className="rb-champ"><span className="rb-champ-libelle">Document de transport</span>
          <input className="form-control" maxLength={80} value={saisie.Document} onChange={(e) => setSaisie((s) => ({ ...s, Document: e.target.value }))} /></label>
        <label className="rb-champ"><span className="rb-champ-libelle">Moyen de transport demandé</span>
          <input className="form-control" maxLength={80} value={saisie.Moyen} onChange={(e) => setSaisie((s) => ({ ...s, Moyen: e.target.value }))} /></label>
        <label className="rb-champ"><span className="rb-champ-libelle">Modes de chargement, un par ligne</span>
          <textarea className="form-control" rows={3} value={saisie.Chargements} onChange={(e) => setSaisie((s) => ({ ...s, Chargements: e.target.value }))} /></label>
      </div>
      {modifie && (
        <div className="rb-actions">
          <button type="button" className="btn btn-secondary" onClick={() => setSaisie({ ...mode, Chargements: (mode.Chargements || []).join('\n') })} title="Annuler les changements"><RotateCcw size={14} /></button>
          <button type="button" className="btn btn-primary" onClick={enregistrer} disabled={envoi} aria-busy={envoi}><Save size={14} /> Enregistrer</button>
        </div>
      )}
    </div>
  );
};

export const SectionTransport = () => {
  const { success, error: toastError } = useToast();
  const [donnees, setDonnees] = useState(null);
  const [garanties, setGaranties] = useState([]);
  const [ouverte, setOuverte] = useState(null);
  const [envoi, setEnvoi] = useState(false);

  const charger = () => parametrageApi.getTransport()
    .then((d) => { setDonnees(d); setGaranties(d.Garanties.map((g) => ({ ...g, Taux: { ...(g.Taux || {}) } }))); })
    .catch((err) => toastError(`Réglages Transport non chargés : ${messageErreurApi(err)}`));
  useEffect(() => { charger(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const modes = donnees?.Modes || [];
  const modifiees = useMemo(() => (donnees ? signature(garanties) !== signature(donnees.Garanties) : false), [garanties, donnees]);
  const changer = (code, cle, valeur) => setGaranties((l) => l.map((g) => (g.Code === code ? { ...g, [cle]: valeur } : g)));
  const changerTaux = (code, mode, valeur) => setGaranties((l) => l.map((g) => (g.Code === code ? { ...g, Taux: { ...g.Taux, [mode]: valeur } } : g)));
  const ajouter = () => {
    const code = `NOUVELLE_${Date.now()}`;
    setGaranties((l) => [...l, { Code: code, Nouvelle: true, Groupe: 'EXTENSION', Libelle: '', Description: '', CodeSousGarantie: '', Taux: {}, TauxMinimum: false, Active: true }]);
    setOuverte(code);
  };
  const enregistrer = async () => {
    setEnvoi(true);
    try {
      const d = await parametrageApi.modifierGarantiesTransport(garanties.map((g) => ({
        ...g, Code: g.Nouvelle ? '' : g.Code,
        Taux: Object.fromEntries(Object.entries(g.Taux || {}).map(([m, t]) => [m, vide(t) ? null : String(t).replace(',', '.')])),
      })));
      setDonnees((x) => ({ ...x, Garanties: d.Garanties }));
      setGaranties(d.Garanties.map((g) => ({ ...g, Taux: { ...(g.Taux || {}) } })));
      setOuverte(null);
      success('Garanties Transport enregistrées : elles s\'appliquent aux prochaines cotations.');
    } catch (err) {
      toastError(messageErreurApi(err));
    } finally {
      setEnvoi(false);
    }
  };
  const remplacerParametre = (p) => { setDonnees((d) => ({ ...d, Parametres: d.Parametres.map((x) => (x.Cle === p.Cle ? p : x)) })); chargerParametrage(true); };

  if (!donnees) {
    return <SectionParametrage icone={ShieldCheck} titre="Tarif Transport"><div style={{ color: 'var(--text-muted)' }}><Loader2 size={15} className="spin" /> Chargement…</div></SectionParametrage>;
  }
  const parGroupe = (groupe) => donnees.Parametres.filter((p) => p.Groupe === groupe).sort((a, b) => a.Ordre - b.Ordre);

  return (
    <>
      <SectionParametrage icone={ShieldCheck} titre="Garanties et taux proposés"
        description="Taux proposé à la cotation pour chaque mode de transport ; vide, le gestionnaire le saisit. « Minimum » : le taux proposé est un plancher, comme le FAP Sauf. Une garantie déjà utilisée se désactive, elle ne se supprime pas."
        actions={<button type="button" className="btn btn-secondary" onClick={ajouter} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}><Plus size={15} /> Ajouter une garantie</button>}>
        <div className="table-wrapper">
          <table className="rb-table">
            <thead>
              <tr>
                <th>Garantie</th>
                {modes.map((m) => <th key={m.Code} className="nombre">{m.Libelle.split(' ')[0]}</th>)}
                <th title="Le taux proposé est un plancher">Minimum</th>
                <th>Proposée</th>
                <th aria-label="Détails" />
              </tr>
            </thead>
            <tbody>
              {garanties.map((g) => (
                <React.Fragment key={g.Code}>
                  <tr className={g.Active ? '' : 'inactive'}>
                    <td>
                      <div style={{ fontWeight: 700 }}>{g.Libelle || <span className="rb-discret">Nouvelle garantie</span>}</div>
                      <span className={`rb-badge ${g.Groupe === 'BASE' ? 'base' : ''}`}>{g.Groupe === 'BASE' ? 'Garantie de base' : 'Extension'}</span>
                    </td>
                    {modes.map((m) => (
                      <td key={m.Code} className="nombre">
                        <span className="rb-taux">
                          <input className="form-control" inputMode="decimal" aria-label={`${g.Libelle || 'Garantie'}, taux ${m.Libelle}`} placeholder="à saisir"
                            value={texteTaux(g.Taux?.[m.Code])} onChange={(e) => changerTaux(g.Code, m.Code, e.target.value)} />
                        </span>
                      </td>
                    ))}
                    <td style={{ textAlign: 'center' }}>
                      <input type="checkbox" checked={!!g.TauxMinimum} aria-label={`${g.Libelle} : taux minimum`} onChange={(e) => changer(g.Code, 'TauxMinimum', e.target.checked)} />
                    </td>
                    <td><Interrupteur actif={!!g.Active} onChange={(v) => changer(g.Code, 'Active', v)} libelle={`${g.Libelle} proposée`} /></td>
                    <td>
                      <button type="button" className="btn btn-link" onClick={() => setOuverte(ouverte === g.Code ? null : g.Code)} aria-expanded={ouverte === g.Code}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '0.2rem', fontSize: '0.8rem' }}>
                        Détails {ouverte === g.Code ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>
                    </td>
                  </tr>
                  {ouverte === g.Code && (
                    <tr className="rb-detail">
                      <td colSpan={modes.length + 4}>
                        <div className="rb-grille">
                          <label className="rb-champ"><span className="rb-champ-libelle">Libellé à la cotation</span>
                            <input className="form-control" maxLength={80} value={g.Libelle} onChange={(e) => changer(g.Code, 'Libelle', e.target.value)} /></label>
                          <label className="rb-champ"><span className="rb-champ-libelle">Type</span>
                            <select className="form-control" value={g.Groupe} onChange={(e) => changer(g.Code, 'Groupe', e.target.value)}>
                              <option value="BASE">Garantie de base, une seule au choix</option>
                              <option value="EXTENSION">Extension ou surprime, cumulable</option>
                            </select></label>
                          <label className="rb-champ"><span className="rb-champ-libelle">Garantie du référentiel</span>
                            <select className="form-control" value={g.CodeSousGarantie} onChange={(e) => changer(g.Code, 'CodeSousGarantie', e.target.value)}>
                              <option value="">Choisir…</option>
                              {donnees.SousGaranties.map((s) => <option key={s.Code} value={s.Code}>{s.Libelle} - {s.Code}</option>)}
                            </select></label>
                          <label className="rb-champ rb-large"><span className="rb-champ-libelle">Explication montrée au gestionnaire</span>
                            <textarea className="form-control" rows={2} maxLength={600} value={g.Description} onChange={(e) => changer(g.Code, 'Description', e.target.value)} /></label>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
        <div className="rb-actions">
          {modifiees && <span className="rb-discret">Modifications non enregistrées</span>}
          {modifiees && <button type="button" className="btn btn-secondary" onClick={() => { setGaranties(donnees.Garanties.map((g) => ({ ...g, Taux: { ...(g.Taux || {}) } }))); setOuverte(null); }} title="Annuler les changements"><RotateCcw size={14} /></button>}
          <button type="button" className="btn btn-primary" onClick={enregistrer} disabled={!modifiees || envoi} aria-busy={envoi}><Save size={14} /> Enregistrer les garanties</button>
        </div>
      </SectionParametrage>

      <SectionParametrage icone={Receipt} titre="Primes minimums, coûts de police et taxe" description="Montants appliqués par la cotation selon le type de police ; vide : rien n'est appliqué.">
        {parGroupe('transport_tarif').map((p) => <LigneParametre key={p.Cle} parametre={p} onEnregistre={remplacerParametre} />)}
      </SectionParametrage>

      <SectionParametrage icone={Ship} titre="Modes de transport" description="Ce que la cotation demande pour chaque mode ; un mode non proposé disparaît de la cotation, les affaires existantes le gardent.">
        <div className="rb-modes">{modes.map((m) => (
          <ModeTransport key={m.Code} mode={m} onEnregistre={(maj) => setDonnees((d) => ({ ...d, Modes: d.Modes.map((x) => (x.Code === maj.Code ? maj : x)) }))} />
        ))}</div>
      </SectionParametrage>

      <SectionParametrage icone={ListChecks} titre="Listes de saisie" description="Valeurs proposées dans les listes de la cotation, une par ligne ; « Autre, à préciser » reste toujours possible.">
        {parGroupe('transport_listes').map((p) => <LigneParametre key={p.Cle} parametre={p} lignes={6} onEnregistre={remplacerParametre} />)}
      </SectionParametrage>
    </>
  );
};

export default SectionTransport;
