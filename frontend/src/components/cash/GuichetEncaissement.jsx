import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle, ArrowLeft, ArrowRight, Banknote, CalendarClock, Check, CheckCircle2, Landmark, Lock, PackageCheck, Phone,
  Printer, RotateCcw, ScrollText, Search, ShieldCheck, Smartphone, UserRound, Wallet,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { cashApi, mineneApi, oreoleApi } from '../../api/endpoints';
import { useToast } from '../../context/ToastContext';
import { aujourdhui, correspondRecherche, dateFr, normaliserTexte } from '../../utils/financeUtils';
import { nomCabinet } from '../../utils/parametrage';
import { ouvrirApercuImpression } from '../../utils/apercuImpression';
import { printRecuEncaissement, printRecuReglementCommun } from '../../utils/exportUtils';
import { ChoixBanque } from './BanqueModal';
import { MontantSaisi } from '../common/MontantSaisi';
import { champsReglementApi, disponibleCheque, modesGuichet, natureMode, reglementVide, useChequeConnu } from './ChampsReglement';

/* =========================================================================
   GUICHET « ENCAISSEMENT DES PRIMES » (demande du 2026-11-25 : « trop d'erreurs ; propose un scénario d'encaissement
   moderne qui ne prête pas à ambiguïté »)
   Quatre étapes, chacune ne demande qu'une chose, puis le reçu :
   1. Client : recherche sur TOUTES les quittances à encaisser (GET caisse/a-encaisser/), n° d'assuré et téléphone
      pour distinguer deux homonymes ;
   2. Quittances : celles du client, cochées une à une, montant de chacune (acompte possible, jamais au-delà du reste dû) ;
      un package Oreole Santé ou MINENE se règle seul ;
   3. Règlement : aucun mode choisi d'avance ; seuls les modes qui font entrer une prime ; numéro obligatoire pour un
      chèque, un virement ou une traite ; « À l'ordre de » à choisir ; chèques déjà remis par le client proposés ;
   4. Vérification : récapitulatif en clair, alertes (acompte, quittance déjà réglée aujourd'hui), validation au montant.
   Le serveur garde ses contrôles (production/database.py save_premium_collection) : l'écran les rend visibles avant.
   ========================================================================= */

const ETAPES = ['Client', 'Quittances', 'Règlement', 'Vérification'];
const MAX_CLIENTS = 30;
const RECENTS = 8;
const ICONES_MODE = { ESP: Banknote, CHQ: ScrollText, VIR: Landmark, PYM: Smartphone };

const arrondi = (v) => Math.round((Number(v) || 0) * 100) / 100;
// Montant en francs, centimes seulement s'il y en a
export const fcfa = (v) => {
  const n = arrondi(v);
  return n.toLocaleString('fr-FR', { minimumFractionDigits: Number.isInteger(n) ? 0 : 2, maximumFractionDigits: 2 });
};
const pluriel = (n, mot) => `${n} ${mot}${n > 1 ? 's' : ''}`;
const abrege = (mode) => String(mode?.abregereglement || '').trim().toUpperCase();
const compact = (texte) => normaliserTexte(texte).replace(/[^0-9a-z]/g, '');
// Références saisies : lettres, chiffres, espaces et séparateurs usuels ; en majuscules pour un n° de chèque ou de virement
const alphanumerique = (valeur) => valeur.replace(/[^\p{L}\p{N} \-/._]/gu, '');

/* ------------------------------------------------------------------ lignes à encaisser */
// Une ligne par quittance ; un package Oreole Santé ou MINENE (une quittance par police) tient sur une ligne, le serveur
// répartit le règlement entre ses quittances
export const construireLignes = (quittances = [], packages = []) => {
  const parNumero = new Map(quittances.map((q) => [q.NumeroQuittance, q]));
  const dansPackage = new Set();
  const lignesPackages = packages.map((p) => {
    p.Quittances.forEach((q) => dansPackage.add(q.NumeroQuittance));
    const membres = p.Quittances.map((q) => parNumero.get(q.NumeroQuittance)).filter(Boolean);
    const reference = membres[0] || {};
    const regles = membres.map((m) => m.RegleAujourdhui).filter(Boolean);
    const minene = p.Branche === 'MINENE';
    const compagnies = [...new Set(p.Quittances.map((q) => q.Compagnie).filter(Boolean))];
    return {
      cle: `${minene ? 'minene' : 'oreole'}-${p.IdDevis}`,
      idClient: reference.IdClient ?? null, client: reference.Client || p.Client || '', numeroAssure: reference.NumeroAssure || '',
      telephone: reference.Telephone || '', numeroQuittance: p.NumeroQuittance, numeroPolice: p.NumeroPolice, policeCompagnie: '',
      compagnie: compagnies.join(', '), compagnies,
      idCompagnie: compagnies.length === 1 ? (p.Quittances[0]?.IdCompagnie ?? null) : null,
      produit: minene ? 'Package MINENE' : 'Package Oreole Santé', avenant: reference.Avenant || '', codeAvenant: reference.CodeAvenant || '',
      dateEmission: p.DateEmission || reference.DateEmission || '', dateEffet: reference.DateEffet || '', dateExpiration: reference.DateExpiration || '',
      prime: Number(p.PrimeTtc) || 0, encaisse: Number(p.Encaisse) || 0, reste: Number(p.Reste) || 0,
      regleAujourdhui: regles.length
        ? { Montant: regles.reduce((t, r) => t + (Number(r.Montant) || 0), 0), Heure: regles.map((r) => r.Heure).sort().pop() || '', Par: regles[0].Par }
        : null,
      package: p, minene, idContrat: reference.IdContrat ?? null,
    };
  });
  const simples = quittances.filter((q) => !dansPackage.has(q.NumeroQuittance)).map((q) => ({
    cle: `q-${q.NumeroQuittance}`, idClient: q.IdClient, client: q.Client || '', numeroAssure: q.NumeroAssure || '', telephone: q.Telephone || '',
    numeroQuittance: q.NumeroQuittance, numeroPolice: q.NumeroPolice, policeCompagnie: q.PoliceCompagnie || '',
    compagnie: q.Compagnie || '', compagnies: q.Compagnie ? [q.Compagnie] : [], idCompagnie: q.IdCompagnie ?? null,
    produit: q.Produit || '', avenant: q.Avenant || '', codeAvenant: q.CodeAvenant || '',
    dateEmission: q.DateEmission || '', dateEffet: q.DateEffet || '', dateExpiration: q.DateExpiration || '',
    prime: Number(q.PrimeTtc) || 0, encaisse: Number(q.Encaisse) || 0, reste: Number(q.Reste) || 0,
    regleAujourdhui: q.RegleAujourdhui || null, package: null, idContrat: q.IdContrat ?? null,
  }));
  return [...lignesPackages, ...simples]
    .sort((a, b) => String(b.dateEmission).localeCompare(String(a.dateEmission)) || (b.idContrat || 0) - (a.idContrat || 0));
};

