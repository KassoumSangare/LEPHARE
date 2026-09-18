/* eslint-disable react-hooks/exhaustive-deps */
import moment from "moment";
import { Fragment, useState } from "react";
import { useEffect } from "react";
import DatePicker from "react-datepicker";
import { ButtonNext, ButtonSave } from "partials/UI/Button/Button";
import { TextInput } from "partials/UI/Inputs";
import {
  termesContrat,
  carosseries,
  dureeContrat,
  typedeContrat,
  renderDuree,
  handleDate,
} from "../../Utils/FormUtils";
import { useSelector } from "react-redux";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import axios from "axios";

function ContratSection({
  nextStep,
  contratSectionData,
  compagnie,
  categorie,
  usage,
  numeroPoliceCompagnie,
  setNumeroPoliceCompagnie,
  carosserie,
  reduction,
  bonusmalus,
  reconduction,
  motif,
  duree,
  dateEmission,
  dateEffet,
  dateExpiration,
  nsiaAutoPlus,
  toggleNsiaAutoPlus,
  setCompagnie,
  setUsage,
  setCategorie,
  setCarosserie,
  setReduction,
  setBonusmalus,
  setReconduction,
  setDuree,
  setDateEffet,
  setDateEmission,
  setDateExpiration,
  expirationIndex,
  setExpirationIndex,
  typeContrat,
  setTypeContrat,
  setTransportCompteAssure,
  setTransportPublicMarchandise,
  setSecu_r,
  devisEdition,
  isEditDevis,
  isEditPolice,
  policeData,
  idAvenant,
  compagnieState,
  usageState,
  carosserieState,
  reductionState,
  bonusmalusState,
  reconductionState,
  dureeState,
  dateEmissionState,
  dateEffetState,
  categorieState,
  dateExpirationState,
  typeContratState,
  idcontrat,
  mouvements,
}) {
  const compagnies = Array.isArray(contratSectionData?.compagnies)
    ? contratSectionData.compagnies
    : [];
  const usages = Array.isArray(contratSectionData?.usages)
    ? contratSectionData.usages
    : [];
  const tarifs = Array.isArray(contratSectionData?.tarifs)
    ? contratSectionData.tarifs
    : [];
  const [transitionMvt, setTransitionMvt] = useState(false);

  const { token } = useSelector((state) => state.auth);
  const navigate = useNavigate();


  const initializingMouvement = async () => {
    console.log('🔷 [DIAGNOSTIC] initializingMouvement - Compagnie envoyée au backend:', compagnie);
    setTransitionMvt(true);
    try {

      // Calculer la date d'expiration en fonction de la durée du contrat
      let calculatedExpirationDate;
      if (parseInt(duree) === 5) {
        // Pour "Divers", calculer la période entre date_effet et date_expiration du contrat original
        // puis appliquer cette même période à la nouvelle date_effet
        if (policeData && policeData.dateeffet && policeData.dateexpiration) {
          // Récupérer les dates originales du contrat (format ISO depuis l'API)
          const originalDateEffet = moment(policeData.dateeffet);
          const originalDateExpiration = moment(policeData.dateexpiration);

          // Calculer la différence en jours entre date d'expiration et date d'effet
          const periodInDays = originalDateExpiration.diff(originalDateEffet, 'days');

          // Appliquer cette période à la nouvelle date d'effet
          calculatedExpirationDate = moment(dateEffet)
            .add(periodInDays, 'days')
            .toDate();
        } else {
          // Fallback : utiliser la date manuelle si les données du contrat original ne sont pas disponibles
          calculatedExpirationDate = expirationIndex || dateExpiration;
        }
      } else {
        // Pour les autres durées, recalculer la date d'expiration
        const monthsToAdd = parseInt(duree) === 1 ? 1 :
          parseInt(duree) === 2 ? 3 :
            parseInt(duree) === 3 ? 6 :
              parseInt(duree) === 4 ? 12 : 0;
        calculatedExpirationDate = moment(dateEffet)
          .add(monthsToAdd, "months")
          .subtract(1, "day")
          .toDate();
      }
      const { data } = await axios.post(
        `${process.env.REACT_APP_API_URL}avenant/initiationmouvement`,
        {
          id_contrat: idcontrat,
          date_emission: handleDate(dateEmission),
          date_effet: handleDate(dateEffet),
          id_avenant: idAvenant,
          date_expiration: handleDate(calculatedExpirationDate),
          // S'assurer que la compagnie choisie est bien prise en compte côté backend
          // afin d'éviter une valeur par défaut (ex: SUNU) lors du renouvellement
          id_compagnie: compagnie ? parseInt(compagnie) : undefined,
          motif_annulation: motif === "" ? "R.A.S" : motif,
        },
        {
          headers: {
            Authorization: `Token ${token}`,
          },
        }
      );
      if (data && data[0] && data[0].ObjectId) {
        if (idAvenant && parseInt(idAvenant) === 2 && data[0].ObjectId !== 0) {
          toast.success(data[0].OutputMessage);
          try {
            // Préparer l'écran d'édition pour une restauration automatique des garanties corrigées
            const newDevisId = parseInt(data[0].ObjectId);
            sessionStorage.setItem(`forceRenewalRestore_${newDevisId}`, '1');
            // Sauvegarder le numéro de police existant pour l'afficher après redirection
            if (numeroPoliceCompagnie && String(numeroPoliceCompagnie).trim() !== '') {
              sessionStorage.setItem(`renew_prev_numero_${newDevisId}`, String(numeroPoliceCompagnie).trim());
            }
            try { localStorage.removeItem(`offres_${newDevisId}`); } catch(_) {}
          } catch(_) {}
          navigate(
            `/production/automobile/edition-devis/${1}/${data[0].ObjectId}`
          );
        }
      }
    } catch (error) {
      if (error && error.response && error.response.data[0].OutputMessage) {
        toast.error(error.response.data[0].OutputMessage);
      }
    } finally {
      setTransitionMvt(false);
    }
  };

  const handleInitMouvement = () => {
    initializingMouvement();
  };

  // Validation professionnelle des dates pour le cas "Divers"
  const validateDates = () => {
    // Vérifier si la durée est "Divers" (id: 5)
    if (parseInt(duree) === 5) {
      if (!dateEffet || !dateExpiration) {
        toast.error("Veuillez renseigner la date d'effet et la date d'expiration");
        return false;
      }

      // Convertir les dates en objets Date pour comparaison
      const dateEffetObj = new Date(dateEffet);
      const dateExpirationObj = new Date(expirationIndex || dateExpiration);

      // Normaliser les dates (enlever les heures pour comparaison pure)
      dateEffetObj.setHours(0, 0, 0, 0);
      dateExpirationObj.setHours(0, 0, 0, 0);

      // Vérifier si la date d'expiration est antérieure à la date d'effet
      if (dateExpirationObj < dateEffetObj) {
        toast.error("La date d'expiration ne peut pas être antérieure à la date d'effet");
        return false;
      }

      // Vérifier si la date d'expiration est égale à la date d'effet
      //if (dateExpirationObj.getTime() === dateEffetObj.getTime()) {
       // toast.error("La date d'expiration doit être postérieure à la date d'effet");
        //return false;
      //}

      // Vérifier que la date d'effet n'est pas dans le passé (optionnel selon les règles métier)
      //const today = new Date();
      //today.setHours(0, 0, 0, 0);
      
      //if (dateEffetObj < today) {
        //toast.error("La date d'effet ne peut pas être antérieure à la date d'aujourd'hui");
        //return false;
      //}
    }

    return true;
  };

  useEffect(() => {
    const objetARechercher = tarifs.find(
      (objet) => objet.IdTarif === parseInt(categorie)
    );

    if (objetARechercher) {
      const libelle = objetARechercher.LibelleTarif;
      const isTransportAssure = libelle.includes(
        "TRANSPORT POUR LE COMPTE DE L'ASSURE"
      );
      setTransportCompteAssure(isTransportAssure);
    }

    if (objetARechercher) {
      const libelle = objetARechercher.LibelleTarif;
      const isTransportMarchandises = libelle.includes(
        "TRANSPORT PUBLIC DE MARCHANDISES (TPM)"
      );
      setTransportPublicMarchandise(isTransportMarchandises);
    }
  }, [categorie, tarifs]);

  // HANDLE FLOTTE ON EDIT DEVIS
  useEffect(() => {
    if (isEditDevis && devisEdition) {
      if (devisEdition.flotte === true) {
        setTypeContrat(1);
      } else {
        setTypeContrat(0);
      }
    } else if (isEditPolice && policeData) {
      if (policeData.flotte === true) {
        setTypeContrat(1);
      } else {
        setTypeContrat(0);
      }
    } else if (!isEditDevis && !isEditPolice) {
      // Nouvelle création : réinitialiser à MONO (0)
      setTypeContrat(0);
    }
  }, [devisEdition, isEditDevis, policeData, isEditPolice]);

  useEffect(() => {
    setDateExpiration(moment(expirationIndex).format("DD-MM-YYYY"));
  }, [expirationIndex]);

  // Initialiser la date d'expiration avec la date d'effet quand on sélectionne "Divers"
  useEffect(() => {
    if (parseInt(duree) === 5 && dateEffet && !expirationIndex) {
      setExpirationIndex(new Date(dateEffet));
    }
  }, [duree, dateEffet, expirationIndex, setExpirationIndex]);


  const selectedMouvement =
    isEditPolice &&
    mouvements &&
    mouvements.find((element) => element.IdAvenant === parseInt(idAvenant));

  return (
    <div className="p-4 mb-6 col-span-full xl:col-span-6 bg-white rounded-md border-2 border-gray-200 ">
      <h2 className="font-bold mb-4 text-sm uppercase text-blue-500">
        Contrat
      </h2>
      <div className="mb-4 flex space-x-4 mt-4">
        {/* typeContrat */}
        <label
          htmlFor="typeContrat"
          className="uppercase text-xs text-gray-500 flex items-center"
        >
          Type de contrat
        </label>
        <select
          name="typeContrat"
          value={typeContrat}
          disabled={isEditPolice}
          onChange={(e) => {
            setTypeContrat(parseInt(e.target.value, 10));
          }}
          className="bg-gray-50 block w-32 rounded-md border-2 border-gray-300  py-1 px-2  focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"
        >
          {typedeContrat.map((typeC, index) => (
            <option key={index} value={typeC.id}>
              {typeC.libelle}
            </option>
          ))}
        </select>
      </div>

      <div className="grid md:grid-cols-4 md:gap-6">
        <TextInput
          type="text"
          name="numeroPoliceCompagnie"
          id="numeroPoliceCompagnie"
          disabled={isEditPolice}
          value={numeroPoliceCompagnie}
          onChange={(e) => setNumeroPoliceCompagnie(e.target.value)}
          label="Numéro de police compagnie"
        />
        {/* COMPAGNIE D'ASSURANCE */}
        <div className="">
          <label
            htmlFor="compagnie"
            className="block text-xs font-normal text-gray-800"
          >
            Compagnie d'Assurance
          </label>
          <select
            name="compagnie"
            value={compagnie}
            disabled={compagnieState}
            onChange={(e) => {
              console.log('🔶 [DIAGNOSTIC] Changement manuel de compagnie:', e.target.value);
              setCompagnie(e.target.value);
            }}
            className="bg-gray-50  mt-1 block w-full rounded-md border-2 border-gray-300  py-1 px-2  focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"
          >
            {compagnies.map((compagnie, index) => (
              <option key={index} value={compagnie.IdCompagnie}>
                {compagnie.RaisonSociale}
              </option>
            ))}
          </select>
        </div>
        {parseInt(typeContrat) === 0 ? (
          <Fragment>
            {/* CATEGORIE */}
            <div className="">
              <label
                htmlFor="categorie"
                className="block text-xs font-normal text-gray-800"
              >
                Catégorie (* requis)
              </label>
              <select
                name="categorie"
                value={categorie}
                disabled={categorieState}
                onChange={(e) => setCategorie(e.target.value)}
                className="bg-gray-50  mt-1 block w-full rounded-md border-2 border-gray-300  py-1 px-2  focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"
              >
                {tarifs.map((tarif, index) => (
                  <option key={index} value={tarif.IdTarif}>
                    {tarif.LibelleTarif}
                  </option>
                ))}
              </select>
            </div>
            {/* USAGE */}
            <div className="">
              <label
                htmlFor="usage"
                className="block text-xs font-normal text-gray-800"
              >
                Usage Véhicule
              </label>
              <select
                name="usage"
                value={usage}
                disabled={usageState}
                onChange={(e) => setUsage(e.target.value)}
                className="bg-gray-50  mt-1 block w-full rounded-md border-2 border-gray-300  py-1 px-2  focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"
              >
                {usages.map((usage, index) => (
                  <option key={index} value={usage.IdUsage}>
                    {usage.LibelleUsage}
                  </option>
                ))}
              </select>
            </div>
            {/* CAROSSERIE */}
            <div className="">
              <label
                htmlFor="carosserie"
                className="block text-xs font-normal text-gray-800"
              >
                Carosseries
              </label>
              <select
                name="carosserie"
                value={carosserie}
                disabled={carosserieState}
                onChange={(e) => setCarosserie(e.target.value)}
                className="bg-gray-50  mt-1 block w-full rounded-md border-2 border-gray-300  py-1 px-2  focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"
              >
                {carosseries.map((carosserie, index) => (
                  <option key={index} value={carosserie.IdCarrosserie}>
                    {carosserie.LibelleCarrosserie}
                  </option>
                ))}
              </select>
            </div>
          </Fragment>
        ) : (
          ""
        )}
        {/* REDUCTION */}
        <div>
          <TextInput
            type="number"
            name="reduction"
            id="reduction"
            value={reduction}
            disabled={reductionState}
            onChange={(e) => {
              const min = 0;
              const max = 35;
              const value = Math.max(
                min,
                Math.min(max, parseFloat(e.target.value))
              );
              setReduction(value);
            }}
            label="Reduction commerciale (* requis)"
            placeholderInput="Reduction commerciale"
            InputClassName="text-xs"
          />
        </div>
        {/* BONUS MALUS */}
        <TextInput
          type="number"
          name="bonusmalus"
          id="bonusmalus"
          step="5"
          value={bonusmalus}
          disabled={bonusmalusState}
          onChange={(e) => {
            const min = 0;
            const max = 35;
            const value = Math.max(
              min,
              Math.min(max, parseFloat(e.target.value))
            );
            setBonusmalus(value);
          }}
          label="Bonus malus (* requis)"
          placeholderInput="Bonus malus"
          InputClassName="text-xs align-middle"
          max="35"
        />
        {/* TERME  */}
        <div className="">
          <label
            htmlFor="reconduction"
            className="block text-xs font-normal text-gray-800"
          >
            Terme du contrat
          </label>
          <select
            name="reconduction"
            value={reconduction}
            disabled={reconductionState}
            onChange={(e) => setReconduction(e.target.value)}
            className="bg-gray-50 mt-1 block w-full rounded-md border-2 border-gray-300  py-1 px-2  focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"
          >
            {termesContrat.map((element, index) => (
              <option key={index} value={element.id}>
                {element.libelle}
              </option>
            ))}
          </select>
        </div>
        {/* NSIA AUTO PLUS */}
        {compagnie && parseInt(compagnie) === 1 && (
          <div className="">
            <label className="relative top-6 left-4 inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                className="sr-only peer "
                checked={nsiaAutoPlus}
                onChange={toggleNsiaAutoPlus}
              />
              <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all  peer-checked:bg-green-600"></div>
              <span className="ml-3 text-sm font-bold text-gray-900">
                NSIA Auto Plus
              </span>
            </label>
          </div>
        )}
        {isEditPolice && (
          <div>
            <label
              htmlFor="dateEmission"
              className="block text-xs font-normal text-gray-800"
            >
              Date d'emission
            </label>
            <DatePicker
              id="dateEmission"
              selected={dateEmission}
              disabled={dateEmissionState}
              onChange={(date) => setDateEmission(date)}
              dateFormat="dd/MM/yyyy"
              placeholderText="JJ/MM/YYYY"
              showMonthDropdown
              showYearDropdown
              className="font-bold bg-gray-50 mt-1 block rounded-md border-2 border-gray-300  focus:border-blue-400 focus:ring-blue-400 text-xs w-5/6 py-1 px-2"
            />
          </div>
        )}
        {!isEditPolice && (
          <div>
            <label
              htmlFor="dateEmission"
              className="block text-xs font-normal text-gray-800"
            >
              Date d'emission
            </label>
            <DatePicker
              id="dateEmission"
              selected={dateEmission}
              /* includeDates retiré pour permettre la saisie de n'importe quelle date */
              disabled={dateEmissionState}
              onChange={(date) => setDateEmission(date)}
              dateFormat="dd/MM/yyyy"
              placeholderText="JJ/MM/YYYY"
              showMonthDropdown
              showYearDropdown
              className="font-bold bg-gray-50 mt-1 block rounded-md border-2 border-gray-300  focus:border-blue-400 focus:ring-blue-400 text-xs w-5/6 py-1 px-2"
            />
          </div>
        )}
        {/* DATE EFFET */}
        <div>
          <label
            htmlFor={dateEffet}
            className="block text-xs font-normal text-gray-800"
          >
            Date d'effet (* requis)
          </label>
          <DatePicker
            selected={dateEffet}
            disabled={dateEffetState}
            dateFormat="dd/MM/yyyy"
            onChange={(date) => setDateEffet(date)}
            className="font-bold bg-gray-50  mt-1 block rounded-md border-2 border-gray-300  focus:border-blue-400 focus:ring-blue-400 text-xs w-5/6 py-1 px-2"
          />
        </div>
        {/* DUREE CONTRAT */}
        <div className="">
          <label
            htmlFor="duree"
            className="block text-xs font-normal text-gray-800"
          >
            Durée du contrat
          </label>
          <select
            name="duree"
            value={duree}
            disabled={dureeState}
            onChange={(e) => setDuree(e.target.value)}
            className="bg-gray-50  mt-1 block w-full rounded-md border-2 border-gray-300  py-1 px-2  focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"
          >
            {dureeContrat.map((element, index) => (
              <option key={index} value={element.id}>
                {element.duree}
              </option>
            ))}
          </select>
        </div>
        {/* DATE EXPIRATION */}
        <div>
          <label
            htmlFor={dateExpiration}
            className="block mb-1 text-xs font-normal text-gray-800"
          >
            Date d'expiration (* requis) <br />
          </label>
          {renderDuree({
            duree,
            setDateExpiration,
            dateEffet,
            expirationIndex,
            dateExpiration,
            setExpirationIndex,
            dateExpirationState,
          })}
        </div>
      </div>


      <div className="mt-8">
        {isEditPolice ? (
          <div className="flex items-center space-x-4">
            {selectedMouvement && (
              <p key={idAvenant} className="font-bold text-red-900 text-lg">
                Vous êtes sur le point d'initialiser un mouvement de :{" "}
                <span className="text-red-500">
                  {selectedMouvement.LibelleAvenant}
                </span>
              </p>
            )}
            <ButtonSave
              disabled={transitionMvt}
              handleClick={handleInitMouvement}
              buttonClassname="text-white bg-blue-500 hover:bg-blue-800"
              content={"Confirmer le mouvement"}
            />
          </div>
        ) : (
          <ButtonNext
            handleClick={() => {
              if (validateDates()) {
                nextStep();
              }
            }}
            buttonClassname="mt-8 transition-all duration-200 text-white bg-blue-500 hover:bg-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            content="Suivant"
          />
        )}
      </div>
    </div>
  );
}

export default ContratSection;
