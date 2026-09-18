/* eslint-disable react-hooks/exhaustive-deps */
import DatePicker from "react-datepicker";
import {
  OutlineButton,
  ButtonNext,
  AddButton,
  Button,
} from "partials/UI/Button/Button";
import { saveDevis, reset } from "features/Devis/devisSlice";
import Automobile from "assets/images/icon3.svg";
import { TextInput } from "partials/UI/Inputs";
import {
  addCommas,
  carosseries,
  removeNonNumeric,
} from "partials/Utils/FormUtils";
import { Fragment, useEffect, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import Spinner from "partials/Utils/Spinner/Spinner";
import moment from "moment";
import axios from "axios";
import { MdOutlineAdd } from "react-icons/md";
import Drawer from "partials/Utils/Drawer/Drawer";
import WelcomeBanner from "partials/UI/Banner/WelcomeBanner";
import { getMarques } from "features/Contrat/contratSlice";

export const VehiculeSectionFlotte = ({
  duree,
  devisDetEdition,
  idAvenantEdition,
  reconduction,
  idAvenant,
  isEditDevis,
  nextStep,
  nomClient,
  nomAssuré,
  conducteur,
  adresseconducteur,
  numeroPermisconducteur,
  numeroPoliceCompagnie,
  prevStep,
  usage,
  idcontrat,
  motif,
  initializedMouvement,
  setInitializedMouvement,
  carosserie,
  vehiculeSectionData,
  contratSectionData,
  offreSectionData,
  categorie,
  setUsage,
  setCategorie,
  setCarosserie,
  energie,
  systemeSecurites,
  marque,
  puissancefiscale,
  chargeUtile,
  nbrPlace,
  valeurNeuf,
  valeurVenale,
  valeurAccessoire,
  setValeurAccessoire,
  immatriculation,
  chassis,
  genre,
  numeromoteur,
  modelevehicule,
  premiereCirculation,
  setEnergie,
  setSystemeSecurites,
  setMarque,
  setPuissancefiscale,
  setChargeUtile,
  setNbrPlace,
  setValeurNeuf,
  setValeurVenale,
  setImmatriculation,
  setChassis,
  setGenre,
  setNumeromoteur,
  setModeleVehicule,
  setPremiereCirculation,
  numeroCarteBrunePhysique,
  setNumeroCarteBrunePhysique,
  // ***
  typevehicule,
  setTypevehicule,
  // utils
  compagnie,
  dateEffet,
  dateExpiration,
  dateEmission,
  reduction,
  bonusmalus,
  offre,
  setOffre,
  controlIdDevis,
  controlIdDevisDet,
  vehiculesFLotte,
  setControlIdDevis,
  setControlIdDevisDet,
  setVehiculesFlotte,
  //
  securiteRoutiere,
  setSecuriteRoutiere,
  remorqueAttelee,
  toggleRemorqueAttelee,
  secu_r,
  setRemorqueAttelee,
  setTransportCompteAssure,
  transportCompteAssure,
  setTransportPublicMarchandise,
  transportPublicMarchandise,
  CarburantAutreMatiere,
  TransportEleves,
  TransportEmployes,
  TransportPassageSupplementaire,
  toggleCarburantAutreMatiere,
  toggleTransportEleves,
  toggleTransportEmployes,
  toggleTransportPassageSupplementaire,
  assistanceAuto,
  assistanceList,
  setAssistanceAuto,
  // mouvement
  policeDetails,
  isEditPolice,
  isRenouvellement,
  vehiculeAddedRenouvellement,
  setVehiculeAddedRenouvellement,
  setvaleurNeufState,
  // input state
  offreState,
  categorieState,
  usageState,
  carosserieState,
  energieState,
  systemeSecuritesState,
  securiteRoutiereState,
  assistanceAutoState,
  CarburantAutreMatiereState,
  TransportElevesState,
  TransportEmployesState,
  TransportPassageSupplementaireState,
  marqueState,
  genreState,
  nsiaAutoPlus,
  typevehiculeState,
  modelevehiculeState,
  puissancefiscaleState,
  chargeUtileState,
  nbrPlaceState,
  valeurNeufState,
  valeurVenaleState,
  valeurAccessoireState,
  immatriculationState,
  numeroCarteBrunePhysiqueState,
  chassisState,
  numeromoteurState,
  premiereCirculationState,
  remorqueAtteleeState,
}) => {
  // utils
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { token } = useSelector((state) => state.auth);

  const { devisSaved, isLoading, isSuccess, isError, message } = useSelector(
    (state) => state.devis
  );

  const usages = contratSectionData.usages;
  const tarifs = contratSectionData.tarifs;
  const energies = vehiculeSectionData.energies;
  const systemesecurites = vehiculeSectionData.systemesecurites;
  const marques = vehiculeSectionData.marques;
  const genrevehicules = vehiculeSectionData.genrevehicules;
  const typevehicules = vehiculeSectionData.typevehicules;
  const offresList = offreSectionData.offres;

  // Sort marques alphabetically
  const sortedMarques = [...marques].sort((a, b) =>
    a.LibelleMarque.localeCompare(b.LibelleMarque, 'fr', { sensitivity: 'base' })
  );

  const initializedRef = useRef(false);
  const [isLoadingVehFlotte, setIsLoadingVehFlotte] = useState(false);
  const [dataVehicule, setDataVehicule] = useState();
  const [editVehicule, setEditVehicule] = useState(false);
  const [openPanelMarque, setOpenPanelMarque] = useState(false);
  const [LibelleMarque, setLibelleMarque] = useState("");
  const [mouvementMessage, setMouvementMessage] = useState("");

  const initializingMouvement = async () => {
    try {
      const { data } = await axios.post(
        `${process.env.REACT_APP_API_URL}avenant/initiationmouvement`,
        {
          id_contrat: idcontrat,
          date_emission: handleDate(dateEmission),
          date_effet: handleDate(dateEffet),
          id_avenant: idAvenant,
          motif_annulation: motif === "" ? "R.A.S" : motif,
        },
        {
          headers: {
            Authorization: `Token ${token}`,
          },
        }
      );
      if (data && data[0] && data[0].ObjectId) {
        setControlIdDevis(data[0].ObjectId);
        setInitializedMouvement((v) => !v);
        if (idAvenant && parseInt(idAvenant) === 2 && data[0].ObjectId !== 0) {
          toast.success(data[0].OutputMessage);
          navigate(
            `/production/automobile/edition-devis/${1}/${data[0].ObjectId}`
          );
        }
      }
      setMouvementMessage(data[0].OutputMessage);
    } catch (error) {
      console.error("Error initializing mouvement:", error);
    }
  };

  useEffect(() => {
    if (isEditPolice && !initializedMouvement && !initializedRef.current) {
      initializingMouvement();
      initializedRef.current = true;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (idAvenant && parseInt(idAvenant) === 6 && controlIdDevis !== 0) {
      toast.success(mouvementMessage);
      navigate(`/production/automobile/details-devis/${controlIdDevis}`);
    }
  }, [controlIdDevis]);

  const postVehicule = async () => {
    try {
      const response = await toast.promise(
        axios.post(
          `${process.env.REACT_APP_API_URL}marque/`,
          {
            LibelleMarque: LibelleMarque,
          },
          {
            headers: {
              Authorization: `Token ${token}`,
            },
          }
        ),
        {
          loading: "Chargement...",
          success: "Succès",
          error: (e) => {
            return `${e.response.data[0].outputmessage}`;
          },
        }
      );

      // Close the sidebar
      setOpenPanelMarque(false);

      // Clear the input
      setLibelleMarque("");

      // Refresh the marques list
      await dispatch(getMarques());

      // Set the newly added marque as selected
      if (response.data && response.data.IdMarque) {
        setMarque(response.data.IdMarque);
      }
    } catch (err) {
      console.error(err);
    }
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

  const verifImmatriculation = (immatriculation, tableauVehicules) => {
    return !tableauVehicules.some(
      (vehicule) => vehicule.immatriculationVehicule === immatriculation
    );
  };

  // Fonction utilitaire pour extraire un ID d'une valeur (objet ou primitive)
  const extractId = (value) => {
    if (typeof value !== 'object' || value === null) {
      return value;
    }
    // Chercher une propriété qui contient "id" (insensible à la casse)
    const idKey = Object.keys(value).find(key => key.toLowerCase().includes('id'));
    return idKey ? value[idKey] : Object.values(value)[0];
  };

  useEffect(() => {
    if (isEditDevis && devisDetEdition && vehiculesFLotte.length === 0) {
      const newVehiculesFlotte = devisDetEdition.map((element) => ({
        iddevis: extractId(element.iddevis),
        idDevisDetail: element.iddevisdetail,
        immatriculationVehicule: element.matricule,
      }));

      setVehiculesFlotte(newVehiculesFlotte);
    }
  }, [isEditDevis, devisDetEdition]);

  useEffect(() => {
    if (isEditPolice && policeDetails) {
      const newVehiculesFlotte = policeDetails.map((element) => ({
        iddevis: extractId(element.idcontrat),
        idDevisDetail: element.idcontratdetail,
        immatriculationVehicule: element.matricule,
      }));

      setVehiculesFlotte(newVehiculesFlotte);
    }
  }, [isEditPolice, policeDetails]);

  useEffect(() => {
    if (isError) {
      toast.error(message);
    }

    if (isSuccess && devisSaved) {
      if (isEditPolice && isRenouvellement) {
        setVehiculeAddedRenouvellement([
          ...vehiculeAddedRenouvellement,
          {
            idDevisDetail: devisSaved.IdDevisDetail,
            idDevis: devisSaved.IdDevis,
          },
        ]);
      }
      if (!isEditDevis) {
        setControlIdDevis(devisSaved.IdDevis);
      }
      // setControlIdDevisDet(devisSaved.IdDevisDetail)
      setVehiculesFlotte([
        ...vehiculesFLotte,
        {
          iddevis: devisSaved.IdDevis,
          idDevisDetail: devisSaved.IdDevisDetail,
          immatriculationVehicule: devisSaved.NumeroImmatriculation,
        },
      ]);

      toast.success(devisSaved.OutputMessage);
      // navigate(`/production/automobile/details-devis/${devisSaved.ObjectId}`);
    }

    dispatch(reset());
  }, [devisSaved, isError, isSuccess, message, navigate, dispatch]);

  const handleDate = (date) => {
    return moment(date).format("DD-MM-YYYY");
  };

  const handleSaveDevis = (e) => {
    e.preventDefault();

    if (verifImmatriculation(immatriculation, vehiculesFLotte)) {
      dispatch(
        saveDevis({
          IdDuree: parseInt(duree),
          IdTerme: parseInt(reconduction),
          NumeroPoliceCompagnie: numeroPoliceCompagnie ? numeroPoliceCompagnie : "RAS",
          IdIntermediaire: 1, // +
          IdCompagnie: parseInt(compagnie), // +
          IdProduit: 1, // *
          NsiaAutoPlus: nsiaAutoPlus,
          IdOffre: parseInt(offre), // +
          IdAvenant: idAvenant ? parseInt(idAvenant) : idAvenantEdition,
          IdClient: parseInt(nomClient),
          IdAssure: parseInt(nomAssuré),
          Flotte: true,
          Coassurance: false,
          DateEffet: handleDate(dateEffet),
          // DateExpiration: handleDate(dateExpiration),

          DateExpiration:
            parseInt(duree) === 5 ? handleDate(dateExpiration) : dateExpiration,
          DateEmission: handleDate(dateEmission),
          IdTarif: parseInt(categorie), // +
          CodeUsage: parseInt(usage), // +
          IdCarrosserie: parseInt(carosserie), // +
          CodeCarburant: parseInt(energie), //  +
          Puissance: parseInt(puissancefiscale), // +
          NombrePlace: parseInt(nbrPlace), // +
          Charge: parseInt(chargeUtile), // +
          ValeurNeuve: parseFloat(valeurNeuf.replace(/ /g, "")),
          ValeurVenale: parseFloat(valeurVenale.replace(/ /g, "")),
          ValeurAccessoire: parseFloat(valeurAccessoire.replace(/ /g, "")),
          TauxReduction: reduction,
          CodeAlarme: parseInt(systemeSecurites), // +
          // Bns: parseInt(bonusmalus),
          Bns: bonusmalus ? bonusmalus : 0,
          NomConducteur: conducteur,
          AdresseConducteur: adresseconducteur,
          DateMec: handleDate(premiereCirculation),
          NumMoteur: numeromoteur,
          NumChassis: chassis,
          IdTypeVehicule: parseInt(typevehicule),
          IdMarque: parseInt(marque), // +
          Matricule: immatriculation,
          NumPermisConduire: numeroPermisconducteur,
          IdGenreVehicule: parseInt(genre),
          NumCarteBrunePhysique: numeroCarteBrunePhysique,
          ModeleVehicule: modelevehicule,
          IdDevis: parseInt(controlIdDevis),
          IdDevisDetail: parseInt(controlIdDevisDet),
          CodeFormuleSecuriteRoutiere: securiteRoutiere,
          RemorqueAttelee: remorqueAttelee,
          CarburantAutreMatiere: CarburantAutreMatiere,
          TransportEleves: TransportEleves,
          TransportEmployes: TransportEmployes,
          TansportPassagerSupplementaire: TransportPassageSupplementaire,
          IdOptionAssistance: parseInt(assistanceAuto),
        })
      );
    } else {
      toast.error("Ce véhicule existe");
    }
  };

  const handleClick = async (iddevisdetail, iddevis) => {
    setIsLoadingVehFlotte(true);
    setEditVehicule(true);

    if (isRenouvellement) {
      const isMatching = vehiculeAddedRenouvellement.some(
        (vehicule) =>
          parseInt(vehicule.idDevisDetail) === parseInt(iddevisdetail) &&
          parseInt(vehicule.idDevis) === parseInt(iddevis)
      );

      setvaleurNeufState(!isMatching);
    }

    try {
      const { data } = await axios.get(
        `${process.env.REACT_APP_API_URL}devisdetail/${iddevis}`,
        {
          headers: {
            Authorization: `Token ${token}`,
          },
        }
      );
      setDataVehicule(
        data.flatMap((n) => {
          if (parseInt(n.iddevisdetail) !== parseInt(iddevisdetail)) {
            return [];
          }
          return [n];
        })
      );
      setControlIdDevisDet(iddevisdetail);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoadingVehFlotte(false);
    }
  };

  const handleCancelEdit = () => {
    setEditVehicule(false);
    setControlIdDevisDet(0);
  };

  const handleEditVehicule = async () => {
    try {
      await toast.promise(
        axios.post(
          `${process.env.REACT_APP_API_URL}enregistrementdevis`,
          {
            IdIntermediaire: 1, // +
            IdCompagnie: parseInt(compagnie), // +
            IdProduit: 1, // *
            IdOffre: parseInt(offre), // +
            IdDuree: parseInt(duree),
            NumeroPoliceCompagnie: numeroPoliceCompagnie ? numeroPoliceCompagnie : "RAS",
            IdAvenant: idAvenant ? parseInt(idAvenant) : idAvenantEdition,
            IdClient: parseInt(nomClient), // *
            IdAssure: parseInt(nomAssuré), //  *
            Flotte: true,
            Coassurance: false,
            DateEffet: handleDate(dateEffet),
            // DateExpiration: handleDate(dateExpiration),
            DateExpiration:
              parseInt(duree) === 5
                ? handleDate(dateExpiration)
                : dateExpiration,
            DateEmission: handleDate(dateEmission),
            IdTarif: parseInt(categorie), // +
            CodeUsage: parseInt(usage), // +
            IdCarrosserie: parseInt(carosserie), // +
            CodeCarburant: parseInt(energie), //  +
            Puissance: parseInt(puissancefiscale), // +
            NombrePlace: parseInt(nbrPlace), // +
            Charge: parseInt(chargeUtile), // +
            ValeurNeuve: parseFloat(valeurNeuf.replace(/ /g, "")),
            ValeurVenale: parseFloat(valeurVenale.replace(/ /g, "")),
            ValeurAccessoire: parseFloat(valeurAccessoire.replace(/ /g, "")),
            TauxReduction: reduction,
            CodeAlarme: parseInt(systemeSecurites), // +
            // Bns: parseInt(bonusmalus),
            Bns: bonusmalus ? bonusmalus : 0,
            NomConducteur: conducteur,
            AdresseConducteur: adresseconducteur,
            DateMec: handleDate(premiereCirculation),
            NumMoteur: numeromoteur,
            NumChassis: chassis,
            IdTypeVehicule: parseInt(typevehicule),
            IdMarque: parseInt(marque), // +
            Matricule: immatriculation,
            NumPermisConduire: numeroPermisconducteur,
            IdGenreVehicule: parseInt(genre),
            NumCarteBrunePhysique: numeroCarteBrunePhysique,
            ModeleVehicule: modelevehicule,
            IdDevis: parseInt(controlIdDevis),
            IdDevisDetail: parseInt(controlIdDevisDet),
            // Mise à jour d'un véhicule existant en mode édition
            IsUpdate: controlIdDevisDet > 0,
            CodeFormuleSecuriteRoutiere: securiteRoutiere,
            RemorqueAttelee: remorqueAttelee,
            CarburantAutreMatiere: CarburantAutreMatiere,
            TransportEleves: TransportEleves,
            TransportEmployes: TransportEmployes,
            TansportPassagerSupplementaire: TransportPassageSupplementaire,
            IdOptionAssistance: parseInt(assistanceAuto),
          },
          {
            headers: {
              Authorization: `Token ${token}`,
            },
          }
        ),
        {
          loading: "Chargement...",
          success: (mes) =>
            mes.data &&
            mes.data[0] &&
            mes.data[0].OutputMessage &&
            mes.data[0].OutputMessage,
          error: (err) =>
            err.response.data[0].OutputMessage &&
            err.response.data[0].OutputMessage,
        }
      );
      setVehiculesFlotte((current) =>
        current.map((vehicule) => {
          if (vehicule.idDevisDetail === controlIdDevisDet) {
            return { ...vehicule, immatriculationVehicule: immatriculation };
          }

          return vehicule;
        })
      );
      setControlIdDevisDet(0);
      // handleGoBack();
      setEditVehicule(false);
    } catch (err) {
      console.error(err.message);
    }
  };

  const handleDeleteVehicule = async () => {
    try {
      await toast.promise(
        axios.post(
          `${process.env.REACT_APP_API_URL}annulationsaisievehicule`,
          {
            IdDevisDetail: dataVehicule.iddevisdetail,
          },
          {
            headers: {
              Authorization: `Token ${token}`,
            },
          }
        ),

        {
          loading: "Chargement...",
          success: (mes) => mes.data[0].OutputMessage,
          error: (err) => err.data[0].OutputMessage,
        }
      );
      setVehiculesFlotte((current) =>
        current.filter(
          (vehicule) => vehicule.idDevisDetail !== dataVehicule.iddevisdetail
        )
      );
      setEditVehicule(false);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (dataVehicule && dataVehicule[0]) {
      setOffre(dataVehicule[0].idoffre);
      setCategorie(dataVehicule[0].idtarif);
      setUsage(dataVehicule[0].idusage.IdUsage);
      setCarosserie(dataVehicule[0].idcarrosserie);
      setEnergie(dataVehicule[0].essence.IdEnergie);
      setMarque(dataVehicule[0].idmarque.IdMarque);
      setGenre(dataVehicule[0].idgenrevehicule.IdGenre);
      setTypevehicule(dataVehicule[0].idtypevehicule.id);
      setModeleVehicule(dataVehicule[0].modelevehicule);
      setPuissancefiscale(dataVehicule[0].puissancefiscale);
      setChargeUtile(parseInt(dataVehicule[0].chargeutile));
      setNbrPlace(dataVehicule[0].nombreplace);
      setValeurNeuf(
        addCommas(removeNonNumeric(parseInt(dataVehicule[0].valeurneuve)))
      );
      setValeurVenale(
        addCommas(removeNonNumeric(parseInt(dataVehicule[0].valeurvenale)))
      );
      setValeurAccessoire(
        addCommas(removeNonNumeric(parseInt(dataVehicule[0].valeuraccessoire)))
      );
      setImmatriculation(dataVehicule[0].matricule);
      setNumeroCarteBrunePhysique(dataVehicule[0].numcarteverte);
      setChassis(dataVehicule[0].numchassis);
      setNumeromoteur(dataVehicule[0].nummoteur);
      setPremiereCirculation(
        Date.parse(
          moment.utc(dataVehicule[0].datemec).format("YYYY-MM-DD") +
          "T00:00:00.000+00:00"
        )
      );
      setSystemeSecurites(dataVehicule[0].securite.IdSystemeSecurite);
      setRemorqueAttelee(dataVehicule[0].remorque);
      // FORMULE & 4 autres champs à ajouter
    }
  }, [dataVehicule]);

  useEffect(() => {
    if (idAvenant && parseInt(idAvenant) === 2) {
      setvaleurNeufState(false);
    }
  }, [vehiculeAddedRenouvellement]);

  // adding vehicule marque

  if (isLoading || isLoadingVehFlotte) {
    return <Spinner />;
  }

  return (
    <div className="lg:flex space-x-4">
      <div className="lg:w-9/12 p-4 mb-6 bg-white rounded-md border-2 border-gray-200">
        <h2 className="font-bold mb-4 text-sm uppercase text-blue-500">
          Véhicules
        </h2>
        <div className="grid md:grid-cols-4 md:gap-6">
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
          {/* OFFRE */}
          <div className="">
            <label
              htmlFor="offre"
              className="block text-xs font-normal text-gray-800"
            >
              Offre
            </label>
            <select
              id="offre"
              name="offre"
              value={offre}
              disabled={offreState}
              onChange={(e) => {
                setOffre(e.target.value);
              }}
              className="bg-gray-50  mt-1 block w-full rounded-md border-2 border-gray-300  py-1 px-2  focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"
            >
              {offresList.map((offre, index) => (
                <option key={index} value={offre.IdOffre}>
                  {offre.LibelleOffre}
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
          {/* ENERGIE */}
          <div className="">
            <label
              htmlFor="energie"
              className="block text-xs font-normal text-gray-700"
            >
              Énergie du véhicule (* requis)
            </label>
            <select
              name="energie"
              value={energie}
              disabled={energieState}
              onChange={(e) => setEnergie(e.target.value)}
              className="bg-gray-50  mt-1 block w-full rounded-md border-2 border-gray-300  py-1 px-2  focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"
            >
              {energies.map((energie, index) => (
                <option key={index} value={energie.IdEnergie}>
                  {energie.Libelle}
                </option>
              ))}
            </select>
          </div>
          {/* SYSTEME DE SECURITE */}
          <div className="">
            <label
              htmlFor="systemeSecurites"
              className="block text-xs font-normal text-gray-700"
            >
              Système de sécurité (* requis)
            </label>
            <select
              name="systemeSecurites"
              value={systemeSecurites}
              disabled={systemeSecuritesState}
              onChange={(e) => setSystemeSecurites(e.target.value)}
              className="bg-gray-50  mt-1 block w-full rounded-md border-2 border-gray-300  py-1 px-2  focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"
            >
              {systemesecurites.map((systemesecurite, index) => (
                <option key={index} value={systemesecurite.IdSystemeSecurite}>
                  {systemesecurite.LibelleSystemeSecurite}
                </option>
              ))}
            </select>
          </div>
          {/* SECURITE ROUTIERE */}
          <div className="">
            <label
              htmlFor="securiteRoutiere"
              className="block text-xs font-normal text-gray-800"
            >
              Formule de sécurité
            </label>
            <select
              name="securiteRoutiere"
              value={securiteRoutiere}
              disabled={securiteRoutiereState}
              onChange={(e) => setSecuriteRoutiere(e.target.value)}
              className="bg-gray-50  mt-1 block w-full rounded-md border-2 border-gray-300  py-1 px-2  focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"
            >
              {secu_r.map((element, index) => (
                <option key={index} value={element.codeformule}>
                  {element.libellelongformule}
                </option>
              ))}
            </select>
          </div>
          {/* ASSISTANCE AUTO */}
          {assistanceList && assistanceList.length > 0 && (
            <div className="">
              <label
                htmlFor="assistanceAuto"
                className="block text-xs font-normal text-gray-800"
              >
                Formule d'assistance
              </label>
              <select
                name="assistanceAuto"
                value={assistanceAuto}
                disabled={assistanceAutoState}
                onChange={(e) => setAssistanceAuto(e.target.value)}
                className="bg-gray-50  mt-1 block w-full rounded-md border-2 border-gray-300  py-1 px-2  focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"
              >
                {assistanceList.map((element) => (
                  <option key={element.id_option} value={element.id_option}>
                    {element.libelle_option}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* REMORQUE ATTELEE */}
          <div className="">
            <label className="relative top-6 left-4 inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                className="sr-only peer "
                checked={remorqueAttelee}
                disabled={remorqueAtteleeState}
                onChange={toggleRemorqueAttelee}
              />
              <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300  rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all  peer-checked:bg-green-600"></div>
              <span className="ml-3 text-sm font-bold text-gray-900">
                Remorque Attelée
              </span>
            </label>
          </div>
          {transportCompteAssure ? (
            <Fragment>
              {/* CARBURANT AUTRE MATIERE */}
              <div className="">
                <label className="relative top-6 left-4 inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer "
                    checked={CarburantAutreMatiere}
                    disabled={CarburantAutreMatiereState}
                    onChange={toggleCarburantAutreMatiere}
                  />
                  <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300  rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all  peer-checked:bg-green-600"></div>
                  <span className="ml-3 text-sm font-bold text-gray-900 ">
                    Carburant autre matière
                  </span>
                </label>
              </div>
              {/* Transport Eleves */}
              <div className="">
                <label className="relative top-6 left-4 inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer "
                    checked={TransportEleves}
                    disabled={TransportElevesState}
                    onChange={toggleTransportEleves}
                  />
                  <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all  peer-checked:bg-green-600"></div>

                  <span className="ml-3 text-sm font-bold text-gray-900 ">
                    Transport élèves
                  </span>
                </label>
              </div>
              {/* TRansport Employés */}
              <div className="">
                <label className="relative top-6 left-4 inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer "
                    checked={TransportEmployes}
                    disabled={TransportEmployesState}
                    onChange={toggleTransportEmployes}
                  />
                  <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all  peer-checked:bg-green-600"></div>

                  <span className="ml-3 text-sm font-bold text-gray-900 ">
                    Transport employés
                  </span>
                </label>
              </div>
              {/* Transport passager supp */}
              <div className="">
                <label className="relative top-6 left-4 inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer "
                    disabled={TransportPassageSupplementaireState}
                    checked={TransportPassageSupplementaire}
                    onChange={toggleTransportPassageSupplementaire}
                  />
                  <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all  peer-checked:bg-green-600"></div>

                  <span className="ml-3 text-sm font-bold text-gray-900 ">
                    Transport passager Supp...
                  </span>
                </label>
              </div>
            </Fragment>
          ) : (
            ""
          )}
          {transportPublicMarchandise ? (
            <Fragment>
              {/* CARBURANT AUTRE MATIERE */}
              <div className="">
                <label className="relative top-6 left-4 inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer "
                    checked={CarburantAutreMatiere}
                    disabled={CarburantAutreMatiereState}
                    onChange={toggleCarburantAutreMatiere}
                  />
                  <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all  peer-checked:bg-green-600"></div>
                  <span className="ml-3 text-sm font-bold text-gray-900 ">
                    Carburant autre matière
                  </span>
                </label>
              </div>
            </Fragment>
          ) : (
            ""
          )}
          {/* MARQUE */}
          <div className="">
            <label
              htmlFor="marque"
              className="block text-xs font-normal text-gray-700"
            >
              Marque du véhicule
            </label>
            <div className="flex space-x-4">
              <select
                name="marque"
                value={marque}
                disabled={marqueState}
                onChange={(e) => setMarque(e.target.value)}
                className="bg-gray-50  mt-1 block w-full rounded-md border-2 border-gray-300  py-1 px-2  focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"
              >
                {sortedMarques.map((marque, index) => (
                  <option key={index} value={marque.IdMarque}>
                    {marque.LibelleMarque}
                  </option>
                ))}
              </select>
              <span
                onClick={() => setOpenPanelMarque(true)}
                className="cursor-pointer font-bold text-sm text-blue-700 hover:text-blue-800 rounded-full bg-blue-50 py-2 px-2 flex items-center"
              >
                <MdOutlineAdd className="h-6 w-6" />
              </span>
            </div>

            <Drawer
              openPanel={openPanelMarque}
              setOpenPanel={setOpenPanelMarque}
              DialogCn="max-w-3xl"
            >
              <WelcomeBanner title="Ajouter un véhicule" />
              <TextInput
                type="text"
                name="LibelleMarque"
                value={LibelleMarque}
                onChange={(e) => setLibelleMarque(e.target.value)}
                label="Libellé de la Marque"
              />
              <AddButton
                buttonClassname="mt-4"
                handleClick={postVehicule}
                content="Valider"
              />
            </Drawer>
          </div>
          {/* GENRE DE VEHICULE */}
          <div className="">
            <label
              htmlFor="genre"
              className="block text-xs font-normal text-gray-700"
            >
              Genre de véhicule
            </label>
            <select
              name="genre"
              value={genre}
              disabled={genreState}
              onChange={(e) => setGenre(e.target.value)}
              className="bg-gray-50  mt-1 block w-full rounded-md border-2 border-gray-300  py-1 px-2  focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"
            >
              {genrevehicules.map((genrevehicule, index) => (
                <option key={index} value={genrevehicule.IdGenre}>
                  {genrevehicule.LibelleGenre}
                </option>
              ))}
            </select>
          </div>
          {/* TYPE COMMERCIAL */}
          <div className="">
            <label
              htmlFor="typevehicule"
              className="block text-xs font-normal text-gray-700"
            >
              Type commercial du véhicule
            </label>
            <select
              name="typevehicule"
              value={typevehicule}
              disabled={typevehiculeState}
              onChange={(e) => setTypevehicule(e.target.value)}
              className="bg-gray-50  mt-1 block w-full rounded-md border-2 border-gray-300  py-1 px-2  focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"
            >
              {typevehicules.map((typevehicule, index) => (
                <option key={index} value={typevehicule.id}>
                  {typevehicule.libelle_type}
                </option>
              ))}
            </select>
          </div>
          {/* MODELE VEHICULE */}
          <TextInput
            type="text"
            name="modelevehicule"
            value={modelevehicule}
            disabled={modelevehiculeState}
            onChange={(e) => setModeleVehicule(e.target.value)}
            label="Modèle véhicule"
            placeholderInput="Modèle de véhicule"
            InputClassName="text-sm"
          />
          {/* PUISSANCE FISCALE */}
          <TextInput
            type="number"
            name="puissancefiscale"
            id="puissancefiscale"
            value={puissancefiscale}
            disabled={puissancefiscaleState}
            onChange={(e) => setPuissancefiscale(e.target.value)}
            label="Puissance fiscale"
            placeholderInput="Puissance fiscale"
            InputClassName="text-sm"
          />
          {/* CHARGE UTILE */}
          <TextInput
            type="number"
            name="chargeUtile"
            value={chargeUtile}
            disabled={chargeUtileState}
            onChange={(e) => setChargeUtile(e.target.value)}
            label="Charge utile (kg) (* requis)"
            placeholderInput="Charge utile"
            InputClassName="text-sm"
          />
          {/* NBRE DE PLACES */}
          <TextInput
            type="number"
            name="nbrPlace"
            value={nbrPlace}
            disabled={nbrPlaceState}
            onChange={(e) => setNbrPlace(e.target.value)}
            label="Nombre de place"
            InputClassName="text-sm"
            placeholderInput="Nombre de places"
          />
          {/* VALEUR NEUVE */}
          <TextInput
            type="text"
            name="valeurNeuf"
            value={valeurNeuf}
            disabled={valeurNeufState}
            onChange={(e) =>
              setValeurNeuf(addCommas(removeNonNumeric(e.target.value)))
            }
            label="Valeur à neuf"
            InputClassName="text-sm"
            placeholderInput="Valeur à neuf"
          />
          {/* VALEUR VENALE */}
          <TextInput
            type="text"
            name="valeurVenale"
            value={valeurVenale}
            disabled={valeurVenaleState}
            onChange={(e) =>
              setValeurVenale(addCommas(removeNonNumeric(e.target.value)))
            }
            label="Valeur vénale"
            placeholderInput="Valeur vénale"
            InputClassName=""
          />
          {/* VALEUR VALEUR ACCESSOIRE */}
          <TextInput
            type="text"
            name="valeurAccessoire"
            value={valeurAccessoire}
            disabled={valeurAccessoireState}
            onChange={(e) =>
              setValeurAccessoire(addCommas(removeNonNumeric(e.target.value)))
            }
            label="Valeur Accessoire"
            placeholderInput="Valeur accessoire "
            InputClassName=""
          />
          {/* IMMATRICULATION */}
          <TextInput
            type="text"
            name="immatriculation"
            value={immatriculation}
            disabled={immatriculationState}
            onChange={(e) => setImmatriculation(e.target.value)}
            label="Immatriculation du véhicule"
            placeholderInput="Immatriculation du véhicule"
            InputClassName="text-sm"
          />
          {/* IMMATRICULATION */}
          <TextInput
            type="text"
            name="numero_carte_brune_physique"
            value={numeroCarteBrunePhysique}
            disabled={numeroCarteBrunePhysiqueState}
            onChange={(e) => setNumeroCarteBrunePhysique(e.target.value)}
            label="Numero carte brune physique"
            placeholderInput="Numero carte brune physique"
            InputClassName="text-sm"
          />
          {/* NUMERO CHASSIS */}
          <TextInput
            type="text"
            name="chassis"
            value={chassis}
            disabled={chassisState}
            onChange={(e) => setChassis(e.target.value)}
            label="Numéro chassis"
            placeholderInput="Numéro du chassis"
            InputClassName="text-sm"
          />
          {/* NUMERO MOTEUR */}
          <TextInput
            type="text"
            name="numeromoteur"
            value={numeromoteur}
            disabled={numeromoteurState}
            onChange={(e) => setNumeromoteur(e.target.value)}
            label="Numéro moteur"
            placeholderInput="Numéro du moteur"
            InputClassName="text-sm"
          />
          {/* 1ERE MISE EN CIRCULATION */}
          <div>
            <label
              htmlFor={premiereCirculation}
              className="block text-xs font-normal text-gray-700"
            >
              1ère mise en circulation
            </label>
            <DatePicker
              startDate={moment().toDate()}
              selected={premiereCirculation}
              disabled={premiereCirculationState}
              dateFormat="dd/MM/yyyy"
              placeholderText="ex: 01/02/2023"
              onChange={(date) => setPremiereCirculation(date)}
              className="font-bold bg-gray-50  mt-1 block rounded-md border-2 border-gray-300  focus:border-blue-400 focus:ring-blue-400 text-xs w-5/6 py-1 px-2"
            />
          </div>
        </div>

        <div className="">
          <p className="">
            {editVehicule ? (
              <Fragment>
                <OutlineButton
                  handleClick={handleCancelEdit}
                  buttonClassname="before:bg-red-600 text-red-600 text-xs"
                  content={"Annuler"}
                />

                <OutlineButton
                  handleClick={handleDeleteVehicule}
                  buttonClassname="text-white bg-red-500 hover:bg-red-600 mt-8 ml-4  "
                  content={"Supprimer le vehicule"}
                />
                <Button
                  handleClick={handleEditVehicule}
                  buttonClassname="text-white bg-green-500 hover:bg-green-600 mt-8 ml-4  "
                  content={"Enregistrer les modifications"}
                />
              </Fragment>
            ) : (
              <Fragment>
                <OutlineButton
                  handleClick={prevStep}
                  buttonClassname="before:bg-red-600 text-red-600 text-xs"
                  content={"Précédent"}
                />
                <AddButton
                  handleClick={handleSaveDevis}
                  buttonClassname="text-white bg-green-500 hover:bg-green-600 mt-8 ml-4  "
                  content={"Valider"}
                />
                <ButtonNext
                  handleClick={nextStep}
                  buttonClassname="text-white bg-blue-500 hover:bg-blue-800 mt-8 ml-4  "
                  content={"Suivant"}
                />
              </Fragment>
            )}
          </p>
        </div>
      </div>
      <div className="lg:w-3/12 p-4 mb-6 bg-white rounded-md border-2 border-gray-200">
        <h2 className="font-medium mb-4 text-xs uppercase text-blue-500">
          Liste des véhicules
        </h2>
        <div className="flex flex-col space-y-2">
          {vehiculesFLotte.map((vehicule) => (
            <article
              key={vehicule.idDevisDetail}
              className="rounded-lg border border-gray-100 bg-white p-4 shadow-sm transition hover:shadow-lg sm:p-6"
            >
              <span className="inline-block rounded bg-blue-50 p-2 text-white">
                <img
                  className="w-8 h-8 rounded-full"
                  src={Automobile}
                  width="44"
                  height="44"
                  alt="car"
                />
              </span>

              <h3 className="mt-0.5 text-lg font-medium text-gray-900">
                Immatriculation :{" "}
                <span className="font-bold">
                  {vehicule.immatriculationVehicule}
                </span>
              </h3>

              {/**/}
              <button
                onClick={() =>
                  handleClick(vehicule.idDevisDetail, vehicule.iddevis)
                }
                className="group mt-4 inline-flex items-center gap-1 text-sm font-medium text-blue-600"
              >
                Editer
                <span
                  aria-hidden="true"
                  className="block transition-all group-hover:ms-0.5 rtl:rotate-180"
                >
                  &rarr;
                </span>
              </button>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
};
