/* Centre des corrections (Administration > Corrections) : pour chaque erreur qu'un utilisateur peut commettre, l'écran qui la
   corrige et le droit qu'il exige. Lu par la page du centre et par le menu de l'administration (section Corrections). */

// Erreur possible -> outil qui la corrige (droit exigé par l'outil)
export const CATALOGUE = [
  {
    domaine: 'Clients',
    cas: [
      { erreur: 'Client créé deux fois', correction: 'Fusionner les deux fiches : contrats, devis, quittances et chèques passent sur la fiche gardée.', lien: '/admin/corrections/clients', outil: 'Fiches clients en double', droit: 'clients.merge' },
      { erreur: 'Nom, téléphone, adresse ou pièce erronés', correction: 'Modifier la fiche du client ; avant et après sont journalisés.', lien: '/user/clients', outil: 'Clients', droit: 'clients.update' },
      { erreur: 'Fiche archivée par erreur', correction: 'La restaurer depuis les Archives.', lien: '/user/archives', outil: 'Archives', droit: 'archives.restore' },
    ],
  },
  {
    domaine: 'Devis',
    cas: [
      { erreur: 'Devis mal saisi, pas encore confirmé', correction: 'Le rouvrir et le modifier depuis le registre des devis.', lien: '/user/quotes', outil: 'Registre des devis', droit: 'devis.update' },
      { erreur: 'Devis créé par erreur', correction: 'Le supprimer depuis le registre des devis, avec un motif.', lien: '/user/quotes', outil: 'Registre des devis', droit: 'devis.delete' },
    ],
  },
  {
    domaine: 'Contrats',
    cas: [
      { erreur: 'Date, référence, véhicule, garantie ou prime erronés', correction: 'Corriger le contrat : les primes sont recalculées jusqu’à la quittance.', lien: '/admin/contracts/edit', outil: 'Corriger un contrat', droit: 'contrats.admin_update' },
      { erreur: 'Contrat au nom du mauvais client ou chez la mauvaise compagnie', correction: 'Corriger le contrat : quittance, devis, soldes et, au choix, toute la police suivent.', lien: '/admin/contracts/edit', outil: 'Corriger un contrat', droit: 'contrats.admin_update' },
      { erreur: 'Contrat ou avenant émis par erreur, rien encaissé', correction: 'Le supprimer depuis sa fiche : le devis redevient confirmable.', lien: '/user/contracts', outil: 'Contrats', droit: 'contrats.delete' },
      { erreur: 'Le client renonce au contrat', correction: 'Avenant d’annulation ou de résiliation depuis la fiche du contrat.', lien: '/user/contracts', outil: 'Contrats', droit: 'contrats.cancel' },
      { erreur: 'Affaire antérieure mal saisie', correction: 'La corriger ou la supprimer depuis Affaires antérieures.', lien: '/user/reprises', outil: 'Affaires antérieures', droit: 'contrats.reprise' },
    ],
  },
  {
    domaine: 'Caisse',
    cas: [
      { erreur: 'Encaissement sur le mauvais client, la mauvaise quittance, le mauvais montant ou le mauvais mode', correction: 'Annuler et réaffecter en une seule fois, sur le même chèque s’il y en a un.', lien: '/admin/corrections/encaissements', outil: 'Corriger un encaissement', droit: 'encaissements.cancel' },
      { erreur: 'N° de chèque, banque, émetteur ou dates erronés', correction: 'Corriger les références : montant et quittance ne changent pas.', lien: '/admin/corrections/encaissements', outil: 'Corriger un encaissement', droit: 'encaissements.cancel' },
      { erreur: 'Encaissement saisi deux fois', correction: 'Annuler le doublon : la quittance redevient à encaisser.', lien: '/admin/corrections/encaissements', outil: 'Corriger un encaissement', droit: 'encaissements.cancel' },
      { erreur: 'Chèque revenu impayé ou rendu au client', correction: 'L’annuler depuis le Portefeuille des règlements.', lien: '/user/cheques', outil: 'Portefeuille des règlements', droit: 'encaissements.cancel' },
      { erreur: 'Chèque annulé à représenter', correction: 'Le réutiliser depuis le Portefeuille des règlements.', lien: '/user/cheques', outil: 'Portefeuille des règlements', droit: 'encaissements.create' },
      { erreur: 'Solde d’un chèque faux', correction: 'Le recalculer d’après ses règlements en cours, depuis « À corriger ».', onglet: 'anomalies', outil: 'À corriger', droit: 'encaissements.cancel' },
      { erreur: 'Ristourne remboursée ou imputée par erreur', correction: 'Annuler le règlement de la ristourne.', lien: '/user/cash/ristournes', outil: 'Ristournes', droit: 'encaissements.cancel' },
    ],
  },
  {
    domaine: 'Reversements et commissions',
    cas: [
      { erreur: 'Bordereau de reversement erroné', correction: 'Annuler le bordereau, avec un motif, puis l’émettre de nouveau.', lien: '/admin/remittances', outil: 'Reversements aux compagnies', droit: 'reversements.cancel' },
      { erreur: 'Commission réclamée ou encaissée par erreur', correction: 'Annuler la réclamation ou le paiement.', lien: '/admin/commissions', outil: 'Commissions du cabinet', droit: 'commissions.cancel' },
      { erreur: 'Commission d’apporteur erronée', correction: 'Annuler la commission ou le règlement de l’apporteur.', lien: '/admin/apporteurs', outil: 'Apporteurs d’affaires', droit: 'apporteurs.cancel' },
    ],
  },
  {
    domaine: 'Sinistres et listes',
    cas: [
      { erreur: 'Sinistre mal saisi', correction: 'Le corriger depuis le Suivi des sinistres.', lien: '/user/claims', outil: 'Suivi des sinistres', droit: 'sinistres.update' },
      { erreur: 'Banque saisie deux fois', correction: 'Les doublons sont signalés dans la liste des banques.', lien: '/admin/settings/banques', outil: 'Banques', droit: 'parametrage.update' },
    ],
  },
];

// Droits qui ouvrent la section Corrections du menu
export const DROITS_CORRECTIONS = [...new Set(CATALOGUE.flatMap((d) => d.cas.map((c) => c.droit)))];