export const cleClient = (ligne) => (ligne.idClient ? `c${ligne.idClient}` : `n${normaliserTexte(ligne.client)}`);
// Numéros portés par la ligne (police, quittance, police de la compagnie, polices et quittances d'un package)
const numerosLigne = (l) => [l.numeroPolice, l.numeroQuittance, l.policeCompagnie,
  ...(l.package ? l.package.Quittances.flatMap((q) => [q.NumeroPolice, q.NumeroQuittance]) : [])].filter(Boolean);
export const champsRecherche = (l) => [l.client, l.numeroAssure, l.telephone, l.compagnie, l.produit, l.avenant, ...numerosLigne(l)];

const grouperParClient = (lignes) => {
  const groupes = new Map();
  lignes.forEach((l) => {
    const cle = cleClient(l);
    if (!groupes.has(cle)) {
      groupes.set(cle, { cle, idClient: l.idClient, client: l.client, numeroAssure: l.numeroAssure, telephone: l.telephone, lignes: [] });
    }
    groupes.get(cle).lignes.push(l);
  });
  return [...groupes.values()].map((g) => ({
    ...g,
    reste: arrondi(g.lignes.reduce((t, l) => t + l.reste, 0)),
    compagnies: [...new Set(g.lignes.flatMap((l) => l.compagnies))],
    derniere: g.lignes.map((l) => l.dateEmission).sort().pop() || '',
  }));
};

// Message d'erreur du serveur : { erreur, details } (caisse, packages), { detail }, { error } ou erreurs de validation
const messageErreur = (err) => {
  const d = err.response?.data;
  if (d?.erreur) return d.details ? `${d.erreur} ${d.details}` : d.erreur;
  if (d?.detail) return d.detail;
  if (d?.error) return d.error;
  if (d && typeof d === 'object') {
    const premier = Object.values(d).flat()[0];
    if (typeof premier === 'string') return premier;
  }
  return 'L\'encaissement n\'a pas pu être enregistré. Veuillez réessayer.';
};

const initiales = (nom) => String(nom || '?').trim().split(/\s+/).slice(0, 2).map((m) => m[0]).join('').toUpperCase();
const periode = (l) => (l.dateEffet ? `du ${dateFr(l.dateEffet)}${l.dateExpiration ? ` au ${dateFr(l.dateExpiration)}` : ''}` : '');
const libelleMouvement = (l) => {
  const avenant = String(l.avenant || '').trim();
  return avenant ? avenant.charAt(0).toUpperCase() + avenant.slice(1).toLowerCase() : '';
};

/* ------------------------------------------------------------------ montant saisi */
// Montant en francs regroupé par milliers pendant la frappe, centimes acceptés (« 125 000 », « 4 684 163,34 ») : MontantSaisi
const ChampMontant = ({ valeur, onChange, id, disabled, invalide, libelle, autoFocus }) => (
  <div className="guichet-montant">
    <MontantSaisi id={id} value={valeur || ''} disabled={disabled} autoFocus={autoFocus} aria-label={libelle} aria-invalid={invalide || undefined}
      onFocus={(e) => e.target.select()} onChange={(n) => onChange(n === null ? 0 : arrondi(n))} />
    <span aria-hidden="true">F</span>
  </div>
);

