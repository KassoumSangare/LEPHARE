/* eslint-disable react-hooks/exhaustive-deps */

import { Fragment, useEffect, useState } from "react";

import { useDispatch, useSelector } from "react-redux";

import {

  getTarifs,

  getEnergies,

  getCompagnies,

  getQualites,

  getProfession,

  getTypeAssure,

  getTypeSouscripteur,

  // getOffres,

  getMarques,

  getSystemesecurites,

  getUsages,

  getTypeVehicule,

  getGenreVehicule,

  getCategoriePermis,

  reset,

} from "features/Contrat/contratSlice";

import { getClients } from "features/Client/clientSlice";

import { reset as resetClient } from "features/Client/clientSlice";

// Contrat Sections

import ContratSection from "partials/Contrats/ContratAutoPartials/ContratSection";

import VehiculeSection from "partials/Contrats/ContratAutoPartials/VehiculeSection";

import OffreSection from "partials/Contrats/ContratAutoPartials/OffreSection";

import ClientRegistration from "partials/Contrats/ContratAutoPartials/ClientRegistration";

import NotFound from "scenes/NotFound";

import Spinner from "partials/Utils/Spinner/Spinner";

import { useNavigate } from "react-router-dom";

import { VehiculeSectionFlotte } from "partials/Contrats/ContratAutoPartials/VehiculeSectionFlotte";

import AnnulationSaisieDevisModal from "partials/Utils/Modal/AnnulationSaisieDevisModal";

import {

  addCommas,

  handlerDate,

  removeNonNumeric,

} from "partials/Utils/FormUtils";

import axios from "axios";

import moment from "moment";



