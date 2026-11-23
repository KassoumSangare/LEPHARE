"""
Catalogue des droits de LE PHARE et rôles livrés.

Un droit = une action contrôlée par le serveur (autorisations/garde.py) sur un module. Le
catalogue suit le code : il est synchronisé en base à chaque migration (synchroniser_droits).
Les rôles, eux, appartiennent à l'administration : ROLES_INITIAUX ne sert qu'à la première
installation (migration autorisations 0005) ; ensuite tout se règle dans Administration > Rôles.

Pour un nouveau module : ajouter ses droits ici et ses routes dans garde.REGLES, rien d'autre.
"""

MODULES = [
    ("cockpit", "Cockpit opérationnel"),
    ("tableau", "Tableau de bord"),
    ("clients", "Clients"),
    ("devis", "Devis et production"),
    ("contrats", "Contrats et avenants"),
    ("encaissements", "Caisse et encaissements"),
    ("reversements", "Reversements aux compagnies"),
    ("commissions", "Commissions du cabinet"),
    ("apporteurs", "Apporteurs d'affaires"),
    ("sinistres", "Sinistres"),
    ("consommations", "Consommations santé"),
    ("rafas", "RAFAS - Régime autofinancé d'assurance santé"),
    ("approbations", "Dérogations et approbations"),
    ("imports", "Imports de fichiers"),
    ("crm", "Suivi commercial"),
    ("documents", "Documents (GED)"),
    ("archives", "Archives"),
    ("asaci", "Attestations ASACI"),
    ("reporting", "États et reporting"),
    ("tarifs", "Tarifs et barèmes"),
    ("parametrage", "Paramétrage"),
    ("users", "Utilisateurs"),
    ("roles", "Rôles et droits"),
    ("audit", "Journal d'audit"),
]

