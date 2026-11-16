import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2, CalendarClock, ChevronRight, Coins, FileSpreadsheet, FolderOpen, HandCoins, HeartHandshake, Loader2, Plus, ShieldCheck, Sparkles,
  Users, Wallet,
} from 'lucide-react';
import { rafasApi } from '../../../api/endpoints';
import { useToast } from '../../../context/ToastContext';
import { aLeDroit } from '../../../utils/droits';
import { messageErreurApi } from '../../../utils/financeUtils';
import { Jauge } from '../sante/consommations/graphiques';
import { Badge, Carte, Entete, Tuile, Vide, dateFr, entier, francsCourts, libelleRang, pct, periode } from './rafasCommun';
import AssistantConvention from './AssistantConvention';

/* =========================================================================
   RAFAS : portefeuille des conventions de régime autofinancé d'assurance santé et création d'une convention (AssistantConvention.jsx : à
   partir du fichier du gestionnaire, seules les cotisations restent à saisir). GET/POST /api/rafas/conventions/ (droits rafas.view, rafas.manage).
   ========================================================================= */

const Echeance = ({ fonds }) => {
  if (!fonds) return null;
  const jours = fonds.JoursAvantEcheance;
  if (jours < 0) return <Badge ton="critique" icone={CalendarClock}>Échue depuis {entier(-jours)} jours</Badge>;
  if (fonds.JoursAvantPreavis <= 0) return <Badge ton="serieux" icone={CalendarClock} titre="Préavis de dénonciation atteint">Échéance dans {entier(jours)} jours</Badge>;
  if (jours <= 90) return <Badge ton="attention" icone={CalendarClock}>Échéance dans {entier(jours)} jours</Badge>;
  return <Badge ton="neutre" icone={CalendarClock}>Échéance le {dateFr(fonds.Echeance)}</Badge>;
};

const CarteConvention = ({ ligne, onOuvrir }) => {
  const c = ligne.Convention;
  const f = ligne.Fonds;
  const budget = f?.BudgetReel || f?.Budget;
  const taux = f ? (f.TauxEnveloppeReel ?? f.TauxEnveloppe) : null;
  const ton = taux > 1 ? 'critique' : taux > 0.8 ? 'attention' : 'normal';
  return (
    <button type="button" className={`glass-panel rafas-convention ton-${f?.Alerte ? 'critique' : ton}`} onClick={onOuvrir}>
      <div className="rafas-convention-tete">
        <span className="rafas-pastille"><Building2 size={18} aria-hidden="true" /></span>
        <div>
          <strong>{c.souscripteur}</strong>
          <span>{c.gestionnaire}{c.polices ? ` - polices ${c.polices}` : ''}</span>
        </div>
        <ChevronRight size={18} className="rafas-convention-fleche" aria-hidden="true" />
      </div>
      <div className="rafas-convention-badges">
        {c.statut === 'RESILIEE' ? <Badge ton="neutre">Résiliée</Badge> : <Badge ton="bon" icone={ShieldCheck}>En vigueur</Badge>}
        <Echeance fonds={f} />
        {f?.Alerte && <Badge ton="critique" icone={Wallet}>Appel de fonds conseillé</Badge>}
      </div>
      {ligne.Exercice && <p className="rafas-convention-periode">{libelleRang(ligne.Exercice.rang)} {periode(ligne.Exercice)}</p>}
      {f ? (
        <>
          <dl className="rafas-convention-chiffres">
            <div><dt>Bénéficiaires</dt><dd>{ligne.Beneficiaires !== null && ligne.Beneficiaires !== undefined ? entier(ligne.Beneficiaires) : '-'}</dd></div>
            <div><dt>Familles</dt><dd>{f.FamillesReelles !== null && f.FamillesReelles !== undefined ? entier(f.FamillesReelles) : entier(f.Familles)}</dd></div>
            <div><dt>Cotisations</dt><dd>{francsCourts(budget?.Cotisations)}</dd></div>
            <div><dt>Solde du fonds</dt><dd className={f.Solde < 0 ? 'rafas-negatif' : undefined}>{francsCourts(f.Solde)}</dd></div>
          </dl>
          <div className="rafas-convention-jauge">
            <div><span>Enveloppe des sinistres consommée</span><strong>{pct(taux, 0)}</strong></div>
            <Jauge taux={taux} projete={budget?.Enveloppe ? (f.Projection || 0) / budget.Enveloppe : null} ton={ton} fine
              libelle={`${pct(taux)} de l'enveloppe des sinistres consommés`} />
            <small>{`${francsCourts(f.Depenses)} remboursés sur ${f.MoisAvecDonnees} mois ; commission facturée ${francsCourts(f.CommissionEmise)}`}</small>
          </div>
        </>
      ) : <p className="cs-muet">Aucun exercice enregistré.</p>}
    </button>
  );
};

