import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Landmark, IdCard, Printer, SlidersHorizontal, BellRing, Save, RotateCcw, Loader2, CheckCircle2 } from 'lucide-react';
import { EnTeteParametrage, SectionParametrage } from '../../../components/admin/EnTeteParametrage';
import { ChampImage } from '../../../components/admin/ChampImage';
import { TableBareme } from '../../../components/admin/TableBareme';
import { AmountInput } from '../../../components/common/AmountInput';
import { parametrageApi } from '../../../api/endpoints';
import { messageErreurApi } from '../../../utils/financeUtils';
import { chargerParametrage } from '../../../utils/parametrage';
import { useToast } from '../../../context/ToastContext';

const ONGLETS = [
  { id: 'identite', libelle: 'Identité du cabinet', icone: IdCard },
  { id: 'documents', libelle: 'Documents imprimés', icone: Printer },
  { id: 'regles', libelle: 'Règles de gestion', icone: SlidersHorizontal },
  { id: 'echeances', libelle: "Avis d'échéance", icone: BellRing },
];

// Groupes de règles de gestion (lephare_parametre.groupe), dans l'ordre d'affichage
const GROUPES_REGLES = [
  { id: 'devis', titre: 'Devis', description: 'Registre des devis et propositions.' },
  { id: 'voyage', titre: 'Voyage', description: 'Contrôles appliqués à l\'enregistrement des devis Voyage.' },
  { id: 'finance', titre: 'Encaissements et reversements', description: 'Suivi des primes encaissées et reversées aux compagnies.' },
];

const CHAMPS_IDENTITE = [
  { cle: 'RaisonSociale', libelle: 'Raison sociale', requis: true, longueur: 50, aide: 'Imprimée dans l\'en-tête des états réglementaires et de gestion.' },
  { cle: 'AdresseGeographique', libelle: 'Adresse du siège', longueur: 100, aide: 'Imprimée après « Siège social » dans l\'en-tête des états.' },
  { cle: 'AdressePostale', libelle: 'Adresse postale', longueur: 50 },
  { cle: 'TelephoneFixe', libelle: 'Téléphone fixe', longueur: 20 },
  { cle: 'TelephoneMobile', libelle: 'Téléphone mobile', longueur: 20 },
  { cle: 'NomExpediteurSms', libelle: 'Expéditeur des SMS', longueur: 11, aide: '11 caractères au plus : nom affiché sur les SMS envoyés aux clients.' },
  { cle: 'IndicatifPays', libelle: 'Indicatif téléphonique du pays', requis: true, longueur: 3, aide: 'Sans le « + » (225 pour la Côte d\'Ivoire).' },
  { cle: 'PrefixesMobile', libelle: 'Préfixes des numéros mobiles', longueur: 200, aide: 'Séparés par « ; » (ex. 01;05;07) : contrôlent la saisie des numéros mobiles.' },
  { cle: 'LongueurNumeroTelephone', libelle: 'Chiffres d\'un numéro de téléphone', type: 'entier', min: 6, max: 15 },
  { cle: 'LongueurPrefixeMobile', libelle: 'Chiffres du préfixe mobile', type: 'entier', min: 1, max: 4 },
];

const COLONNES_ECHEANCES = [
  { champ: 'produit', titre: 'Produit', type: 'produit', requis: true, filtre: true },
  { champ: 'duree_contrat_minimum', titre: 'Contrats de (jours)', type: 'entier', requis: true, min: 1 },
  { champ: 'duree_contrat_maximum', titre: 'À (jours)', type: 'entier', requis: true, min: 1 },
  { champ: 'delai_mono', titre: 'Délai — mono (jours)', type: 'entier', requis: true, min: 0, aide: 'Jours avant l\'échéance où le contrat apparaît dans les avis d\'échéance.' },
  { champ: 'delai_flotte', titre: 'Délai — flotte (jours)', type: 'entier', requis: true, min: 0 },
];