# (code, libellé, description, sensible, motif obligatoire à l'installation, séparation des tâches possible)
DROITS = [
    ("cockpit.view", "Consulter le cockpit opérationnel",
     "Écran d'accueil de l'espace Production ; chaque bloc ne s'affiche qu'avec son droit ci-dessous.",
     False, False, False),
    # Blocs du cockpit (demande du 2026-11-23 : « chaque bloc du cockpit et du tableau de bord visible par un utilisateur
    # qu'avec des droits ») : un droit par bloc, le serveur n'envoie pas les chiffres d'un bloc non accordé
    ("cockpit.chiffre_affaires", "Bloc « Chiffre d'affaires »",
     "Chiffre d'affaires du cabinet depuis le 1er janvier : composition, mois par mois, taux moyen, comparaison avec l'an dernier.",
     True, False, False),
    ("cockpit.percu", "Bloc « Perçu »", "Commissions et frais reçus par le cabinet depuis le 1er janvier, dont ce mois-ci.", True, False, False),
    ("cockpit.reste_a_percevoir", "Bloc « Reste à percevoir »",
     "Commissions pas encore reçues : en attente du reversement, à réclamer, réclamées non payées.", True, False, False),
    ("cockpit.commissions_listes", "Chiffre d'affaires dans les autres blocs",
     "Colonne chiffre d'affaires de la production par branche, commission en jeu des polices et des échéances, commission "
     "des derniers contrats émis.", True, False, False),
    ("cockpit.primes", "Bloc « Primes émises »", "Primes TTC émises depuis le 1er janvier et ce mois-ci, comparaison avec l'an dernier.",
     False, False, False),
    ("cockpit.polices", "Bloc « Polices en vigueur »",
     "Polices en vigueur, échéances dans les 30 jours, polices échues depuis moins de 30 jours.", False, False, False),
    ("cockpit.devis", "Bloc « Devis en cours »", "Devis encore valables, primes proposées, devis expirés.", False, False, False),
    ("cockpit.transformation", "Bloc « Transformation »", "Devis émis depuis le 1er janvier et part déjà confirmée en contrat.",
     False, False, False),
    ("cockpit.encaisse", "Bloc « Encaissé »", "Encaissements depuis le 1er janvier et ce mois-ci.", False, False, False),
    ("cockpit.reste_a_encaisser", "Bloc « Reste à encaisser »", "Quittances non soldées de l'exercice et des années antérieures.",
     False, False, False),
    ("cockpit.a_reverser", "Bloc « À reverser aux compagnies »", "Primes encaissées pas encore reversées aux compagnies.",
     False, False, False),
    ("cockpit.commissions", "Bloc « Commissions en attente »", "Commissions à réclamer et réclamées non payées.", False, False, False),
    ("cockpit.a_traiter", "Bloc « À traiter »",
     "Points en attente d'une action ; chaque point exige aussi le droit de consulter son module.", False, False, False),
    ("cockpit.branches", "Bloc « Production par branche »",
     "Actes et primes TTC émis par branche depuis le 1er janvier.", False, False, False),
    ("cockpit.echeances", "Bloc « Échéances à suivre »",
     "Polices échues ou à échoir, sans renouvellement enregistré. Liste de clients : exige aussi « Consulter les contrats ».",
     False, False, False),
    ("cockpit.derniers_devis", "Bloc « Derniers devis en cours »",
     "Liste de clients : exige aussi « Consulter les devis ».", False, False, False),
    ("cockpit.derniers_contrats", "Bloc « Derniers contrats émis »",
     "Polices et avenants les plus récents, avec leur règlement. Liste de clients : exige aussi « Consulter les contrats ».",
     False, False, False),

    # Blocs du tableau de bord (écran ouvert par « Consulter les états »)
    ("tableau.chiffre_affaires", "Bloc « Chiffre d'affaires »",
     "Chiffre d'affaires de l'exercice : composition, taux moyen, part des primes, comparaison avec l'exercice précédent.",
     True, False, False),
    ("tableau.percu", "Bloc « Perçu »", "Sommes reçues par le cabinet sur l'exercice, par origine.", True, False, False),
    ("tableau.reste_a_percevoir", "Bloc « Reste à percevoir »",
     "Commissions de l'exercice pas encore reçues : en attente du reversement, à réclamer, réclamées non payées.", True, False, False),
    ("tableau.ca_par_mois", "Bloc « Chiffre d'affaires par mois »", "Graphique du chiffre d'affaires et du perçu, mois par mois.",
     True, False, False),
    ("tableau.ca_listes", "Chiffre d'affaires dans les autres blocs",
     "Colonnes chiffre d'affaires et perçu de la synthèse par branche et du tableau par compagnie ; sans ce droit, ces blocs "
     "ne montrent que les primes et les encaissements.", True, False, False),
    ("tableau.primes", "Bloc « Primes émises »", "Primes TTC émises sur l'exercice, actes, comparaison avec l'exercice précédent.",
     False, False, False),
    ("tableau.encaisse", "Bloc « Encaissé »", "Encaissements de l'exercice, primes de l'exercice et des exercices antérieurs.",
     False, False, False),
    ("tableau.recouvrement", "Bloc « Recouvrement des émissions »", "Part des primes émises déjà encaissée, reste à encaisser.",
     False, False, False),
    ("tableau.primes_par_mois", "Bloc « Primes et encaissements par mois »", "", False, False, False),
    ("tableau.alertes", "Bloc « Alertes de conformité »",
     "Reversements en retard, chèques échus, primes impayées, commissions, dérogations ; chaque alerte exige aussi le droit "
     "de consulter son module.", False, False, False),
    ("tableau.compagnies", "Bloc « Par compagnie »", "Primes TTC et actes par compagnie.", False, False, False),
    ("tableau.branches", "Bloc « Synthèse par branche »",
     "Actes, primes, encaissements et recouvrement par branche, avec la catégorie CIMA.", False, False, False),

    ("clients.view", "Consulter les clients", "Liste, recherche, fiche et dossier 360° des clients.", False, False, False),
    ("clients.create", "Créer un client", "", False, False, False),
    ("clients.update", "Modifier un client", "Identité, coordonnées, qualité : valeurs avant / après journalisées.", True, False, False),
    ("clients.delete", "Supprimer un client", "", True, True, False),
    ("clients.merge", "Regrouper des clients", "Fusion de fiches en doublon.", True, True, False),

    ("devis.view", "Consulter les devis", "Registre, fiche devis, impressions, calculs de prime sans enregistrement.", False, False, False),
    ("devis.create", "Créer un devis", "Toutes branches, brouillons compris.", False, False, False),
    ("devis.update", "Modifier un devis", "« Modifier », garanties, véhicules, assurés, pièces jointes.", False, False, False),
    ("devis.validate", "Transformer un devis en contrat", "Confirmation du devis : police et quittance émises.", True, False, True),
    ("devis.cancel", "Archiver un devis", "Archivage et abandon d'une saisie. La restauration est un droit à part (Archives).", True, False, False),
    ("devis.delete", "Supprimer un devis", "Suppression définitive d'un devis non confirmé et de sa saisie.", True, True, False),
    ("devis.primes", "Imposer ou corriger les primes", "Primes imposées, correction des primes, répartition des garanties.", True, True, False),
    ("devis.derogation_age", "Déroger à la limite d'âge",
     "Admettre un assuré au-delà des limites d'âge des conditions (Santé MINENE : adulte, enfant), en saisie ou à l'import.",
     True, False, False),

    ("contrats.view", "Consulter les contrats", "Portefeuille, quittances, garanties, véhicules, certificats.", False, False, False),
    ("contrats.update", "Modifier un contrat", "Garanties du contrat, pièces jointes.", True, False, False),
    ("contrats.admin_update", "Modifier toutes les informations d’un contrat",
     "Écran d’administration : contrat, risques/véhicules et garanties ; justification obligatoire et journal avant/après.", True, True, False),
    ("contrats.avenant", "Établir un avenant", "Renouvellement, incorporation, retrait, changement d'immatriculation, prise d'effet.", True, False, False),
    ("contrats.cancel", "Annuler un contrat", "Avenant d'annulation ou de résiliation.", True, True, False),
    ("contrats.delete", "Supprimer un contrat",
     "Suppression définitive d'un contrat sans encaissement et de sa quittance ; son devis revient en attente.", True, True, False),
    ("contrats.reprise", "Saisir les affaires antérieures",
     "Reprise des contrats et quittances des années passées absents de LE PHARE : saisie, import Excel, suppression d'une "
     "reprise erronée par son auteur.", False, False, False),

    ("encaissements.view", "Consulter la caisse", "Contrats à encaisser, encaissements, reçus, chèques.", False, False, False),
    ("encaissements.create", "Encaisser une prime", "Encaissement, échéancier de chèques, paiement mobile, demande d'annulation.", False, False, False),
    ("encaissements.cancel", "Annuler un encaissement", "Annulation d'encaissement, décaissement ou suppression d'un chèque.", True, True, False),
    ("encaissements.auteur", "Voir qui a encaissé", "Nom de l'utilisateur qui a saisi chaque règlement, dans la fiche du contrat.", False, False, False),

    ("reversements.view", "Consulter les reversements", "", False, False, False),
    ("reversements.create", "Préparer un reversement", "", False, False, False),
    ("reversements.validate", "Valider un reversement", "", True, False, False),

    ("commissions.view", "Consulter les commissions", "États, tableaux de bord, affaires éligibles.", False, False, False),
    ("commissions.create", "Réclamer une commission", "Réclamations et préparation des paiements de commission.", False, False, False),
    ("commissions.validate", "Encaisser une commission", "Encaissement et validation des paiements de commission.", True, False, False),
    ("commissions.cancel", "Annuler une commission", "", True, True, False),

    ("apporteurs.view", "Consulter les apporteurs et leurs commissions", "Fiches, apporteurs d'une affaire, commissions et règlements.", False, False, False),
    ("apporteurs.update", "Gérer les apporteurs", "Création, modification, désactivation d'un apporteur.", False, False, False),
    ("apporteurs.rattacher", "Rattacher un apporteur à une affaire", "Ajout d'un apporteur sur un devis ou un contrat, taux convenu, retrait.", False, False, False),
    ("apporteurs.payer", "Régler les commissions d'apporteurs", "Enregistrement d'un règlement versé à un apporteur.", True, False, False),
    ("apporteurs.cancel", "Annuler une commission ou un règlement d'apporteur", "", True, True, False),

    ("sinistres.view", "Consulter les sinistres", "", False, False, False),
    ("sinistres.create", "Déclarer un sinistre", "", False, False, False),
    ("sinistres.update", "Instruire un sinistre", "Pièces, demande d'accord, suivi du dossier.", False, False, False),
    ("sinistres.settle", "Régler un sinistre", "Règlement sous plafond de délégation et émission de la quittance subrogative.",
     True, False, False),

    ("consommations.view", "Consulter les consommations santé",
     "Relevés du gestionnaire santé : droits, prestations, plafonds et soldes par assuré, statistiques par entreprise. Données de santé.",
     True, False, False),
    ("consommations.import", "Importer les relevés du gestionnaire santé", "Relevés de prestations et effectifs reçus du gestionnaire (MCI CARE).",
     True, False, False),
    ("consommations.fraude", "Détecter et instruire les anomalies santé",
     "Signaux d'anomalie par bénéficiaire et décision d'instruction ; aucune décision n'est automatique.", True, False, False),

    ("rafas.view", "Consulter le RAFAS",
     "Conventions des régimes autofinancés, fonds, effectifs, dépenses de santé et contrôles du gestionnaire. Données de santé.", True, False, False),
    ("rafas.manage", "Gérer les conventions RAFAS et leur fonds",
     "Conventions, exercices et collèges, appels de fonds, versements du souscripteur, honoraires et commission.", True, False, False),
    ("rafas.import", "Importer les fichiers du gestionnaire RAFAS", "Effectifs et relevés de prestations (VITALIS SANTE).", True, False, False),

    ("approbations.view", "Consulter les demandes d'autorisation", "", False, False, False),
    ("approbations.decider", "Approuver ou rejeter une demande", "Décisions sur les demandes et dérogations accordées.", True, False, True),

    ("imports.excel", "Importer un fichier Excel", "Assurés IA, affiliés Santé, véhicules d'une flotte.", True, False, False),
    ("imports.guce", "Importer un bordereau GUCE", "Transport : analyse et import des certificats.", True, False, False),

    ("crm.view", "Consulter le suivi commercial", "", False, False, False),
    ("crm.update", "Mettre à jour le suivi commercial", "", False, False, False),

    ("documents.view", "Consulter les documents", "", False, False, False),
    ("documents.update", "Classer ou retirer des documents", "", False, False, False),

    ("archives.restore", "Restaurer un élément archivé", "Bouton « Restaurer » de la page Archives : clients, devis, contrats et sinistres.", True, False, False),

    ("asaci.attestations", "Gérer les attestations ASACI", "Demande, suivi et mise à jour des attestations.", False, False, False),

    ("reporting.view", "Consulter les états", "États CIMA, états de gestion, bordereaux d'émission.", False, False, False),

    ("tarifs.view", "Consulter les tarifs et barèmes", "Écrans d'administration des barèmes.", False, False, False),
    ("tarifs.update", "Modifier les tarifs et barèmes", "Offres, garanties, taxes, accessoires, commissions, réductions, grilles, réglages Dommages.", True, False, False),

    ("parametrage.update", "Paramétrage général", "Cabinet, compagnies, produits, règles de gestion, listes de référence, conventions.", True, False, False),
    ("parametrage.technique", "Paramétrage technique", "Tables internes, numérotation, tâches planifiées et menus de l'application.", True, False, False),

    ("users.view", "Consulter les utilisateurs", "", False, False, False),
    ("users.create", "Créer un utilisateur", "", True, False, False),
    ("users.update", "Modifier un utilisateur", "Identité et rôles attribués.", True, False, False),
    ("users.disable", "Activer ou désactiver un utilisateur", "", True, False, False),
    ("users.password", "Réinitialiser un mot de passe", "", True, False, False),

    ("roles.view", "Consulter les rôles et droits", "", False, False, False),
    ("roles.manage", "Gérer les rôles et leurs droits", "Création, modification, activation des rôles et réglage des droits.", True, False, False),

    ("audit.view", "Consulter le journal d'audit", "", False, False, False),
    ("audit.export", "Exporter le journal d'audit", "", False, False, False),
]

