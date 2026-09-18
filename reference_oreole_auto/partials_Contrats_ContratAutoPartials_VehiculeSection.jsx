import DatePicker from "react-datepicker";
import {
  OutlineButton,
  ButtonNext,
  AddButton,
} from "partials/UI/Button/Button";
import { TextInput } from "partials/UI/Inputs";

import { Fragment, useEffect, useState } from "react";
import { toast } from "react-hot-toast";
import axios from "axios";
import { useSelector, useDispatch } from "react-redux";
import { MdOutlineAdd } from "react-icons/md";
import Drawer from "partials/Utils/Drawer/Drawer";
import WelcomeBanner from "partials/UI/Banner/WelcomeBanner";
import { addCommas, removeNonNumeric } from "partials/Utils/FormUtils";
import { getMarques } from "features/Contrat/contratSlice";

function VehiculeSection({
  // mouvement
  isEditPolice,
  dateEffet,
  dateEmission,
  idAvenant,
  idcontrat,
  controlIdDevis,
  setControlIdDevis,
  initializedMouvement,
  setInitializedMouvement,
  motif,
  nextStep,
  prevStep,
  vehiculeSectionData,
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
  securiteRoutiere,
  setSecuriteRoutiere,
  remorqueAttelee,
  toggleRemorqueAttelee,
  typevehicule,
  setTypevehicule,
  typeContrat,
  secu_r,
  transportCompteAssure,
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
  energieState,
  systemeSecuritesState,
  securiteRoutiereState,
  assistanceAutoState,
  marqueState,
  genreState,
  typevehiculeState,
  remorqueAtteleeState,
  CarburantAutreMatiereState,
  TransportElevesState,
  TransportEmployesState,
  TransportPassageSupplementaireState,
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
  categorie
}) {
  const { token } = useSelector((state) => state.auth);
  const dispatch = useDispatch();
  const [isEbene, setIsEbene] = useState(false);

  useEffect(() => {
    setIsEbene(parseInt(categorie) === 123 || parseInt(categorie) === 122);
  }, [categorie]);

  function shouldDisplayButton(premiereCirculation) {
    const circulationDate = new Date(premiereCirculation);
    if (isNaN(circulationDate)) {
      return false;
    }
    const diffYears = (new Date() - circulationDate) / (1000 * 60 * 60 * 24 * 365.25);
    return diffYears > 4 && diffYears < 11;
  }


  const energies = vehiculeSectionData.energies;
  const systemesecurites = vehiculeSectionData.systemesecurites;
  const marques = vehiculeSectionData.marques;
  const genrevehicules = vehiculeSectionData.genrevehicules;
  const typevehicules = vehiculeSectionData.typevehicules;

  // Sort marques alphabetically
  const sortedMarques = [...marques].sort((a, b) =>
    a.LibelleMarque.localeCompare(b.LibelleMarque, 'fr', { sensitivity: 'base' })
  );

  // adding vehicule marque
  const [openPanel, setOpenPanel] = useState(false);
  const [LibelleMarque, setLibelleMarque] = useState("");

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
      setOpenPanel(false);

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

  return (
    <div className="p-4 mb-6 col-span-full xl:col-span-6 bg-white rounded-md border-2 border-gray-200">
      <h2 className="font-bold mb-4 text-sm uppercase text-blue-500">
        Véhicule
      </h2>
      <div className="grid md:grid-cols-4 md:gap-6">
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
            {energies.map((energie) => (
              <option key={energie.IdEnergie} value={energie.IdEnergie}>
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
            {systemesecurites.map((systemesecurite) => (
              <option
                key={systemesecurite.IdSystemeSecurite}
                value={systemesecurite.IdSystemeSecurite}
              >
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
            {secu_r.map((element) => (
              <option key={element.codeformule} value={element.codeformule}>
                {element.libellelongformule}
              </option>
            ))}
          </select>
        </div>
        {/* ASSISTANCE AUTO */}
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
              {sortedMarques.map((marque) => (
                <option key={marque.IdMarque} value={marque.IdMarque}>
                  {marque.LibelleMarque}
                </option>
              ))}
            </select>
            <span
              onClick={() => setOpenPanel(true)}
              className="cursor-pointer font-bold text-sm text-blue-700 hover:text-blue-800 rounded-full bg-blue-50 py-2 px-2 flex items-center"
            >
              <MdOutlineAdd className="h-6 w-6" />
            </span>
          </div>

          <Drawer
            openPanel={openPanel}
            setOpenPanel={setOpenPanel}
            DialogCn="max-w-3xl"
          >
            <WelcomeBanner title="Ajouter un véhicule" />
            {/* NOM DU CONDUCTEUR */}
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
            {genrevehicules.map((genrevehicule) => (
              <option key={genrevehicule.IdGenre} value={genrevehicule.IdGenre}>
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
            {typevehicules.map((typevehicule) => (
              <option key={typevehicule.id} value={typevehicule.id}>
                {typevehicule.libelle_type}
              </option>
            ))}
          </select>
        </div>
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
            <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all  peer-checked:bg-green-600"></div>
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
                <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all  peer-checked:bg-green-600"></div>
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
                <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300  rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all  peer-checked:bg-green-600"></div>
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
                  className="sr-only peer"
                  disabled={TransportEmployesState}
                  checked={TransportEmployes}
                  onChange={toggleTransportEmployes}
                />
                <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all  peer-checked:bg-green-600"></div>
                <span className="ml-3 text-sm font-bold text-gray-900">
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
                  Transport passager Supplémentaire
                </span>
              </label>
            </div>
          </Fragment>
        ) : (
          ""
        )}
        {transportPublicMarchandise ? (
          <Fragment>
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
          disabled={puissancefiscaleState}
          value={puissancefiscale}
          onChange={(e) => setPuissancefiscale(e.target.value)}
          label="Puissance fiscale (* requis)"
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
            selected={premiereCirculation}
            disabled={premiereCirculationState}
            dateFormat="dd/MM/yyyy"
            placeholderText="ex: 01/02/2023"
            onChange={(date) => setPremiereCirculation(date)}
            className="font-bold bg-gray-50  mt-1 block rounded-md border-2 border-gray-300  focus:border-blue-400 focus:ring-blue-400 text-xs w-5/6 py-1 px-2"
          />
          {isEbene && !shouldDisplayButton(premiereCirculation) && <p className="mt-2 text-xs italic font-bold text-red-600">Le véhicule doit avoir plus de 4 ans et moins de 11 ans.</p>
          }
        </div>
      </div>
      <div className="mt-8">
        <OutlineButton
          handleClick={prevStep}
          buttonClassname="before:bg-red-600 text-red-600 text-xs"
          content={"Précédent"}
        />
        {isEbene && shouldDisplayButton(premiereCirculation) && (
          <ButtonNext
            handleClick={nextStep}
            buttonClassname="text-white bg-blue-500 hover:bg-blue-800 ml-4"
            content={"Suivant"}
          />
        )}
        {!isEbene && (
          <ButtonNext
            handleClick={nextStep}
            buttonClassname="text-white bg-blue-500 hover:bg-blue-800 ml-4"
            content={"Suivant"}
          />
        )}
      </div>
    </div>
  );
}

export default VehiculeSection;
