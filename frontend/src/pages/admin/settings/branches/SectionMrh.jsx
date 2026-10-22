import React, { useEffect, useMemo, useState } from 'react';
import { Calculator, Home, Loader2, RotateCcw, Save, Sparkles, Tag } from 'lucide-react';
import { SectionParametrage } from '../../../../components/admin/EnTeteParametrage';
import { Interrupteur } from '../../../../components/admin/Interrupteur';
import { AmountInput } from '../../../../components/common/AmountInput';
import { parametrageApi } from '../../../../api/endpoints';
import { useToast } from '../../../../context/ToastContext';
import { messageErreurApi } from '../../../../utils/financeUtils';

// Réglages Multirisque Habitation (configuration_api/parametrage_mrh.py) : tables du tarif lues par
// production/services/mrh_calcul_service.py (prime de base par usage, part de chaque garantie, options, forfaits).

const CAPITAUX = [
  { cle: 'coeff_valeur_batiment', requis: 'param_valeur_batiment_requis', libelle: 'Valeur du bâtiment', formule: 'Valeur bâtiment', exemple: 20000000 },
  { cle: 'coeff_valeur_contenu', requis: 'param_valeur_contenu_requis', libelle: 'Valeur du contenu', formule: 'Valeur contenu', exemple: 5000000 },
  { cle: 'coeff_loyer', requis: 'param_loyer_requis', libelle: 'Loyer mensuel × 12 × 15', formule: 'Loyer × 12 × 15', exemple: 150000, facteur: 180 },
  { cle: 'coeff_capital_rvt', requis: 'param_capital_rvt_requis', libelle: 'Capital RVT', formule: 'Capital RVT', exemple: 10000000 },
];
const AJUSTEMENTS = {
  TYPE1: { unite: '‰', aide: 'de la prime de base' },
  TYPE2: { unite: '%', aide: 'de la prime de la garantie' },
  FORFAIT: { unite: 'F', aide: 'montant fixe' },
};
const fcfa = (v) => Math.round(Number(v) || 0).toLocaleString('fr-FR');
const nombre = (v) => Number(String(v ?? '').replace(',', '.')) || 0;
const texte = (v) => (v === null || v === undefined ? '' : String(v).replace('.', ','));

const saisieUsage = (u) => ({
  Parametres: {
    ...Object.fromEntries(CAPITAUX.flatMap((c) => [[c.cle, texte(u.Parametres?.[c.cle])], [c.requis, !!u.Parametres?.[c.requis]]])),
    coeff_reduction: texte(u.Parametres?.coeff_reduction ?? 1),
    forfait_fixe: Math.round(Number(u.Parametres?.forfait_fixe) || 0),
  },
  Garanties: u.Garanties.map((g) => ({ ...g, TauxRepartition: texte(g.TauxRepartition) })),
  Options: { ...u.Options },
});

const Option = ({ option, onEnregistre }) => {
  const { success, error: toastError } = useToast();
  const initial = { Libelle: option.Libelle, Valeur: option.TypeAjustement === 'FORFAIT' ? Math.round(option.MontantForfait || 0) : texte(option.TauxAjustement), Signe: option.Signe, Actif: option.Actif };
  const [saisie, setSaisie] = useState(initial);
  const [envoi, setEnvoi] = useState(false);
  const modifie = JSON.stringify(saisie) !== JSON.stringify(initial);
  const a = AJUSTEMENTS[option.TypeAjustement] || AJUSTEMENTS.TYPE2;
  const enregistrer = async () => {
    setEnvoi(true);
    try {
      const maj = await parametrageApi.modifierOptionMrh(option.Code, {
        Libelle: saisie.Libelle, Signe: saisie.Signe, Actif: saisie.Actif,
        ...(option.TypeAjustement === 'FORFAIT' ? { MontantForfait: saisie.Valeur } : { TauxAjustement: saisie.Valeur }),
      });
      onEnregistre(maj);
      success(`Option « ${maj.Libelle} » enregistrée.`);
    } catch (err) {
      toastError(messageErreurApi(err));
    } finally {
      setEnvoi(false);
    }
  };
  return (
    <tr className={saisie.Actif ? '' : 'inactive'}>
      <td><input className="form-control" maxLength={200} value={saisie.Libelle} onChange={(e) => setSaisie((s) => ({ ...s, Libelle: e.target.value }))} aria-label="Libellé de l'option" />
        {option.GarantieCible && <span className="rb-discret">Sur : {option.GarantieCible}</span>}</td>
      <td style={{ minWidth: 150 }}>
        <select className="form-control" value={saisie.Signe} onChange={(e) => setSaisie((s) => ({ ...s, Signe: e.target.value }))} aria-label="Majoration ou réduction">
          <option value="+">Majoration</option>
          <option value="-">Réduction</option>
        </select>
      </td>
      <td style={{ minWidth: 170 }}>
        {option.TypeAjustement === 'FORFAIT'
          ? <AmountInput value={saisie.Valeur} onChange={(n) => setSaisie((s) => ({ ...s, Valeur: Number(n) || 0 }))} />
          : <span className="rb-unite" data-unite={a.unite}><input className="form-control" inputMode="decimal" aria-label="Taux d'ajustement" value={saisie.Valeur} onChange={(e) => setSaisie((s) => ({ ...s, Valeur: e.target.value }))} /></span>}
        <span className="rb-discret">{a.aide}</span>
      </td>
      <td><Interrupteur actif={!!saisie.Actif} onChange={(v) => setSaisie((s) => ({ ...s, Actif: v }))} libelle={`Option ${option.Libelle} active`} /></td>
      <td>{modifie && <button type="button" className="btn btn-primary" onClick={enregistrer} disabled={envoi} aria-busy={envoi}><Save size={14} /></button>}</td>
    </tr>
  );
};

