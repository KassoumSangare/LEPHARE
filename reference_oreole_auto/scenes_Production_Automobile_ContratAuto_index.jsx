// partials
import WelcomeBanner from "partials/UI/Banner/WelcomeBanner";
import ContratForm from "./ContratForm/ContratForm";
import { Fragment, useState } from "react";
import { useParams } from "react-router-dom";

const NouveauContratAuto = () => {
  const { idproduit } = useParams();
  const [valeurNeufState, setvaleurNeufState] = useState(false);
  
  return (
    <Fragment>
      <WelcomeBanner
        title="Production de contrat Automobile"
        subtitle="Pour créer un nouveau contrat, veuillez remplir le formulaire suivant"
      />

      {idproduit && <ContratForm idproduit={idproduit} idAvenant={1} valeurNeufState={valeurNeufState} setvaleurNeufState={setvaleurNeufState} />}
    </Fragment>
  );
};

export default NouveauContratAuto;
