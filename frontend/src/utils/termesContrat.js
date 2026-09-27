// Termes du contrat (stddevis.idterme), identiques à la liste de l'API /terme/
// (configuration_api.TermeViewSet) : il n'existe pas de table en base, les ids sont fixes.
export const TERMES_CONTRAT = [
  { id: 1, libelle: 'Tacite reconduction' },
  { id: 2, libelle: 'Ferme' },
  { id: 3, libelle: 'Autre' },
];

export const ID_TERME_PAR_DEFAUT = 1;

// Id de terme enregistrable : un id inconnu (ou absent) retombe sur Tacite reconduction
export const idTermeValide = (id) => (TERMES_CONTRAT.some((t) => t.id === Number(id)) ? Number(id) : ID_TERME_PAR_DEFAUT);

export const libelleTerme = (id) => TERMES_CONTRAT.find((t) => t.id === idTermeValide(id)).libelle;
