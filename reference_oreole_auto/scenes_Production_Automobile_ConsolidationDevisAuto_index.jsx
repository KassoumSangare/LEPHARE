import { useEffect, useMemo, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
 
 
 
import { getDevisInfo, reset } from "features/Devis/devisSlice";
import { OutlineButton, SimpleButton, ButtonSearch } from "partials/UI/Button/Button";
import axios from "axios";
import { toast } from "react-hot-toast";
import { MdSearch, MdClose } from "react-icons/md";

export default function ConsolidationDevisAuto() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { devisinfos } = useSelector(
    (state) => state.devis
  );
  const { token } = useSelector((state) => state.auth);

  const [currentPage, setCurrentPage] = useState(0);
  const itemsPerPage = 6;
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [nomClient, setNomClient] = useState("");
  const [searchInfo, setSearchInfo] = useState("");
  const [selectedIds, setSelectedIds] = useState([]);
  // Sauvegarde/restore des filtres pour revenir sur la même liste après "Voir"
  const CONSOLIDATION_STATE_KEY = 'consolidation_devis_search';


  // Restaurer le filtre au retour (si présent en sessionStorage)
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(CONSOLIDATION_STATE_KEY);
      if (raw) {
        const saved = JSON.parse(raw);
        if (saved && typeof saved.nomClient === 'string' && saved.nomClient.trim()) {
          setNomClient(saved.nomClient);
        }
      }
    } catch (_) { }
  }, []);


  const [isConsolidating, setIsConsolidating] = useState(false);
  const [infoType, setInfoType] = useState(""); // 'success' | 'error' | ''
  const [showConfirm, setShowConfirm] = useState(false);
  const [pendingPayload, setPendingPayload] = useState(null);
  const confirmBtnRef = useRef(null);
  // Popover state for multi-vehicules details
  const [openPopover, setOpenPopover] = useState(null); // iddevis currently open

  // (initials helper removed: we only display the client name)

  useEffect(() => {
    // charger les devis automobile (id_produit = 1)
    dispatch(getDevisInfo(1));
    return () => dispatch(reset());
  }, [dispatch]);


  // Helpers (repris de la page Automobile)
  const normalizeBoolean = (val) => {
    if (val === true) return true;
    if (val === 1) return true;
    if (typeof val === "string") {
      const s = val.trim().toLowerCase();
      return s === "true" || s === "1" || s === "oui" || s === "yes";
    }
    return false;
  };

  // Format date as dd/mm/yyyy; returns '-' if invalid/empty
  const formatDate = (value) => {
    try {
      if (!value) return '-';
      // Accept common shapes: 'yyyy-mm-dd', 'yyyy/mm/dd', ISO string, Date object
      let d;
      if (value instanceof Date) d = value;
      else if (typeof value === 'string') {
        const s = value.trim();
        // If looks like yyyy-mm-dd or yyyy/mm/dd
        const m = s.match(/^(\d{4})[-\/.](\d{1,2})[-\/.](\d{1,2})/);
        if (m) {
          const year = Number(m[1]);
          const month = Number(m[2]) - 1;
          const day = Number(m[3]);
          d = new Date(year, month, day);
        } else {
          const parsed = new Date(s);
          if (!isNaN(parsed.getTime())) d = parsed;
        }
      }
      if (!d || isNaN(d.getTime())) return '-';
      const dd = String(d.getDate()).padStart(2, '0');
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const yyyy = d.getFullYear();
      return `${dd}/${mm}/${yyyy}`;
    } catch { return '-'; }
  };

  // Accessibilité de la modale: focus, Esc (fermer), Enter (confirmer)
  useEffect(() => {
    if (!showConfirm) return;
    // focus sur le bouton confirmer
    const t = setTimeout(() => {
      try { confirmBtnRef.current && confirmBtnRef.current.focus(); } catch (_) { }
    }, 50);

    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        setShowConfirm(false);
        setPendingPayload(null);
      }
      if (e.key === 'Enter') {
        e.preventDefault();
        const payload = pendingPayload;
        setShowConfirm(false);
        if (Array.isArray(payload) && payload.length >= 2) {
          doConsolidate(payload);
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => {
      clearTimeout(t);
      window.removeEventListener('keydown', onKey);
    };
  }, [showConfirm, pendingPayload]);

  // Fermer le popover au clic en dehors et sur Escape
  useEffect(() => {
    if (!openPopover) return undefined;
    const onDocClick = (e) => {
      const el = e.target;
      const inside = el && typeof el.closest === 'function' && el.closest('[data-popover="vehicules"]');
      if (!inside) setOpenPopover(null);
    };
    const onKey = (e) => { if (e.key === 'Escape') setOpenPopover(null); };
    document.addEventListener('mousedown', onDocClick, true);
    document.addEventListener('keydown', onKey, true);
    return () => {
      document.removeEventListener('mousedown', onDocClick, true);
      document.removeEventListener('keydown', onKey, true);
    };
  }, [openPopover]);

  const getContratId = (row) => {
    const candidates = [
      row?.id_contrat,
      row?.IdContrat,
      row?.idContrat,
      row?.ObjectId,
      row?.Id,
      row?.id,
    ];
    for (const v of candidates) {
      if (v !== undefined && v !== null && String(v).trim() !== "") return v;
    }
    try {
      const found = Object.entries(row || {}).find(([k, v]) =>
        typeof k === "string" && k.toLowerCase().includes("contrat") && (typeof v === "number" || (typeof v === "string" && v.trim() !== ""))
      );
      if (found) return found[1];
    } catch (_) { }
    return undefined;
  };


  const getDevisId = (row) => {
    const candidates = [
      row?.id_devis,
      row?.iddevis,
      row?.IdDevis,
      row?.Iddevis,
      row?.idDevis,
      row?.DevisId,
      row?.devisId,
      row?.ObjectId,
      row?.Id,
      row?.id,
    ];
    for (const v of candidates) {
      if (v !== undefined && v !== null && String(v).trim() !== "") return v;
    }
    try {
      const found = Object.entries(row || {}).find(([k, v]) =>
        typeof k === "string" && k.toLowerCase().includes("devis") && (typeof v === "number" || (typeof v === "string" && v.trim() !== ""))
      );
      if (found) return found[1];
    } catch (_) { }
    return undefined;
  };

  // ne garder que les devis AUTO non confirmés (affichables dans details-devis)
  const devisAuto = useMemo(() => {
    return (devisinfos || []).filter(
      (d) => d?.id_produit === 1 && (d?.confirme === false || d?.confirme === 0 || String(d?.confirme).toLowerCase() === "false")
    );
  }, [devisinfos]);

  const paginatedData = useMemo(() => {
    return devisAuto.slice(currentPage * itemsPerPage, (currentPage + 1) * itemsPerPage);
  }, [devisAuto, currentPage]);

  // données à afficher: si recherche, prendre seulement les devis non confirmés dans les résultats
  const searchFiltered = useMemo(() => {
    if (!(searchResults && searchResults.length > 0)) return [];
    return searchResults.filter(
      (d) => d?.__forceInclude === true || (d?.id_produit === 1 && (d?.confirme === false || d?.confirme === 0 || String(d?.confirme).toLowerCase() === "false"))
    );
  }, [searchResults]);


  const handleSearch = async () => {
    // reset page and previous results
    setCurrentPage(0);
    setSearchResults(null);
    setSearchInfo("");
    setInfoType("");
    setSelectedIds([]);

    if (!nomClient || !nomClient.trim()) return;

    try {
      setIsSearching(true);
      setSearchInfo("");
      // Préparer outils
      const base = process.env.REACT_APP_API_URL || "";
      const headers = { Authorization: `Token ${token}` };
      const fold = (s) => s && s.normalize ? s.normalize('NFD').replace(/[\u0300-\u036f]/g, '') : s;
      const norm = (v) => (v === null || v === undefined) ? "" : fold(String(v)).toLowerCase().trim().replace(/\s+/g, " ");
      const pickFrom = (p) => Array.isArray(p) ? p : (Array.isArray(p?.data) ? p.data : (Array.isArray(p?.results) ? p.results : []));
      const tryOnce = async (paramsObj, pathSuffix = '') => {
        try {
          const url = `${base}devisclient${pathSuffix}`;
          const { data } = await axios.get(url, { headers, params: paramsObj });
          return pickFrom(data);
        } catch (_) { return undefined; }
      };

      let list;
      // 1) Rechercher via devisclient en utilisant exclusivement 'nomclient' + 'idproduit=1'
      // eslint-disable-next-line no-await-in-loop
      list = await tryOnce({ nomclient: nomClient, idproduit: 1, page: 1, page_size: 200 });

      // 2) Fallback doux: autres noms de paramètres texte sur le même endpoint (au cas où l'API attendrait un autre nom)
      if (!list || list.length === 0) {
        const paramNames = ['search', 'q', 'nom', 'client', 'name'];
        for (const p of paramNames) {
          // eslint-disable-next-line no-await-in-loop
          const res = await tryOnce({ [p]: nomClient, idproduit: 1, page: 1, page_size: 200 });
          if (res && res.length) { list = res; break; }
        }
      }

      // 3) Fallback REST /devisclient/<nom>
      if (!list || list.length === 0) {
        // eslint-disable-next-line no-await-in-loop
        const res = await tryOnce({ idproduit: 1 }, `/${encodeURIComponent(nomClient)}`);
        if (res && res.length) list = res;
      }

      // 4) Dernier recours: rien trouvé => liste vide (on évite les faux positifs)
      if (!list) list = [];

      // Normaliser pour l'affichage
      const mappedRaw = (list || []).map((row) => {
        const rawDetails = row?.details ?? row?.Details ?? null;
        const detailsList = Array.isArray(rawDetails) ? rawDetails : (rawDetails ? [rawDetails] : []);
        const primary = detailsList.length > 0 ? detailsList[0] : null;
        const primaryDetail = primary ? {
          matricule: primary?.matricule ?? primary?.Matricule ?? null,
          marque: primary?.marque ?? primary?.Marque ?? null,
          datemec: formatDate(primary?.datemec ?? primary?.DateMec ?? primary?.date_mec ?? null),
        } : null;
        return {
          iddevis: row?.iddevis ?? row?.IdDevis ?? row?.id_devis ?? row?.id,
          numerodevis: row?.numerodevis ?? row?.NumeroDevis ?? row?.numero_devis ?? row?.numero ?? row?.Numero,
          nomclient: row?.nomclient ?? row?.NomClient ?? row?.nom ?? row?.Nom ?? row?.NomPrenoms ?? row?.NomComplet,
          // Pré-formatage en jj/mm/aaaa pour éviter un reparse au rendu
          dateeffet: formatDate(row?.dateeffet ?? row?.DateEffet ?? row?.date_effet ?? row?.Date_Effet),
          // Nouveau: date d'émission (garde compatibilité avec d'anciens noms)
          dateemission: formatDate(
            row?.dateemission ?? row?.DateEmission ?? row?.date_emission ?? row?.Date_Emission
            ?? row?.dateexpirtation /* legacy typo */
            ?? row?.dateexpiration ?? row?.DateExpiration ?? row?.date_expiration ?? row?.Date_Expiration
          ),
          detailsList,
          primaryDetail,
          id_produit: row?.id_produit ?? 1,
          confirme: row?.confirme ?? false,
          flotte: (row?.flotte ?? row?.Flotte)
            ?? (Array.isArray(detailsList) ? detailsList.length > 1 : false),
        };
      }).filter((r) => r.iddevis && r.nomclient);

      // Filtre strict côté client sur le champ nomclient uniquement
      const needle = norm(nomClient);
      const mapped = mappedRaw.filter((r) => norm(r.nomclient).includes(needle));

      setSearchResults(mapped);
      if (mapped.length === 0) setSearchInfo("Aucun devis correspondant.");
    } catch (e) {
      setSearchResults([]);
      setSearchInfo("Erreur lors de la recherche.");
      console.error('[ConsolidationDevisAuto] Erreur recherche devisclient:', e?.response?.status, e?.response?.data || e?.message);
    } finally {
      setIsSearching(false);
    }
  };

  const handleResetSearch = () => {
    setNomClient("");
    setSearchResults(null);
    setCurrentPage(0);
    setSearchInfo("");
    setInfoType("");
    setSelectedIds([]);
  };

  // Consolidation effective (appel API) après confirmation
  const extractBackendMessage = (data, fallback) => {
    try {
      if (data == null) return fallback;
      if (typeof data === 'string') return data;
      if (typeof data.message === 'string' && data.message.trim()) return data.message;
      if (typeof data.error === 'string' && data.error.trim()) return data.error;
      if (Array.isArray(data) && data.length > 0) {
        const first = data[0];
        if (typeof first === 'string') return first;
        if (first && typeof first.OutputMessage === 'string' && first.OutputMessage.trim()) return first.OutputMessage;
        if (first && typeof first.message === 'string' && first.message.trim()) return first.message;
      }
      // Chercher une première valeur string exploitable dans l'objet
      const entry = Object.values(data).find((v) => typeof v === 'string' && v.trim());
      if (entry) return entry;
      return fallback;
    } catch (_) { return fallback; }
  };

  const doConsolidate = async (payload) => {
    try {
      setIsConsolidating(true);
      setSearchInfo('');
      setInfoType('');
      const url = `${process.env.REACT_APP_API_URL}consolidationdevis/`;
      const headers = { Authorization: `Token ${token}`, 'Content-Type': 'application/json' };
      const { data } = await axios.post(url, payload, { headers });
      // Log complet côté dev, mais ne rien afficher d'autre à l'écran
      // console.log('[Consolidation] Réponse backend:', data);
      // Récupérer l'id du nouveau devis
      const idCandidates = [
        data?.id_devis, data?.iddevis, data?.IdDevis, data?.Iddevis,
        data?.idDevis, data?.DevisId, data?.devisId, data?.ObjectId, data?.Id, data?.id,
      ];
      const newDevisId = idCandidates.find((v) => v !== undefined && v !== null && String(v).trim() !== "");
      let numero;
      let devisData;
      if (newDevisId) {
        try {
          const devisUrl = `${process.env.REACT_APP_API_URL}devis/${encodeURIComponent(newDevisId)}`;
          const resp = await axios.get(devisUrl, { headers });
          devisData = resp?.data;
          console.log('[Consolidation] GET devis/:id =>', devisData);
          numero = devisData?.numerodevis ?? devisData?.NumeroDevis ?? devisData?.numero ?? devisData?.Numero;
        } catch (e2) {
          console.warn('[Consolidation] Impossible de récupérer numerodevis via /devis/:id, fallback POST payload', e2?.message);
        }
      }
      if (!numero) {
        numero = data?.numerodevis ?? data?.NumeroDevis ?? data?.numero ?? data?.Numero;
      }
      const msg = numero
        ? `Consolidation effectuée avec succès — N° de devis: ${numero}`
        : (data?.message || 'Consolidation effectuée avec succès.');
      toast.success(msg);
      // Rediriger vers la page de détails du devis consolidé
      if (newDevisId) {
        navigate(`/production/automobile/details-devis/${newDevisId}`);
        return;
      }
      // Fallback: rafraîchir l'affichage local si pas d'ID
      setSearchInfo('');
      setInfoType('');
      setSelectedIds([]);
    } catch (e) {
      setInfoType('error');
      const backendData = e?.response?.data;
      const backendMsg = extractBackendMessage(backendData, e?.message || 'Erreur de consolidation.');
      setSearchInfo(backendMsg);
      toast.error(backendMsg);
    } finally {
      setIsConsolidating(false);
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-100 p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-slate-800 font-semibold">Consolidation</h1>
          <p className="text-xs text-gray-500">Liste des devis automobile (non confirmés)</p>
        </div>
        <Link to="/production/automobile">
          <SimpleButton content="Retour" buttonClassname="border-blue-600 text-blue-600" />
        </Link>
      </div>

      {/* Barre de recherche (centrée et stylée) */}
      <div className="mb-8 flex flex-col items-center">
        <label className="block mb-3 text-xs font-semibold tracking-wide text-blue-600 text-center">Rechercher un devis</label>
        <div className="w-full max-w-2xl flex items-center justify-center">
          <div className="relative flex w-full items-stretch rounded-full bg-white shadow-lg ring-1 ring-blue-100 overflow-hidden">
            <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-slate-400 text-lg">
              <MdSearch />
            </span>
            <input
              id="nomClient"
              className="flex-1 h-12 pl-11 pr-4 text-sm text-slate-700 placeholder-slate-400 bg-white outline-none border-0 focus:ring-0"
              type="text"
              value={nomClient}
              onChange={(e) => setNomClient(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleSearch(); } }}
              placeholder="Nom du client (ex: KOUASSI)"
            />
            {nomClient && (
              <button
                type="button"
                aria-label="Effacer"
                className="absolute inset-y-0 right-28 pr-3 flex items-center text-slate-400 hover:text-slate-600"
                onClick={handleResetSearch}
              >
                <MdClose />
              </button>
            )}

            {/* Modale de confirmation de consolidation (UI soignée) */}
            {showConfirm && (
              <div className="fixed inset-0 z-[70] flex items-center justify-center">
                <div className="absolute inset-0 bg-gradient-to-b from-slate-900/60 to-slate-900/50 backdrop-blur-[2px]" onClick={() => setShowConfirm(false)} />
                <div
                  role="dialog"
                  aria-modal="true"
                  className="relative mx-4 w-full max-w-xl overflow-hidden rounded-3xl bg-white/90 backdrop-blur-md shadow-[0_24px_64px_-20px_rgba(2,6,23,0.45)] ring-1 ring-slate-200
                       transition-all duration-200 ease-out animate-[fadeIn_.2s_ease-out]"
                >
                  {/* En-tête gradient avec icône */}
                  <div className="relative flex items-center gap-3 px-6 py-4 bg-gradient-to-r from-indigo-600 via-blue-600 to-sky-500 text-white">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/15 ring-1 ring-white/20 shadow-inner">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" className="h-5 w-5">
                        <path d="M12 6v6l4 2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold">Confirmer la consolidation</h3>
                      <p className="text-[11px] opacity-90">Étape finale avant création d’un devis consolidé</p>
                    </div>
                    <div className="absolute right-3 top-3">
                      <button
                        type="button"
                        aria-label="Fermer"
                        className="h-8 w-8 rounded-full bg-white/10 hover:bg-white/20 active:scale-95 transition flex items-center justify-center ring-1 ring-white/20"
                        onClick={() => setShowConfirm(false)}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" className="h-4 w-4">
                          <path d="M6 6l12 12M18 6l-12 12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                        </svg>
                      </button>
                    </div>
                  </div>

                  {/* Corps */}
                  <div className="px-6 pt-5 pb-2">
                    <p className="text-sm text-slate-700">
                      Vous êtes sur le point de consolider <span className="font-semibold text-slate-900">{selectedIds.length}</span> devis.
                      Cette opération créera un <span className="font-semibold text-slate-900">nouveau devis</span> récapitulatif.
                    </p>

                    {(() => {
                      try {
                        const nums = (searchFiltered || [])
                          .filter(d => selectedIds.includes(getDevisId(d)))
                          .map(d => d?.numerodevis)
                          .filter(Boolean);
                        return (
                          <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50/60">
                            <div className="px-4 py-2 text-[11px] font-semibold tracking-wide text-slate-600">DEVIS SÉLECTIONNÉS</div>
                            <div className="px-4 pb-4">
                              <div className="max-h-28 overflow-auto custom-scrollbar pr-1">
                                <div className="flex flex-wrap gap-2">
                                  {nums.length > 0 ? (
                                    nums.map((n, i) => (
                                      <span key={i} className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1 text-[11px] font-medium text-slate-700 ring-1 ring-slate-200 shadow-sm">
                                        <span className="h-1.5 w-1.5 rounded-full bg-blue-600 shadow-[0_0_0_2px_rgba(59,130,246,.15)]" />
                                        {n}
                                      </span>
                                    ))
                                  ) : (
                                    <span className="text-xs text-slate-500">Sélection en cours…</span>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      } catch { return null; }
                    })()}

                    <p className="mt-3 text-xs text-slate-500">Souhaitez-vous poursuivre ?</p>
                  </div>

                  {/* Actions */}
                  <div className="px-6 pb-6 pt-2 flex items-center justify-end gap-2">
                    <button
                      type="button"
                      className="px-4 py-2 rounded-full border border-slate-300 bg-white text-slate-700 text-xs hover:bg-slate-50 active:scale-[.99] transition"
                      onClick={() => {
                        setShowConfirm(false);
                        setPendingPayload(null);
                      }}
                    >
                      Annuler
                    </button>
                    <button
                      type="button"
                      ref={confirmBtnRef}
                      className={`px-4 py-2 rounded-full text-white text-xs shadow transition active:scale-[.99] inline-flex items-center gap-2 ${isConsolidating ? 'bg-blue-400 cursor-not-allowed' : 'bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700'}`}
                      disabled={isConsolidating}
                      onClick={async () => {
                        const payload = pendingPayload;
                        setShowConfirm(false);
                        if (Array.isArray(payload) && payload.length >= 2) {
                          await doConsolidate(payload);
                        }
                      }}
                    >
                      {isConsolidating && (
                        <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                          <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                          <path d="M22 12a10 10 0 00-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                        </svg>
                      )}
                      <span>Confirmer</span>
                    </button>
                  </div>
                </div>
              </div>
            )}
            <ButtonSearch
              content={isSearching ? "Chargement..." : "Chercher"}
              disabled={isSearching}
              handleClick={handleSearch}
              buttonClassname="h-12 px-6 rounded-none rounded-r-full bg-blue-600 text-white font-semibold hover:bg-blue-700 transition"
            />
          </div>
          <div className="ml-3">
            <SimpleButton
              content="Rénitialiser"
              handleClick={handleResetSearch}
              buttonClassname="rounded-full border-slate-300 text-slate-700 px-5 py-2.5 hover:bg-slate-50 shadow-sm"
            />
          </div>
        </div>
      </div>

      {/* Résultats (compact) basés sur la liste /production/automobile */}
      {isSearching && (
        <div className="text-center text-xs text-slate-500">Chargement...</div>
      )}
      {(!isSearching && searchFiltered && searchFiltered.length > 0) && (
        <div className="overflow-x-auto rounded-2xl bg-white/80 backdrop-blur-xl shadow-2xl ring-1 ring-slate-100">
          <table className="min-w-full">
            {(() => {
              // Afficher un bandeau au-dessus des en-têtes quand un seul client est concerné
              const groups = new Map();
              (searchFiltered || []).forEach((d) => {
                const name = d?.nomclient || 'Client';
                if (!groups.has(name)) groups.set(name, []);
                groups.get(name).push(d);
              });
              if (groups.size === 1) {
                const [name, items] = Array.from(groups.entries())[0];
                return (
                  <caption className="caption-top">
                    <div className="flex items-center gap-3 px-5 py-3 bg-gradient-to-r from-slate-50 to-slate-100/70">
                      <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-blue-50 text-blue-600 ring-1 ring-blue-200">
                        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 12a5 5 0 100-10 5 5 0 000 10z" /><path d="M20 21a8 8 0 10-16 0" /></svg>
                      </span>
                      <div>
                        <div className="text-sm font-semibold text-slate-800 tracking-wide">{name}</div>
                        <div className="text-[11px] text-slate-500">{items.length} devis trouvé(s)</div>
                      </div>
                    </div>
                  </caption>
                );
              }
              return null;
            })()}
            <thead className="bg-gradient-to-r from-blue-50 to-indigo-50 sticky top-0 z-10">
              <tr>
                <th className="w-10 px-3 py-3 text-center"></th>
                <th className="px-5 py-3 text-[11px] font-semibold tracking-wider text-blue-700 uppercase text-left">Type</th>
                <th className="px-5 py-3 text-[11px] font-semibold tracking-wider text-blue-700 uppercase text-center">Numero de devis</th>
                <th className="px-5 py-3 text-[11px] font-semibold tracking-wider text-blue-700 uppercase text-center">Date d'effet</th>
                <th className="px-5 py-3 text-[11px] font-semibold tracking-wider text-blue-700 uppercase text-center">Date d'émission</th>
                <th className="px-5 py-3 text-[11px] font-semibold tracking-wider text-blue-700 uppercase text-center">Details</th>
                <th className="px-5 py-3 text-[11px] font-semibold tracking-wider text-blue-700 uppercase text-center"></th>

              </tr>
            </thead>
            <tbody className="text-sm divide-y divide-slate-100">
              {(() => {
                const groups = new Map();
                (searchFiltered || []).forEach((d) => {
                  const name = d?.nomclient || 'Client';
                  if (!groups.has(name)) groups.set(name, []);
                  groups.get(name).push(d);
                });
                const isSingleClient = groups.size === 1;
                const rows = [];
                let keyIdx = 0;
                groups.forEach((items, name) => {
                  if (!isSingleClient) {
                    rows.push(
                      <tr key={`hdr-${keyIdx++}`} className="bg-gradient-to-r from-slate-50 to-slate-100/70">
                        <td colSpan={7} className="px-5 py-3">
                          <div className="flex items-center gap-3">
                            <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-blue-50 text-blue-600 ring-1 ring-blue-200">
                              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 12a5 5 0 100-10 5 5 0 000 10z" /><path d="M20 21a8 8 0 10-16 0" /></svg>
                            </span>
                            <div>
                              <div className="text-sm font-semibold text-slate-800 tracking-wide">{name}</div>
                              <div className="text-[11px] text-slate-500">{items.length} devis trouvé(s)</div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    );
                  }
                  items.forEach((d, i) => {
                    rows.push(
                      <tr
                        key={`row-${getDevisId(d) || keyIdx}-${i}`}
                        className="group even:bg-slate-50/40 hover:bg-blue-50/50 transition-colors duration-200"
                      >
                        <td className="px-3 py-3 text-center">
                          {(() => {
                            const id = getDevisId(d);
                            const checked = selectedIds.includes(id);
                            return (
                              <input
                                type="checkbox"
                                aria-label={`Sélectionner le devis ${id}`}
                                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                                checked={checked}
                                onChange={() => {
                                  setSelectedIds((prev) => (
                                    checked ? prev.filter((x) => x !== id) : [...prev, id]
                                  ));
                                }}
                              />
                            );
                          })()}
                        </td>
                        <td className="px-5 py-3">
                          {(() => {
                            const isFlotte = !!d?.flotte;
                            const label = isFlotte ? 'FLOTTE' : 'MONO';
                            const cls = isFlotte
                              ? 'bg-amber-50 text-amber-700 ring-amber-200'
                              : 'bg-indigo-50 text-indigo-700 ring-indigo-200';
                            return (
                              <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-semibold ring-1 ${cls}`}>
                                <span className={`h-1.5 w-1.5 rounded-full ${isFlotte ? 'bg-amber-500' : 'bg-indigo-500'}`} />
                                {label}
                              </span>
                            );
                          })()}
                        </td>
                        <td className="px-5 py-3">
                          <div className="flex items-center justify-center gap-2 flex-wrap">
                            <span className="inline-block rounded-xl bg-gradient-to-br from-indigo-600 to-blue-600 text-white px-3 py-1 text-[11px] font-mono tracking-widest shadow-sm group-hover:shadow">
                              {d?.numerodevis}
                            </span>
                            {(d?.confirme === true || String(d?.confirme).toLowerCase() === 'true') && (
                              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 text-emerald-700 px-2.5 py-0.5 text-[10px] ring-1 ring-emerald-200">
                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> CONSOLIDÉ
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-5 py-3 text-center">
                          <span className="inline-block text-xs text-slate-700">{d?.dateeffet || '-'}</span>
                        </td>
                        <td className="px-5 py-3 text-center">
                          <span className="inline-block text-xs text-slate-700">{d?.dateemission || '-'}</span>
                        </td>
                        <td className="px-5 py-3 text-center">
                          {(() => {
                            const primary = d?.primaryDetail || {};
                            const count = Array.isArray(d?.detailsList) ? d.detailsList.length : 0;
                            const matricule = primary?.matricule ?? '-';
                            const marque = primary?.marque ?? '-';
                            const datemec = primary?.datemec ?? '-';
                            const isOpen = openPopover === d?.iddevis;
                            return (
                              <div data-popover="vehicules" className="relative inline-flex items-start gap-3 rounded-xl bg-slate-50 ring-1 ring-slate-200 px-3 py-2 text-left shadow-sm">
                                <div className="flex items-center gap-2">
                                  <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-blue-50 text-blue-600 ring-1 ring-blue-200">
                                    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="6" width="18" height="12" rx="2" /><path d="M7 10h10M7 14h6" /></svg>
                                  </span>
                                  <div className="flex flex-col">
                                    <span className="text-[10px] uppercase tracking-wider text-slate-500">Matricule</span>
                                    <div className="flex items-center gap-2">
                                      <span className="text-xs font-semibold text-slate-800">{matricule}</span>
                                      {count > 1 && (
                                        <button
                                          type="button"
                                          className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 ring-1 ring-blue-200 hover:bg-blue-200 focus:outline-none"
                                          onClick={(e) => { e.stopPropagation(); setOpenPopover(isOpen ? null : d?.iddevis); }}
                                          title="Voir les autres véhicules"
                                        >
                                          +{count - 1}
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                <div className="h-8 w-px bg-slate-200" />
                                <div className="flex items-center gap-2">
                                  <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-indigo-50 text-indigo-600 ring-1 ring-indigo-200">
                                    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="3" /><path d="M3 12h6M15 12h6M12 3v6M12 15v6" /></svg>
                                  </span>
                                  <div className="flex flex-col">
                                    <span className="text-[10px] uppercase tracking-wider text-slate-500">Marque</span>
                                    <span className="text-xs font-semibold text-slate-800">{marque}</span>
                                  </div>
                                </div>
                                <div className="h-8 w-px bg-slate-200" />
                                <div className="flex items-center gap-2">
                                  <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 ring-1 ring-emerald-200">
                                    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="4" width="18" height="17" rx="2" /><path d="M8 2v4M16 2v4M3 10h18" /></svg>
                                  </span>
                                  <div className="flex flex-col">
                                    <span className="text-[10px] uppercase tracking-wider text-slate-500">Mise en circulation</span>
                                    <span className="text-xs font-semibold text-slate-800">{datemec}</span>
                                  </div>
                                </div>
                                {isOpen && count > 1 && (
                                  <div className="absolute left-0 top-full mt-2 z-50 w-[360px] max-w-[85vw] rounded-2xl bg-white shadow-2xl ring-1 ring-slate-200 p-3">
                                    <div className="flex items-center justify-between mb-2">
                                      <div className="text-[11px] font-semibold text-slate-700">Autres véhicules ({count - 1})</div>
                                      <button
                                        type="button"
                                        className="h-6 w-6 inline-flex items-center justify-center rounded-full bg-slate-100 text-slate-600 hover:bg-slate-200"
                                        onClick={(e) => { e.stopPropagation(); setOpenPopover(null); }}
                                        aria-label="Fermer le détail"
                                      >
                                        <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M6 6l12 12M18 6l-12 12" /></svg>
                                      </button>
                                    </div>
                                    <div className="max-h-56 overflow-auto custom-scrollbar pr-1">
                                      <table className="min-w-full text-xs">
                                        <thead>
                                          <tr className="text-[10px] uppercase tracking-wider text-slate-500">
                                            <th className="text-left py-1 pr-2">Matricule</th>
                                            <th className="text-left py-1 pr-2">Marque</th>
                                            <th className="text-left py-1">Mise en circ.</th>
                                          </tr>
                                        </thead>
                                        <tbody className="text-slate-700">
                                          {d.detailsList.slice(1).map((veh, idx) => (
                                            <tr key={idx} className="border-t border-slate-100">
                                              <td className="py-1 pr-2 font-medium">{veh?.matricule ?? veh?.Matricule ?? '-'}</td>
                                              <td className="py-1 pr-2">{veh?.marque ?? veh?.Marque ?? '-'}</td>
                                              <td className="py-1">{formatDate(veh?.datemec ?? veh?.DateMec ?? veh?.date_mec)}</td>
                                            </tr>
                                          ))}
                                        </tbody>
                                      </table>
                                    </div>
                                  </div>
                                )}
                              </div>
                            );
                          })()}
                        </td>
                        <td className="px-5 py-3 text-center">
                          {(() => {
                            const isConfirme = normalizeBoolean(d?.confirme);
                            const contratId = getContratId(d);
                            const devisId = getDevisId(d);
                            const to = (isConfirme && contratId)
                              ? `/production/automobile/details-contrat/${contratId}`
                              : `/production/automobile/details-devis/${devisId}`;
                            return (
                              <Link
                                to={to}
                                state={{ iddevis: devisId, fromConsolidation: true, filters: { nomClient } }}
                                className="inline-block"
                                onClick={() => {
                                  try {
                                    sessionStorage.setItem(CONSOLIDATION_STATE_KEY, JSON.stringify({ nomClient }));
                                  } catch (_) { }
                                }}
                              >
                                <OutlineButton content="Voir" buttonClassname="before:bg-blue-700 text-blue-600" />
                              </Link>
                            );
                          })()}
                        </td>
                      </tr>
                    );
                  });
                });
                return rows;
              })()}
            </tbody>
          </table>
        </div>
      )}
      {/* Notification globale (succès/erreur) */}
      {(!isSearching && searchInfo) && (
        <div className="mx-auto max-w-2xl mt-3">
          <div className={`rounded-xl px-4 py-3 text-xs shadow-sm ring-1 ${infoType === 'success' ? 'bg-green-50 text-green-700 ring-green-200' : 'bg-rose-50 text-rose-700 ring-rose-200'}`}>
            {searchInfo}
          </div>
        </div>
      )}

      {/* Table des devis (masqué temporairement) */}
      {false && (
        <div className="overflow-x-auto">
          <table className="table-auto w-full">{/* ...table hidden... */}</table>
          {searchInfo && (
            <div className="text-center text-xs text-slate-500 mt-2">{searchInfo}</div>
          )}
        </div>
      )}

      {/* Barre d'actions flottante (affichée quand il y a une sélection) */}
      {(searchFiltered && selectedIds.length > 0) && (
        <div className="fixed inset-x-0 bottom-4 z-40">
          <div className="mx-auto w-[95%] sm:max-w-2xl md:max-w-3xl lg:max-w-4xl">
            <div className="flex items-center justify-between gap-3 rounded-2xl bg-white/90 backdrop-blur-md shadow-2xl ring-1 ring-slate-200 px-4 py-3">
              <div className="text-xs text-slate-600">
                <strong className="text-slate-900">{selectedIds.length}</strong> sélectionné(s)
              </div>
              <div className="flex items-center gap-2">
                {(() => {
                  const all = (searchFiltered || []).map((d) => getDevisId(d)).filter(Boolean);
                  const allSelected = all.length > 0 && all.every((id) => selectedIds.includes(id));
                  const handleToggleAll = () => {
                    if (allSelected) {
                      // désélectionner uniquement les visibles
                      setSelectedIds((prev) => prev.filter((id) => !all.includes(id)));
                    } else {
                      // ajouter tous les visibles à la sélection (sans doublons)
                      setSelectedIds((prev) => Array.from(new Set([...prev, ...all])));
                    }
                  };
                  return (
                    <button
                      type="button"
                      className="px-4 py-2 rounded-full border border-slate-300 text-slate-700 text-xs hover:bg-slate-50"
                      onClick={handleToggleAll}
                    >
                      {allSelected ? 'Désélectionner tout' : 'Sélectionner tout'}
                    </button>
                  );
                })()}
                <button
                  type="button"
                  className={`px-4 py-2 rounded-full text-white text-xs shadow ${isConsolidating ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
                  disabled={isConsolidating}
                  onClick={async () => {
                    const payload = (selectedIds || []).map((id) => ({ iddevis: id })).filter((x) => typeof x.iddevis !== 'undefined');
                    if (!payload || payload.length < 2) {
                      setInfoType('error');
                      const msg = 'La consolidation requiert au moins deux devis. Sélectionnez au minimum deux éléments, puis réessayez.';
                      setSearchInfo(msg);
                      toast.error(msg);
                      return;
                    }
                    setPendingPayload(payload);
                    setShowConfirm(true);
                  }}
                >
                  {isConsolidating ? 'Validation...' : 'Valider'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Pagination supprimée: plus d'appel à ReactPaginate */}

    </div>
  );
}