const formatDateHeure = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '');
const affichage = (p, v) => {
  if (v === '' || v === null || v === undefined) return 'vide';
  if (p.Type === 'date') return String(v).split('-').reverse().join('/');
  if (p.Type === 'booleen') return ['true', '1', 'oui'].includes(String(v).toLowerCase()) ? 'Oui' : 'Non';
  if (['montant'].includes(p.Type)) return `${Number(v).toLocaleString('fr-FR')} F`;
  return `${v}${p.Unite ? ` ${p.Unite}` : ''}`;
};

/** Une règle de gestion : saisie typée, unité, valeur d'origine, dernière modification. */
const LigneParametre = ({ parametre, onEnregistre }) => {
  const { success, error: toastError } = useToast();
  const [valeur, setValeur] = useState(parametre.Valeur);
  const [envoi, setEnvoi] = useState(false);
  useEffect(() => setValeur(parametre.Valeur), [parametre.Valeur]);
  const modifie = String(valeur ?? '') !== String(parametre.Valeur ?? '');
  const different = String(parametre.Valeur ?? '') !== String(parametre.ValeurOrigine ?? '');

  const envoyer = async (retablir) => {
    setEnvoi(true);
    try {
      const p = retablir ? await parametrageApi.retablirParametre(parametre.Cle) : await parametrageApi.modifierParametre(parametre.Cle, valeur);
      onEnregistre(p);
      success(`${parametre.Libelle} : ${retablir ? 'valeur d\'origine rétablie' : 'enregistré'}.`);
    } catch (err) {
      toastError(messageErreurApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  let saisie;
  if (parametre.Type === 'image') {
    saisie = null;
  } else if (parametre.Type === 'booleen') {
    saisie = (
      <select className="form-control" value={['true', '1'].includes(String(valeur)) ? 'true' : 'false'} onChange={(e) => setValeur(e.target.value)}>
        <option value="true">Oui</option>
        <option value="false">Non</option>
      </select>
    );
  } else if (parametre.Type === 'date') {
    saisie = <input type="date" className="form-control" value={valeur || ''} onChange={(e) => setValeur(e.target.value)} />;
  } else if (parametre.Type === 'montant') {
    saisie = <AmountInput value={valeur === '' || !Number.isFinite(Number(valeur)) ? '' : Math.round(Number(valeur))} onChange={(n) => setValeur(String(n))} suffix="FCFA" />;
  } else if (['entier', 'decimal', 'pourcentage'].includes(parametre.Type)) {
    saisie = (
      <div style={{ position: 'relative' }}>
        <input type="number" className="form-control" step={parametre.Type === 'entier' ? 1 : 'any'}
          min={parametre.Minimum ?? undefined} max={parametre.Maximum ?? undefined}
          value={valeur ?? ''} onChange={(e) => setValeur(e.target.value)} style={{ paddingRight: parametre.Unite ? '3rem' : undefined }} />
        {parametre.Unite && <span style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>{parametre.Unite}</span>}
      </div>
    );
  } else if (parametre.Type === 'texte_long') {
    saisie = <textarea className="form-control" rows={3} value={valeur || ''} onChange={(e) => setValeur(e.target.value)} />;
  } else {
    saisie = <input type="text" className="form-control" value={valeur || ''} maxLength={200} onChange={(e) => setValeur(e.target.value)} />;
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 1.2fr) minmax(200px, 1fr) auto', gap: '0.75rem 1.25rem', alignItems: 'center', padding: '0.85rem 0', borderTop: '1px solid var(--border-subtle)' }}>
      <div>
        <div style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--text-primary)' }}>{parametre.Libelle}</div>
        {parametre.Aide && <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: 2 }}>{parametre.Aide}</div>}
        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4 }}>
          Valeur d'origine : <strong>{affichage(parametre, parametre.ValeurOrigine)}</strong>
          {parametre.ModifiePar && different ? ` — modifiée le ${formatDateHeure(parametre.DateModification)} par ${parametre.ModifiePar}` : ''}
        </div>
      </div>
      <div>{saisie}</div>
      <div style={{ display: 'flex', gap: '0.4rem' }}>
        <button type="button" className="btn btn-primary" disabled={!modifie || envoi} onClick={() => envoyer(false)} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem' }}>
          {envoi ? <Loader2 size={14} className="spin" /> : <Save size={14} />} Enregistrer
        </button>
        {different && (
          <button type="button" className="btn btn-secondary" disabled={envoi} onClick={() => envoyer(true)} title="Rétablir la valeur d'origine" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem' }}>
            <RotateCcw size={14} /> Rétablir
          </button>
        )}
      </div>
    </div>
  );
};

