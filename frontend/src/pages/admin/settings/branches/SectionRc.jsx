import React, { useEffect, useState } from 'react';
import { Briefcase, Loader2, Plus, Save, Trash2 } from 'lucide-react';
import { SectionParametrage } from '../../../../components/admin/EnTeteParametrage';
import { risquesDiversApi } from '../../../../api/endpoints';
import { useToast } from '../../../../context/ToastContext';
import { messageErreurApi } from '../../../../utils/financeUtils';
import { confirmer } from '../../../../utils/dialogue';

// Réglages Responsabilité civile : domaines d'activité proposés à la saisie des devis RC (stddomaineactivite).

const Domaine = ({ domaine, onEnregistre, onRetire }) => {
  const { success, error: toastError } = useToast();
  const [libelle, setLibelle] = useState(domaine.libelle);
  const [envoi, setEnvoi] = useState(false);
  const enregistrer = async () => {
    setEnvoi(true);
    try {
      const maj = await risquesDiversApi.modifierDomaine(domaine.id_domaine_activite, libelle.trim());
      onEnregistre(maj);
      success(`Domaine « ${maj.libelle} » enregistré.`);
    } catch (err) {
      toastError(messageErreurApi(err));
    } finally {
      setEnvoi(false);
    }
  };
  const retirer = async () => {
    if (!(await confirmer({ ton: 'danger', titre: `Retirer « ${domaine.libelle} » ?`, message: 'Il ne sera plus proposé à la saisie des devis RC. Un domaine déjà utilisé par un devis ne peut pas être retiré.', confirmer: 'Retirer le domaine', annuler: 'Garder' }))) return;
    try {
      await risquesDiversApi.supprimerDomaine(domaine.id_domaine_activite);
      onRetire(domaine.id_domaine_activite);
      success(`Domaine « ${domaine.libelle} » retiré.`);
    } catch (err) {
      toastError(`Domaine non retiré, sans doute utilisé par des devis : ${messageErreurApi(err)}`);
    }
  };
  return (
    <tr>
      <td><input className="form-control" maxLength={100} value={libelle} aria-label="Domaine d'activité" onChange={(e) => setLibelle(e.target.value)} /></td>
      <td style={{ whiteSpace: 'nowrap' }}>
        {libelle.trim() && libelle !== domaine.libelle && <button type="button" className="btn btn-primary" onClick={enregistrer} disabled={envoi} aria-busy={envoi}><Save size={14} /></button>}
        <button type="button" className="btn btn-link" onClick={retirer} aria-label={`Retirer ${domaine.libelle}`}><Trash2 size={15} /></button>
      </td>
    </tr>
  );
};

export const SectionRc = () => {
  const { success, error: toastError } = useToast();
  const [domaines, setDomaines] = useState(null);
  const [nouveau, setNouveau] = useState('');
  useEffect(() => {
    risquesDiversApi.getDomaines()
      .then((l) => setDomaines(Array.isArray(l) ? l : []))
      .catch((err) => toastError(`Domaines d'activité non chargés : ${messageErreurApi(err)}`));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const ajouter = async () => {
    try {
      const d = await risquesDiversApi.creerDomaine(nouveau.trim());
      setDomaines((l) => [...l, d]);
      setNouveau('');
      success(`Domaine « ${d.libelle} » ajouté.`);
    } catch (err) {
      toastError(messageErreurApi(err));
    }
  };
  return (
    <SectionParametrage icone={Briefcase} titre="Domaines d'activité" description="Proposés à la saisie d'un devis RC ; le gestionnaire peut aussi en ajouter un depuis le formulaire.">
      {!domaines ? <div style={{ color: 'var(--text-muted)' }}><Loader2 size={15} className="spin" /> Chargement…</div> : (
        <div className="table-wrapper">
          <table className="rb-table">
            <tbody>
              {domaines.map((d) => (
                <Domaine key={d.id_domaine_activite} domaine={d}
                  onEnregistre={(maj) => setDomaines((l) => l.map((x) => (x.id_domaine_activite === maj.id_domaine_activite ? maj : x)))}
                  onRetire={(id) => setDomaines((l) => l.filter((x) => x.id_domaine_activite !== id))} />
              ))}
              <tr>
                <td><input className="form-control" maxLength={100} placeholder="Nouveau domaine d'activité" value={nouveau} onChange={(e) => setNouveau(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && nouveau.trim()) ajouter(); }} aria-label="Nouveau domaine d'activité" /></td>
                <td><button type="button" className="btn btn-secondary" onClick={ajouter} disabled={!nouveau.trim()} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}><Plus size={15} /> Ajouter</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </SectionParametrage>
  );
};

export default SectionRc;