const Forfait = ({ forfait, onEnregistre }) => {
  const { success, error: toastError } = useToast();
  const initial = { PrimeNette: Math.round(forfait.PrimeNette || 0), Actif: forfait.Actif };
  const [saisie, setSaisie] = useState(initial);
  const [envoi, setEnvoi] = useState(false);
  const modifie = JSON.stringify(saisie) !== JSON.stringify(initial);
  const enregistrer = async () => {
    setEnvoi(true);
    try {
      const maj = await parametrageApi.modifierForfaitMrh(forfait.Code, saisie);
      onEnregistre(maj);
      success(`« ${maj.Libelle} » : ${fcfa(maj.PrimeNette)} F.`);
    } catch (err) {
      toastError(messageErreurApi(err));
    } finally {
      setEnvoi(false);
    }
  };
  return (
    <tr className={saisie.Actif ? '' : 'inactive'}>
      <td style={{ fontWeight: 700 }}>{forfait.Libelle}</td>
      <td style={{ minWidth: 170 }}><AmountInput value={saisie.PrimeNette} onChange={(n) => setSaisie((s) => ({ ...s, PrimeNette: Number(n) || 0 }))} /></td>
      <td><Interrupteur actif={!!saisie.Actif} onChange={(v) => setSaisie((s) => ({ ...s, Actif: v }))} libelle={`${forfait.Libelle} proposée`} /></td>
      <td>{modifie && <button type="button" className="btn btn-primary" onClick={enregistrer} disabled={envoi} aria-busy={envoi}><Save size={14} /></button>}</td>
    </tr>
  );
};