TOUS = [d[0] for d in DROITS]
# Blocs du cockpit et du tableau de bord : tous accordés à l'installation, à retirer ensuite rôle par rôle
BLOCS_COCKPIT = [d[0] for d in DROITS if d[0].startswith("cockpit.") and d[0] != "cockpit.view"]
BLOCS_TABLEAU = [d[0] for d in DROITS if d[0].startswith("tableau.")]
BLOCS_ECRANS = BLOCS_COCKPIT + BLOCS_TABLEAU
_VUES_METIER = [
    "clients.view", "devis.view", "contrats.view", "encaissements.view", "reversements.view", "commissions.view", "apporteurs.view",
    "sinistres.view", "approbations.view", "crm.view", "documents.view", "reporting.view",
] + BLOCS_ECRANS

# (code, libellé, description, droits) : composition proposée à l'installation, modifiable ensuite
ROLES_INITIAUX = [
    ("ADMIN_TECH", "Administrateur technique", "Accès complet pour administrer et maintenir l'application.", TOUS),
    ("DEVELOPPEUR", "Développeur", "Accès complet pour la maintenance de l'application.", TOUS),
    ("DIRECTION", "Direction", "Vision complète de l'activité (devis, contrats, clients, caisse, états, journal) "
     "et décision sur les demandes d'autorisation ; pas de paramétrage technique.",
     _VUES_METIER + ["approbations.decider", "audit.view", "users.view", "tarifs.view", "encaissements.auteur"]),
    ("RESPONSABLE", "Responsable", "Contrôle et validation des opérations, sans modifier les tarifs.",
     _VUES_METIER + [
         "devis.validate", "devis.cancel", "devis.primes", "contrats.update", "contrats.avenant", "contrats.cancel",
         "encaissements.cancel", "reversements.create", "reversements.validate", "commissions.validate",
         "commissions.cancel", "apporteurs.rattacher", "apporteurs.payer", "apporteurs.cancel", "sinistres.settle",
         "approbations.decider", "crm.update", "documents.update",
         "audit.view", "tarifs.view", "encaissements.auteur",
     ]),
    ("GESTIONNAIRE", "Gestionnaire", "Production complète (clients, devis, contrats, caisse, sinistres, imports) "
     "sans paramétrage ; attribué aux comptes importés non administrateurs.",
     _VUES_METIER + [
         "clients.create", "clients.update", "devis.create", "devis.update", "devis.validate", "devis.cancel",
         "devis.primes", "contrats.update", "contrats.avenant", "encaissements.create", "reversements.create",
         "commissions.create", "apporteurs.rattacher", "sinistres.create", "sinistres.update", "imports.excel", "imports.guce",
         "crm.update", "documents.update", "asaci.attestations",
     ]),
    ("AGENT_SAISIE", "Agent de saisie", "Saisie des clients et des devis ; ne valide pas et ne touche pas aux primes.",
     ["clients.view", "clients.create", "clients.update", "devis.view", "devis.create", "devis.update",
      "contrats.view", "encaissements.view", "documents.view", "documents.update", "crm.view"] + BLOCS_ECRANS),
    ("AGENT_VALIDATION", "Agent de validation", "Contrôle et transformation des devis en contrats.",
     ["clients.view", "devis.view", "devis.validate", "contrats.view", "approbations.view", "documents.view"] + BLOCS_ECRANS),
    ("CONSULTATION", "Consultation", "Lecture seule de l'activité.",
     ["clients.view", "devis.view", "contrats.view", "encaissements.view", "sinistres.view", "reporting.view",
      "documents.view"] + BLOCS_ECRANS),
]


def synchroniser_droits(Droit):
    """Crée ou met à jour le catalogue en base. Les réglages faits dans l'admin (motif obligatoire,
    séparation des tâches) sont conservés pour un droit existant. Renvoie les codes créés."""
    libelles_modules = dict(MODULES)
    ordre_modules = {code: i for i, (code, _) in enumerate(MODULES)}
    crees = []
    for i, (code, libelle, description, sensible, motif, separation) in enumerate(DROITS):
        module = code.split(".")[0]
        valeurs = dict(
            module=module,
            module_libelle=libelles_modules.get(module, module),
            action=code.split(".", 1)[1],
            libelle=libelle,
            description=description,
            sensible=sensible,
            separation_possible=separation,
            ordre=ordre_modules.get(module, 99) * 100 + i,
        )
        droit, cree = Droit.objects.get_or_create(code=code, defaults={**valeurs, "motif_obligatoire": motif})
        if cree:
            crees.append(code)
        else:
            modifie = False
            for cle, valeur in valeurs.items():
                if getattr(droit, cle) != valeur:
                    setattr(droit, cle, valeur)
                    modifie = True
            if not separation and droit.separation_taches:
                droit.separation_taches = False
                modifie = True
            if modifie:
                droit.save()
    return crees
