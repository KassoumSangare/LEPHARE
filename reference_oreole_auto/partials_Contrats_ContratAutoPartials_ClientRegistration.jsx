import { Fragment, useEffect, useState } from "react";

import { Dialog, Transition } from "@headlessui/react";

import { useSelector, useDispatch } from "react-redux";

import { useNavigate } from "react-router-dom";

//

import {
  saveDevis,
  finalisationdevisauto,
  reset,
} from "features/Devis/devisSlice";
import { clearModifications } from "features/Offre/offreSlice";
import { clearEditedPrimes } from "features/Garanties/garantieSlice";

import Spinner from "partials/Utils/Spinner/Spinner";

import moment from "moment";

import { ButtonSave, OutlineButton } from "partials/UI/Button/Button";

import { TextInput } from "partials/UI/Inputs";

import { toast } from "react-hot-toast";

import { NewClientContrat } from "scenes/Client/CreateClient/NewClient";

import WelcomeBanner from "partials/UI/Banner/WelcomeBanner";

import SearchableSelect from "partials/UI/Inputs/SearchableSelect";



function ClientRegistration({

  // edit devis

  editDevisId,

  editDevisIdDet,

  duree,

  idAvenantEdition,

  reconduction,

  // données devis pour initialisation

  devisEdition,

  devisDetEdition,

  isEditDevis,

  prevStep,

  // search 

  searchClientTerm,

  setSearchClientTerm,

  // 🎯 CORRECTION DES PRIMES
  correctionFunctions,

  searchAssureTerm,

  setSearchAssureTerm,

  searchClientResults,

  setSearchClientResults,

  searchAssureResults,

  setSearchAssureResults,

  // police

  numeroPoliceCompagnie,

  policeData,

  clientSectionData,

  qualites,

  professions,

  typesouscripteurs,

  typeassures,

  conducteur,

  nomClient,

  nomAssuré,

  numeroTelephone,

  adresseconducteur,

  permisconducteur,

  numeroPermisconducteur,

  habitation,

  numeroconducteur,

  setConducteur,

  setNomClient,

  setNomAssuré,

  setNumeroTelephone,

  setAdresseconducteur,

  setPermisconducteur,

  setNumeroPermisconducteur,

  setHabitation,

  setNumeroconducteur,

  // devis utils

  compagnie,

  offre,

  dateEffet,

  dateExpiration,

  dateEmission,

  reduction,

  categorie,

  usage,

  carosserie,

  energie,

  puissancefiscale,

  nbrPlace,

  chargeUtile,

  valeurNeuf,

  valeurAccessoire,

  valeurVenale,

  systemeSecurites,

  bonusmalus,

  premiereCirculation,

  numeromoteur,

  chassis,

  typevehicule,

  marque,

  immatriculation,

  numeroCarteBrunePhysique,

  genre,

  modelevehicule,

  controlIdDevis,

  typeContrat,

  securiteRoutiere,

  remorqueAttelee,

  CarburantAutreMatiere,

  TransportEleves,

  TransportEmployes,

  TransportPassageSupplementaire,

  assistanceAuto,

  /**

   * HANDLE SAVE AVENANT

   */

  isEditPolice,

  handleAnnulationPolice,

  handleRenouvellementPolice,

  idcontrat,

  idAvenant,

  // input state

  nomClientState,

  nomAssuréState,

  numeroTelephoneState,

  conducteurState,

  nsiaAutoPlus,

  adresseconducteurState,

  permisconducteurState,

  numeroPermisconducteurState,

  habitationState,

  numeroconducteurState,

}) {

  const dispatch = useDispatch();
  // Offres from store for liste_garantie (top-level to respect hooks rules)
  const { offres: offresStore } = useSelector((state) => state.offres || { offres: [] });

  const navigate = useNavigate();



  const clients = clientSectionData.clients;

  const categoriepermis = clientSectionData.categoriepermis;



  const [openPanel, setOpenPanel] = useState(false);

  // État pour suivre si les données ont été initialisées une fois
  const [dataInitialized, setDataInitialized] = useState(false);
  
  // État pour suivre si l'utilisateur a modifié des valeurs
  const [userModified, setUserModified] = useState(false);

  const { devisSaved, endeddevis, isLoading, isSuccess, isError, message } =

    useSelector((state) => state.devis);

  // Réinitialiser les flags quand on change de devis
  useEffect(() => {
    setDataInitialized(false);
    setUserModified(false);
  }, [editDevisId, editDevisIdDet]);

  // Empêcher la réinitialisation après une sauvegarde réussie
  useEffect(() => {
    if (isSuccess && devisSaved) {
      setDataInitialized(true);
      setUserModified(false);
    }
  }, [isSuccess, devisSaved]);



  // Initialiser les searchTerm avec les valeurs sélectionnées au chargement (seulement si pas en mode renouvellement)

  useEffect(() => {

    if (!isEditPolice && clients && nomClient) {

      const souscripteur = clients.find((c) => c.IdClient === nomClient);

      if (souscripteur) {

        setSearchClientTerm(formatName(souscripteur.Nom || ""));

      }

    }

    if (!isEditPolice && clients && nomAssuré) {

      const assure = clients.find((c) => c.IdClient === nomAssuré);

      if (assure) {

        setSearchAssureTerm(formatName(assure.Nom || ""));

      }

    }

    // eslint-disable-next-line react-hooks/exhaustive-deps

  }, [clients, nomClient, nomAssuré, isEditPolice]);



  // Forcer la synchronisation des searchTerm quand les valeurs changent (seulement si pas en mode renouvellement)

  useEffect(() => {

    if (!isEditPolice && clients && nomClient) {

      const souscripteur = clients.find((c) => c.IdClient === nomClient);

      if (souscripteur) {

        setSearchClientTerm(formatName(souscripteur.Nom || ""));

      }

    }

  }, [nomClient, clients, setSearchClientTerm, isEditPolice]);



  useEffect(() => {

    if (!isEditPolice && clients && nomAssuré) {

      const assure = clients.find((c) => c.IdClient === nomAssuré);

      if (assure) {

        setSearchAssureTerm(formatName(assure.Nom || ""));

      }

    }

  }, [nomAssuré, clients, setSearchAssureTerm, isEditPolice]);



  // Initialiser les champs avec les données du devis lors de l'édition
  // MAIS seulement une seule fois et si l'utilisateur n'a pas encore modifié

  useEffect(() => {

    if (isEditDevis && devisEdition && devisDetEdition && devisDetEdition[0] && !dataInitialized && !userModified) {

      console.log("=== INITIALISATION DES DONNÉES DEVIS ===");
      console.log("Données du devis:", devisEdition);
      console.log("Données détail devis:", devisDetEdition[0]);

      // Initialiser les champs conducteur avec les données du client/assuré
      setAdresseconducteur(devisEdition.assure.Adresse1 || "");

      // Pour habitation, utiliser d'abord villecnd, sinon l'intermédiaire, sinon l'assuré
      const habitationValue = devisDetEdition[0].villecnd || 
                             devisEdition.intermediaire.Adresse || 
                             devisEdition.assure.Adresse2 || 
                             "";
      console.log("Initialisation habitation:", {
        villecnd: devisDetEdition[0].villecnd,
        intermediaireAdresse: devisEdition.intermediaire.Adresse,
        assureAdresse2: devisEdition.assure.Adresse2,
        habitationValue
      });
      setHabitation(habitationValue);

      // Initialiser la catégorie de permis avec les données du devisdetail
      setPermisconducteur(devisDetEdition[0].pctype || "");

      setNumeroPermisconducteur(devisDetEdition[0].numpccnd || "");

      // Initialiser le numéro du conducteur avec les données de l'assuré
      setNumeroconducteur(devisEdition.assure.Telephone || "");

      // Marquer que les données ont été initialisées
      setDataInitialized(true);

      console.log("=== FIN INITIALISATION ===");

    }
  }, [isEditDevis, devisEdition?.iddevis, devisDetEdition?.[0]?.iddevisdetail]);

  // Initialiser les searchTerm et informations depuis la police lors du renouvellement (isEditPolice)
  useEffect(() => {
    // Ne pas réécraser les valeurs utilisateur après validation
    if (dataInitialized || userModified) return;
    if (!(isEditPolice && policeData && clients)) return;

    // Souscripteur
    if (policeData.idclient) {
      const souscripteur = clients.find((c) => c.IdClient === parseInt(policeData.idclient));
      if (souscripteur) {
        setNomClient(souscripteur.IdClient);
        setSearchClientTerm(formatName(souscripteur.Nom || ""));
        setSearchClientResults([souscripteur]);
        const phoneSouscripteur = souscripteur.Mobile || souscripteur.Telephone || "";
        if (phoneSouscripteur) setNumeroTelephone(phoneSouscripteur);
      }
    }

    // Assuré
    if (policeData.idassure) {
      const assure = clients.find((c) => c.IdClient === parseInt(policeData.idassure));
      if (assure) {
        setNomAssuré(assure.IdClient);
        setSearchAssureTerm(formatName(assure.Nom || ""));
        setSearchAssureResults([assure]);
        const phoneAssure = assure.Mobile || assure.Telephone || "";
        if (phoneAssure && phoneAssure !== numeroTelephone) setNumeroTelephone(phoneAssure);
      }
    }
  }, [isEditPolice, policeData, clients, setNomClient, setNomAssuré, setSearchClientTerm, setSearchAssureTerm, setNumeroTelephone, setSearchClientResults, setSearchAssureResults, dataInitialized, userModified]);




  // Synchroniser automatiquement tous les champs quand le souscripteur change
  // MAIS PAS en mode édition de devis pour préserver les modifications utilisateur

  useEffect(() => {

    // Ne pas synchroniser automatiquement en mode édition de devis
    if (isEditDevis) return;

    if (!nomClient || !clients) return;

    const souscripteur = clients.find((c) => c.IdClient === nomClient);

    if (!souscripteur) return;



    // Synchroniser l'assuré avec le souscripteur seulement si l'assuré n'est pas déjà défini différemment

    if (!nomAssuré || nomAssuré === nomClient) {

      setNomAssuré(souscripteur.IdClient);

      setSearchAssureTerm(formatName(souscripteur.Nom || ""));

    }

    

    // Renseigner les informations de contact et conducteur

    const phoneAuto = souscripteur.Mobile || souscripteur.Telephone || "";

    setNumeroTelephone(phoneAuto);

    setConducteur(formatName(souscripteur.Nom || ""));

    // Utiliser les données de l'intermédiaire au lieu du souscripteur
    // setAdresseconducteur(souscripteur.Adresse1 || "");
    // setHabitation(souscripteur.Adresse2 || "");

    setNumeroconducteur(phoneAuto);

    // eslint-disable-next-line react-hooks/exhaustive-deps

  }, [nomClient, clients, isEditDevis]);



  // Mettre à jour les informations quand l'assuré change (si différent du souscripteur)
  // MAIS PAS en mode édition de devis pour préserver les modifications utilisateur

  useEffect(() => {

    // Ne pas synchroniser automatiquement en mode édition de devis
    if (isEditDevis) return;

    if (!nomAssuré || !clients || nomAssuré === nomClient) return;

    const assure = clients.find((c) => c.IdClient === nomAssuré);

    if (!assure) return;



    setSearchAssureTerm(formatName(assure.Nom || ""));

    setConducteur(formatName(assure.Nom || ""));

    // Utiliser les données de l'intermédiaire au lieu de l'assuré
    // setAdresseconducteur(assure.Adresse1 || "");
    // setHabitation(assure.Adresse2 || "");

    setNumeroconducteur(assure.Mobile || assure.Telephone || "");

    setNumeroTelephone(assure.Mobile || assure.Telephone || "");

    // eslint-disable-next-line react-hooks/exhaustive-deps

  }, [nomAssuré, clients, nomClient, isEditDevis]);



  useEffect(() => {

    if (isError) {

      toast.error(message);

    }



    if (isSuccess && devisSaved) {

      toast.success(devisSaved.OutputMessage);

      navigate(`/production/automobile/details-devis/${devisSaved.IdDevis}`);

    }



    if (isSuccess && endeddevis) {

      toast.success(endeddevis.OutputMessage);

      navigate(`/production/automobile/details-devis/${endeddevis.ObjectId}`);

    }



    dispatch(reset());

  }, [devisSaved, endeddevis, isError, isSuccess, message, navigate, dispatch]);




  const handleDate = (date) => {

    // Si la date est déjà au format DD-MM-YYYY, on la parse avec ce format

    if (typeof date === 'string' && date.includes('-') && date.split('-').length === 3) {

      const parts = date.split('-');

      // Vérifier si c'est au format DD-MM-YYYY (2 chiffres, 2 chiffres, 4 chiffres)

      if (parts[0].length === 2 && parts[1].length === 2 && parts[2].length === 4) {

        return moment(date, 'DD-MM-YYYY').format("DD-MM-YYYY");

      }

    }

    // Sinon, utiliser le parsing par défaut

    return moment(date).format("DD-MM-YYYY");

  };

  const formatName = (raw) => {

    if (!raw && raw !== 0) return "";

    return String(raw).trim().replace(/\s+/g, " ").toUpperCase();

  };



  // Fonction pour obtenir la durée attendue en jours selon l'ID de durée

  const getExpectedDuration = (dureeId) => {

    switch (dureeId) {

      case 1: // 1 mois

        return 30; // 1 mois exact (avec soustraction de 1 jour)

      case 2: // 3 mois

        return 91; // 3 mois exact (avec soustraction de 1 jour)

      case 3: // 6 mois

        return 183; // 6 mois exact (avec soustraction de 1 jour)

      case 4: // 1 an

        return 365; // 1 an exact (avec soustraction de 1 jour)

      default:

        return 0;

    }

  };



  /* handle save devis */

  // (déjà déclaré plus haut) offres vient du store

  const handleSaveDevis = () => {
    console.log("=== DÉBUT handleSaveDevis ===");
    console.log("Mode édition:", isEditDevis);
    console.log("Valeurs reçues dans handleSaveDevis:", {
      nomClient,
      nomAssuré,
      numeroTelephone,
      adresseconducteur,
      habitation,
      permisconducteur,
      numeroconducteur,
      controlIdDevis,
      editDevisId
    });

    // Validation des champs requis

    if (!nomClient || !nomAssuré || !dateEffet || !dateExpiration || !dateEmission) {

      toast.error("Veuillez remplir tous les champs obligatoires");

      return;

    }



    // Validation de la date d'émission (ne doit pas être supérieure à aujourd'hui)

    const today = new Date();

    today.setHours(23, 59, 59, 999); // Fin de la journée

    const emissionDate = new Date(dateEmission);

    if (emissionDate > today) {

      toast.error("La date d'émission ne peut pas être supérieure à la date d'aujourd'hui");

      return;

    }



    // Validation de la date d'expiration

    const formattedExpiration = handleDate(dateExpiration);

    if (formattedExpiration === "Invalid date") {

      console.error("Erreur de formatage de la date d'expiration:", dateExpiration);

      toast.error("Erreur de formatage de la date d'expiration");

      return;

    }







    // La validation de cohérence entre durée et période de couverture a été supprimée
    // car les dates sont maintenant calculées automatiquement de manière cohérente
    // avec les attentes du backend



    // Fonction utilitaire pour parser les entiers de manière sécurisée

    const safeParseInt = (value, defaultValue = 0) => {

      if (!value || value === '') return defaultValue;

      const parsed = parseInt(value);

      return isNaN(parsed) ? defaultValue : parsed;

    };



    // Fonction utilitaire pour parser les flottants de manière sécurisée

    const safeParseFloat = (value, defaultValue = 0) => {

      if (!value || value === '') return defaultValue;

      const cleaned = String(value).replace(/ /g, "");

      const parsed = parseFloat(cleaned);

      return isNaN(parsed) ? defaultValue : parsed;

    };



    // Construire la liste des garanties existantes
    const garantiesExistantes = (offresStore || []).filter(o => o && o.IdGarantie !== 0 && o.IdSousGarantie !== 0).map((o) => ({
      id_garantie: o.IdGarantie,
      id_devis_detail: o.IdDevisDetail ?? null,
      prime_annuelle: parseFloat(o.PrimeAnnuelle || 0),
      prime_nette: parseFloat(o.PrimeNette || 0),
      capital: parseFloat(o.Capital || 0),
      acquise: true,
      libelle_sous_garantie: o.LibelleSousGarantie,
      montant_franchise: parseFloat(o.Franchise || 0),
      taux_franchise: parseFloat(o.TauxFranchise || 0),
      franchise_minimum: parseFloat(o.FranchiseMin || 0),
      franchise_maximum: parseFloat(o.FranchiseMax || 0),
      capital_deces: parseFloat(o.CapitalDeces || 0),
      capital_ipp: parseFloat(o.CapitalIPP || 0),
      capital_ft: parseFloat(o.CapitalFT || 0),
      reduction_commerciale: parseFloat(o.ReductionCommerciale || 0),
      reduction_bns: parseFloat(o.ReductionBns || 0),
    }));

    // Récupérer les nouvelles garanties depuis les fonctions de correction
    const nouvellesGaranties = correctionFunctions?.getCorrectionData?.()?.liste_garantie?.filter(g => g.is_new_garantie === true) || [];
    
    // Formater les nouvelles garanties pour l'API de sauvegarde
    const nouvellesGarantiesFormatees = nouvellesGaranties.map(g => ({
      id_garantie: g.id_garantie, // null pour que le backend génère un ID
      id_devis_detail: g.id_devis_detail,
      prime_annuelle: g.prime_annuelle,
      prime_nette: g.prime_nette,
      capital: g.capital,
      acquise: g.acquise,
      libelle_sous_garantie: g.libelle_sous_garantie,
      montant_franchise: g.montant_franchise,
      taux_franchise: g.taux_franchise,
      franchise_minimum: g.franchise_minimum,
      franchise_maximum: g.franchise_maximum,
      capital_deces: g.capital_deces,
      capital_ipp: g.capital_ipp,
      capital_ft: g.capital_ft,
      reduction_commerciale: g.reduction_commerciale,
      reduction_bns: g.reduction_bns,
    }));
    
    console.log("🔍 Garanties pour le devis:", {
      garantiesExistantes: garantiesExistantes.length,
      nouvellesGaranties: nouvellesGaranties.length,
      nouvellesGarantiesData: nouvellesGaranties,
      nouvellesGarantiesFormatees: nouvellesGarantiesFormatees
    });
    
    const garanties = [...garantiesExistantes, ...nouvellesGarantiesFormatees];

    const devisData = {

        IdIntermediaire: 1,

        IdCompagnie: safeParseInt(compagnie),

        IdProduit: 1,

        IdOffre: safeParseInt(offre),

        IdAvenant: idAvenant ? safeParseInt(idAvenant) : (idAvenantEdition || 0),

        NumeroPoliceCompagnie: numeroPoliceCompagnie || "RAS",

        NsiaAutoPlus: nsiaAutoPlus || false,

        IdClient: safeParseInt(nomClient),

        IdAssure: safeParseInt(nomAssuré),

        Telephone: numeroTelephone || "",

        Flotte: parseInt(typeContrat) === 1,

        CodeFormuleSecuriteRoutiere: securiteRoutiere || "",

        RemorqueAttelee: remorqueAttelee || false,

        CarburantAutreMatiere: CarburantAutreMatiere || false,

        TransportEleves: TransportEleves || false,

        TransportEmployes: TransportEmployes || false,

        TansportPassagerSupplementaire: TransportPassageSupplementaire || false,

        Coassurance: false,

        DateEffet: handleDate(dateEffet),

        DateExpiration: handleDate(dateExpiration),

        DateEmission: handleDate(dateEmission),

        IdTarif: safeParseInt(categorie),

        CodeUsage: safeParseInt(usage),

        IdCarrosserie: safeParseInt(carosserie),

        CodeCarburant: safeParseInt(energie),

        Puissance: safeParseInt(puissancefiscale),

        NombrePlace: safeParseInt(nbrPlace),

        Charge: safeParseInt(chargeUtile),

        ValeurNeuve: safeParseFloat(valeurNeuf),

        ValeurVenale: safeParseFloat(valeurVenale),

        ValeurAccessoire: safeParseFloat(valeurAccessoire),

        TauxReduction: reduction || 0,

        CodeAlarme: safeParseInt(systemeSecurites),

        Bns: bonusmalus || 0,

        NomConducteur: conducteur || "",

        AdresseConducteur: adresseconducteur || "",

        Habitation: habitation || "",
        LieuHabitation: habitation || "",
        VilleConducteur: habitation || "",

        DateMec: premiereCirculation ? handleDate(premiereCirculation) : "",

        NumMoteur: numeromoteur || "",

        NumChassis: chassis || "",

        IdTypeVehicule: safeParseInt(typevehicule),

        IdMarque: safeParseInt(marque),

        Matricule: immatriculation || "",

        NumPermisConduire: numeroPermisconducteur || "",

        PcType: permisconducteur || "",

        NumeroConducteur: numeroconducteur || "",

        IdGenreVehicule: safeParseInt(genre),

        NumCarteBrunePhysique: numeroCarteBrunePhysique || "",

        ModeleVehicule: modelevehicule || "",
        IdDuree: safeParseInt(duree),

        IdTerme: safeParseInt(reconduction),

        IdDevis: controlIdDevis || 0,

        IdDevisDetail: editDevisId || 0,

        // Forcer la mise à jour en mode édition, en renouvellement, ou si l'utilisateur a modifié des champs
        IsUpdate: Boolean(isEditDevis || isEditPolice || userModified),

        IdOptionAssistance: safeParseInt(assistanceAuto),
        // Liste garantie pour enregistrement, si attendue par l'API
        liste_garantie: garanties,

    };

    console.log("Données envoyées au backend:", devisData);
    console.log("=== ENVOI AU BACKEND ===");
    console.log("Valeur de habitation avant envoi:", habitation);
    console.log("Champs habitation dans devisData:", {
      Habitation: devisData.Habitation,
      LieuHabitation: devisData.LieuHabitation,
      VilleConducteur: devisData.VilleConducteur
    });
    console.log("Dispatch de saveDevis avec:", devisData);
    console.log("IDs pour mise à jour:", {
      IdDevis: devisData.IdDevis,
      IdDevisDetail: devisData.IdDevisDetail,
      controlIdDevis,
      editDevisId
    });

    // Log des données pour débogage

    console.log("Données envoyées au serveur:", devisData);
    
    // Log spécifique pour l'édition
    console.log("Mode édition:", {
      isEditDevis,
      controlIdDevis,
      editDevisId,
      editDevisIdDet
    });
    
    // Log des champs conducteur
    console.log("Champs conducteur:", {
      adresseconducteur,
      habitation,
      permisconducteur,
      numeroPermisconducteur,
      numeroconducteur,
      numeroTelephone
    });

    console.log("Champs client/assuré:", {
      nomClient,
      nomAssuré
    });

    console.log("=== VALEURS FINALES ENVOYÉES À L'API ===");
    console.log("Téléphone:", numeroTelephone);
    console.log("Adresse conducteur:", adresseconducteur);
    console.log("Habitation:", habitation);
    console.log("Numéro conducteur:", numeroconducteur);
    console.log("Catégorie permis:", permisconducteur);
    console.log("Numéro permis:", numeroPermisconducteur);
    console.log("Données initialisées:", dataInitialized);
    console.log("Utilisateur a modifié:", userModified);
    console.log("Mode édition devis:", isEditDevis);
    
    // Log spécifique pour le débogage des dates
    console.log("Détails des dates:", {
      dateEffet: dateEffet,
      dateExpiration: dateExpiration,
      dateEmission: dateEmission,
      duree: duree,
      IdDuree: safeParseInt(duree),
      formattedDateEffet: handleDate(dateEffet),
      formattedDateExpiration: handleDate(dateExpiration),
      formattedDateEmission: handleDate(dateEmission)
    });

    

    // Validation des types de données critiques

    if (!compagnie || !offre || !categorie || !nomClient || !nomAssuré) {

      toast.error("Veuillez remplir tous les champs obligatoires");

      return;

    }



    console.log("=== AVANT DISPATCH ===");
    
    // 🎯 ÉTAPE 1: SAUVEGARDER LE DEVIS
    dispatch(saveDevis(devisData))
      .then(async (result) => {
        console.log("=== RÉPONSE BACKEND ===", result);
        if (result.type === 'savedevis/create/fulfilled') {
          console.log("✅ Sauvegarde réussie !");
          console.log("🔍 Réponse complète de sauvegarde:", result.payload);
          console.log("🔍 ID devis retourné:", result.payload[0]?.IdDevis);
          
          // 🎯 ÉTAPE 2: APPLIQUER SYSTÉMATIQUEMENT LA CORRECTION DES PRIMES
          if (correctionFunctions) {
            console.log("🔄 Application de la correction des primes...");
            
            try {
              const devisId = result.payload[0]?.IdDevis;
              if (!devisId || devisId <= 0) {
                console.error("❌ ID devis invalide retourné par l'API:", devisId);
                toast.error("❌ ID devis invalide, impossible d'appliquer la correction");
                return;
              }
              
              const correctionResult = await correctionFunctions.applyCorrectionWithDevisId(devisId);
              
              if (correctionResult && correctionResult.success) {
                //toast.success("✅ Devis enregistré et primes corrigées avec succès !");
                console.log("✅ Correction appliquée:", correctionResult);
                // Marquer proprement la fin d'édition côté UI
                // Ne pas supprimer le cache local: il sert à restaurer les primes corrigées après refresh
                dispatch(clearModifications());
                dispatch(clearEditedPrimes());
              } else {
                toast.error("⚠️ Devis enregistré mais erreur lors de la correction des primes");
                console.warn("⚠️ Erreur correction:", correctionResult?.message);
              }
            } catch (error) {
              console.error("❌ Erreur lors de la correction:", error);
              toast.error("⚠️ Devis enregistré mais erreur lors de la correction des primes");
            }
          } else {
            toast.success("✅ Devis enregistré avec succès !");
            console.log("ℹ️ Aucune correction de primes nécessaire");
          }
        } else {
          console.log("❌ Erreur de sauvegarde:", result);
          toast.error("❌ Erreur lors de l'enregistrement du devis");
        }
      })
      .catch((error) => {
        console.log("❌ Erreur lors de la sauvegarde:", error);
        toast.error("❌ Erreur lors de l'enregistrement du devis");
      });
    console.log("=== APRÈS DISPATCH ===");

  };



  // ending save devis auto

  const handleEndDevis = () => {

    dispatch(

      finalisationdevisauto({

        IdDevis: parseInt(controlIdDevis),

        IdClient: parseInt(nomClient),

        IdAssure: parseInt(nomAssuré),

        Flotte: true,

      })

    );

  };



  const handleClickSaveDevis = () => {
    console.log("=== DÉBUT handleClickSaveDevis ===");
    console.log("isEditDevis:", isEditDevis);
    console.log("Valeurs actuelles:", {
      nomClient,
      nomAssuré,
      numeroTelephone,
      adresseconducteur,
      habitation,
      permisconducteur,
      numeroconducteur
    });

    // Si on est en mode édition de devis, utiliser la même logique que les autres pages
    if (isEditDevis) {
      console.log("Mode édition détecté, appel de handleSaveDevis");
      // Pour l'édition, on utilise handleSaveDevis qui met à jour le devis existant
      handleSaveDevis();
      return;
    }

    if (!isEditPolice) {

      if (parseInt(typeContrat) === 0) {

        handleSaveDevis();

      } else {

        handleEndDevis();

      }

    } else {

        handleSaveDevis();

    }

  };




  if (isLoading) {

    return <Spinner />;

  }



  return (

    <div className="p-4 mb-6 col-span-full xl:col-span-6 bg-white rounded-md border-2 border-gray-200">

      <h2 className="font-bold mb-4 text-sm uppercase text-blue-500">

        Client/Assuré/Conducteur

      </h2>

      <div className="grid grid-cols-3 gap-6">

      

        {/* NOM */}

        <SearchableSelect

          label="Nom du souscripteur"

          value={nomClient}

          searchTerm={searchClientTerm}

          setSearchResults={setSearchClientResults}

          setSearchTerm={setSearchClientTerm}

          searchResults={searchClientResults}

          onChange={setNomClient}

          onSelectClient={(client) => {

            // En mode édition de devis, ne pas synchroniser automatiquement
            // pour préserver les modifications de l'utilisateur
            if (isEditDevis) return;

            // Renseigner infos de contact et conducteur

            const phone = client.Mobile || client.Telephone || "";

            setNumeroTelephone(phone);

            setConducteur(formatName(client.Nom || ""));

            // Utiliser les données de l'intermédiaire au lieu du client
            // setAdresseconducteur(client.Adresse1 || "");
            // setHabitation(client.Adresse2 || "");

            setNumeroconducteur(phone);

          }}

          disabled={nomClientState}

          clients={clients}

          placeholder="Rechercher un client..."

          showAddButton={true}

          onAddClick={() => setOpenPanel(true)}

          // Synchronisation bidirectionnelle avec l'assuré

          syncWithField="assure"

          setSyncValue={setNomAssuré}

          setSyncSearchTerm={setSearchAssureTerm}

          setSyncSearchResults={setSearchAssureResults}

        />

          <Transition.Root show={openPanel} as={Fragment}>

            <Dialog

              as="div"

              className="relative z-60 font-Overpass"

              open={openPanel}

              onClose={setOpenPanel}

            >

              <Transition.Child

                as={Fragment}

                enter="ease-in-out duration-500"

                enterFrom="opacity-0"

                enterTo="opacity-100"

                leave="ease-in-out duration-500"

                leaveFrom="opacity-100"

                leaveTo="opacity-0"

              >

                <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />

              </Transition.Child>

              <div className="fixed inset-0 overflow-hidden">

                <div className="absolute inset-0 overflow-hidden">

                  <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">

                    <Transition.Child

                      as={Fragment}

                      enter="transform transition ease-in-out duration-500 sm:duration-700"

                      enterFrom="translate-x-full"

                      enterTo="translate-x-0"

                      leave="transform transition ease-in-out duration-500 sm:duration-700"

                      leaveFrom="translate-x-0"

                      leaveTo="translate-x-full"

                    >

                      <Dialog.Panel className="pointer-events-auto relative w-screen max-w-2xl">

                        <Transition.Child

                          as={Fragment}

                          enter="ease-in-out duration-500"

                          enterFrom="opacity-0"

                          enterTo="opacity-100"

                          leave="ease-in-out duration-500"

                          leaveFrom="opacity-100"

                          leaveTo="opacity-0"

                        >

                          <div className="absolute top-0 left-0 -ml-8 flex pt-4 pr-2 sm:-ml-10 sm:pr-4">

                            <button

                              type="button"

                              className="rounded-full text-white hover:text-white "

                              onClick={() => setOpenPanel(false)}

                            >

                              <span className="sr-only">Close panel</span>

                              <span className="font-bold text-xl">X</span>

                            </button>

                          </div>

                        </Transition.Child>

                        <div className="flex h-full flex-col overflow-y-scroll bg-white py-6 shadow-xl">

                          <div className="m-8 md:col-span-2 md:mt-0">

                            <WelcomeBanner title="Nouveau client" />

                            <NewClientContrat

                              qualites={qualites}

                              professions={professions}

                              typesouscripteurs={typesouscripteurs}

                              typeassures={typeassures}

                            />

                          </div>

                        </div>

                      </Dialog.Panel>

                    </Transition.Child>

                  </div>

                </div>

              </div>

            </Dialog>

          </Transition.Root>

      

        {/* ASSURE */}

        <SearchableSelect

          label="Nom de l'assuré"

          value={nomAssuré}

          searchTerm={searchAssureTerm}

          setSearchResults={setSearchAssureResults}

          setSearchTerm={setSearchAssureTerm}

          searchResults={searchAssureResults}

          onChange={setNomAssuré}

          onSelectClient={(client) => {

            // En mode édition de devis, ne pas synchroniser automatiquement
            // pour préserver les modifications de l'utilisateur
            if (isEditDevis) return;

            const phone = client.Mobile || client.Telephone || "";

            setNumeroTelephone(phone);

            setConducteur(formatName(client.Nom || ""));

            // Utiliser les données de l'intermédiaire au lieu de l'assuré
            // setAdresseconducteur(client.Adresse1 || "");
            // setHabitation(client.Adresse2 || "");

            setNumeroconducteur(phone);

          }}

          disabled={nomAssuréState}

          clients={clients}

          placeholder="Rechercher un assuré..."

          // Synchronisation bidirectionnelle avec le souscripteur

          syncWithField="souscripteur"

          setSyncValue={setNomClient}

          setSyncSearchTerm={setSearchClientTerm}

          setSyncSearchResults={setSearchClientResults}

        />

        

        {/* NUMERO DE TELEPHONE  */}

        <div className="relative z-0 w-full group">

          <label

            htmlFor="numeroTelephone"

            className="block text-xs font-normal text-gray-700"

          >

            Numéro de téléphone

          </label>

          <div className="mt-1 flex rounded-md shadow-sm">

            <span className="inline-flex items-center rounded-l-md border-2 border-r-0 border-gray-300 bg-blue-50 px-3 text-sm text-gray-500">

              +225

            </span>

            <input

              type="text"

              name="numeroTelephone"

              id="numeroTelephone"

              value={numeroTelephone}

              disabled={numeroTelephoneState && !isEditDevis}

              onChange={(e) => {
                setNumeroTelephone(e.target.value);
                setUserModified(true);
              }}

              className="block w-full flex-1 rounded-none rounded-r-md border-2 border-gray-300  focus:border-blue-500 focus:ring-blue-500 text-xs"

              placeholder="Entrez votre numéro de téléphone"

            />

          </div>

        </div>

        {/* NOM DU CONDUCTEUR */}

        <TextInput

          type="text"

          name="conducteur"

          value={conducteur}

          disabled={conducteurState}

          onChange={(e) => {
            setConducteur(e.target.value);
            setUserModified(true);
          }}

          label="Nom du conducteur"

        />

        {/* ADRESSE DU CONDUCTEUR */}

        <TextInput

          type="text"

          name="adresseconducteur"

          value={adresseconducteur}

          disabled={adresseconducteurState && !isEditDevis}

          label="Adresse du conducteur"

          onChange={(e) => {
            setAdresseconducteur(e.target.value);
            setUserModified(true);
          }}

          placeholderInput="Adresse du conducteur"

        />

        {/* PERMIS DU CONDUCTEUR */}

        <div className="">

          <label

            htmlFor="permisconducteur"

            className="block text-xs font-normal text-gray-700"

          >

            Catégorie de permis

          </label>

          <select

            id="permisconducteur"

            name="permisconducteur"

            value={permisconducteur}

            disabled={permisconducteurState && !isEditDevis}

            onChange={(e) => {
              setPermisconducteur(e.target.value);
              setUserModified(true);
            }}

            className="bg-gray-50  mt-0.5 block w-full rounded-md border-2 border-gray-300  py-1 px-2  focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-xs font-bold"

          >

            {categoriepermis.map((categoriepermi, index) => (

              <option key={index} value={categoriepermi.id}>

                {categoriepermi.libelle}

              </option>

            ))}

          </select>

        </div>

        {/* NUMERO DE PERMIS */}

        <TextInput

          type="text"

          name="numeroPermisconducteur"

          value={numeroPermisconducteur}

          disabled={numeroPermisconducteurState}

          onChange={(e) => {
            setNumeroPermisconducteur(e.target.value);
            setUserModified(true);
          }}

          label="Numéro du permis"

          placeholderInput="Numéro du permis"

          InputClassName="text-sm"

        />

        {/* HABITATION */}

        <TextInput

          type="text"

          name="habitation"

          value={habitation}

          disabled={habitationState && !isEditDevis}

          onChange={(e) => {
            setHabitation(e.target.value);
            setUserModified(true);
          }}

          label="Lieu d'habitation"

          placeholderInput="Lieu d'habitation"

          InputClassName="text-sm"

        />

        {/* NUMERO DU CONDUCTEUR */}

        <div className="relative z-0 w-full group">

          <label

            htmlFor="numeroconducteur"

            className="block text-xs font-normal text-gray-700"

          >

            Numéro du conducteur

          </label>

          <div className="mt-1 flex rounded-md shadow-sm">

            <span className="inline-flex items-center rounded-l-md border-2 border-r-0 border-gray-300 bg-blue-50 px-3 text-sm text-gray-500">

              +225

            </span>

            <input

              type="number"

              name="numeroconducteur"

              id="numeroconducteur"

              value={numeroconducteur}

              disabled={numeroconducteurState && !isEditDevis}

              onChange={(e) => {
                setNumeroconducteur(e.target.value);
                setUserModified(true);
              }}

              className="block w-full flex-1 rounded-none rounded-r-md border-2 border-gray-300  focus:border-blue-500 focus:ring-blue-500 text-xs"

              placeholder="Entrez le numéro du conducteur"

            />

          </div>

        </div>

      </div>

      <div className="">

        <p className="">

          <OutlineButton

            handleClick={prevStep}

            buttonClassname="before:bg-red-600 text-red-600 text-xs"

            content={"Précédent"}

          />

          <ButtonSave

            handleClick={handleClickSaveDevis}

            content="Valider"

            buttonClassname="text-white bg-blue-400 hover:bg-blue-500 mt-8 ml-4"

          />

        </p>

      </div>

    </div>

  );

}



export default ClientRegistration;