export const SectionMrh = () => {
  const { success, error: toastError } = useToast();
  const [donnees, setDonnees] = useState(null);
  const [code, setCode] = useState('');
  const [saisie, setSaisie] = useState(null);
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    parametrageApi.getMrh()
      .then((d) => { setDonnees(d); setCode(d.Usages[0]?.Code || ''); })
      .catch((err) => toastError(`Réglages MRH non chargés : ${messageErreurApi(err)}`));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const usage = donnees?.Usages.find((u) => u.Code === code) || null;
  useEffect(() => { if (usage) setSaisie(saisieUsage(usage)); }, [code, donnees]); // eslint-disable-line react-hooks/exhaustive-deps

  const p = saisie?.Parametres;
  const formule = useMemo(() => {
    if (!p) return '';
    const termes = CAPITAUX.filter((c) => nombre(p[c.cle])).map((c) => `${c.formule} × ${texte(nombre(p[c.cle]))}‰`);
    if (Number(p.forfait_fixe)) termes.push(fcfa(p.forfait_fixe));
    const base = termes.join(' + ') || '0';
    const reduction = nombre(p.coeff_reduction);
    return reduction && reduction !== 1 ? `${termes.length > 1 ? `(${base})` : base} × ${texte(reduction)}` : base;
  }, [p]);
  const exemple = useMemo(() => {
    if (!p) return 0;
    const base = CAPITAUX.reduce((s, c) => s + (nombre(p[c.cle]) ? c.exemple * (c.facteur || 1) * nombre(p[c.cle]) / 1000 : 0), 0) + (Number(p.forfait_fixe) || 0);
    return base * (nombre(p.coeff_reduction) || 1);
  }, [p]);
  const totalParts = (saisie?.Garanties || []).filter((g) => g.Obligatoire && g.Actif).reduce((s, g) => s + nombre(g.TauxRepartition), 0);
  const modifie = usage && saisie && JSON.stringify(saisie) !== JSON.stringify(saisieUsage(usage));

  if (!donnees || !saisie) {
    return <SectionParametrage icone={Home} titre="Tarif Multirisque Habitation"><div style={{ color: 'var(--text-muted)' }}><Loader2 size={15} className="spin" /> Chargement…</div></SectionParametrage>;
  }
  const changerParam = (cle, valeur) => setSaisie((s) => ({ ...s, Parametres: { ...s.Parametres, [cle]: valeur } }));
  const changerGarantie = (c, cle, valeur) => setSaisie((s) => ({ ...s, Garanties: s.Garanties.map((g) => (g.Code === c ? { ...g, [cle]: valeur } : g)) }));
  const enregistrer = async () => {
    setEnvoi(true);
    try {
      const maj = await parametrageApi.modifierUsageMrh(code, {
        Parametres: { ...saisie.Parametres, ...Object.fromEntries(CAPITAUX.map((c) => [c.cle, String(saisie.Parametres[c.cle] || '').replace(',', '.')])),
          coeff_reduction: String(saisie.Parametres.coeff_reduction || '1').replace(',', '.') },
        Garanties: saisie.Garanties.map((g) => ({ Code: g.Code, Obligatoire: g.Obligatoire, TauxRepartition: String(g.TauxRepartition || '').replace(',', '.'), Ordre: g.Ordre, Actif: g.Actif })),
        Options: saisie.Options,
      });
      setDonnees((d) => ({ ...d, Usages: d.Usages.map((u) => (u.Code === maj.Code ? maj : u)) }));
      success(`Usage « ${maj.Libelle} » enregistré : formule ${maj.Parametres?.formule_texte}.`);
    } catch (err) {
      toastError(messageErreurApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <>
      <SectionParametrage icone={Home} titre="Usages d'habitation"
        description="Chaque usage a sa formule de prime de base, ses garanties comprises et leur part, et ses options. Choisissez l'usage à régler.">
        <div className="trp-puces" role="radiogroup" aria-label="Usage d'habitation" style={{ marginBottom: '1rem' }}>
          {donnees.Usages.map((u) => (
            <button key={u.Code} type="button" className="trp-puce" role="radio" aria-checked={u.Code === code} onClick={() => setCode(u.Code)}
              title={u.QualiteAssure}>{u.Libelle}{u.Actif ? '' : ', inactif'}</button>
          ))}
        </div>

        <div className="rb-mode">
          <div className="rb-mode-entete"><Calculator size={16} /> <strong>Prime de base</strong> <span className="rb-discret">{usage.QualiteAssure}{usage.Offre ? ` · offre ${usage.Offre}` : ''}</span></div>
          <div className="rb-grille">
            {CAPITAUX.map((c) => (
              <div key={c.cle} className="rb-champ">
                <span className="rb-champ-libelle">{c.libelle}</span>
                <span className="rb-unite" data-unite="‰">
                  <input className="form-control" inputMode="decimal" placeholder="non retenu" aria-label={`Coefficient ${c.libelle}`} value={p[c.cle]} onChange={(e) => changerParam(c.cle, e.target.value)} />
                </span>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.78rem' }}>
                  <input type="checkbox" checked={!!p[c.requis]} onChange={(e) => changerParam(c.requis, e.target.checked)} /> Demandé à la saisie
                </label>
              </div>
            ))}
            <label className="rb-champ"><span className="rb-champ-libelle">Forfait fixe ajouté</span>
              <AmountInput value={p.forfait_fixe} onChange={(n) => changerParam('forfait_fixe', Number(n) || 0)} /></label>
            <label className="rb-champ"><span className="rb-champ-libelle">Coefficient de réduction</span>
              <input className="form-control" inputMode="decimal" value={p.coeff_reduction} onChange={(e) => changerParam('coeff_reduction', e.target.value)} />
              <span className="rb-discret">1 : aucune réduction ; 0,95 : moins 5 %</span></label>
          </div>
          <div className="rb-formule"><Sparkles size={15} /> <span>Prime de base = <strong>{formule}</strong></span>
            <span className="rb-discret">Exemple avec les capitaux demandés, bâtiment 20 M, contenu 5 M, loyer 150 000, RVT 10 M : {fcfa(exemple)} F</span></div>
        </div>

        <div className="rb-mode">
          <div className="rb-mode-entete"><strong>Garanties de l'usage</strong>
            <span className={`rb-total ${Math.abs(totalParts - 100) < 0.01 ? 'juste' : 'faux'}`}>Parts des garanties comprises : {texte(Math.round(totalParts * 100) / 100)} %</span></div>
          <div className="table-wrapper">
            <table className="rb-table">
              <thead><tr><th>Garantie</th><th>Comprise</th><th className="nombre">Part de la prime de base</th><th className="nombre">Ordre</th><th>Proposée</th></tr></thead>
              <tbody>
                {saisie.Garanties.map((g) => (
                  <tr key={g.Code} className={g.Actif ? '' : 'inactive'}>
                    <td style={{ fontWeight: 700 }}>{g.Libelle}{!g.Obligatoire && g.PrimeForfait ? <span className="rb-discret"> Forfait {fcfa(g.PrimeForfait)} F</span> : null}</td>
                    <td><Interrupteur actif={!!g.Obligatoire} onChange={(v) => changerGarantie(g.Code, 'Obligatoire', v)} libelle={`${g.Libelle} comprise`} /></td>
                    <td className="nombre"><span className="rb-unite" data-unite="%"><input className="form-control" inputMode="decimal" disabled={!g.Obligatoire} aria-label={`Part ${g.Libelle}`} value={g.Obligatoire ? g.TauxRepartition : ''} onChange={(e) => changerGarantie(g.Code, 'TauxRepartition', e.target.value)} /></span></td>
                    <td className="nombre"><input className="form-control" type="number" min={0} max={99} style={{ width: 70 }} aria-label={`Ordre ${g.Libelle}`} value={g.Ordre} onChange={(e) => changerGarantie(g.Code, 'Ordre', Number(e.target.value) || 0)} /></td>
                    <td><Interrupteur actif={!!g.Actif} onChange={(v) => changerGarantie(g.Code, 'Actif', v)} libelle={`${g.Libelle} proposée`} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rb-mode">
          <div className="rb-mode-entete"><strong>Options proposées pour cet usage</strong></div>
          <div className="trp-puces">
            {donnees.Options.map((o) => {
              const actif = !!saisie.Options[o.Code];
              return (
                <button key={o.Code} type="button" className="trp-puce" aria-pressed={actif}
                  onClick={() => setSaisie((s) => ({ ...s, Options: { ...s.Options, [o.Code]: !actif } }))}>{o.Libelle}</button>
              );
            })}
          </div>
        </div>

        <div className="rb-actions">
          {modifie && <span className="rb-discret">Modifications non enregistrées</span>}
          {modifie && <button type="button" className="btn btn-secondary" onClick={() => setSaisie(saisieUsage(usage))} title="Annuler les changements"><RotateCcw size={14} /></button>}
          <button type="button" className="btn btn-primary" onClick={enregistrer} disabled={!modifie || envoi} aria-busy={envoi}><Save size={14} /> Enregistrer l'usage</button>
        </div>
      </SectionParametrage>

      <SectionParametrage icone={Tag} titre="Options" description="Ajustement de la prime quand l'option est cochée à la saisie : en ‰ de la prime de base, en % de la prime de la garantie visée, ou montant fixe.">
        <div className="table-wrapper">
          <table className="rb-table">
            <thead><tr><th>Option</th><th>Effet</th><th>Ajustement</th><th>Active</th><th aria-label="Enregistrer" /></tr></thead>
            <tbody>{donnees.Options.map((o) => <Option key={o.Code} option={o} onEnregistre={(maj) => setDonnees((d) => ({ ...d, Options: d.Options.map((x) => (x.Code === maj.Code ? maj : x)) }))} />)}</tbody>
          </table>
        </div>
      </SectionParametrage>

      <SectionParametrage icone={Tag} titre="Garanties facultatives à prime forfaitaire" description="Prime nette ajoutée quand la garantie est choisie, quel que soit le capital.">
        <div className="table-wrapper">
          <table className="rb-table">
            <thead><tr><th>Garantie</th><th>Prime nette</th><th>Proposée</th><th aria-label="Enregistrer" /></tr></thead>
            <tbody>{donnees.Forfaits.map((f) => <Forfait key={f.Code} forfait={f} onEnregistre={(maj) => setDonnees((d) => ({ ...d, Forfaits: d.Forfaits.map((x) => (x.Code === maj.Code ? { ...x, ...maj } : x)) }))} />)}</tbody>
          </table>
        </div>
      </SectionParametrage>
    </>
  );
};

export default SectionMrh;
