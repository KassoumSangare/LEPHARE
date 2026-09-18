/* eslint-disable react-hooks/exhaustive-deps */
import { Fragment, useEffect, useState } from "react";
import WelcomeBanner from "partials/UI/Banner/WelcomeBanner";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { useDispatch, useSelector } from "react-redux";
import { SelectInput, TextAreaInput } from "partials/UI/Inputs";
import ContratForm from "../ContratForm/ContratForm";
import { annulationPolice, renouvellementPolice, reset } from "features/Police/policeSlice";
import { toast } from "react-hot-toast";
import Spinner from "partials/Utils/Spinner/Spinner";
import { handleDate } from "partials/Utils/FormUtils";


export default function MouvementPoliceAuto() {
  const { token } = useSelector((state) => state.auth);
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const { idproduit, idcontrat } = useParams();
  const [policeDevis, setPoliceDevis] = useState();
  const [isEditPolice, setIsEditPolice] = useState(true);
  const [policeData, setPoliceData] = useState();
  const [policeDetails, setPoliceDetails] = useState();
  const [idAvenant, setIdAvenant] = useState(2);
  const [mouvements, setMouvements] = useState();
  const {
    policeCanceled,
    policeRenewed,
    isLoading,
    isSuccess,
    isError,
    message,
  } = useSelector((state) => state.police);
  // MOTIF
  const [needMotif, setNeedMotif] = useState(false);
  const [motif, setMotif] = useState("");
  /**
   * INPUT STATE
   *
   */
  const [isRenouvellement, setIsRenouvellement] = useState(false);
  const [vehiculeAddedRenouvellement, setVehiculeAddedRenouvellement] = useState([]);
  const [actionContent, setactionContent] = useState("Enregistrer");
  const [compagnieState, setcompagnieState] = useState(false);
  const [usageState, setusageState] = useState(false);
  const [carosserieState, setcarosserieState] = useState(false);
  const [reductionState, setreductionState] = useState(false);
  const [bonusmalusState, setbonusmalusState] = useState(false);
  const [reconductionState, setreconductionState] = useState(false);
  const [dureeState, setdureeState] = useState(false);
  const [dateEmissionState, setdateEmissionState] = useState(false);
  const [dateEffetState, setdateEffetState] = useState(false);
  const [dateExpirationState, setdateExpirationState] = useState(false);
  const [assistanceAutoState, setassistanceAutoState] = useState(false);
  const [assistanceListState, setassistanceListState] = useState(false);
  const [securiteRoutiereState, setsecuriteRoutiereState] = useState(false);
  const [secu_rState, setsecu_rState] = useState(false);
  const [remorqueAtteleeState, setremorqueAtteleeState] = useState(false);
  const [energieState, setenergieState] = useState(false);
  const [modelevehiculeState, setmodelevehiculeState] = useState(false);
  const [systemeSecuritesState, setsystemeSecuritesState] = useState(false);
  const [marqueState, setmarqueState] = useState(false);
  const [puissancefiscaleState, setpuissancefiscaleState] = useState(false);
  const [chargeUtileState, setchargeUtileState] = useState(false);
  const [nbrPlaceState, setnbrPlaceState] = useState(false);
  const [valeurNeufState, setvaleurNeufState] = useState(false);
  const [valeurVenaleState, setvaleurVenaleState] = useState(false);
  const [valeurAccessoireState, setvaleurAccessoireState] = useState(false);
  const [immatriculationState, setimmatriculationState] = useState(false);
  const [chassisState, setchassisState] = useState(false);
  const [genreState, setgenreState] = useState(false);
  const [numeromoteurState, setnumeromoteurState] = useState(false);
  const [nbreExtincteurState, setnbreExtincteurState] = useState(false);
  const [premiereCirculationState, setpremiereCirculationState] =
    useState(false);
  const [categorieState, setcategorieState] = useState(false);
  const [offreState, setoffreState] = useState(false);
  const [conducteurState, setconducteurState] = useState(false);
  const [nomClientState, setnomClientState] = useState(false);
  const [nomAssuréState, setnomAssuréState] = useState(false);
  const [numeroTelephoneState, setnumeroTelephoneState] = useState(false);
  const [adresseconducteurState, setadresseconducteurState] = useState(false);
  const [permisconducteurState, setpermisconducteurState] = useState(false);
  const [numeroPermisconducteurState, setnumeroPermisconducteurState] =
    useState(false);
  const [habitationState, sethabitationState] = useState(false);
  const [numeroconducteurState, setnumeroconducteurState] = useState(false);
  const [qualiteState, setqualiteState] = useState(false);
  const [typevehiculeState, settypevehiculeState] = useState(false);
  const [numeroCarteBrunePhysiqueState, setnumeroCarteBrunePhysiqueState] =
    useState(false);
  const [typeContratState, settypeContratState] = useState(false);
  const [offreFlotteState, setoffreFlotteState] = useState(false);
  const [transportCompteAssureState, settransportCompteAssureState] =
    useState(false);
  const [transportPublicMarchandiseState, settransportPublicMarchandiseState] =
    useState(false);
  const [CarburantAutreMatiereState, setCarburantAutreMatiereState] =
    useState(false);
  const [TransportElevesState, setTransportElevesState] = useState(false);
  const [TransportEmployesState, setTransportEmployesState] = useState(false);
    const [
    TransportPassageSupplementaireState,
    setTransportPassageSupplementaireState,
  ] = useState(false);



  const getPoliceData = async () => {
    const config = {
      headers: {
        Authorization: `Token ${token}`,
      },
    };
    const { data } = await axios.get(
      `${process.env.REACT_APP_API_URL}contrat/${idcontrat}`,
      config
    );
    setPoliceData(data);
  };

  const getPoliceDetails = async () => {
    const config = {
      headers: {
        Authorization: `Token ${token}`,
      },
    };
    const { data } = await axios.get(
      `${process.env.REACT_APP_API_URL}contratdetail/${idcontrat}`,
      config
    );
    setPoliceDetails(data);
  };

  const getAvenants = async (flotte) => {
    const config = {
      headers: {
        Authorization: `Token ${token}`,
      },
      params: {
        idproduit: 1,
        flotte,
      },
    };
    const { data } = await axios.get(
      `${process.env.REACT_APP_API_URL}avenant`,
      config
    );
    setMouvements(data);
  };


  const getDevisDetails = async (iddevisPolice) => {
    if (!iddevisPolice || isNaN(iddevisPolice)) {
      console.warn("getDevisDetails: iddevisPolice invalide", iddevisPolice);
      return;
    }
    
    try {
      const config = {
        headers: {
          Authorization: `Token ${token}`,
        },
      };
      const { data } = await axios.get(
        `${process.env.REACT_APP_API_URL}devisdetail/${iddevisPolice}`,
        config
      );
      setPoliceDevis(data[0]);
    } catch (error) {
      console.error("Erreur lors de la récupération des détails du devis:", error);
      // Ne pas faire planter l'application si le devis n'existe pas
      if (error.response?.status === 404) {
        console.warn(`Devis ${iddevisPolice} non trouvé`);
      } else {
        toast.error("Erreur lors de la récupération des détails du devis");
      }
    }
  };


  useEffect(() => {
    setIsEditPolice(true);
    getPoliceData();
    getPoliceDetails();

    return () => {
      setIsEditPolice(false);
    };
  }, []);


  useEffect(() => {
    if (policeData && policeData.iddevis) {
      const iddevis = parseInt(policeData.iddevis);
      if (!isNaN(iddevis) && iddevis > 0) {
        getDevisDetails(iddevis);
      }
    }

    if (policeData) {
      getAvenants(policeData.flotte);
    }

  }, [policeData]);




  /**
   * EFFECT
   */
  useEffect(() => {
    if (isError) {
      toast.error(message);
    }

    if (isSuccess && policeCanceled) {
      navigate(
        `/production/automobile/details-devis/${policeCanceled[0].ObjectId}`
      );
      toast.success(`${policeCanceled[0].OutputMessage}`);
    }

    
    if (isSuccess && policeRenewed) {
      navigate(`/production/automobile/details-devis/${policeRenewed[0].ObjectId}`);
      toast.success(`${policeRenewed[0].OutputMessage}`);
    }

    dispatch(reset());
  }, [dispatch, policeRenewed, policeCanceled, isSuccess, isError, message]);

  /**
   *
   *
   * HANDLE NEED MOTIF
   */

  useEffect(() => {
    if (
      parseInt(idAvenant) === 6 ||
      parseInt(idAvenant) === 9 ||
      parseInt(idAvenant) === 8
    ) {
      setNeedMotif(true);
    } else {
      setNeedMotif();
    }
    
    if (idAvenant && parseInt(idAvenant) === 2) {
      setIsRenouvellement(true);
    } else {
      setIsRenouvellement(false);
    }

  }, [idAvenant]);

  /**
   *
   *
   * HANDLE AVENANT
   */

  const handleAnnulationPolice = ({
    dateEffet,
    dateEmission,
    idAvenant,
    idcontrat,
  }) => {
    const annulationData = {
      date_effet: handleDate(dateEffet),
      date_emission: handleDate(dateEmission),
      id_avenant: parseInt(idAvenant),
      id_contrat: parseInt(idcontrat),
    };

    if (needMotif) {
      annulationData.motif = motif;
    }

    dispatch(annulationPolice(annulationData));
  };


  // renouvellement
  const handleRenouvellementPolice = ({
    dateEffet,
    dateEmission,
    idAvenant,
    idcontrat,
  }) => {
    dispatch(
      renouvellementPolice({
        date_effet: handleDate(dateEffet),
        date_emission: handleDate(dateEmission),
        id_avenant: parseInt(idAvenant),
        id_contrat: parseInt(idcontrat),
      })
    );
  };
  /**
   *  INPUT STATE
   *
   */

  useEffect(() => {
    if (isEditPolice) {
      setactionContent("Confirmer le mouvement");
      settypeContratState(true);

      if (idAvenant && parseInt(idAvenant) === 6) {
        // ANNULATION
        setdateEffetState(false);
        // disabled fields
        setcompagnieState(true);
        setusageState(true);
        setcarosserieState(true);
        setreductionState(true);
        setbonusmalusState(true);
        setreconductionState(true);
        setdureeState(true);
        setdateEmissionState(true);
        setdateExpirationState(true);
        setassistanceAutoState(true);
        setassistanceListState(true);
        setsecuriteRoutiereState(true);
        setsecu_rState(true);
        setremorqueAtteleeState(true);
        setenergieState(true);
        setmodelevehiculeState(true);
        setsystemeSecuritesState(true);
        setmarqueState(true);
        setpuissancefiscaleState(true);
        setchargeUtileState(true);
        setnbrPlaceState(true);
        setvaleurNeufState(true);
        setvaleurVenaleState(true);
        setvaleurAccessoireState(true);
        setimmatriculationState(true);
        setchassisState(true);
        setgenreState(true);
        setnumeromoteurState(true);
        setnbreExtincteurState(true);
        setpremiereCirculationState(true);
        setcategorieState(true);
        setoffreState(true);
        setconducteurState(true);
        setnomClientState(true);
        setnomAssuréState(true);
        setnumeroTelephoneState(true);
        setadresseconducteurState(true);
        setpermisconducteurState(true);
        setnumeroPermisconducteurState(true);
        sethabitationState(true);
        setnumeroconducteurState(true);
        setqualiteState(true);
        settypevehiculeState(true);
        setnumeroCarteBrunePhysiqueState(true);
        settypeContratState(true);
        setoffreFlotteState(true);
        settransportCompteAssureState(true);
        settransportPublicMarchandiseState(true);
        setCarburantAutreMatiereState(true);
        setTransportElevesState(true);
        setTransportEmployesState(true);
        setTransportPassageSupplementaireState(true);
      } else  if (idAvenant && parseInt(idAvenant) === 3) {
        // INCORPORATION
        setcompagnieState(true);
        setreconductionState(true);
        setdateExpirationState(true);
      } else {
        setcompagnieState();
        setusageState();
        setcarosserieState();
        setreductionState();
        setbonusmalusState();
        setreconductionState();
        setdureeState();
        setdateEmissionState();
        setdateEffetState();
        setdateExpirationState();
        setassistanceAutoState();
        setassistanceListState();
        setsecuriteRoutiereState();
        setsecu_rState();
        setremorqueAtteleeState();
        setenergieState();
        setmodelevehiculeState();
        setsystemeSecuritesState();
        setmarqueState();
        setpuissancefiscaleState();
        setchargeUtileState();
        setnbrPlaceState();
        setvaleurNeufState();
        setvaleurVenaleState();
        setvaleurAccessoireState();
        setimmatriculationState();
        setchassisState();
        setgenreState();
        setnumeromoteurState();
        setnbreExtincteurState();
        setpremiereCirculationState();
        setcategorieState();
        setoffreState();
        setconducteurState();
        setnomClientState();
        setnomAssuréState();
        setnumeroTelephoneState();
        setadresseconducteurState();
        setpermisconducteurState();
        setnumeroPermisconducteurState();
        sethabitationState();
        setnumeroconducteurState();
        setqualiteState();
        settypevehiculeState();
        setnumeroCarteBrunePhysiqueState();
        settypeContratState();
        setoffreFlotteState();
        settransportCompteAssureState();
        settransportPublicMarchandiseState();
        setCarburantAutreMatiereState();
        setTransportElevesState();
        setTransportEmployesState();
        setTransportPassageSupplementaireState();
      }

     
    }
  }, [isEditPolice, idAvenant]);


  /**
   * LOADER
   *
   */
  if (isLoading) {
    return <Spinner />;
  }

  /**
   *
   *
   */

  return (
    <Fragment>
      <WelcomeBanner
        title={`Mouvement police n°${policeData && policeData.numeropolice}`}
      />
      <div className="flex flex-row-reverse text-xs mb-2">
        <div className="mr-4 grid grid-cols-2 gap-4">
          {needMotif && (
            <TextAreaInput
              label="Veuillez entrez un Motif"
              name="motif"
              value={motif}
              onChange={(e) => setMotif(e.target.value)}
            />
          )}
          <SelectInput
            label="Mouvement"
            htmlFor="idAvenant"
            inputValue={idAvenant}
            handleOnChange={(e) => setIdAvenant(e.target.value)}
          >
            {mouvements &&
              mouvements.map((element) => (
                <option key={element.IdAvenant} value={element.IdAvenant}>
                  {element.LibelleAvenant}
                </option>
              ))}
          </SelectInput>
        </div>
      </div>

      {isEditPolice && idproduit && idcontrat && policeData && (
        <ContratForm
          isEditPolice={isEditPolice}
          policeData={policeData}
          policeDetails={policeDetails}
          idcontrat={parseInt(idcontrat)}
          policeDevis={policeDevis}
          idproduit={idproduit}
          idAvenant={idAvenant}
          mouvements={mouvements}
          motif={motif}
          actionContent={actionContent}
          compagnieState={compagnieState}
          usageState={usageState}
          carosserieState={carosserieState}
          reductionState={reductionState}
          bonusmalusState={bonusmalusState}
          reconductionState={reconductionState}
          dureeState={dureeState}
          dateEmissionState={dateEmissionState}
          dateEffetState={dateEffetState}
          dateExpirationState={dateExpirationState}
          assistanceAutoState={assistanceAutoState}
          assistanceListState={assistanceListState}
          securiteRoutiereState={securiteRoutiereState}
          secu_rState={secu_rState}
          remorqueAtteleeState={remorqueAtteleeState}
          energieState={energieState}
          modelevehiculeState={modelevehiculeState}
          systemeSecuritesState={systemeSecuritesState}
          marqueState={marqueState}
          puissancefiscaleState={puissancefiscaleState}
          chargeUtileState={chargeUtileState}
          nbrPlaceState={nbrPlaceState}
          valeurNeufState={valeurNeufState}
          setvaleurNeufState={setvaleurNeufState}
          valeurVenaleState={valeurVenaleState}
          valeurAccessoireState={valeurAccessoireState}
          immatriculationState={immatriculationState}
          chassisState={chassisState}
          genreState={genreState}
          numeromoteurState={numeromoteurState}
          nbreExtincteurState={nbreExtincteurState}
          premiereCirculationState={premiereCirculationState}
          categorieState={categorieState}
          offreState={offreState}
          conducteurState={conducteurState}
          nomClientState={nomClientState}
          nomAssuréState={nomAssuréState}
          numeroTelephoneState={numeroTelephoneState}
          adresseconducteurState={adresseconducteurState}
          permisconducteurState={permisconducteurState}
          numeroPermisconducteurState={numeroPermisconducteurState}
          habitationState={habitationState}
          numeroconducteurState={numeroconducteurState}
          qualiteState={qualiteState}
          typevehiculeState={typevehiculeState}
          numeroCarteBrunePhysiqueState={numeroCarteBrunePhysiqueState}
          typeContratState={typeContratState}
          offreFlotteState={offreFlotteState}
          transportCompteAssureState={transportCompteAssureState}
          transportPublicMarchandiseState={transportPublicMarchandiseState}
          CarburantAutreMatiereState={CarburantAutreMatiereState}
          TransportElevesState={TransportElevesState}
          TransportEmployesState={TransportEmployesState}
          TransportPassageSupplementaireState={
            TransportPassageSupplementaireState
          }
          /**
           * HANDLE AVENANT
           */
          handleAnnulationPolice={handleAnnulationPolice}
          handleRenouvellementPolice={handleRenouvellementPolice}
          isRenouvellement={isRenouvellement}
          vehiculeAddedRenouvellement={vehiculeAddedRenouvellement}
          setVehiculeAddedRenouvellement={setVehiculeAddedRenouvellement}
        />
      )}
    </Fragment>
  );
}