export const CabinetSettingsPage = () => {
  const { success, error: toastError } = useToast();
  const [parametresUrl, setParametresUrl] = useSearchParams();
  const onglet = ONGLETS.some((o) => o.id === parametresUrl.get('onglet')) ? parametresUrl.get('onglet') : 'identite';
  const [parametres, setParametres] = useState([]);
  const [cabinet, setCabinet] = useState(null);
  const [identite, setIdentite] = useState({});
  const [envoi, setEnvoi] = useState(false);
  const [logos, setLogos] = useState({});

  useEffect(() => {
    parametrageApi.getParametres().then((liste) => {
      setParametres(liste);
      setLogos(Object.fromEntries(liste.filter((p) => p.Type === 'image').map((p) => [p.Cle, p.Valeur])));
    }).catch((err) => toastError(`Règles de gestion non chargées : ${messageErreurApi(err)}`));
    parametrageApi.getCabinet().then((c) => { setCabinet(c); setIdentite(c); })
      .catch((err) => toastError(`Identité du cabinet non chargée : ${messageErreurApi(err)}`));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const remplacer = (p) => {
    setParametres((liste) => liste.map((x) => (x.Cle === p.Cle ? p : x)));
    chargerParametrage(true);
  };

  const parGroupe = useMemo(() => {
    const groupes = {};
    parametres.forEach((p) => { (groupes[p.Groupe] = groupes[p.Groupe] || []).push(p); });
    Object.values(groupes).forEach((l) => l.sort((a, b) => a.Ordre - b.Ordre));
    return groupes;
  }, [parametres]);

  const identiteModifiee = cabinet && CHAMPS_IDENTITE.some((c) => String(identite[c.cle] ?? '') !== String(cabinet[c.cle] ?? ''));
  const enregistrerIdentite = async (e) => {
    e.preventDefault();
    setEnvoi(true);
    try {
      const c = await parametrageApi.modifierCabinet(Object.fromEntries(CHAMPS_IDENTITE.map((ch) => [ch.cle, identite[ch.cle]])));
      setCabinet(c);
      setIdentite(c);
      chargerParametrage(true);
      success('Identité du cabinet enregistrée.');
    } catch (err) {
      toastError(messageErreurApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  const enregistrerLogo = async (cle, valeur) => {
    setLogos((l) => ({ ...l, [cle]: valeur }));
    try {
      remplacer(await parametrageApi.modifierParametre(cle, valeur));
      success(valeur ? 'Logo enregistré : il apparaît sur les prochains documents imprimés.' : 'Logo d\'origine rétabli.');
    } catch (err) {
      toastError(messageErreurApi(err));
      setLogos((l) => ({ ...l, [cle]: parametres.find((p) => p.Cle === cle)?.Valeur || '' }));
    }
  };

  const documents = (parGroupe.documents || []);

  return (
    <div style={{ padding: '1.5rem' }}>
      <EnTeteParametrage
        icone={Landmark}
        titre="Le cabinet & règles de gestion"
        description="Identité du cabinet, ce que reprennent les documents imprimés, et les règles de gestion qui s'appliquaient jusqu'ici sans pouvoir être modifiées."
        usage="Chaque modification est enregistrée au journal d'audit et s'applique immédiatement (les documents déjà imprimés ne changent pas)."
      />

      <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        {ONGLETS.map((o) => (
          <button key={o.id} type="button" onClick={() => setParametresUrl({ onglet: o.id })} className={`btn ${onglet === o.id ? 'btn-primary' : 'btn-secondary'}`} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <o.icone size={15} /> {o.libelle}
          </button>
        ))}
      </div>

      {onglet === 'identite' && (
        <SectionParametrage icone={IdCard} titre="Identité du cabinet" description="Coordonnées du cabinet reprises par les états imprimés et par la saisie des numéros de téléphone.">
          {!cabinet ? <div style={{ color: 'var(--text-muted)' }}><Loader2 size={15} className="spin" /> Chargement…</div> : (
            <form onSubmit={enregistrerIdentite}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', columnGap: '1.1rem' }}>
                {CHAMPS_IDENTITE.map((c) => (
                  <div className="form-group" key={c.cle}>
                    <label className="form-label" htmlFor={`cab-${c.cle}`}>{c.libelle}{c.requis ? ' *' : ''}</label>
                    <input id={`cab-${c.cle}`} className="form-control" required={c.requis}
                      type={c.type === 'entier' ? 'number' : 'text'} min={c.min} max={c.max} maxLength={c.longueur}
                      value={identite[c.cle] ?? ''} onChange={(e) => setIdentite((v) => ({ ...v, [c.cle]: e.target.value }))} />
                    {c.aide && <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{c.aide}</span>}
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', alignItems: 'center' }}>
                {!identiteModifiee && <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}><CheckCircle2 size={14} /> À jour</span>}
                {identiteModifiee && <button type="button" className="btn btn-secondary" onClick={() => setIdentite(cabinet)} disabled={envoi}>Annuler les changements</button>}
                <button type="submit" className="btn btn-primary" disabled={!identiteModifiee || envoi} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  {envoi ? <Loader2 size={14} className="spin" /> : <Save size={14} />} Enregistrer
                </button>
              </div>
            </form>
          )}
        </SectionParametrage>
      )}

      {onglet === 'documents' && (
        <>
          <SectionParametrage icone={Printer} titre="Logos du cabinet" description="Logos imprimés en haut et en bas des devis, factures, conditions particulières et bordereaux. Les logos des compagnies se règlent dans « Compagnies partenaires ».">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
              {documents.filter((p) => p.Type === 'image').map((p) => (
                <ChampImage key={p.Cle} libelle={p.Libelle} aide={p.Aide} valeur={logos[p.Cle] || ''}
                  imageOrigine={p.Cle === 'documents.logo_entete' ? '/assets/print/logo-oreole-entete.png' : '/assets/print/logo-oreole-pied.png'}
                  onChange={(v) => enregistrerLogo(p.Cle, v)} />
              ))}
            </div>
          </SectionParametrage>
          <SectionParametrage icone={Printer} titre="Mentions imprimées" description="Textes repris sur les documents.">
            {documents.filter((p) => p.Type !== 'image').map((p) => <LigneParametre key={p.Cle} parametre={p} onEnregistre={remplacer} />)}
          </SectionParametrage>
        </>
      )}

      {onglet === 'regles' && GROUPES_REGLES.filter((g) => parGroupe[g.id]?.length).map((g) => (
        <SectionParametrage key={g.id} icone={SlidersHorizontal} titre={g.titre} description={g.description}>
          {parGroupe[g.id].map((p) => <LigneParametre key={p.Cle} parametre={p} onEnregistre={remplacer} />)}
        </SectionParametrage>
      ))}

      {onglet === 'echeances' && (
        <SectionParametrage icone={BellRing} titre="Délais d'avis d'échéance" description="Nombre de jours avant l'échéance où un contrat apparaît dans les avis d'échéance, selon le produit et la durée du contrat.">
          <TableBareme
            route="delaiavisecheance"
            cle="id_delai_avis_echeance"
            libelle="Délai d'avis d'échéance"
            colonnes={COLONNES_ECHEANCES}
            controle={(l) => (Number(l.duree_contrat_minimum) > Number(l.duree_contrat_maximum) ? 'La durée minimum doit être inférieure ou égale à la durée maximum.' : null)}
            tri={(a, b) => Number(a.produit) - Number(b.produit) || Number(a.duree_contrat_minimum) - Number(b.duree_contrat_minimum)}
          />
        </SectionParametrage>
      )}
    </div>
  );
};

export default CabinetSettingsPage;