function ContratForm({

  devisEdition,

  isEditDevis,

  iddevisEdition,

  devisDetEdition,

  policeDevis,

  isEditPolice,

  policeData,

  policeDetails,

  idcontrat,

  idproduit,

  idAvenant,

  mouvements,

  motif,

  handleRenouvellementPolice,

  handleAnnulationPolice,

  isRenouvellement,

  vehiculeAddedRenouvellement,

  setVehiculeAddedRenouvellement,

  actionContent,

  compagnieState,

  usageState,

  carosserieState,

  reductionState,

  bonusmalusState,

  reconductionState,

  dureeState,

  dateEmissionState,

  dateEffetState,

  dateExpirationState,

  assistanceAutoState,

  assistanceListState,

  securiteRoutiereState,

  secu_rState,

  remorqueAtteleeState,

  energieState,

  modelevehiculeState,

  systemeSecuritesState,

  marqueState,

  puissancefiscaleState,

  chargeUtileState,

  nbrPlaceState,

  valeurNeufState,

  setvaleurNeufState,

  valeurVenaleState,

  valeurAccessoireState,

  immatriculationState,

  chassisState,

  genreState,

  numeromoteurState,

  nbreExtincteurState,

  premiereCirculationState,

  categorieState,

  offreState,

  conducteurState,

  nomClientState,

  nomAssuréState,

  numeroTelephoneState,

  adresseconducteurState,

  permisconducteurState,

  numeroPermisconducteurState,

  habitationState,

  numeroconducteurState,

  qualiteState,

  typevehiculeState,

  numeroCarteBrunePhysiqueState,

  typeContratState,

  offreFlotteState,

  transportCompteAssureState,

  transportPublicMarchandiseState,

  CarburantAutreMatiereState,

  TransportElevesState,

  TransportEmployesState,

  TransportPassageSupplementaireState,

}) {

  const { token } = useSelector((state) => state.auth);



  // CONTRATS AUTO DATA

  const [searchClientTerm, setSearchClientTerm] = useState("");

  const [searchAssureTerm, setSearchAssureTerm] = useState("");

  const [searchClientResults, setSearchClientResults] = useState(null);

  const [searchAssureResults, setSearchAssureResults] = useState(null);

  const [step, setStep] = useState(1);

  // 🎯 STATE POUR LES FONCTIONS DE CORRECTION DES PRIMES
  const [correctionFunctions, setCorrectionFunctions] = useState(null);

  // edit devis

  const [editDevisId, setEditDevisId] = useState(0);

  const [editDevisIdDet, setEditDevisIdDet] = useState(0);

  const [initiateMouvement, setInitiateMouvement] = useState(undefined);

  const [initializedMouvement, setInitializedMouvement] = useState(false);

  // contrat section

  const [numeroPoliceCompagnie, setNumeroPoliceCompagnie] = useState("");

  const [compagnie, setCompagnie] = useState();

  const [offres, setOffres] = useState([]);

  const [usage, setUsage] = useState();

  const [carosserie, setCarosserie] = useState(9);

  const [reduction, setReduction] = useState(0);

  const [bonusmalus, setBonusmalus] = useState(0);

  const [reconduction, setReconduction] = useState(1);

  const [duree, setDuree] = useState(1);

  const [dateEmission, setDateEmission] = useState(new Date());

  const [dateEffet, setDateEffet] = useState(new Date());

  const [dateExpiration, setDateExpiration] = useState(new Date());

  const [expirationIndex, setExpirationIndex] = useState(new Date());

  // vehicule

  const [assistanceAuto, setAssistanceAuto] = useState();

  const [assistanceList, setAssistanceList] = useState([]);

  const [securiteRoutiere, setSecuriteRoutiere] = useState("");

  const [secu_r, setSecu_r] = useState([]);

  const [nsiaAutoPlus, setNsiaAutoPlus] = useState(false);

  const toggleNsiaAutoPlus = () => setNsiaAutoPlus((value) => !value);

  const [remorqueAttelee, setRemorqueAttelee] = useState(false);

  const toggleRemorqueAttelee = () => setRemorqueAttelee((value) => !value);

  const [energie, setEnergie] = useState();

  const [modelevehicule, setModeleVehicule] = useState("");

  const [systemeSecurites, setSystemeSecurites] = useState();

  const [marque, setMarque] = useState();

  const [puissancefiscale, setPuissancefiscale] = useState(0);

  const [chargeUtile, setChargeUtile] = useState(0);

  const [nbrPlace, setNbrPlace] = useState(0);

  const [valeurNeuf, setValeurNeuf] = useState("0");

  const [valeurVenale, setValeurVenale] = useState("0");

  const [valeurAccessoire, setValeurAccessoire] = useState("0");

  const [immatriculation, setImmatriculation] = useState();

  const [chassis, setChassis] = useState();

  const [genre, setGenre] = useState();

  const [numeromoteur, setNumeromoteur] = useState("");

  const [nbreExtincteur, setNbreExtincteur] = useState();

  const [premiereCirculation, setPremiereCirculation] = useState(new Date());

  // offre

  const [categorie, setCategorie] = useState();

  const [offre, setOffre] = useState();

  const [checkedState, setCheckedState] = useState([]);

  const [PrimeAnnuelle, setPrimeAnnuelle] = useState(0);

  const [PrimeNette, setPrimeNette] = useState(0);

  // client

  const [conducteur, setConducteur] = useState("");

  const [nomClient, setNomClient] = useState("");

  const [nomAssuré, setNomAssuré] = useState("");

  const [numeroTelephone, setNumeroTelephone] = useState();

  const [adresseconducteur, setAdresseconducteur] = useState("");

  const [permisconducteur, setPermisconducteur] = useState("");

  const [numeroPermisconducteur, setNumeroPermisconducteur] = useState("");

  const [habitation, setHabitation] = useState("");

  const [numeroconducteur, setNumeroconducteur] = useState("");

  const [qualite, setQualite] = useState("");

  // utils

  const [typevehicule, setTypevehicule] = useState("");

  const [numeroCarteBrunePhysique, setNumeroCarteBrunePhysique] = useState("");

  // contrat flotte

  const [idAvenantEdition, setIdAvenantEdition] = useState(1);

  // utils flotte/mono

  const [typeContrat, setTypeContrat] = useState(0);

  const [offreFlotte, setOffreFlotte] = useState();

  const [controlIdDevis, setControlIdDevis] = useState(0);

  const [controlIdDevisDet, setControlIdDevisDet] = useState(0);

  const [vehiculesFLotte, setVehiculesFlotte] = useState([]);

  const [openModalAnnulation, setOpenModalAnnulation] = useState(false);

  // transport compte assure

  const [transportCompteAssure, setTransportCompteAssure] = useState(false);

  const [transportPublicMarchandise, setTransportPublicMarchandise] =

    useState(false);

  const [CarburantAutreMatiere, setCarburantAutreMatiere] = useState(false);

  const toggleCarburantAutreMatiere = () =>

    setCarburantAutreMatiere((value) => !value);

  const [TransportEleves, setTransportEleves] = useState(false);

  const toggleTransportEleves = () => setTransportEleves((value) => !value);

  const [TransportEmployes, setTransportEmployes] = useState(false);

  const toggleTransportEmployes = () => setTransportEmployes((value) => !value);

  const [TransportPassageSupplementaire, setTransportPassageSupplementaire] =

    useState(false);

  const toggleTransportPassageSupplementaire = () =>

    setTransportPassageSupplementaire((value) => !value);



  // Proceed to next step

  const nextStep = () => {

    setStep(step + 1);

  };

  // Go back to prev step

  const prevStep = () => {

    setStep(step - 1);

  };



  const dispatch = useDispatch();

  const navigate = useNavigate();

  const { clients } = useSelector((state) => state.clients);



  const {

    tarifs,

    energies,

    compagnies,

    qualites,

    // offres,

    marques,

    systemesecurites,

    usages,

    professions,

    typesouscripteurs,

    typeassures,

    // **

    typevehicules,

    genrevehicules,

    categoriepermis,

    isLoading,

    isError,

    message,

  } = useSelector((state) => state.contrats);



  const handleGoBack = () => {

    navigate(-1);

  };



  const contratSectionData = { compagnies, usages, tarifs };



  const vehiculeSectionData = {

    energies,

    systemesecurites,

    marques,

    typevehicules,

    genrevehicules,

  };

  const clientSectionData = {

    clients,

    qualites,

    categoriepermis,

  };

  const offreSectionData = { offres };



  // get assistance automobile

  const getAssistanceAuto = async () => {

    const { data } = await axios({

      method: "get",

      url: `${process.env.REACT_APP_API_URL}assistanceautomobile/${compagnie}`,

      headers: {

        Authorization: `Token ${token}`,

      },

    });

    setAssistanceList(data.data);

  };



  const getSecuriteRoutiere = async (idcompagnie) => {

    try {

      const { data } = await axios.get(

        `${process.env.REACT_APP_API_URL}securiteroutiereparcompagnie/${idcompagnie}`,

        {

          headers: {

            Authorization: `Token ${token}`,

          },

        }

      );

      setSecu_r(data.data);

    } catch (err) {

      console.error(err);

    }

  };



  const getOffres = async ({ idproduit, idtarif, token }) => {

    const config = {

      headers: {

        Authorization: `Token ${token}`,

      },

      params: {

        idproduit: idproduit,

        idtarif: idtarif,

      },

    };

    const response = await axios.get(

      `${process.env.REACT_APP_API_URL}offreparproduit/`,

      config

    );

    setOffres(response.data.data);

  };



  /**

   *

   *

   * HOOKS

   */



  useEffect(() => {

    if (compagnie) {

      getSecuriteRoutiere(parseInt(compagnie));

    }

    // eslint-disable-next-line react-hooks/exhaustive-deps

  }, [compagnie]);



  useEffect(() => {

    dispatch(getTarifs(idproduit));

    dispatch(getEnergies());

    dispatch(getCompagnies());

    dispatch(getQualites());

    dispatch(getProfession());

    dispatch(getTypeAssure());

    dispatch(getTypeSouscripteur());

    dispatch(getMarques());

    dispatch(getSystemesecurites());

    dispatch(getUsages());

    dispatch(getClients());

    dispatch(getCategoriePermis());

    dispatch(getTypeVehicule());

    dispatch(getGenreVehicule());



    return () => {

      dispatch(reset());

      dispatch(resetClient());

    };

    // eslint-disable-next-line react-hooks/exhaustive-deps

  }, [isError, message, dispatch]);



  useEffect(() => {

    if (categorie && idproduit) {

      getOffres({ idproduit, idtarif: categorie, token });

    }

    // eslint-disable-next-line react-hooks/exhaustive-deps

  }, [categorie]);



  useEffect(() => {

    if (!isEditDevis && !isEditPolice) {

      if (tarifs[0]) {

        setCategorie(Object.values(tarifs[0])[0]);

      }

    }

  }, [tarifs]);



  useEffect(() => {

    if (!isEditDevis && !isEditPolice) {

      if (usages[0]) {

        setUsage(Object.values(usages[0])[0]);

      }

    }

  }, [usages]);



  useEffect(() => {

    if (!isEditDevis && !isEditPolice) {

      if (compagnies[0]) {
        console.log('🔵 [DIAGNOSTIC] useEffect compagnies - Initialisation par défaut:', Object.values(compagnies[0])[0]);

        setCompagnie(Object.values(compagnies[0])[0]);

      }

    }

  }, [compagnies]);



  useEffect(() => {

    if (!isEditDevis && !isEditPolice) {

      if (clients[0] && categoriepermis[0]) {

        setNomClient(Object.values(clients[0])[0]);

        setNomAssuré(Object.values(clients[0])[0]);

        setPermisconducteur(Object.values(categoriepermis[0])[0]);

      }

    }

  }, [clients]);



  useEffect(() => {

    if (!isEditDevis && !isEditPolice) {

      if (

        energies[0] &&

        systemesecurites[0] &&

        marques[0] &&

        genrevehicules[0] &&

        typevehicules[0]

      ) {

        setEnergie(Object.values(energies[0])[0]);

        setSystemeSecurites(Object.values(systemesecurites[0])[0]);

        setMarque(Object.values(marques[0])[0]);

        setGenre(Object.values(genrevehicules[0])[0]);

        setTypevehicule(Object.values(typevehicules[0])[0]);

      }

    }

  }, [energies, systemesecurites, marques, genrevehicules, typevehicules]);



  useEffect(() => {

    if (!isEditDevis && !isEditPolice) {

      if (offres && offres[0]) {

        setOffre(Object.values(offres[0])[0]);

      }

    }

  }, [offres]);



  useEffect(() => {

    if (!isEditDevis && !isEditPolice) {

      if (secu_r[0]) {

        setSecuriteRoutiere(Object.values(secu_r[0])[1]);

      }

    }

  }, [secu_r]);



  useEffect(() => {

    if (!isEditDevis && !isEditPolice) {

      if (assistanceList[0]) {

        setAssistanceAuto(Object.values(assistanceList[0])[0]);

      }

    }

  }, [assistanceList]);



  useEffect(() => {

    if (compagnie) {

      getAssistanceAuto();

    }

  }, [compagnie]);



  useEffect(() => {

    if (isEditDevis && devisEdition && iddevisEdition) {

      if (

        devisEdition &&

        devisEdition.avenant &&

        devisEdition.avenant.IdAvenant

      ) {

        setIdAvenantEdition(devisEdition.avenant.IdAvenant);

      }



      // Restaurer le numéro de police depuis l'API ou depuis la session (cas renouvellement)
      let policeNum = devisEdition.numero_police_compagnie;
      try {
        const fromSession = sessionStorage.getItem(`renew_prev_numero_${iddevisEdition}`);
        if ((!policeNum || String(policeNum).trim() === '' || String(policeNum).trim().toUpperCase() === 'RAS') && fromSession) {
          policeNum = fromSession;
        }
      } catch (_) {}
      setNumeroPoliceCompagnie(policeNum);

      setControlIdDevis(iddevisEdition);

      setEditDevisId(iddevisEdition);

      console.log('🟢 [DIAGNOSTIC] Edition devis - Compagnie depuis BD:', devisEdition.compagnie.IdCompagnie, 'Nom:', devisEdition.compagnie.RaisonSociale);
      setCompagnie(parseInt(devisEdition.compagnie.IdCompagnie));

      setDuree(parseInt(devisEdition.idduree));

      setReconduction(devisEdition.idterme);

      setOffre(devisEdition.offre.IdOffre);

      setNomClient(devisEdition.client.IdClient);

      setNomAssuré(devisEdition.assure.IdClient);

      // Initialiser les termes de recherche avec les noms complets
      setSearchClientTerm(devisEdition.client.Nom || "");

      setSearchAssureTerm(devisEdition.assure.Nom || "");

      // Initialiser les résultats de recherche avec les clients complets
      setSearchClientResults([devisEdition.client]);

      setSearchAssureResults([devisEdition.assure]);

      setDateEffet(handlerDate(devisEdition.dateeffet));

      setDateExpiration(handlerDate(devisEdition.dateexpiration));

      setDateEmission(handlerDate(devisEdition.dateemission));

      setNumeroTelephone(devisEdition.assure.Telephone);

      // Initialiser les champs conducteur avec les données du client/assuré
      setAdresseconducteur(devisEdition.assure.Adresse1 || "");

      setHabitation(devisEdition.intermediaire.Adresse || "");

      // Initialiser la catégorie de permis avec les données du devisdetail
      if (devisDetEdition && devisDetEdition[0]) {
        setPermisconducteur(devisDetEdition[0].pctype || "");
        setNumeroPermisconducteur(devisDetEdition[0].numpccnd || "");

        setControlIdDevisDet(devisDetEdition[0].iddevisdetail);

        setEditDevisIdDet(devisDetEdition[0].iddevisdetail);

        setCategorie(parseInt(devisDetEdition[0].idtarif));

        setUsage(devisDetEdition[0].idusage.IdUsage);

        setCarosserie(devisDetEdition[0].idcarrosserie);

        setEnergie(devisDetEdition[0].essence.IdEnergie);

        setPuissancefiscale(devisDetEdition[0].puissancefiscale);

        setNbrPlace(devisDetEdition[0].nombreplace);

        setChargeUtile(parseInt(devisDetEdition[0].chargeutile));

        setValeurNeuf(

          addCommas(removeNonNumeric(parseInt(devisDetEdition[0].valeurneuve)))

        );

        setValeurVenale(

          addCommas(removeNonNumeric(parseInt(devisDetEdition[0].valeurvenale)))

        );

        setValeurAccessoire(

          addCommas(

            removeNonNumeric(parseInt(devisDetEdition[0].valeuraccessoire))

          )

        );

        setReduction(parseInt(devisDetEdition[0].taux_reduction));

        setSystemeSecurites(devisDetEdition[0].securite.IdSystemeSecurite);

        setBonusmalus(parseInt(devisDetEdition[0].bns));

        setConducteur(devisDetEdition[0].conducteur);

        setAdresseconducteur(devisDetEdition[0].adressecnd);

        setPremiereCirculation(handlerDate(devisDetEdition[0].datemec));

        setNumeromoteur(devisDetEdition[0].nummoteur);

        setChassis(devisDetEdition[0].numchassis);

        setTypevehicule(devisDetEdition[0].idtypevehicule.id);

        setMarque(devisDetEdition[0].idmarque.IdMarque);

        setImmatriculation(devisDetEdition[0].matricule);

        setNumeroPermisconducteur(devisDetEdition[0].numpccnd);

        setGenre(devisDetEdition[0].idgenrevehicule.IdGenre);

        setModeleVehicule(devisDetEdition[0].modelevehicule);

        setSecuriteRoutiere(devisDetEdition[0].formule_securite_routiere);

        setCarburantAutreMatiere(devisDetEdition[0].carburant_autre_matiere);

        setTransportEleves(devisDetEdition[0].transport_eleves);

        setTransportEmployes(devisDetEdition[0].transport_employes);

        setTransportPassageSupplementaire(

          devisDetEdition[0].transport_passager_supplementaire

        );

        setRemorqueAttelee(devisDetEdition[0].remorque);

        setNumeroCarteBrunePhysique(devisDetEdition[0].numcarteverte);

      }

    }

  }, [isEditDevis, devisDetEdition, devisEdition]);



  useEffect(() => {

    if (isEditDevis) {

      if (

        !devisDetEdition ||

        !devisDetEdition[0] ||

        devisDetEdition.length === 0

      ) {

        if (secu_r[0]) {

          setSecuriteRoutiere(Object.values(secu_r[0])[1]);

        }

        if (assistanceList[0]) {

          setAssistanceAuto(Object.values(assistanceList[0])[0]);

        }

        if (usages[0]) {

          setUsage(Object.values(usages[0])[0]);

        }

        if (tarifs[0]) {

          setCategorie(Object.values(tarifs[0])[0]);

        }

      }

    }

  }, [isEditDevis, devisDetEdition, secu_r, compagnies, usages, tarifs, assistanceList]);



  useEffect(() => {

    if (isEditDevis) {

      if (

        !devisDetEdition ||

        !devisDetEdition[0] ||

        devisDetEdition.length === 0

      ) {

        if (offres && offres[0]) {

          setOffre(Object.values(offres[0])[0]);

        }

      }

    }

  }, [isEditDevis, devisDetEdition, offres]);



  useEffect(() => {

    if (isEditDevis) {

      if (

        !devisDetEdition ||

        !devisDetEdition[0] ||

        devisDetEdition.length === 0

      ) {

        if (

          energies[0] &&

          systemesecurites[0] &&

          marques[0] &&

          genrevehicules[0] &&

          typevehicules[0]

        ) {

          setEnergie(Object.values(energies[0])[0]);

          setSystemeSecurites(Object.values(systemesecurites[0])[0]);

          setMarque(Object.values(marques[0])[0]);

          setGenre(Object.values(genrevehicules[0])[0]);

          setTypevehicule(Object.values(typevehicules[0])[0]);

        }



        if (clients[0] && categoriepermis[0]) {

          setNomClient(Object.values(clients[0])[0]);

          setNomAssuré(Object.values(clients[0])[0]);

          setPermisconducteur(Object.values(categoriepermis[0])[0]);

        }

      }

    }

  }, [isEditDevis, devisDetEdition, clients, energies, systemeSecurites, marques, genrevehicules, typevehicules, categoriepermis]);



  useEffect(() => {

    if (initiateMouvement && initiateMouvement[0]) {

      setControlIdDevis(initiateMouvement[0]);

    }

  }, [initiateMouvement]);



  useEffect(() => {

    if (isEditPolice && policeData && policeDetails && idcontrat) {

      const updateStates = () => {

        if (policeData.numeropolice) {

          setNumeroPoliceCompagnie(policeData.numeropolice);

        }



        if (policeDevis) {

          setEditDevisIdDet(parseInt(policeDevis.iddevisdetail));

        }



        if (energies && energies[0]) {

          setEnergie(Object.values(energies[0])[0]);

        } else {

          setEnergie(0);

        }



        console.log('🟡 [DIAGNOSTIC] Edition police - Compagnie depuis BD:', policeData.idcompagnie);
        setCompagnie(parseInt(policeData.idcompagnie));

        // const dureeMap = {

        //   30: 1,

        //   90: 2,

        //   180: 3,

        //   365: 4,

        // };

        // const mappedId = dureeMap[policeData.idduree] || 5;

        setDuree(parseInt(policeData.idduree));

        setReconduction(parseInt(policeData.idterme));

        setNomClient(parseInt(policeData.idclient));

        setNomAssuré(parseInt(policeData.idassure));

        // Pour le renouvellement, la date d'effet = date d'expiration + 1 jour
        if (parseInt(idAvenant) === 2 && policeData.dateexpiration) {
          const expirationDate = handlerDate(policeData.dateexpiration);
          const newDateEffet = new Date(expirationDate);
          newDateEffet.setDate(newDateEffet.getDate() + 1);
          setDateEffet(newDateEffet);

          // Calculer la nouvelle date d'expiration en fonction de la durée du contrat
          const dureeContrat = parseInt(policeData.idduree);

          if (dureeContrat === 5) {
            // Pour "Divers", calculer la période entre date_effet et date_expiration du contrat original
            const originalDateEffet = moment(policeData.dateeffet);
            const originalDateExpiration = moment(policeData.dateexpiration);
            const periodInDays = originalDateExpiration.diff(originalDateEffet, 'days');

            // Appliquer cette période à la nouvelle date d'effet
            const newExpirationDate = moment(newDateEffet).add(periodInDays, 'days').toDate();
            setDateExpiration(newExpirationDate);
            setExpirationIndex(newExpirationDate);
          } else {
            // Pour les autres durées (Mensuelle, Trimestrielle, Semestrielle, Annuelle)
            const monthsToAdd = dureeContrat === 1 ? 1 :
                               dureeContrat === 2 ? 3 :
                               dureeContrat === 3 ? 6 :
                               dureeContrat === 4 ? 12 : 0;

            const newExpirationDate = moment(newDateEffet)
              .add(monthsToAdd, "months")
              .subtract(1, "day")
              .toDate();

            setDateExpiration(newExpirationDate);
          }
        } else {
          setDateEffet(handlerDate(policeData.dateeffet));
          setDateExpiration(handlerDate(policeData.dateexpiration));
        }



        if (policeDetails[0]) {

          setOffre(parseInt(policeDetails[0].idoffre));

          setCategorie(parseInt(policeDetails[0].idtarif));

          setUsage(parseInt(policeDetails[0].idusage));

          setCarosserie(policeDetails[0].idcarrosserie);

          setPuissancefiscale(policeDetails[0].puissancefiscale);

          setNbrPlace(policeDetails[0].nombreplace);

          setChargeUtile(parseInt(policeDetails[0].chargeutile));

          setValeurNeuf(

            addCommas(removeNonNumeric(parseInt(policeDetails[0].valeurneuve)))

          );

          setValeurVenale(

            addCommas(removeNonNumeric(parseInt(policeDetails[0].valeurvenale)))

          );

          setValeurAccessoire(

            addCommas(

              removeNonNumeric(parseInt(policeDetails[0].valeuraccessoire))

            )

          );

          setReduction(parseInt(policeDetails[0].taux_reduction));

          setSystemeSecurites(parseInt(policeDetails[0].securite));

          setBonusmalus(parseInt(policeDetails[0].bns));

          setConducteur(policeDetails[0].conducteur);

          setAdresseconducteur(policeDetails[0].adressecnd);

          setPremiereCirculation(handlerDate(policeDetails[0].datemec));

          setNumeromoteur(policeDetails[0].nummoteur);

          setChassis(policeDetails[0].numchassis);

          setTypevehicule(policeDetails[0].idtypevehicule);

          setMarque(policeDetails[0].idmarque);

          setImmatriculation(policeDetails[0].matricule);

          setNumeroPermisconducteur(policeDetails[0].numpccnd);

          setGenre(policeDetails[0].idgenrevehicule);

          setModeleVehicule(policeDetails[0].modelevehicule);

          // setSecuriteRoutiere(policeDetails[0].formule_securite_routiere);

          setCarburantAutreMatiere(policeDetails[0].carburant_autre_matiere);

          setTransportEleves(policeDetails[0].transport_eleves);

          setTransportEmployes(policeDetails[0].transport_employes);

          setTransportPassageSupplementaire(

            policeDetails[0].transport_passager_supplementaire

          );

          setRemorqueAttelee(policeDetails[0].remorque);

          setNumeroCarteBrunePhysique(policeDetails[0].numcarteverte);

        }



        if (idAvenant && idAvenant === 2) {

          setDateEmission(new Date());

        } else {

          setDateEmission(handlerDate(policeData.emission));

        }

      };



      updateStates();

    }

  }, [isEditPolice, policeData, policeDetails, idcontrat, policeDevis]);



  if (isLoading) {

    return <Spinner />;

  }



  return (

    <Fragment>

      {(() => {

        switch (step) {

          case 1:

            return (

              <Fragment>

                <div className="mb-2 flex">

                  <p className="text-sm">

                    {controlIdDevis ? (

                      <button

                        onClick={() => setOpenModalAnnulation(true)}

                        className="mb-2 ml-2 relative font-medium text-red-600 before:absolute before:-bottom-1 before:h-0.5 before:w-full before:origin-left before:scale-x-0 before:bg-red-600 before:transition hover:before:scale-100"

                      >

                        Annuler

                      </button>

                    ) : (

                      <button

                        onClick={handleGoBack}

                        className="mb-2 ml-2 relative font-medium text-red-600 before:absolute before:-bottom-1 before:h-0.5 before:w-full before:origin-left before:scale-x-0 before:bg-red-600 before:transition hover:before:scale-100"

                      >

                        Annuler

                      </button>

                    )}

                    <AnnulationSaisieDevisModal

                      controlIdDevis={controlIdDevis}

                      setOpenModalAnnulation={setOpenModalAnnulation}

                      openModalAnnulation={openModalAnnulation}

                    />

                  </p>

                </div>

                <ContratSection

                  isEditDevis={isEditDevis}

                  devisEdition={devisEdition}

                  numeroPoliceCompagnie={numeroPoliceCompagnie}

                  setNumeroPoliceCompagnie={setNumeroPoliceCompagnie}

                  setSecu_r={setSecu_r}

                  idcontrat={idcontrat}

                  nextStep={nextStep}

                  motif={motif}

                  mouvements={mouvements}

                  idAvenant={idAvenant}

                  contratSectionData={contratSectionData}

                  compagnie={compagnie}

                  categorie={categorie}

                  usage={usage}

                  carosserie={carosserie}

                  reduction={reduction}

                  bonusmalus={bonusmalus}

                  reconduction={reconduction}

                  duree={duree}

                  nsiaAutoPlus={nsiaAutoPlus}

                  toggleNsiaAutoPlus={toggleNsiaAutoPlus}

                  dateEmission={dateEmission}

                  dateEffet={dateEffet}

                  dateExpiration={dateExpiration}

                  expirationIndex={expirationIndex}

                  setExpirationIndex={setExpirationIndex}

                  typeContrat={typeContrat}

                  setTypeContrat={setTypeContrat}

                  setCompagnie={setCompagnie}

                  setUsage={setUsage}

                  setCategorie={setCategorie}

                  setCarosserie={setCarosserie}

                  setReduction={setReduction}

                  setBonusmalus={setBonusmalus}

                  setReconduction={setReconduction}

                  setDuree={setDuree}

                  setDateEmission={setDateEmission}

                  setDateEffet={setDateEffet}

                  setDateExpiration={setDateExpiration}

                  dateExpirationState={dateExpirationState}

                  setTransportCompteAssure={setTransportCompteAssure}

                  transportCompteAssure={transportCompteAssure}

                  setTransportPublicMarchandise={setTransportPublicMarchandise}

                  transportPublicMarchandise={transportPublicMarchandise}

                  assistanceAuto={assistanceAuto}

                  isEditPolice={isEditPolice}

                  policeData={policeData}

                  compagnieState={compagnieState}

                  categorieState={categorieState}

                  typeContratState={typeContratState}

                  usageState={usageState}

                  carosserieState={carosserieState}

                  reductionState={reductionState}

                  bonusmalusState={bonusmalusState}

                  reconductionState={reconductionState}

                  dureeState={dureeState}

                  dateEmissionState={dateEmissionState}

                  dateEffetState={dateEffetState}

                />

              </Fragment>

            );

          case 2:

            return parseInt(typeContrat) === 0 ? (

              <Fragment>

                <div className="mb-2 flex ">

                  <p className="text-sm">

                    {controlIdDevis ? (

                      <button

                        onClick={() => setOpenModalAnnulation(true)}

                        className="mb-2 ml-2 relative font-medium text-red-600 before:absolute before:-bottom-1 before:h-0.5 before:w-full before:origin-left before:scale-x-0 before:bg-red-600 before:transition hover:before:scale-100"

                      >

                        Annuler

                      </button>

                    ) : (

                      <button

                        onClick={handleGoBack}

                        className="mb-2 ml-2 relative font-medium text-red-600 before:absolute before:-bottom-1 before:h-0.5 before:w-full before:origin-left before:scale-x-0 before:bg-red-600 before:transition hover:before:scale-100"

                      >

                        Annuler

                      </button>

                    )}

                    <AnnulationSaisieDevisModal

                      controlIdDevis={controlIdDevis}

                      setOpenModalAnnulation={setOpenModalAnnulation}

                      openModalAnnulation={openModalAnnulation}

                    />

                  </p>

                </div>

                <VehiculeSection

                  isEditPolice={isEditPolice}

                  idAvenant={idAvenant}

                  idcontrat={idcontrat}

                  motif={motif}

                  categorie={categorie}



                  initializedMouvement={initializedMouvement}

                  setInitializedMouvement={setInitializedMouvement}

                  controlIdDevis={controlIdDevis}

                  setControlIdDevis={setControlIdDevis}

                  setInitiateMouvement={setInitiateMouvement}

                  assistanceAuto={assistanceAuto}

                  assistanceList={assistanceList}

                  setAssistanceAuto={setAssistanceAuto}

                  nsiaAutoPlus={nsiaAutoPlus}

                  secu_r={secu_r}

                  securiteRoutiere={securiteRoutiere}

                  setSecuriteRoutiere={setSecuriteRoutiere}

                  remorqueAttelee={remorqueAttelee}

                  transportCompteAssure={transportCompteAssure}

                  transportPublicMarchandise={transportPublicMarchandise}

                  toggleRemorqueAttelee={toggleRemorqueAttelee}

                  typeContrat={typeContrat}

                  modelevehicule={modelevehicule}

                  setModeleVehicule={setModeleVehicule}

                  nextStep={nextStep}

                  prevStep={prevStep}

                  vehiculeSectionData={vehiculeSectionData}

                  energie={energie}

                  systemeSecurites={systemeSecurites}

                  marque={marque}

                  puissancefiscale={puissancefiscale}

                  chargeUtile={chargeUtile}

                  nbrPlace={nbrPlace}

                  valeurNeuf={valeurNeuf}

                  valeurVenale={valeurVenale}

                  valeurAccessoire={valeurAccessoire}

                  setValeurAccessoire={setValeurAccessoire}

                  immatriculation={immatriculation}

                  chassis={chassis}

                  dateEffet={dateEffet}

                  dateEmission={dateEmission}

                  genre={genre}

                  numeromoteur={numeromoteur}

                  nbreExtincteur={nbreExtincteur}

                  premiereCirculation={premiereCirculation}

                  setEnergie={setEnergie}

                  setSystemeSecurites={setSystemeSecurites}

                  setMarque={setMarque}

                  setPuissancefiscale={setPuissancefiscale}

                  setChargeUtile={setChargeUtile}

                  setNbrPlace={setNbrPlace}

                  setValeurNeuf={setValeurNeuf}

                  setValeurVenale={setValeurVenale}

                  setImmatriculation={setImmatriculation}

                  setChassis={setChassis}

                  setGenre={setGenre}

                  setNumeromoteur={setNumeromoteur}

                  setNbreExtincteur={setNbreExtincteur}

                  setPremiereCirculation={setPremiereCirculation}

                  // **

                  typevehicule={typevehicule}

                  setTypevehicule={setTypevehicule}

                  numeroCarteBrunePhysique={numeroCarteBrunePhysique}

                  setNumeroCarteBrunePhysique={setNumeroCarteBrunePhysique}

                  // helpers

                  CarburantAutreMatiere={CarburantAutreMatiere}

                  TransportEleves={TransportEleves}

                  TransportEmployes={TransportEmployes}

                  TransportPassageSupplementaire={

                    TransportPassageSupplementaire

                  }

                  toggleCarburantAutreMatiere={toggleCarburantAutreMatiere}

                  toggleTransportEleves={toggleTransportEleves}

                  toggleTransportEmployes={toggleTransportEmployes}

                  toggleTransportPassageSupplementaire={

                    toggleTransportPassageSupplementaire

                  }

                  // input state

                  energieState={energieState}

                  systemeSecuritesState={systemeSecuritesState}

                  securiteRoutiereState={securiteRoutiereState}

                  assistanceAutoState={assistanceAutoState}

                  marqueState={marqueState}

                  genreState={genreState}

                  typevehiculeState={typevehiculeState}

                  remorqueAtteleeState={remorqueAtteleeState}

                  CarburantAutreMatiereState={CarburantAutreMatiereState}

                  TransportElevesState={TransportElevesState}

                  TransportEmployesState={TransportEmployesState}

                  TransportPassageSupplementaireState={

                    TransportPassageSupplementaireState

                  }

                  modelevehiculeState={modelevehiculeState}

                  puissancefiscaleState={puissancefiscaleState}

                  chargeUtileState={chargeUtileState}

                  nbrPlaceState={nbrPlaceState}

                  valeurNeufState={valeurNeufState}

                  valeurVenaleState={valeurVenaleState}

                  valeurAccessoireState={valeurAccessoireState}

                  immatriculationState={immatriculationState}

                  numeroCarteBrunePhysiqueState={numeroCarteBrunePhysiqueState}

                  chassisState={chassisState}

                  numeromoteurState={numeromoteurState}

                  premiereCirculationState={premiereCirculationState}

                />

              </Fragment>

            ) : (

              <Fragment>

                <div className="mb-2 flex ">

                  <p className="text-sm">

                    {controlIdDevis ? (

                      <button

                        onClick={() => setOpenModalAnnulation(true)}

                        className="mb-2 ml-2 relative font-medium text-red-600 before:absolute before:-bottom-1 before:h-0.5 before:w-full before:origin-left before:scale-x-0 before:bg-red-600 before:transition hover:before:scale-100"

                      >

                        Annuler

                      </button>

                    ) : (

                      <button

                        onClick={() => navigate("/production/automobile")}

                        className="mb-2 ml-2 relative font-medium text-red-600 before:absolute before:-bottom-1 before:h-0.5 before:w-full before:origin-left before:scale-x-0 before:bg-red-600 before:transition hover:before:scale-100"

                      >

                        Annuler

                      </button>

                    )}

                    <AnnulationSaisieDevisModal

                      controlIdDevis={controlIdDevis}

                      setOpenModalAnnulation={setOpenModalAnnulation}

                      openModalAnnulation={openModalAnnulation}

                    />

                  </p>

                </div>

                <VehiculeSectionFlotte

                  idAvenant={idAvenant}

                  idcontrat={idcontrat}

                  nomClient={nomClient}

                  nomAssuré={nomAssuré}

                  numeroPermisconducteur={numeroPermisconducteur}

                  conducteur={conducteur}

                  permisconducteur={permisconducteur}

                  numeroconducteur={numeroconducteur}

                  adresseconducteur={adresseconducteur}

                  idAvenantEdition={idAvenantEdition}

                  initializedMouvement={initializedMouvement}

                  setInitializedMouvement={setInitializedMouvement}

                  motif={motif}

                  assistanceAuto={assistanceAuto}

                  assistanceList={assistanceList}

                  numeroPoliceCompagnie={numeroPoliceCompagnie}

                  setAssistanceAuto={setAssistanceAuto}

                  reconduction={reconduction}

                  duree={duree}

                  devisDetEdition={devisDetEdition}

                  isEditDevis={isEditDevis}

                  nsiaAutoPlus={nsiaAutoPlus}

                  iddevisEdition={iddevisEdition}

                  secu_r={secu_r}

                  securiteRoutiere={securiteRoutiere}

                  setSecuriteRoutiere={setSecuriteRoutiere}

                  remorqueAttelee={remorqueAttelee}

                  // utils

                  setTransportCompteAssure={setTransportCompteAssure}

                  transportCompteAssure={transportCompteAssure}

                  setTransportPublicMarchandise={setTransportPublicMarchandise}

                  transportPublicMarchandise={transportPublicMarchandise}

                  setRemorqueAttelee={setRemorqueAttelee}

                  toggleRemorqueAttelee={toggleRemorqueAttelee}

                  controlIdDevis={controlIdDevis}

                  controlIdDevisDet={controlIdDevisDet}

                  vehiculesFLotte={vehiculesFLotte}

                  setControlIdDevis={setControlIdDevis}

                  setControlIdDevisDet={setControlIdDevisDet}

                  setVehiculesFlotte={setVehiculesFlotte}

                  nextStep={nextStep}

                  prevStep={prevStep}

                  typeContrat={typeContrat}

                  vehiculeSectionData={vehiculeSectionData}

                  contratSectionData={contratSectionData}

                  modelevehicule={modelevehicule}

                  setModeleVehicule={setModeleVehicule}

                  offreSectionData={offreSectionData}

                  offreFlotte={offreFlotte}

                  setOffreFlotte={setOffreFlotte}

                  categorie={categorie}

                  usage={usage}

                  carosserie={carosserie}

                  setUsage={setUsage}

                  setCategorie={setCategorie}

                  setCarosserie={setCarosserie}

                  energie={energie}

                  systemeSecurites={systemeSecurites}

                  marque={marque}

                  puissancefiscale={puissancefiscale}

                  chargeUtile={chargeUtile}

                  nbrPlace={nbrPlace}

                  valeurNeuf={valeurNeuf}

                  valeurVenale={valeurVenale}

                  valeurAccessoire={valeurAccessoire}

                  setValeurAccessoire={setValeurAccessoire}

                  immatriculation={immatriculation}

                  chassis={chassis}

                  genre={genre}

                  numeromoteur={numeromoteur}

                  nbreExtincteur={nbreExtincteur}

                  premiereCirculation={premiereCirculation}

                  setEnergie={setEnergie}

                  setSystemeSecurites={setSystemeSecurites}

                  setMarque={setMarque}

                  setPuissancefiscale={setPuissancefiscale}

                  setChargeUtile={setChargeUtile}

                  setNbrPlace={setNbrPlace}

                  setValeurNeuf={setValeurNeuf}

                  setValeurVenale={setValeurVenale}

                  setImmatriculation={setImmatriculation}

                  setChassis={setChassis}

                  setGenre={setGenre}

                  setNumeromoteur={setNumeromoteur}

                  setNbreExtincteur={setNbreExtincteur}

                  setPremiereCirculation={setPremiereCirculation}

                  // **

                  typevehicule={typevehicule}

                  setTypevehicule={setTypevehicule}

                  numeroCarteBrunePhysique={numeroCarteBrunePhysique}

                  setNumeroCarteBrunePhysique={setNumeroCarteBrunePhysique}

                  //handle save

                  compagnie={compagnie}

                  offre={offre}

                  setOffre={setOffre}

                  dateEffet={dateEffet}

                  dateExpiration={dateExpiration}

                  dateEmission={dateEmission}

                  reduction={reduction}

                  bonusmalus={bonusmalus}

                  CarburantAutreMatiere={CarburantAutreMatiere}

                  TransportEleves={TransportEleves}

                  TransportEmployes={TransportEmployes}

                  TransportPassageSupplementaire={

                    TransportPassageSupplementaire

                  }

                  toggleCarburantAutreMatiere={toggleCarburantAutreMatiere}

                  toggleTransportEleves={toggleTransportEleves}

                  toggleTransportEmployes={toggleTransportEmployes}

                  toggleTransportPassageSupplementaire={

                    toggleTransportPassageSupplementaire

                  }

                  // mouvement helpers

                  policeDetails={policeDetails}

                  isEditPolice={isEditPolice}

                  isRenouvellement={isRenouvellement}

                  vehiculeAddedRenouvellement={vehiculeAddedRenouvellement}

                  setVehiculeAddedRenouvellement={

                    setVehiculeAddedRenouvellement

                  }

                  /**

                   * input state

                   */

                  offreState={offreState}

                  categorieState={categorieState}

                  usageState={usageState}

                  carosserieState={carosserieState}

                  energieState={energieState}

                  systemeSecuritesState={systemeSecuritesState}

                  securiteRoutiereState={securiteRoutiereState}

                  assistanceAutoState={assistanceAutoState}

                  marqueState={marqueState}

                  remorqueAtteleeState={remorqueAtteleeState}

                  genreState={genreState}

                  typevehiculeState={typevehiculeState}

                  modelevehiculeState={modelevehiculeState}

                  puissancefiscaleState={puissancefiscaleState}

                  chargeUtileState={chargeUtileState}

                  nbrPlaceState={nbrPlaceState}

                  valeurNeufState={valeurNeufState}

                  setvaleurNeufState={setvaleurNeufState}

                  valeurVenaleState={valeurVenaleState}

                  valeurAccessoireState={valeurAccessoireState}

                  immatriculationState={immatriculationState}

                  numeroCarteBrunePhysiqueState={numeroCarteBrunePhysiqueState}

                  chassisState={chassisState}

                  numeromoteurState={numeromoteurState}

                  premiereCirculationState={premiereCirculationState}

                  ///

                  CarburantAutreMatiereState={CarburantAutreMatiereState}

                  TransportElevesState={TransportElevesState}

                  TransportEmployesState={TransportEmployesState}

                  TransportPassageSupplementaireState={

                    TransportPassageSupplementaireState

                  }

                />

              </Fragment>

            );

          case 3:

            return parseInt(typeContrat) === 0 ? (

              <Fragment>

                <div className="mb-2 flex ">

                  <p className="text-sm">

                    {controlIdDevis ? (

                      <button

                        onClick={() => setOpenModalAnnulation(true)}

                        className="mb-2 ml-2 relative font-medium text-red-600 before:absolute before:-bottom-1 before:h-0.5 before:w-full before:origin-left before:scale-x-0 before:bg-red-600 before:transition hover:before:scale-100"

                      >

                        Annuler

                      </button>

                    ) : (

                      <button

                        onClick={() => navigate("/production/automobile")}

                        className="mb-2 ml-2 relative font-medium text-red-600 before:absolute before:-bottom-1 before:h-0.5 before:w-full before:origin-left before:scale-x-0 before:bg-red-600 before:transition hover:before:scale-100"

                      >

                        Annuler

                      </button>

                    )}

                    <AnnulationSaisieDevisModal

                      controlIdDevis={controlIdDevis}

                      setOpenModalAnnulation={setOpenModalAnnulation}

                      openModalAnnulation={openModalAnnulation}

                    />

                  </p>

                </div>

                <OffreSection

                  premiereCirculation={premiereCirculation}

                  assistanceAuto={assistanceAuto}

                  remorqueAttelee={remorqueAttelee}

                  securiteRoutiere={securiteRoutiere}

                  typeContrat={typeContrat}

                  nextStep={nextStep}

                  prevStep={prevStep}

                  offreSectionData={offreSectionData}

                  offre={offre}

                  nsiaAutoPlus={nsiaAutoPlus}

                  setOffre={setOffre}

                  categorie={categorie}

                  valeurNeuf={valeurNeuf}

                  valeurVenale={valeurVenale}

                  valeurAccessoire={valeurAccessoire}

                  puissancefiscale={puissancefiscale}

                  chargeUtile={chargeUtile}

                  energie={energie}

                  // ****

                  reduction={reduction}

                  systemeSecurites={systemeSecurites}

                  dateEffet={dateEffet}

                  dateExpiration={dateExpiration}
                  dateEmission={dateEmission}

                  bonusmalus={bonusmalus}

                  // offres utils

                  setCheckedState={setCheckedState}

                  setPrimeAnnuelle={setPrimeAnnuelle}

                  setPrimeNette={setPrimeNette}

                  PrimeAnnuelle={PrimeAnnuelle}

                  PrimeNette={PrimeNette}

                  checkedState={checkedState}

                  compagnie={compagnie}

                  nbrPlace={nbrPlace}

                  usage={usage}

                  CarburantAutreMatiere={CarburantAutreMatiere}

                  TransportEleves={TransportEleves}

                  TransportEmployes={TransportEmployes}

                  TransportPassageSupplementaire={

                    TransportPassageSupplementaire

                  }

                  /**

                   * input state

                   */

                  isEditPolice={isEditPolice}

                  offreState={offreState}

                  // 🎯 PROP POUR LA CORRECTION DES PRIMES
                  onCorrectionDataReady={setCorrectionFunctions}

                />

              </Fragment>

            ) : (

              <Fragment>

                <div className="mb-2 flex ">

                  <p className="text-sm">

                    {controlIdDevis ? (

                      <button

                        onClick={() => setOpenModalAnnulation(true)}

                        className="mb-2 ml-2 relative font-medium text-red-600 before:absolute before:-bottom-1 before:h-0.5 before:w-full before:origin-left before:scale-x-0 before:bg-red-600 before:transition hover:before:scale-100"

                      >

                        Annuler

                      </button>

                    ) : (

                      <button

                        onClick={() => navigate("/production/automobile")}

                        className="mb-2 ml-2 relative font-medium text-red-600 before:absolute before:-bottom-1 before:h-0.5 before:w-full before:origin-left before:scale-x-0 before:bg-red-600 before:transition hover:before:scale-100"

                      >

                        Annuler

                      </button>

                    )}

                    <AnnulationSaisieDevisModal

                    controlIdDevis={controlIdDevis}

                    setOpenModalAnnulation={setOpenModalAnnulation}

                    openModalAnnulation={openModalAnnulation}

                    />

                    </p>

                    </div>

                    <ClientRegistration

                    // edit devis

                    devisEdition={devisEdition}

                    devisDetEdition={devisDetEdition}

                    isEditDevis={isEditDevis}

                    searchClientTerm={searchClientTerm}

                    setSearchClientTerm={setSearchClientTerm}

                    searchAssureTerm={searchAssureTerm}

                    setSearchAssureTerm={setSearchAssureTerm}

                    searchClientResults={searchClientResults}

                    setSearchClientResults={setSearchClientResults}

                    searchAssureResults={searchAssureResults}

                    setSearchAssureResults={setSearchAssureResults}

                    editDevisId={editDevisIdDet}

                    editDevisIdDet={editDevisId}

                  duree={duree}

                  numeroPoliceCompagnie={numeroPoliceCompagnie}

                  nsiaAutoPlus={nsiaAutoPlus}

                  reconduction={reconduction}

                  // *

                  assistanceAuto={assistanceAuto}

                  securiteRoutiere={securiteRoutiere}

                  remorqueAttelee={remorqueAttelee}

                  typeContrat={typeContrat}

                  controlIdDevis={controlIdDevis}

                  nextStep={nextStep}

                  prevStep={prevStep}

                  clientSectionData={clientSectionData}

                  idAvenant={idAvenant}

                  idAvenantEdition={idAvenantEdition}

                  conducteur={conducteur}

                  nomClient={nomClient}

                  nomAssuré={nomAssuré}

                  numeroTelephone={numeroTelephone}

                  adresseconducteur={adresseconducteur}

                  permisconducteur={permisconducteur}

                  numeroPermisconducteur={numeroPermisconducteur}

                  habitation={habitation}

                  numeroconducteur={numeroconducteur}

                  qualite={qualite}

                  setConducteur={setConducteur}

                  setNomClient={setNomClient}

                  setNomAssuré={setNomAssuré}

                  setNumeroTelephone={setNumeroTelephone}

                  setAdresseconducteur={setAdresseconducteur}

                  setPermisconducteur={setPermisconducteur}

                  setNumeroPermisconducteur={setNumeroPermisconducteur}

                  setHabitation={setHabitation}

                  setNumeroconducteur={setNumeroconducteur}

                  setQualite={setQualite}

                  // devis utils

                  compagnie={compagnie}

                  offre={offre}

                  dateEffet={dateEffet}

                  dateExpiration={dateExpiration}

                  immatriculation={immatriculation}

                  dateEmission={dateEmission}

                  categorie={categorie}

                  usage={usage}

                  carosserie={carosserie}

                  energie={energie}

                  puissancefiscale={puissancefiscale}

                  nbrPlace={nbrPlace}

                  chargeUtile={chargeUtile}

                  valeurNeuf={valeurNeuf}

                  valeurAccessoire={valeurAccessoire}

                  valeurVenale={valeurVenale}

                  reduction={reduction}

                  systemeSecurites={systemeSecurites}

                  bonusmalus={bonusmalus}

                  premiereCirculation={premiereCirculation}

                  numeromoteur={numeromoteur}

                  chassis={chassis}

                  typevehicule={typevehicule}

                  marque={marque}

                  numeroCarteBrunePhysique={numeroCarteBrunePhysique}

                  genre={genre}

                  modelevehicule={modelevehicule}

                  //** client creation

                  qualites={qualites}

                  professions={professions}

                  typesouscripteurs={typesouscripteurs}

                  typeassures={typeassures}

                  CarburantAutreMatiere={CarburantAutreMatiere}

                  TransportEleves={TransportEleves}

                  TransportEmployes={TransportEmployes}

                  TransportPassageSupplementaire={

                    TransportPassageSupplementaire

                  }

                  /**

                   * input state

                   */

                  nomClientState={nomClientState}

                  nomAssuréState={nomAssuréState}

                  numeroTelephoneState={numeroTelephoneState}

                  conducteurState={conducteurState}

                  adresseconducteurState={adresseconducteurState}

                  permisconducteurState={permisconducteurState}

                  numeroPermisconducteurState={numeroPermisconducteurState}

                  habitationState={habitationState}

                  numeroconducteurState={numeroconducteurState}

                  /**

                   * mouvement

                   */

                  isEditPolice={isEditPolice}

                  handleAnnulationPolice={handleAnnulationPolice}

                  handleRenouvellementPolice={handleRenouvellementPolice}

                  idcontrat={idcontrat}

                  actionContent={actionContent}

                  // 🎯 PROP POUR LA CORRECTION DES PRIMES
                  correctionFunctions={correctionFunctions}

                />

              </Fragment>

            );

          case 4:

            return (

              <Fragment>

                <div className="mb-2 flex ">

                  <p className="text-sm">

                    {controlIdDevis ? (

                      <button

                        onClick={() => setOpenModalAnnulation(true)}

                        className="mb-2 ml-2 relative font-medium text-red-600 before:absolute before:-bottom-1 before:h-0.5 before:w-full before:origin-left before:scale-x-0 before:bg-red-600 before:transition hover:before:scale-100"

                      >

                        Annuler

                      </button>

                    ) : (

                      <button

                        onClick={() => navigate("/production/automobile")}

                        className="mb-2 ml-2 relative font-medium text-red-600 before:absolute before:-bottom-1 before:h-0.5 before:w-full before:origin-left before:scale-x-0 before:bg-red-600 before:transition hover:before:scale-100"

                      >

                        Annuler

                      </button>

                    )}

                    <AnnulationSaisieDevisModal

                      controlIdDevis={controlIdDevis}

                      setOpenModalAnnulation={setOpenModalAnnulation}

                      openModalAnnulation={openModalAnnulation}

                    />

                  </p>

                </div>

                <ClientRegistration

                  // edit devis

                  devisEdition={devisEdition}

                  devisDetEdition={devisDetEdition}

                  isEditDevis={isEditDevis}

                  searchClientTerm={searchClientTerm}

                  setSearchClientTerm={setSearchClientTerm}

                  searchAssureTerm={searchAssureTerm}

                  setSearchAssureTerm={setSearchAssureTerm}

                  searchClientResults={searchClientResults}

                  setSearchClientResults={setSearchClientResults}

                  searchAssureResults={searchAssureResults}

                  setSearchAssureResults={setSearchAssureResults}

                  editDevisId={editDevisIdDet}

                  editDevisIdDet={editDevisId}

                  duree={duree}

                  numeroPoliceCompagnie={numeroPoliceCompagnie}

                  reconduction={reconduction}

                  // *

                  assistanceAuto={assistanceAuto}

                  securiteRoutiere={securiteRoutiere}

                  remorqueAttelee={remorqueAttelee}

                  typeContrat={typeContrat}

                  controlIdDevis={controlIdDevis}

                  nextStep={nextStep}

                  prevStep={prevStep}

                  clientSectionData={clientSectionData}

                  conducteur={conducteur}

                  nomClient={nomClient}

                  nomAssuré={nomAssuré}

                  numeroTelephone={numeroTelephone}

                  adresseconducteur={adresseconducteur}

                  permisconducteur={permisconducteur}

                  numeroPermisconducteur={numeroPermisconducteur}

                  habitation={habitation}

                  numeroconducteur={numeroconducteur}

                  qualite={qualite}

                  setConducteur={setConducteur}

                  setNomClient={setNomClient}

                  setNomAssuré={setNomAssuré}

                  setNumeroTelephone={setNumeroTelephone}

                  setAdresseconducteur={setAdresseconducteur}

                  setPermisconducteur={setPermisconducteur}

                  setNumeroPermisconducteur={setNumeroPermisconducteur}

                  setHabitation={setHabitation}

                  setNumeroconducteur={setNumeroconducteur}

                  setQualite={setQualite}

                  // devis utils

                  compagnie={compagnie}

                  offre={offre}

                  dateEffet={dateEffet}

                  dateExpiration={dateExpiration}

                  immatriculation={immatriculation}

                  dateEmission={dateEmission}

                  categorie={categorie}

                  usage={usage}

                  carosserie={carosserie}

                  energie={energie}

                  puissancefiscale={puissancefiscale}

                  nbrPlace={nbrPlace}

                  chargeUtile={chargeUtile}

                  valeurNeuf={valeurNeuf}

                  valeurAccessoire={valeurAccessoire}

                  valeurVenale={valeurVenale}

                  reduction={reduction}

                  systemeSecurites={systemeSecurites}

                  bonusmalus={bonusmalus}

                  premiereCirculation={premiereCirculation}

                  numeromoteur={numeromoteur}

                  chassis={chassis}

                  typevehicule={typevehicule}

                  marque={marque}

                  numeroCarteBrunePhysique={numeroCarteBrunePhysique}

                  genre={genre}

                  modelevehicule={modelevehicule}

                  //** client creation

                  qualites={qualites}

                  professions={professions}

                  typesouscripteurs={typesouscripteurs}

                  typeassures={typeassures}

                  /**

                   * mouvement

                   */

                  isEditPolice={isEditPolice}

                  actionContent={actionContent}

                  handleAnnulationPolice={handleAnnulationPolice}

                  handleRenouvellementPolice={handleRenouvellementPolice}

                  idcontrat={idcontrat}

                  idAvenant={idAvenant}

                  /**

                   * input state

                   */

                  nomClientState={nomClientState}

                  nomAssuréState={nomAssuréState}

                  numeroTelephoneState={numeroTelephoneState}

                  conducteurState={conducteurState}

                  adresseconducteurState={adresseconducteurState}

                  permisconducteurState={permisconducteurState}

                  numeroPermisconducteurState={numeroPermisconducteurState}

                  habitationState={habitationState}

                  numeroconducteurState={numeroconducteurState}

                  // 🎯 PROP POUR LA CORRECTION DES PRIMES
                  correctionFunctions={correctionFunctions}

                />

              </Fragment>

            );

          default:

            return <NotFound />;

        }

      })()}

    </Fragment>

  );

}



export default ContratForm;

