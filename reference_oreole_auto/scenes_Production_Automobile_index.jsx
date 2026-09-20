import { Fragment, useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import { toast } from "react-hot-toast";
import moment from "moment";
// methods
import { getDevisInfo, getDevisCounts, reset } from "features/Devis/devisSlice";
// components
import Spinner from "partials/Utils/Spinner/Spinner";
import WelcomeBanner from "partials/UI/Banner/WelcomeBanner";
import DashboardCard01 from "partials/UI/Cards/DashboardCard01";
import { AddButton, OutlineButton } from "partials/UI/Button/Button";
import ErrorBoundary from "features/ErrorHandler/ErrorBoundary";
import {
  BsFillArrowLeftSquareFill,
  BsFillArrowRightSquareFill,
} from "react-icons/bs";
import ReactPaginate from "react-paginate";
import { FilterCard } from "partials/UI/Filter";
import ContratClientInput from "../Search/ContratClientInput";

const Automobile = () => {
  const dispatch = useDispatch();
  const [listeProduction, setListeProduction] = useState([]);
  const [showConfirme, setShowConfirme] = useState(false);
  const toggleShowConfirme = () => setShowConfirme((value) => !value);
  const [searchResults, setSearchResults] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);

  // get devis
  const { devisinfos, devisCounts, isLoading, isError, message } = useSelector(
    (state) => state.devis
  );

  useEffect(() => {
    if (isError) {
      toast.error(message);
    }

    dispatch(getDevisInfo(1));
    dispatch(getDevisCounts(1));

    return () => {
      dispatch(reset());
    };
  }, [isError, message, dispatch]);

  // filtre devis confirmé
  useEffect(() => {
    if (!devisinfos || !Array.isArray(devisinfos)) {
      setListeProduction([]);
      return;
    }

    if (showConfirme) {
      setListeProduction(
        devisinfos.filter(
          (oneDevis) => oneDevis.id_produit === 1 && oneDevis.confirme === true
        )
      );
    } else {
      setListeProduction(
        devisinfos.filter((oneDevis) => oneDevis.id_produit === 1)
      );
    }
  }, [showConfirme, devisinfos]);

  const [currentPage, setCurrentPage] = useState(0);

  // Helpers centralisés: normalisation et extraction d'IDs robustes
  const normalizeBoolean = (val) => {
    if (val === true) return true;
    if (val === 1) return true;
    if (typeof val === "string") {
      const s = val.trim().toLowerCase();
      return s === "true" || s === "1" || s === "oui" || s === "yes";
    }
    return false;
  };

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

  const [itemsPerPage, setItemsPerPage] = useState(10); // Nombre de clients par page

  // const itemsPerPage = 6;

  const paginatedData = listeProduction.slice(
    currentPage * itemsPerPage,
    (currentPage + 1) * itemsPerPage
  );

  const paginatedSearchResults = searchResults?.slice(
    currentPage * itemsPerPage,
    (currentPage + 1) * itemsPerPage
  );

  // Fonction pour afficher le contenu du tableau
  const renderTableContent = () => {
    if (hasSearched) {
      return searchResults.length > 0 ? (
        paginatedSearchResults.map((oneDevis, index) => (
          <tr key={index}>
            <td className="p-2">
              <div className="text-center tracking-wide">
                {oneDevis.nomclient}
              </div>
            </td>
            <td className="p-2">
              <div className="text-center font-bold tracking-wide">
                {oneDevis.numerodevis}
              </div>
            </td>
            <td className="p-2">
              <div className="text-center font-normal text-indigo-600">
                {oneDevis.libelle_categorie}
              </div>
            </td>
            <td className="p-2">
              <div className="text-center font-bold text-slate-700 bg-indigo-100 px-1 rounded-md py-1.3">
                {oneDevis.libelle_avenant}
              </div>
            </td>
            <td className="p-2">
              <div className="text-center font-bold text-slate-700 bg-indigo-100 px-1 rounded-md py-1.3">
                {oneDevis.flotte ? "FLOTTE" : "MONO"}
              </div>
            </td>
            <td className="p-2">
              <div className="text-center">
                <strong className="tracking-wider rounded bg-blue-50 px-4 py-1.5 font-bold text-gray-700">
                  {moment(oneDevis.dateemission).format("DD/MM/YYYY")}
                </strong>
              </div>
            </td>
            <td className="p-2">
              <div className="text-center">
                <strong className="tracking-wider rounded bg-blue-50 px-4 py-1.5 font-bold text-gray-700">
                  {moment(oneDevis.dateexpiration).format("DD/MM/YYYY")}
                </strong>
              </div>
            </td>
            <td className="p-2">
              <div className="text-center text-gray-700 font-bold text-sm tracking-wide">
                {Intl.NumberFormat().format(parseInt(oneDevis.primenette))}
              </div>
            </td>
            <td className="p-2">
              <div className="text-center text-gray-700 font-bold text-sm tracking-wide">
                {Intl.NumberFormat().format(parseInt(oneDevis.primettc))}
              </div>
            </td>
            <td className="p-2">
              <div className="text-center">
                {oneDevis.confirme === true ? (
                  <strong className="rounded bg-green-100 px-3 py-1.5 text-green-700 uppercase">
                    Confirmé
                  </strong>
                ) : (
                  <strong className="rounded bg-orange-100 px-3 py-1.5 text-orange-700 uppercase">
                    Attente
                  </strong>
                )}
              </div>
            </td>
            <td className="p-2">
              <Link
                to={normalizeBoolean(oneDevis.confirme) ?
                  `/production/automobile/details-contrat/${getContratId(oneDevis)}` :
                  `/production/automobile/details-devis/${getDevisId(oneDevis)}`}
                state={{ iddevis: getDevisId(oneDevis) }}
                className="block"
              >
                <OutlineButton
                  content="Voir"
                  buttonClassname="before:bg-blue-700 text-blue-600"
                />
              </Link>
            </td>
          </tr>
        ))
      ) : (
        <tr>
          <td colSpan="10" className="text-center py-4">
            Aucun résultat trouvé
          </td>
        </tr>
      );
    }

    // Affichage par défaut (sans recherche)
    return devisinfos && Array.isArray(devisinfos) && devisinfos.length > 0 ? (
      paginatedData.map((oneDevis, index) => (
        <tr key={index}>
          <td className="p-2">
            <div className="text-center tracking-wide">
              {oneDevis.nomclient}
            </div>
          </td>
          <td className="p-2">
            <div className="text-center font-bold tracking-wide">
              {oneDevis.numerodevis}
            </div>
          </td>
          <td className="p-2">
            <div className="text-center font-normal text-indigo-600">
              {oneDevis.libelle_categorie}
            </div>
          </td>
          <td className="p-2">
            <div className="text-center font-bold text-slate-700 bg-indigo-100 px-1 rounded-md py-1.3">
              {oneDevis.libelle_avenant}
            </div>
          </td>
          <td className="p-2">
            <div className="text-center font-bold text-slate-700 bg-indigo-100 px-1 rounded-md py-1.3">
              {oneDevis.flotte ? "FLOTTE" : "MONO"}
            </div>
          </td>
          <td className="p-2">
            <div className="text-center">
              <strong className="tracking-wider rounded bg-blue-50 px-4 py-1.5 font-bold text-gray-700">
                {moment(oneDevis.dateemission).format("DD/MM/YYYY")}
              </strong>
            </div>
          </td>
          <td className="p-2">
            <div className="text-center">
              <strong className="tracking-wider rounded bg-blue-50 px-4 py-1.5 font-bold text-gray-700">
                {moment(oneDevis.dateexpiration).format("DD/MM/YYYY")}
              </strong>
            </div>
          </td>
          <td className="p-2">
            <div className="text-center text-gray-700 font-bold text-sm tracking-wide">
              {Intl.NumberFormat().format(parseInt(oneDevis.primenette))}
            </div>
          </td>
          <td className="p-2">
            <div className="text-center text-gray-700 font-bold text-sm tracking-wide">
              {Intl.NumberFormat().format(parseInt(oneDevis.primettc))}
            </div>
          </td>
          <td className="p-2">
            <div className="text-center">
              {oneDevis.confirme === true ? (
                <strong className="rounded bg-green-100 px-3 py-1.5 text-green-700 uppercase">
                  Confirmé
                </strong>
              ) : (
                <strong className="rounded bg-orange-100 px-3 py-1.5 text-orange-700 uppercase">
                  Attente
                </strong>
              )}
            </div>
          </td>
          <td className="p-2">
            <Link
              to={normalizeBoolean(oneDevis.confirme) ?
                `/production/automobile/details-contrat/${getContratId(oneDevis)}` :
                `/production/automobile/details-devis/${getDevisId(oneDevis)}`}
              state={{ iddevis: getDevisId(oneDevis) }}
              className="block"
            >
              <OutlineButton
                content="Voir"
                buttonClassname="before:bg-blue-700 text-blue-600"
              />
            </Link>
          </td>
        </tr>
      ))
    ) : (
      <tr>
        <td colSpan="10" className="text-center py-4">
          Aucun contrat. Veuillez en créer un.
        </td>
      </tr>
    );
  };

  if (isLoading) {
    return <Spinner />;
  }

  return (
    <Fragment>
      <WelcomeBanner
        title="Assurance Automobile"
        subtitle="Production de contrat automobile"
      />
      {/* CONTRAT AUTO */}
      <div className="mb-4">
        <DashboardCard01
          numbDevis={devisCounts?.nb_devis ?? 0}
          numbContrat={devisCounts?.nb_contrats ?? 0}
        />
      </div>

      <div className="rounded-lg border border-gray-100 bg-white p-4 mb-8">
        <div className="sm:flex sm:justify-between sm:items-center">
          <ContratClientInput
            idproduit={1}
            setDataResult={(results) => {
              setSearchResults(results || []);
              setHasSearched(true);
            }}
          />
          <div className="flex items-center ml-2">
            <Link to="/production/automobile/consolidation-devis" className="block mr-3">
              <AddButton content="Consolidation de devis" buttonClassname="!bg-orange-500 hover:!bg-orange-600" />
            </Link>
            <Link
              to={`/production/automobile/nouveau-contrat/${1}`}
              className="block"
            >
              <AddButton content="Affaire Nouvelle" />
            </Link>
          </div>
        </div>
      </div>

      {/* LISTES DES CONTRATS AUTOMOBILE */}
      <div className="col-span-full xl:col-span-6 bg-white shadow-xs rounded-md border border-slate-200">
        <header className="px-4 py-4 border-b border-slate-100">
          <h2 className=" text-slate-800">Contrats automobile</h2>
        </header>
        <div className="p-3">
          <div className="overflow-x-auto">
            <table className="table-auto w-full">
              {/* Table header */}
              <thead className="bg-gray-100 text-xs text-gray-500 font-light">
                <tr>
                  <th className="p-2">
                    <div className="text-center">Nom et Prenoms Client</div>
                  </th>
                  <th className="p-2">
                    <div className="text-center">N°</div>
                  </th>
                  <th className="p-2">
                    <div className="text-center">Catégorie</div>
                  </th>
                  <th className="p-2">
                    <div className="text-center">Avenant</div>
                  </th>
                  <th className="p-2">
                    <div className="text-center">Type</div>
                  </th>
                  <th className="p-2">
                    <div className="text-center">Emission</div>
                  </th>

                  <th className="p-2">
                    <div className="text-center">Expiration</div>
                  </th>
                  <th className="p-2">
                    <div className="text-center">Prime nette</div>
                  </th>
                  <th className="p-2">
                    <div className="text-center">Prime TTC</div>
                  </th>
                  <th className="p-2">
                    <FilterCard
                      title="Statut"
                      showConfirme={showConfirme}
                      toggleShowConfirme={toggleShowConfirme}
                    />
                  </th>
                  <th className="p-2">
                    <div className="text-center"></div>
                  </th>
                </tr>
              </thead>
              <ErrorBoundary>
                <tbody className="text-xs divide-y divide-slate-100">
                  {renderTableContent()}
                </tbody>
              </ErrorBoundary>
            </table>
            <div className="p-4">
              {((searchResults && searchResults.length > itemsPerPage) || listeProduction.length > itemsPerPage) && (
                <div className="flex items-center justify-center mt-4 gap-6">
                  <ReactPaginate
                    previousLabel={
                      <BsFillArrowLeftSquareFill fontSize="1.5rem" />
                    }
                    nextLabel={<BsFillArrowRightSquareFill fontSize="1.5rem" />}
                    breakLabel={"..."}
                    pageCount={Math.ceil(
                      (searchResults?.length || listeProduction.length) / itemsPerPage
                    )}
                    marginPagesDisplayed={2}
                    pageRangeDisplayed={5}
                    onPageChange={({ selected }) => setCurrentPage(selected)}
                    containerClassName={"pagination flex justify-center mt-4"}
                    activeClassName={"bg-blue-500 text-white px-3 py-1 rounded"}
                    pageClassName={"px-3 py-1"}
                    previousClassName={"mr-2 flex flex-col justify-center"}
                    nextClassName={"ml-2 flex flex-col justify-center"}
                    breakClassName={"px-3 py-1"}
                    disabledClassName={"opacity-50 cursor-not-allowed"}
                  />
                  <div className="flex items-center gap-2 mt-4">
                    <input
                      id="itemsPerPage"
                      type="number"
                      min="1"
                      max="100"
                      value={itemsPerPage}
                      onChange={(e) => {
                        setItemsPerPage(Math.max(1, parseInt(e.target.value) || 10));
                        setCurrentPage(0);
                      }}
                      className="w-16 px-2 py-1 border border-slate-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <label htmlFor="itemsPerPage" className="text-sm font-medium text-slate-700">
                      Éléments par page
                    </label>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </Fragment>
  );
};

export default Automobile;