// ------------------------------------------------------------------ page
const RafasAccueilPage = () => {
  const navigate = useNavigate();
  const { error: toastError } = useToast();
  const [donnees, setDonnees] = useState(null);
  const [erreur, setErreur] = useState('');
  const [creation, setCreation] = useState(false);
  const peutGerer = aLeDroit('rafas.manage');
  const charger = useCallback(() => {
    rafasApi.conventions().then((d) => { setDonnees(d); setErreur(''); }).catch((err) => { setErreur(messageErreurApi(err)); toastError(messageErreurApi(err)); });
  }, [toastError]);
  useEffect(() => { charger(); }, [charger]);
  const conventions = donnees?.Conventions || [];
  const totaux = useMemo(() => conventions.reduce((t, l) => ({
    beneficiaires: t.beneficiaires + (l.Beneficiaires || 0),
    cotisations: t.cotisations + ((l.Fonds?.BudgetReel || l.Fonds?.Budget)?.Cotisations || 0),
    commission: t.commission + (l.Fonds?.CommissionEmise || 0),
    alertes: t.alertes + (l.Fonds?.Alerte ? 1 : 0),
  }), { beneficiaires: 0, cotisations: 0, commission: 0, alertes: 0 }), [conventions]);

  return (
    <div className="cs-page rafas-page">
      <Entete icone={HeartHandshake} titre="Régimes autofinancés d'assurance santé"
        surtitre={<><Sparkles size={13} aria-hidden="true" />Branche RAFAS</>}
        actions={peutGerer && (
          <button type="button" className="btn btn-primary rafas-bouton" onClick={() => setCreation(true)} disabled={!donnees}>
            <Plus size={16} /> Nouvelle convention
          </button>
        )}>
        <p>L'entreprise finance elle-même les soins de son personnel : le gestionnaire traite et paie les prestations, le cabinet conseille, suit le fonds
          alimenté par les appels de fonds et analyse les dépenses. La commission de courtage sur les cotisations entre dans le chiffre d'affaires.</p>
      </Entete>

      <ol className="rafas-parcours">
        {[
          { icone: ShieldCheck, titre: 'Convention et collèges', texte: 'Période, cotisation par famille de chaque collège, barème, honoraires du gestionnaire et commission du cabinet.' },
          { icone: HandCoins, titre: 'Fonds du régime', texte: "Appels de fonds au souscripteur, versements, dépenses remboursées et solde ; facture de commission." },
          { icone: FileSpreadsheet, titre: 'Fichiers du gestionnaire', texte: "Effectifs et relevés de prestations : analyse de la période, contrôles des incohérences, rapport Word." },
        ].map((x, i) => (
          <li key={x.titre} className="rafas-parcours-etape">
            <span className="rafas-parcours-icone" aria-hidden="true"><x.icone size={18} /></span>
            <div><span className="rafas-parcours-rang">{`Étape ${i + 1}`}</span><strong>{x.titre}</strong><p>{x.texte}</p></div>
          </li>
        ))}
      </ol>

      {erreur && !donnees && <Carte titre="RAFAS indisponible"><p className="rafas-erreur">{erreur}</p></Carte>}
      {!donnees && !erreur && <div className="rafas-chargement"><Loader2 size={22} className="spin" /> Chargement des conventions…</div>}

      {donnees && conventions.length > 0 && (
        <div className="cs-tuiles larges">
          <Tuile libelle="Conventions" icone={FolderOpen} nombre={conventions.length} detail="Régimes suivis par le cabinet" />
          <Tuile libelle="Bénéficiaires couverts" icone={Users} nombre={totaux.beneficiaires} detail="Derniers effectifs du gestionnaire" />
          <Tuile libelle="Cotisations de l'exercice" icone={Coins} valeur={francsCourts(totaux.cotisations)} detail="Sur l'effectif quand il est importé" />
          <Tuile libelle="Commission facturée" icone={HandCoins} ton="accent" valeur={francsCourts(totaux.commission)} detail="Exercices en cours" />
          <Tuile libelle="Fonds à réapprovisionner" icone={Wallet} ton={totaux.alertes ? 'critique' : 'bon'} nombre={totaux.alertes}
            detail={totaux.alertes ? 'Appel de fonds conseillé' : 'Aucun fonds sous son seuil'} />
        </div>
      )}

      {donnees && conventions.length > 0 && <h2 className="rafas-bande">Portefeuille des conventions</h2>}
      {donnees && (conventions.length ? (
        <div className="rafas-conventions">
          {conventions.map((l) => <CarteConvention key={l.Convention.idconvention} ligne={l} onOuvrir={() => navigate(`/user/rafas/${l.Convention.idconvention}`)} />)}
        </div>
      ) : (
        <Vide texte="Aucune convention RAFAS pour le moment. Commencez par enregistrer la convention du souscripteur, ses collèges et ses cotisations."
          action={peutGerer && <button type="button" className="btn btn-primary rafas-bouton" onClick={() => setCreation(true)}><Plus size={16} /> Nouvelle convention</button>} />
      ))}

      <AssistantConvention ouvert={creation} onFermer={() => setCreation(false)} modeles={donnees?.Modeles}
        onOuvrirExistante={(id) => { setCreation(false); navigate(`/user/rafas/${id}?onglet=convention`); }}
        onCree={(id, importe) => { setCreation(false); navigate(`/user/rafas/${id}?onglet=${importe ? 'ensemble' : 'imports'}`); }} />
    </div>
  );
};

export default RafasAccueilPage;