/* ------------------------------------------------------------------ guichet */
// lignes : construireLignes(...) ; modes, banques : listes de référence ; demande : { cleLigne } ou { cleClient } pour ouvrir
// directement un client (bouton « Encaisser » de la liste, lien d'une fiche contrat) ; chequeAReutiliser : chèque annulé
// remis en service depuis le Portefeuille des règlements ; onEnregistre(reponse, reglement) après chaque encaissement
export const GuichetEncaissement = ({
  lignes, chargement, erreurChargement, onRecharger, modes, banques, onBanqueCreee, demande, chequeAReutiliser, onEnregistre,
}) => {
  const { error: toastError } = useToast();
  const [etape, setEtape] = useState(1);
  const [recherche, setRecherche] = useState('');
  const [cleClientChoisi, setCleClientChoisi] = useState(null);
  // Quittances cochées : clé de la ligne -> montant réglé
  const [selection, setSelection] = useState({});
  // Quittances réglées par acompte (le client paie sa prime en plusieurs fois) : clé de la ligne -> vrai ; sinon totalité
  const [acomptes, setAcomptes] = useState({});
  const [reglement, setReglement] = useState(() => ({ ...reglementVide(), ordre: '' }));
  const [tentative, setTentative] = useState(false);
  const [doublonConfirme, setDoublonConfirme] = useState(false);
  const [enregistrement, setEnregistrement] = useState(false);
  const [resultat, setResultat] = useState(null);
  const [chequesClient, setChequesClient] = useState([]);
  const champRecherche = useRef(null);

  const { principaux, autres } = useMemo(() => modesGuichet(modes), [modes]);
  const tousModes = useMemo(() => [...principaux, ...autres], [principaux, autres]);
  const modeChoisi = tousModes.find((m) => String(m.idmodeencaissement) === String(reglement.idMode));
  const nature = natureMode(modeChoisi);
  const changer = (champ, valeur) => setReglement((r) => ({ ...r, [champ]: valeur }));

  /* ---------- étape 1 : client */
  const groupes = useMemo(() => grouperParClient(lignes), [lignes]);
  const resultats = useMemo(() => {
    const texte = recherche.trim();
    if (!texte) {
      return { groupes: [...groupes].sort((a, b) => b.derniere.localeCompare(a.derniere)).slice(0, RECENTS), total: 0, recents: true, ciblees: {} };
    }
    const cle = compact(texte);
    const ciblees = {};
    const trouves = groupes.filter((g) => {
      let trouve = false;
      g.lignes.forEach((l) => {
        if (correspondRecherche(texte, champsRecherche(l))) trouve = true;
        // N° de police ou de quittance saisi : la quittance visée sera cochée d'office
        if (cle.length >= 4 && numerosLigne(l).some((n) => compact(n).includes(cle))) {
          trouve = true;
          ciblees[g.cle] = [...(ciblees[g.cle] || []), l.cle];
        }
      });
      return trouve;
    }).sort((a, b) => (ciblees[b.cle] ? 1 : 0) - (ciblees[a.cle] ? 1 : 0) || b.derniere.localeCompare(a.derniere));
    return { groupes: trouves.slice(0, MAX_CLIENTS), total: trouves.length, recents: false, ciblees };
  }, [groupes, recherche]);

  const groupeChoisi = groupes.find((g) => g.cle === cleClientChoisi) || null;
  const lignesClient = groupeChoisi ? groupeChoisi.lignes : [];

  const ouvrirClient = (cle, cochees = []) => {
    const groupe = groupes.find((g) => g.cle === cle);
    if (!groupe) return;
    setCleClientChoisi(cle);
    // Une seule quittance : cochée d'office ; sinon celles visées par la recherche ou la demande
    const aCocher = groupe.lignes.length === 1 ? [groupe.lignes[0].cle] : cochees;
    const premierPackage = aCocher.map((c) => groupe.lignes.find((l) => l.cle === c)).find((l) => l?.package);
    const retenues = premierPackage ? [premierPackage.cle] : aCocher;
    setSelection(Object.fromEntries(retenues.map((c) => [c, groupe.lignes.find((l) => l.cle === c)?.reste || 0])));
    setAcomptes({});
    setReglement({ ...reglementVide(String(groupe.client || '').slice(0, 50)), ordre: '' });
    setTentative(false);
    setDoublonConfirme(false);
    setResultat(null);
    setEtape(2);
  };

  const nouveauClient = () => {
    setCleClientChoisi(null);
    setSelection({});
    setAcomptes({});
    setReglement({ ...reglementVide(), ordre: '' });
    setResultat(null);
    setTentative(false);
    setDoublonConfirme(false);
    setRecherche('');
    setEtape(1);
    setTimeout(() => champRecherche.current?.focus(), 50);
  };

  // Demande venue de la liste ou d'une fiche contrat : client ouvert, quittance cochée. Une seule fois : le rechargement qui
  // suit l'encaissement ne doit pas rouvrir le client par-dessus l'écran du reçu
  const demandeTraitee = useRef(null);
  useEffect(() => {
    if (!demande || !lignes.length || demandeTraitee.current === demande) return;
    demandeTraitee.current = demande;
    const ligne = demande.cleLigne ? lignes.find((l) => l.cle === demande.cleLigne) : null;
    const cle = ligne ? cleClient(ligne) : demande.cleClient;
    if (cle) ouvrirClient(cle, ligne ? [ligne.cle] : []);
    else if (demande.cleLigne) toastError('Cette quittance n\'est plus à encaisser.');
  }, [demande, lignes.length]); // eslint-disable-line react-hooks/exhaustive-deps

  /* ---------- étape 2 : quittances */
  const choisies = lignesClient.filter((l) => selection[l.cle] !== undefined);
  const total = arrondi(choisies.reduce((t, l) => t + (Number(selection[l.cle]) || 0), 0));
  // Totalité : le reste dû, sans saisie. Acompte : un montant à saisir, inférieur au reste dû
  const erreurMontant = (l) => {
    const m = selection[l.cle];
    if (m === undefined) return '';
    if (Number.isNaN(m) || !(m > 0)) return acomptes[l.cle] ? 'Montant de l’acompte à saisir' : 'Montant à saisir';
    if (m > l.reste) return `Au plus ${fcfa(l.reste)} F`;
    if (acomptes[l.cle] && m >= l.reste) return `Égal au reste dû : choisissez « Totalité »`;
    return '';
  };
  const choisirPaiement = (ligne, acompte) => {
    setAcomptes((a) => {
      const { [ligne.cle]: _ancien, ...autres } = a;
      return acompte ? { ...autres, [ligne.cle]: true } : autres;
    });
    setSelection((s) => ({ ...s, [ligne.cle]: acompte ? 0 : ligne.reste }));
    setDoublonConfirme(false);
  };
  const selectionValide = choisies.length > 0 && choisies.every((l) => !erreurMontant(l));
  const packageChoisi = choisies.find((l) => l.package) || null;

  const basculer = (ligne) => {
    // Cochée de nouveau : réglée en totalité, l'acompte se choisit ensuite
    setAcomptes(({ [ligne.cle]: _acompte, ...autres }) => autres);
    setSelection((actuelle) => {
      if (actuelle[ligne.cle] !== undefined) {
        const { [ligne.cle]: _retiree, ...reste } = actuelle;
        return reste;
      }
      // Un package se règle seul ; une quittance ordinaire ne se joint pas à un package
      if (ligne.package) return { [ligne.cle]: ligne.reste };
      const sansPackage = Object.fromEntries(Object.entries(actuelle).filter(([c]) => !lignesClient.find((l) => l.cle === c)?.package));
      return { ...sansPackage, [ligne.cle]: ligne.reste };
    });
    setDoublonConfirme(false);
  };
  const toutCocher = () => {
    const ordinaires = lignesClient.filter((l) => !l.package);
    setSelection(Object.fromEntries(ordinaires.map((l) => [l.cle, l.reste])));
    setAcomptes({});
  };

  /* ---------- étape 3 : règlement */
  const compagniesChoisies = [...new Set(choisies.flatMap((l) => l.compagnies))];
  // Package Oreole Santé, ou MINENE de plusieurs compagnies : toujours à l'ordre du cabinet (le serveur le refuse sinon)
  const ordreImpose = packageChoisi && (!packageChoisi.minene || packageChoisi.compagnies.length > 1) ? 'CABINET' : '';
  const avecOrdre = nature.bancaire && !nature.especes;
  const ordre = ordreImpose || reglement.ordre;

  useEffect(() => {
    if (etape !== 3 || !groupeChoisi?.idClient) { if (etape === 1) setChequesClient([]); return undefined; }
    let vivant = true;
    cashApi.chequesClient(groupeChoisi.idClient)
      .then((r) => { if (vivant) setChequesClient(r?.Cheques || []); })
      .catch(() => { if (vivant) setChequesClient([]); });
    return () => { vivant = false; };
  }, [etape, groupeChoisi?.idClient]);

  const chequeConnu = useChequeConnu({
    actif: nature.cheque, idBanque: reglement.idBanque, numero: reglement.numero,
    onMontantInitial: (montant) => changer('montantInitialCheque', montant),
    onNumero: (numero) => changer('numero', numero),
  });
  const chequeAnnule = Boolean(chequeConnu?.existe && chequeConnu.annule);
  const disponible = nature.cheque ? disponibleCheque(chequeConnu, reglement.montantInitialCheque) : null;
  const montantChequeVerrouille = Boolean(chequeConnu?.existe && !chequeConnu.montant_modifiable);
  const chequeDuClient = chequesClient.find((c) => String(c.IdBanque) === String(reglement.idBanque) && c.Numero === reglement.numero.trim());

  const choisirMode = (mode) => {
    const n = natureMode(mode);
    setReglement((r) => {
      const base = { ...reglementVide(r.nomEmetteur), ordre: '', idMode: String(mode.idmodeencaissement) };
      // Chèque annulé remis en service depuis le Portefeuille des règlements : proposé tel quel
      if (n.cheque && chequeAReutiliser && !packageChoisi) {
        return { ...base, idBanque: String(chequeAReutiliser.banque), numero: chequeAReutiliser.numero_cheque,
          montantInitialCheque: String(Math.round(Number(chequeAReutiliser.montant_initial) || 0)) };
      }
      return base;
    });
    setTentative(false);
  };
  // Chèque annulé à réutiliser : le mode Chèque est proposé dès l'étape du règlement
  useEffect(() => {
    if (etape === 3 && !reglement.idMode && chequeAReutiliser && !packageChoisi) {
      const cheque = principaux.find((m) => abrege(m) === 'CHQ');
      if (cheque) choisirMode(cheque);
    }
  }, [etape]); // eslint-disable-line react-hooks/exhaustive-deps

  const prendreCheque = (c) => setReglement((r) => ({ ...r, idBanque: String(c.IdBanque), numero: c.Numero }));

  const erreursReglement = () => {
    const e = [];
    if (!modeChoisi) return ['Choisissez le mode de paiement.'];
    if (nature.bancaire && !nature.especes) {
      if (!reglement.idBanque || String(reglement.idBanque) === '1') e.push('Choisissez la banque.');
      if (!reglement.numero.trim()) e.push(`Saisissez le ${nature.libelleNumero.toLowerCase()}.`);
    }
    if (nature.cheque) {
      if (!(Number(reglement.montantInitialCheque) > 0) && !chequeConnu?.existe) e.push('Saisissez le montant du chèque.');
      else if (disponible !== null && total > disponible + 0.001) {
        e.push(`Le chèque ne couvre pas le total : ${fcfa(Math.max(0, disponible))} F disponibles pour ${fcfa(total)} F à encaisser.`);
      }
      if (!reglement.dateReceptionCheque) e.push('Saisissez la date de réception du chèque.');
      else if (reglement.dateReceptionCheque > aujourdhui()) e.push('La date de réception du chèque ne peut pas dépasser aujourd\'hui.');
    }
    if (avecOrdre && !ordre) e.push('Indiquez à l\'ordre de qui est le règlement.');
    if (avecOrdre && ordre === 'COMPAGNIE' && compagniesChoisies.length > 1) {
      e.push('À l\'ordre d\'une compagnie, le règlement ne couvre que ses quittances : décochez celles des autres compagnies.');
    }
    if (nature.mobile && !reglement.numeroRecuOperateur.trim()) e.push('Saisissez le n° du reçu de l\'opérateur.');
    if (nature.compensation) {
      if (!reglement.referenceCompensation.trim()) e.push('Saisissez la référence de la compensation.');
      if (!reglement.motifCompensation.trim()) e.push('Saisissez le motif de la compensation.');
    }
    if (!reglement.nomEmetteur.trim()) e.push(nature.cheque ? 'Saisissez le tireur du chèque.' : 'Saisissez le nom de la personne qui paie.');
    return e;
  };
  const erreurs = etape >= 3 ? erreursReglement() : [];

  /* ---------- étape 4 : vérification */
  const lignesAcompte = choisies.filter((l) => (Number(selection[l.cle]) || 0) < l.reste);
  const dejaRegles = choisies.filter((l) => l.regleAujourdhui);
  const alertes = [
    ...lignesAcompte.map((l) => `Acompte : la quittance ${l.numeroQuittance} restera due de ${fcfa(l.reste - selection[l.cle])} F.`),
    ...(chequeDuClient?.Statut === 'A_DEPOSER' && chequeDuClient.DateEcheance > aujourdhui()
      ? [`Chèque prévu au dépôt le ${dateFr(chequeDuClient.DateEcheance)} : il sera compté encaissé aujourd'hui.`] : []),
    ...(chequeAnnule ? [`Chèque annulé${chequeConnu.date_annulation ? ` le ${dateFr(chequeConnu.date_annulation)}` : ''} : il sera remis en service.`] : []),
    ...(nature.cheque && reglement.dateCheque && reglement.dateCheque > aujourdhui() ? [`Chèque daté du ${dateFr(reglement.dateCheque)}, postérieur à aujourd'hui.`] : []),
  ];
  const libelleMode = modeChoisi ? String(modeChoisi.libellemodepaiement || '').trim() : '';
  const nomBanque = banques.find((b) => String(b.idbanque) === String(reglement.idBanque))?.libelle || '';
  const referenceTexte = () => {
    if (nature.bancaire && !nature.especes) return `${nature.libelleNumero.replace('Numéro', 'n°')} ${reglement.numero.trim()}${nomBanque ? ` - ${String(nomBanque).trim()}` : ''}`;
    if (nature.mobile) return `reçu ${reglement.numeroRecuOperateur.trim()}`;
    if (nature.especes && reglement.numeroBordereau.trim()) return `bordereau ${reglement.numeroBordereau.trim()}`;
    if (nature.compensation) return `référence ${reglement.referenceCompensation.trim()}`;
    return '';
  };
  const libelleOrdre = ordre === 'COMPAGNIE' ? 'Compagnie' : nomCabinet();
  const resteCheque = nature.cheque && disponible !== null ? arrondi(disponible - total) : null;

  const valider = async () => {
    if (enregistrement || !groupeChoisi) return;
    const fenetre = ouvrirApercuImpression();
    if (fenetre) fenetre.document.write('<p style="font-family:Arial;padding:20px;">Enregistrement de l\'encaissement…</p>');
    setEnregistrement(true);
    try {
      const [annee, mois, jour] = aujourdhui().split('-');
      const charge = {
        ...champsReglementApi({ ...reglement, ordre }, modeChoisi),
        date_encaissement: `${jour}-${mois}-${annee}`,
        montant_total: total,
      };
      const res = packageChoisi
        ? await (packageChoisi.minene ? mineneApi : oreoleApi).encaisser(packageChoisi.package.IdDevis, charge)
        : await cashApi.collectPremium({
          ...charge,
          liste_quittance: choisies.map((l) => ({ numero_quittance: l.numeroQuittance, montant_encaissement: arrondi(selection[l.cle]) })),
        });
      const idEncaissement = res.data?.id_encaissement;
      const recu = { idEncaissement, commun: Boolean(packageChoisi) || choisies.length > 1 };
      setResultat({
        recu, total, client: groupeChoisi.client, mode: libelleMode, reference: referenceTexte(), message: res.data?.message || '',
        quittances: choisies.map((l) => ({ cle: l.cle, numero: l.numeroQuittance, police: l.numeroPolice, montant: selection[l.cle], solde: selection[l.cle] >= l.reste })),
        chequeReutilise: Boolean(res.data?.cheque_reutilise), soldeCheque: res.data?.solde_restant_cheque,
      });
      setEtape(5);
      onEnregistre?.(res.data, reglement);
      await imprimerRecu(recu, fenetre);
    } catch (err) {
      console.error('Erreur encaissement :', err.response?.data || err);
      if (fenetre) fenetre.close();
      toastError(messageErreur(err));
    } finally {
      setEnregistrement(false);
    }
  };

  const imprimerRecu = async (recu, fenetreOuverte = null) => {
    const fenetre = fenetreOuverte || ouvrirApercuImpression();
    if (!recu?.idEncaissement) { if (fenetre) fenetre.close(); return; }
    if (recu.commun) {
      await printRecuReglementCommun(recu.idEncaissement, fenetre);
      return;
    }
    const [detail] = await cashApi.getDetailsEncaissement(recu.idEncaissement);
    await printRecuEncaissement(detail?.iddetailencaissement, fenetre);
  };

  const resteClient = groupeChoisi ? groupeChoisi.lignes : [];

  /* ------------------------------------------------------------------ rendu */
  const resumeEtape = (n) => {
    if (n === 1 && groupeChoisi) return groupeChoisi.client;
    if (n === 2 && choisies.length) return `${pluriel(choisies.length, 'quittance')} · ${fcfa(total)} F`;
    if (n === 3 && modeChoisi && etape > 3) return libelleMode;
    return '';
  };

  return (
    <div className="guichet">
      {etape <= 4 && (
        <ol className="guichet-etapes" aria-label="Étapes de l'encaissement">
          {ETAPES.map((libelle, i) => {
            const n = i + 1;
            const etat = n < etape ? 'faite' : n === etape ? 'active' : 'a-venir';
            return (
              <li key={libelle} className={etat} aria-current={n === etape ? 'step' : undefined}>
                <button type="button" disabled={n >= etape} onClick={() => setEtape(n)} title={n < etape ? `Revenir à l'étape ${libelle}` : undefined}>
                  <span className="guichet-etape-num">{n < etape ? <Check size={14} /> : n}</span>
                  <span className="guichet-etape-texte">
                    <span>{libelle}</span>
                    {resumeEtape(n) && <small>{resumeEtape(n)}</small>}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      )}

      {/* ---------------------------------------------------------------- 1. client */}
      {etape === 1 && (
        <section className="guichet-volet" aria-labelledby="guichet-titre-1">
          <h2 id="guichet-titre-1" className="guichet-titre">Qui paie ?</h2>
          <div className="guichet-recherche">
            <Search size={18} aria-hidden="true" />
            <input ref={champRecherche} type="search" autoFocus value={recherche} onChange={(e) => setRecherche(e.target.value)}
              placeholder="Nom du client, n° de police, de quittance, téléphone, n° d'assuré…" aria-label="Rechercher le client"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && resultats.groupes.length === 1) ouvrirClient(resultats.groupes[0].cle, resultats.ciblees[resultats.groupes[0].cle] || []);
              }} />
          </div>
          {chargement && <div className="guichet-vide">Chargement des quittances à encaisser…</div>}
          {!chargement && erreurChargement && (
            <div className="guichet-vide erreur">
              <AlertTriangle size={18} aria-hidden="true" /> {erreurChargement}
              <button type="button" className="btn btn-secondary" onClick={onRecharger}><RotateCcw size={14} /> Réessayer</button>
            </div>
          )}
          {!chargement && !erreurChargement && (
            <>
              <div className="guichet-sous-titre">
                {resultats.recents ? 'Derniers contrats émis' : `${pluriel(resultats.total, 'client')} trouvé${resultats.total > 1 ? 's' : ''}`}
                {resultats.total > MAX_CLIENTS && ` : les ${MAX_CLIENTS} premiers, précisez la recherche`}
              </div>
              <div className="guichet-clients">
                {resultats.groupes.map((g, i) => (
                  <button key={g.cle} type="button" className={`guichet-client${resultats.ciblees[g.cle] ? ' cible' : ''}`} style={{ animationDelay: `${Math.min(i, 10) * 25}ms` }}
                    onClick={() => ouvrirClient(g.cle, resultats.ciblees[g.cle] || [])}>
                    <span className="guichet-avatar" aria-hidden="true">{initiales(g.client)}</span>
                    <span className="guichet-client-identite">
                      <strong>{g.client || 'Client sans nom'}</strong>
                      <span>
                        {g.numeroAssure && <span>N° {g.numeroAssure}</span>}
                        {g.telephone && <span><Phone size={12} aria-hidden="true" /> {g.telephone}</span>}
                        {!g.numeroAssure && !g.telephone && g.idClient && <span>Client {g.idClient}</span>}
                      </span>
                      <span className="guichet-muet">{g.compagnies.slice(0, 3).join(', ')}{g.compagnies.length > 3 ? '…' : ''}</span>
                    </span>
                    <span className="guichet-client-reste">
                      <strong>{fcfa(g.reste)} F</strong>
                      <span>{pluriel(g.lignes.length, 'quittance')}</span>
                    </span>
                    <ArrowRight size={16} aria-hidden="true" className="guichet-fleche" />
                  </button>
                ))}
                {!resultats.groupes.length && (
                  <div className="guichet-vide">
                    {recherche.trim() ? 'Aucune quittance à encaisser ne correspond.' : 'Aucune quittance à encaisser.'}
                    {recherche.trim() && <Link to="/user/cash/recherche" className="btn btn-secondary"><Search size={14} /> Déjà réglée ? Rechercher un règlement</Link>}
                  </div>
                )}
              </div>
            </>
          )}
        </section>
      )}

      {etape >= 2 && etape <= 4 && !groupeChoisi && !chargement && (
        <section className="guichet-volet">
          <div className="guichet-vide">
            Ce client n'a plus de quittance à encaisser.
            <button type="button" className="btn btn-primary" onClick={nouveauClient}><UserRound size={16} /> Nouveau client</button>
          </div>
        </section>
      )}

      {/* ---------------------------------------------------------------- 2. quittances */}
      {etape === 2 && groupeChoisi && (
        <section className="guichet-volet" aria-labelledby="guichet-titre-2">
          <div className="guichet-carte-client">
            <span className="guichet-avatar grand" aria-hidden="true">{initiales(groupeChoisi.client)}</span>
            <div>
              <strong>{groupeChoisi.client}</strong>
              <span className="guichet-muet">
                {[groupeChoisi.numeroAssure && `N° ${groupeChoisi.numeroAssure}`, groupeChoisi.telephone].filter(Boolean).join(' · ')}
              </span>
            </div>
            <button type="button" className="btn btn-secondary" onClick={nouveauClient}><UserRound size={14} /> Changer de client</button>
          </div>
          <div className="guichet-entete-liste">
            <h2 id="guichet-titre-2" className="guichet-titre">Quelles quittances règle-t-il ?</h2>
            {lignesClient.filter((l) => !l.package).length > 1 && (
              <button type="button" className="btn btn-secondary" onClick={toutCocher}>Tout cocher</button>
            )}
          </div>
          <div className="guichet-quittances" role="group" aria-label="Quittances à encaisser du client">
            {lignesClient.map((l) => {
              const cochee = selection[l.cle] !== undefined;
              const erreur = erreurMontant(l);
              const montant = selection[l.cle];
              return (
                <div key={l.cle} className={`guichet-quittance${cochee ? ' cochee' : ''}${erreur ? ' en-erreur' : ''}`}>
                  <label className="guichet-quittance-tete">
                    <input type="checkbox" checked={cochee} onChange={() => basculer(l)} />
                    <span className="guichet-quittance-ident">
                      <strong>Police {l.numeroPolice}</strong>
                      <span className="guichet-muet">Quittance {l.numeroQuittance}{l.policeCompagnie ? ` · police compagnie ${l.policeCompagnie}` : ''}</span>
                      <span>
                        {l.package && <PackageCheck size={13} aria-hidden="true" />} {l.produit}{l.compagnie ? ` · ${l.compagnie}` : ''}
                        {libelleMouvement(l) ? ` · ${libelleMouvement(l)}` : ''}{periode(l) ? ` · ${periode(l)}` : ''}
                      </span>
                    </span>
                    <span className="guichet-quittance-chiffres">
                      <span className="guichet-muet">Prime {fcfa(l.prime)} F{l.encaisse > 0 ? ` · acomptes déjà versés ${fcfa(l.encaisse)} F` : ''}</span>
                      <strong>Reste dû {fcfa(l.reste)} F</strong>
                    </span>
                  </label>
                  {l.package && (
                    <div className="guichet-package">
                      {l.package.Quittances.map((q) => (
                        <span key={q.NumeroQuittance}>{q.Produit} - {q.Compagnie} : {fcfa(q.Reste)} F</span>
                      ))}
                      <span className="guichet-muet">Se règle seul, en un règlement réparti entre ses polices.</span>
                    </div>
                  )}
                  {l.regleAujourdhui && (
                    <div className="guichet-alerte-ligne">
                      <AlertTriangle size={14} aria-hidden="true" />
                      Déjà réglé aujourd'hui : {fcfa(l.regleAujourdhui.Montant)} F{l.regleAujourdhui.Heure ? ` à ${l.regleAujourdhui.Heure}` : ''}{l.regleAujourdhui.Par ? ` par ${l.regleAujourdhui.Par}` : ''}
                    </div>
                  )}
                  {cochee && (
                    <div className="guichet-quittance-montant">
                      <div className="guichet-paiement" role="radiogroup" aria-label={`Paiement de la quittance ${l.numeroQuittance}`}>
                        <button type="button" role="radio" aria-checked={!acomptes[l.cle]} className={!acomptes[l.cle] ? 'choisi' : ''} onClick={() => choisirPaiement(l, false)}>
                          Totalité · {fcfa(l.reste)} F
                        </button>
                        <button type="button" role="radio" aria-checked={Boolean(acomptes[l.cle])} className={acomptes[l.cle] ? 'choisi' : ''} onClick={() => choisirPaiement(l, true)}>
                          Acompte
                        </button>
                      </div>
                      {acomptes[l.cle] && (
                        <>
                          <label htmlFor={`montant-${l.cle}`}>Montant de l’acompte</label>
                          <ChampMontant id={`montant-${l.cle}`} valeur={montant} libelle={`Montant de l’acompte sur la quittance ${l.numeroQuittance}`} invalide={Boolean(erreur)}
                            autoFocus onChange={(v) => setSelection((s) => ({ ...s, [l.cle]: v }))} />
                        </>
                      )}
                      {erreur
                        ? <span className="guichet-erreur">{erreur}</span>
                        : acomptes[l.cle]
                          ? <span className="guichet-acompte">Reste après cet acompte : {fcfa(l.reste - montant)} F</span>
                          : <span className="guichet-solde"><Check size={13} /> Soldée</span>}
                    </div>
                  )}
                </div>
              );
            })}
            {!lignesClient.length && <div className="guichet-vide">Ce client n'a plus de quittance à encaisser.</div>}
          </div>
          <div className="guichet-barre">
            <span>{choisies.length ? <>{pluriel(choisies.length, 'quittance')} · Total à encaisser <strong>{fcfa(total)} F</strong></> : 'Cochez au moins une quittance.'}</span>
            <button type="button" className="btn btn-primary" disabled={!selectionValide} onClick={() => { setTentative(false); setEtape(3); }}>
              Continuer <ArrowRight size={16} />
            </button>
          </div>
        </section>
      )}

      {/* ---------------------------------------------------------------- 3. règlement */}
      {etape === 3 && groupeChoisi && (
        <section className="guichet-volet" aria-labelledby="guichet-titre-3">
          <div className="guichet-entete-liste">
            <h2 id="guichet-titre-3" className="guichet-titre">Comment paie-t-il {fcfa(total)} F ?</h2>
          </div>
          <div className="guichet-modes" role="radiogroup" aria-label="Mode de paiement">
            {principaux.map((m) => {
              const Icone = ICONES_MODE[abrege(m)] || Wallet;
              const choisi = String(m.idmodeencaissement) === String(reglement.idMode);
              return (
                <button key={m.idmodeencaissement} type="button" role="radio" aria-checked={choisi} className={`guichet-mode${choisi ? ' choisi' : ''}`}
                  onClick={() => choisirMode(m)}>
                  <Icone size={22} aria-hidden="true" />
                  <span>{String(m.libellemodepaiement || '').trim()}</span>
                </button>
              );
            })}
            {autres.length > 0 && (
              <select className={`form-control guichet-mode-autre${autres.some((m) => String(m.idmodeencaissement) === String(reglement.idMode)) ? ' choisi' : ''}`}
                aria-label="Autre mode de paiement"
                value={autres.some((m) => String(m.idmodeencaissement) === String(reglement.idMode)) ? reglement.idMode : ''}
                onChange={(e) => { const m = autres.find((x) => String(x.idmodeencaissement) === e.target.value); if (m) choisirMode(m); }}>
                <option value="">Autre mode</option>
                {autres.map((m) => <option key={m.idmodeencaissement} value={m.idmodeencaissement}>{String(m.libellemodepaiement || '').trim()}</option>)}
              </select>
            )}
          </div>

          {modeChoisi && (
            <div className="guichet-champs" key={reglement.idMode}>
              {nature.cheque && chequesClient.length > 0 && (
                <div className="guichet-cheques-client">
                  <span className="form-label">Chèques déjà remis par ce client</span>
                  <div>
                    {chequesClient.map((c) => {
                      const actif = String(c.IdBanque) === String(reglement.idBanque) && c.Numero === reglement.numero.trim();
                      return (
                        <button key={c.IdCheque} type="button" className={`guichet-puce${actif ? ' choisie' : ''}`} onClick={() => prendreCheque(c)} aria-pressed={actif}>
                          <ScrollText size={14} aria-hidden="true" /> n° {c.Numero} · {c.Banque}
                          <small>{c.Statut === 'A_DEPOSER' ? `à déposer le ${dateFr(c.DateEcheance)} · ${fcfa(c.Solde)} F` : `solde ${fcfa(c.Solde)} F`}</small>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {nature.bancaire && !nature.especes && (
                <div className="responsive-form-row">
                  <div className="form-group">
                    <label className="form-label" htmlFor="guichet-banque">Banque</label>
                    <ChoixBanque id="guichet-banque" banques={banques} value={reglement.idBanque} required
                      onChange={(id) => changer('idBanque', id)} onBanqueCreee={onBanqueCreee} />
                  </div>
                  <div className="form-group">
                    <label className="form-label" htmlFor="guichet-numero">{nature.libelleNumero}</label>
                    <input id="guichet-numero" type="text" className="form-control guichet-reference" maxLength={50} required autoComplete="off"
                      value={reglement.numero} onChange={(e) => changer('numero', alphanumerique(e.target.value).toUpperCase())} />
                  </div>
                  {nature.cheque && (
                    <div className="form-group">
                      <label className="form-label" htmlFor="guichet-montant-cheque">Montant du chèque</label>
                      {montantChequeVerrouille ? (
                        <div className="guichet-fixe" id="guichet-montant-cheque"><Lock size={13} aria-hidden="true" /> {fcfa(reglement.montantInitialCheque)} F</div>
                      ) : (
                        <ChampMontant id="guichet-montant-cheque" valeur={Number(reglement.montantInitialCheque) || 0} libelle="Montant du chèque"
                          onChange={(v) => changer('montantInitialCheque', Number.isNaN(v) || !v ? '' : String(v))} />
                      )}
                    </div>
                  )}
                </div>
              )}

              {nature.cheque && chequeConnu?.existe && (
                <div className={`guichet-info-cheque${chequeAnnule ? ' annule' : ''}`}>
                  {chequeAnnule
                    ? <><RotateCcw size={14} aria-hidden="true" /> Chèque annulé{chequeConnu.date_annulation ? ` le ${dateFr(chequeConnu.date_annulation)}` : ''}{chequeConnu.motif_annulation ? ` (« ${chequeConnu.motif_annulation} »)` : ''} : remis en service par cet encaissement.</>
                    : <><ScrollText size={14} aria-hidden="true" /> Chèque déjà enregistré : {fcfa(chequeConnu.solde_disponible)} F disponibles sur {fcfa(chequeConnu.montant_initial)} F.</>}
                </div>
              )}
              {nature.cheque && disponible !== null && (disponible > 0 || chequeConnu?.existe) && (
                <div className={`guichet-couverture${total > disponible + 0.001 ? ' insuffisant' : ''}`}>
                  {total > disponible + 0.001
                    ? `Le chèque ne couvre pas le total : ${fcfa(disponible)} F disponibles pour ${fcfa(total)} F à encaisser.`
                    : resteCheque > 0
                      ? `Ce chèque règle ${fcfa(total)} F ; il restera ${fcfa(resteCheque)} F sur le chèque pour d'autres quittances.`
                      : `Ce chèque règle exactement ${fcfa(total)} F.`}
                </div>
              )}

              {nature.cheque && (
                <div className="responsive-form-row">
                  <div className="form-group">
                    <label className="form-label" htmlFor="guichet-date-cheque">Date d'émission du chèque</label>
                    <input id="guichet-date-cheque" type="date" className="form-control" value={reglement.dateCheque || ''} onChange={(e) => changer('dateCheque', e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label className="form-label" htmlFor="guichet-reception">Date de réception du chèque</label>
                    <input id="guichet-reception" type="date" className="form-control" required max={aujourdhui()} value={reglement.dateReceptionCheque || ''}
                      onChange={(e) => changer('dateReceptionCheque', e.target.value)} />
                  </div>
                </div>
              )}

              {avecOrdre && (
                <div className="form-group">
                  <span className="form-label" id="guichet-ordre-libelle">À l'ordre de</span>
                  <div className="guichet-ordre" role="radiogroup" aria-labelledby="guichet-ordre-libelle">
                    <button type="button" role="radio" aria-checked={ordre === 'CABINET'} className={ordre === 'CABINET' ? 'choisi' : ''}
                      disabled={Boolean(ordreImpose)} onClick={() => changer('ordre', 'CABINET')}>
                      {ordreImpose && <Lock size={13} aria-hidden="true" />} {nomCabinet()}
                    </button>
                    <button type="button" role="radio" aria-checked={ordre === 'COMPAGNIE'} className={ordre === 'COMPAGNIE' ? 'choisi' : ''}
                      disabled={Boolean(ordreImpose) || compagniesChoisies.length !== 1} onClick={() => changer('ordre', 'COMPAGNIE')}
                      title={compagniesChoisies.length > 1 ? 'Les quittances choisies relèvent de plusieurs compagnies' : undefined}>
                      Compagnie
                    </button>
                  </div>
                </div>
              )}

              {nature.especes && (
                <div className="form-group">
                  <label className="form-label" htmlFor="guichet-bordereau">Numéro de bordereau</label>
                  <input id="guichet-bordereau" type="text" className="form-control guichet-reference" maxLength={50} value={reglement.numeroBordereau}
                    onChange={(e) => changer('numeroBordereau', alphanumerique(e.target.value))} />
                </div>
              )}
              {nature.mobile && (
                <div className="form-group">
                  <label className="form-label" htmlFor="guichet-recu">N° du reçu de l'opérateur</label>
                  <input id="guichet-recu" type="text" className="form-control guichet-reference" maxLength={50} required placeholder="Orange Money, MTN, Moov, Wave…"
                    value={reglement.numeroRecuOperateur} onChange={(e) => changer('numeroRecuOperateur', alphanumerique(e.target.value))} />
                </div>
              )}
              {nature.compensation && (
                <div className="responsive-form-row">
                  <div className="form-group">
                    <label className="form-label" htmlFor="guichet-compensation">Référence de la compensation</label>
                    <input id="guichet-compensation" type="text" className="form-control" maxLength={50} required value={reglement.referenceCompensation}
                      onChange={(e) => changer('referenceCompensation', alphanumerique(e.target.value))} />
                  </div>
                  <div className="form-group">
                    <label className="form-label" htmlFor="guichet-motif">Motif de la compensation</label>
                    <input id="guichet-motif" type="text" className="form-control" maxLength={255} required value={reglement.motifCompensation}
                      onChange={(e) => changer('motifCompensation', e.target.value)} />
                  </div>
                </div>
              )}

              <div className="form-group">
                <label className="form-label" htmlFor="guichet-emetteur">
                  {nature.cheque ? 'Tireur du chèque' : abrege(modeChoisi) === 'VIR' ? 'Donneur d\'ordre du virement' : 'Payé par'}
                </label>
                <input id="guichet-emetteur" type="text" className="form-control" maxLength={50} required value={reglement.nomEmetteur}
                  onChange={(e) => changer('nomEmetteur', e.target.value)} />
              </div>
            </div>
          )}

          {tentative && erreurs.length > 0 && (
            <ul className="guichet-erreurs" role="alert">
              {erreurs.map((e) => <li key={e}>{e}</li>)}
            </ul>
          )}
          <div className="guichet-barre">
            <button type="button" className="btn btn-secondary" onClick={() => setEtape(2)}><ArrowLeft size={16} /> Quittances</button>
            <button type="button" className="btn btn-primary" onClick={() => { setTentative(true); if (!erreursReglement().length) { setDoublonConfirme(false); setEtape(4); } }}>
              Vérifier <ArrowRight size={16} />
            </button>
          </div>
        </section>
      )}

      {/* ---------------------------------------------------------------- 4. vérification */}
      {etape === 4 && groupeChoisi && (
        <section className="guichet-volet" aria-labelledby="guichet-titre-4">
          <h2 id="guichet-titre-4" className="guichet-titre">Vérifiez avant de valider</h2>
          <div className="guichet-recap">
            <div className="guichet-recap-montant">
              <span>Encaissement de</span>
              <strong>{fcfa(total)} F</strong>
              <span>{libelleMode}{referenceTexte() ? ` · ${referenceTexte()}` : ''}</span>
            </div>
            <dl className="guichet-recap-details">
              <div><dt>Client</dt><dd>{groupeChoisi.client}{groupeChoisi.numeroAssure ? ` · N° ${groupeChoisi.numeroAssure}` : ''}</dd></div>
              {avecOrdre && <div><dt>À l'ordre de</dt><dd>{libelleOrdre}</dd></div>}
              {nature.cheque && (
                <div>
                  <dt>Chèque</dt>
                  <dd>
                    {fcfa(chequeConnu?.existe && !chequeAnnule ? chequeConnu.montant_initial : reglement.montantInitialCheque)} F
                    {reglement.dateCheque ? `, émis le ${dateFr(reglement.dateCheque)}` : ''}, reçu le {dateFr(reglement.dateReceptionCheque)}
                    {resteCheque > 0 ? ` · il restera ${fcfa(resteCheque)} F sur le chèque` : ''}
                  </dd>
                </div>
              )}
              <div><dt>{nature.cheque ? 'Tireur' : abrege(modeChoisi) === 'VIR' ? 'Donneur d\'ordre' : 'Payé par'}</dt><dd>{reglement.nomEmetteur.trim()}</dd></div>
              <div><dt>Date de saisie</dt><dd>{dateFr(aujourdhui())}</dd></div>
            </dl>
            <table className="guichet-recap-table">
              <thead><tr><th>Police / quittance</th><th>Produit</th><th className="nombre">Réglé</th><th className="nombre">Après</th></tr></thead>
              <tbody>
                {choisies.map((l) => (
                  <tr key={l.cle}>
                    <td><strong>{l.numeroPolice}</strong><div className="guichet-muet">{l.numeroQuittance}</div></td>
                    <td>{l.produit}<div className="guichet-muet">{l.compagnie}</div></td>
                    <td className="nombre"><strong>{fcfa(selection[l.cle])} F</strong></td>
                    <td className="nombre">{selection[l.cle] >= l.reste ? <span className="guichet-solde"><Check size={13} /> Soldée</span> : <span className="guichet-acompte">Reste {fcfa(l.reste - selection[l.cle])} F</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {alertes.length > 0 && (
            <ul className="guichet-alertes">
              {alertes.map((a) => <li key={a}><CalendarClock size={14} aria-hidden="true" /> {a}</li>)}
            </ul>
          )}
          {dejaRegles.length > 0 && (
            <div className="guichet-doublon" role="alert">
              <div>
                <AlertTriangle size={16} aria-hidden="true" />
                <span>
                  {dejaRegles.map((l) => `La quittance ${l.numeroQuittance} a déjà reçu ${fcfa(l.regleAujourdhui.Montant)} F aujourd'hui${l.regleAujourdhui.Heure ? ` à ${l.regleAujourdhui.Heure}` : ''}${l.regleAujourdhui.Par ? ` (${l.regleAujourdhui.Par})` : ''}.`).join(' ')}
                </span>
              </div>
              <label className="correction-case">
                <input type="checkbox" checked={doublonConfirme} onChange={(e) => setDoublonConfirme(e.target.checked)} />
                Ce n'est pas une saisie en double : le client paie de nouveau
              </label>
            </div>
          )}

          <div className="guichet-barre">
            <button type="button" className="btn btn-secondary" onClick={() => setEtape(3)} disabled={enregistrement}><ArrowLeft size={16} /> Modifier</button>
            <button type="button" className="btn btn-primary guichet-valider" disabled={enregistrement || (dejaRegles.length > 0 && !doublonConfirme)} onClick={valider}>
              <ShieldCheck size={18} /> {enregistrement ? 'Enregistrement…' : `Valider l'encaissement de ${fcfa(total)} F`}
            </button>
          </div>
        </section>
      )}

      {/* ---------------------------------------------------------------- reçu */}
      {etape === 5 && resultat && (
        <section className="guichet-volet guichet-termine" aria-live="polite">
          <CheckCircle2 size={44} className="guichet-termine-icone" aria-hidden="true" />
          <h2 className="guichet-titre">Encaissement enregistré</h2>
          <div className="guichet-termine-montant">{fcfa(resultat.total)} F</div>
          <div className="guichet-muet">
            {resultat.client} · {resultat.mode}{resultat.reference ? ` · ${resultat.reference}` : ''}
          </div>
          <ul className="guichet-termine-quittances">
            {resultat.quittances.map((q) => (
              <li key={q.cle}>Police {q.police} · quittance {q.numero} : {fcfa(q.montant)} F {q.solde ? <span className="guichet-solde"><Check size={13} /> soldée</span> : <span className="guichet-acompte">acompte</span>}</li>
            ))}
          </ul>
          {resultat.chequeReutilise && <div className="guichet-muet">Chèque annulé remis en service.</div>}
          {Number(resultat.soldeCheque) > 0 && <div className="guichet-muet">Reste sur le chèque : {fcfa(resultat.soldeCheque)} F.</div>}
          <div className="guichet-termine-actions">
            <button type="button" className="btn btn-secondary" onClick={() => imprimerRecu(resultat.recu)}><Printer size={16} /> Réimprimer le reçu</button>
            {resteClient.length > 0 && (
              <button type="button" className="btn btn-secondary" onClick={() => ouvrirClient(cleClientChoisi)}>
                Autre quittance de ce client ({resteClient.length})
              </button>
            )}
            <button type="button" className="btn btn-primary" onClick={nouveauClient}><UserRound size={16} /> Nouveau client</button>
          </div>
        </section>
      )}
    </div>
  );
};

export default GuichetEncaissement;
