import { Fragment, useEffect, useState } from "react";
import ContratForm from "../ContratForm/ContratForm";
import WelcomeBanner from "partials/UI/Banner/WelcomeBanner";
import { useParams } from "react-router-dom";
import axios from "axios";
import { useSelector } from "react-redux";

function EditionDevisAuto() {
  const { token } = useSelector(state => state.auth)
  const { idproduit, iddevisEdition } = useParams();
  const [isEditDevis, setIsEditDevis] = useState(true)
  const [devisEdition, setDevisEdition] = useState();
  const [devisDetEdition, setDevisDetEdition] = useState();
  const [valeurNeufState, setvaleurNeufState] = useState(false);

  useEffect(() => {
    setIsEditDevis(true);
    getSingleDevis();
    getDevisDetails();

    return () => {
      setIsEditDevis(false);
    };
  }, []);
	
   const getSingleDevis = async () => {
     const config = {
       headers: {
         Authorization: `Token ${token}`,
       },
     };
     const { data } = await axios.get(
       `${process.env.REACT_APP_API_URL}devis/${iddevisEdition}/`,
       config
     );
     setDevisEdition(data);
   };

  const getDevisDetails = async () => {
    if (!iddevisEdition) {
      console.warn("getDevisDetails: iddevisEdition manquant");
      return;
    }
    
    try {
      const config = {
        headers: {
          Authorization: `Token ${token}`,
        },
      };
      const { data } = await axios.get(
        `${process.env.REACT_APP_API_URL}devisdetail/${iddevisEdition}`,
        config
      );
      setDevisDetEdition(data);
    } catch (error) {
      console.error("Erreur lors de la récupération des détails du devis:", error);
      // Ne pas faire planter l'application si le devis n'existe pas
      if (error.response?.status === 404) {
        console.warn(`Devis ${iddevisEdition} non trouvé`);
      }
    }
  };

  return (
    <Fragment>
      <WelcomeBanner title={`Edition devis n°${devisEdition && devisEdition.numerodevis}`} />

      {idproduit && iddevisEdition && devisEdition && (
        <ContratForm
          devisEdition={devisEdition}
          isEditDevis={isEditDevis}
          idproduit={idproduit}
          idAvenant={devisEdition.avenant.IdAvenant}
          iddevisEdition={iddevisEdition}
          devisDetEdition={devisDetEdition}
          valeurNeufState={valeurNeufState}
          setvaleurNeufState={setvaleurNeufState}
        />
      )}
    </Fragment>
  );
}

export default EditionDevisAuto;
