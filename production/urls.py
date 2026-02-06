from django.urls import include, path

from rest_framework import routers

from .views import DevisViewSet, DevisDetGarantieViewSet
from .views import TarifEcranViewSet, ContratViewSet
from .views import (
    ContratDetGarantieViewSet,
    QuittancePropositionView,
    QuittanceContratView,
    AyantDroitIaView,
    AyantDroitMineneView,
    ExtendedQuotationInfoView,
    QuittanceViewSet,
    DetailQuittanceViewSet,
    EncaissementViewSet,
    DetailEncaissementViewSet,
    NumeroViewSet,
    GarantieContratView,
    ListeVehiculeContratView,
    ListeVehiculeDevisView,
    ReversementCompagnieViewSet,
    DetailReversementViewSet,
    ListeContratReversementView,
    InfoEncaissementView,
    InfoVehiculeView,
    InfoReversementView,
    DetailEncaissementListView,
    DetailReversementListView,
    ContratDetailInfoView,
    DevisDetailInfoView,
    ExtendedQuotationInfoRechercheView,
    AssureIaInfoView,
    AssureIaParDevisView,
    AssureIaParContratView,
    ReductionFlotteDevisView,
    GarantieSouscriteContratView,
    GarantieSouscriteDevisView,
    EncaissementRechercheView,
    ImportationAssureIaViewSet,
    ImportationFichierGUCEViewSet,
    CertificatTransportView,
    ListeContratClientView,
    CorrectionDevisViewSet,
    PrimeUpdateAPIView,
    DevisClientView,
    ConsolidationDevisView,
    ContractListView,
    ReversementCompagnieNonValideViewSet,
    ResumeFinancierDevisView,
    CheckChequeStatusView, 
    ChequeListView, 
    ChequeDetailOperationsView,
)
from .importation_views import ImportAssuresAPIView, VerifierFichierAPIView, ImportsHistoriqueListAPIView, ImportsHistoriqueDetailAPIView, StatistiquesImportsAPIView
from .views import (
    create_contract,
    create_quotation,
    creer_ayant_droit_ia,
    create_quotation_voyage,
    create_quotation_ia,
    create_quotation_mrh,
    create_quotation_tousrisquesinfo,
    create_quotation_rc,
    create_quotation_globaledebanque,
    finalize_quotation_flotte,
    quote_archival,
    car_input_cancelation,
    collect_premium,
    #cancel_premium_collection,
    get_contracts_for_pc,
    remit_premium,
    validate_premium_remittance,
    create_insured_ia,
    change_plate_number,
    modify_policy,
    quote_unarchival,
)

from .views import UsageHabitationViewSet, SousGarantieMRHViewSet, OptionViewSet, DevisMRHViewSet, SousGarantieForfaitViewSet, CalculMaisonView, MaisonViewSet, ValidateParametersView, RecalculerDevisView

from .views import (
    ImposerPrimeMaisonView,
    ImposerPrimeDevisView,
    LeverImpositionView,
    HistoriqueImpositionsView,
    StatutImpositionView,
    DetailMaisonView,
)
# Créer le router pour les ViewSets
router = routers.DefaultRouter()

# Enregistrer les ViewSets de référence (lecture seule)
router.register(r'mrh/usages', UsageHabitationViewSet, basename='usage')
router.register(r'mrh/garanties', SousGarantieMRHViewSet, basename='garantie')
router.register(r'mrh/garanties-forfait', SousGarantieForfaitViewSet, basename='garantie-forfait')
router.register(r'mrh/options', OptionViewSet, basename='option')
# Enregistrer les ViewSets de gestion (avec actions personnalisées)
router.register(r'mrh/devis', DevisMRHViewSet, basename='devis-mrh')


router.register(r"devis", DevisViewSet)
# router.register(r"devisdetail", DevisDetailViewSet)
router.register(r"devisdetgarantie", DevisDetGarantieViewSet)
router.register(r"tarifecran", TarifEcranViewSet)
router.register(r"contrat", ContratViewSet)
# router.register(r"contratdetail", ContratDetailViewSet)
router.register(r"contratdetgarantie", ContratDetGarantieViewSet)
router.register(r"quittance", QuittanceViewSet)
router.register(r"detailquittance", DetailQuittanceViewSet)
router.register(r"encaissement", EncaissementViewSet, basename="encaissement")
router.register(r"detailencaissement", DetailEncaissementViewSet)
router.register(r"reversement", ReversementCompagnieViewSet, basename="reversement")
router.register(r"reversementnonvalide", ReversementCompagnieNonValideViewSet, basename="reversement_non_valide")
router.register(r"detailreversement", DetailReversementViewSet)
router.register(r"numero", NumeroViewSet)
# router.register(
#     r"importationassureia",
#     ImportationAssureIaViewSet,
#     basename="importationassureia",
# )

router.register(
    r"importationfichierguce",
    ImportationFichierGUCEViewSet,
    basename="importationfichierguce",
)
router.register(
    r"correctiondevis",
    CorrectionDevisViewSet,
    basename="correctiondevis",
)

urlpatterns = [
    path("", include(router.urls)),
    path(r"enregistrementdevis", create_quotation, name="enregistrement_devis_auto"),
    path(
        r"finalisationdevisauto",
        finalize_quotation_flotte,
        name="finalisation_devis_auto",
    ),
    path(
        r"finalisationdevisia",
        finalize_quotation_flotte,
        name="finalisation_devis_ia",
    ),
    path(
        r"annulationsaisiedevis",
        quote_archival,
        name="annulation_saisie_devis",
    ),
    path(
        r"archivagedevis",
        quote_archival,
        name="archivage_devis",
    ),
    path(
        r"desarchivagedevis",
        quote_unarchival,
        name="desarchivage_devis",
    ),
    path(
        r"consolidationdevis/",
        ConsolidationDevisView.as_view(),
        name="consolidation_devis",
    ),
    path(
        r"annulationsaisievehicule",
        car_input_cancelation,
        name="annulation_saisie_vehicule",
    ),
    path(r"enregistrementassureia", create_insured_ia, name="enregistrement_assure_ia"),
    path(r"enregistrementdevisia", create_quotation_ia, name="enregistrement_devis_ia"),
    path(
        r"enregistrementdevisvoyage",
        create_quotation_voyage,
        name="enregistrement_devis_voyage",
    ),
    path(
        r"enregistrementdevismrh",
        create_quotation_mrh,
        name="enregistrement_devis_mrh",
    ),
    path(
        r"enregistrementdevistousrisquesinfo",
        create_quotation_tousrisquesinfo,
        name="enregistrement_devis_tousrisquesinfo",
    ),
    path(
        r"enregistrementdevisrc",
        create_quotation_rc,
        name="enregistrement_devis_rc",
    ),
    path(
        r"enregistrementdevisglobaledebanque",
        create_quotation_globaledebanque,
        name="enregistrement_devis_globaledebanque",
    ),
    path(r"saisieayantdroitia", creer_ayant_droit_ia, name="saisie_ayant_droit_devis"),
    path(r"confirmationdevis", create_contract, name="confirmation_devis"),
    path(
        r"assureiainfo/<int:iddevis>",
        AssureIaInfoView.as_view(),
        name="assure_ia_info",
    ),
    path(
        r"assureiapardevis/<int:iddevis>",
        AssureIaParDevisView.as_view(),
        name="assure_ia_par_devis",
    ),
    path(
        r"assureiaparcontrat/<int:idcontrat>",
        AssureIaParContratView.as_view(),
        name="assure_ia_par_contrat",
    ),
    path(
        r"devisdetail/<int:iddevis>",
        DevisDetailInfoView.as_view(),
        name="devis_detail_info",
    ),
    path(
        r"contratdetail/<int:idcontrat>",
        ContratDetailInfoView.as_view(),
        name="contrat_detail_info",
    ),
    path(
        r"quittanceproposition/<int:iddevis>",
        QuittancePropositionView.as_view(),
        name="quittance_proposition",
    ),
    path(
        r"quittancecontrat/<int:idcontrat>",
        QuittanceContratView.as_view(),
        name="quittance_contrat",
    ),
    path(
        r"garantiecontrat/<int:idcontrat>",
        GarantieContratView.as_view(),
        name="garantie_contrat",
    ),
    path(
        r"listevehiculecontrat/<int:idcontrat>",
        ListeVehiculeContratView.as_view(),
        name="liste_vehicule_contrat",
    ),
    path(
        r"listevehiculedevis/<int:iddevis>",
        ListeVehiculeDevisView.as_view(),
        name="liste_vehicule_devis",
    ),
    path(
        r"garantiesouscritecontrat/<int:idcontrat>",
        GarantieSouscriteContratView.as_view(),
        name="garantie_souscrite_contrat",
    ),
    path(
        r"garantiesouscritedevis/<int:iddevis>",
        GarantieSouscriteDevisView.as_view(),
        name="garantie_souscrite_devis",
    ),
    path(
        r"contratpourencaissement/",
        get_contracts_for_pc,
        name="contrat_pour_encaissement",
    ),
    path(
        r"contratpourreversement/<int:idcompagnie>",
        ListeContratReversementView.as_view(),
        name="contrat_pour_reversement",
    ),
    path(
        r"infodevis/<int:idproduit>",
        ExtendedQuotationInfoView.as_view(),
        name="info_devis_cent",
    ),
    path(
        r"infodevisrecherche/<slug:champrecherche>",
        ExtendedQuotationInfoRechercheView.as_view(),
        name="info_devis_recherche",
    ),
    path(
        r"ayantdroitia/<int:idassure>",
        AyantDroitIaView.as_view(),
        name="ayant_droit_par_assure",
    ),
    path(
        r"ayantdroitminene/<slug:numeropolice>",
        AyantDroitMineneView.as_view(),
        name="ayant_droit_minene",
    ),
    # path(
    #     r"pythonlogrecord",
    #     LogRecordView.as_view(),
    #     name="python_log_record",
    # ),
    path(
        r"enregistrementencaissement",
        collect_premium,
        name="enregistrement_encaissement",
    ),
    # path(
    #     r"annulationencaissement",
    #     cancel_premium_collection,
    #     name="annulation_encaissement",
    # ),
    path(
        r"listecontratclient/",
        ListeContratClientView.as_view(),
        name="liste_contrat_client",
    ),
    path(
        r"enregistrementreversement",
        remit_premium,
        name="enregistrement_reversement",
    ),
    path(
        r"validationreversement",
        validate_premium_remittance,
        name="validation_reversement",
    ),
    path(
        r"infoencaissement/<int:iddetailencaissement>",
        InfoEncaissementView.as_view(),
        name="info_encaissement",
    ),
    path(
        r"encaissementrecherche/",
        EncaissementRechercheView.as_view(),
        name="encaissement_recherche",
    ),
    path(
        r"certificattransport/",
        CertificatTransportView.as_view(),
        name="certificat_transport",
    ),
    path(
        r"devisclient/",
        DevisClientView.as_view(),
        name="devis_client",
    ),
    path(
        r"infovehicule/<int:idcontrat>",
        InfoVehiculeView.as_view(),
        name="info_vehicule",
    ),
    path(
        r"inforeversement/<int:idreversement>",
        InfoReversementView.as_view(),
        name="info_reversement",
    ),
    path(
        r"listedetailencaissement/<int:idencaissement>",
        DetailEncaissementListView.as_view(),
        name="liste_detail_encaissement",
    ),
    path(
        r"listedetailreversement/<int:idreversement>",
        DetailReversementListView.as_view(),
        name="liste_detail_reversement",
    ),
    path(
        r"reductionflottedevis/<int:iddevis>",
        ReductionFlotteDevisView.as_view(),
        name="reduction_flotte_devis",
    ),
    path(
        r"avenant/changementimmatriculation",
        change_plate_number,
        name="changement_immatriculation",
    ),
    path(
        r"avenant/initiationmouvement",
        modify_policy,
        name="avenant_initiation_mouvement",
    ),
    path(
        r"avenant/annulation",
        modify_policy,
        name="avenant_annulation",
    ),
    path(
        r"avenant/renouvellement",
        modify_policy,
        name="avenant_renouvellement",
    ),
    path(
        r"avenant/modificationpriseeffet",
        modify_policy,
        name="avenant_modification_prise_effet",
    ),
    path(
        r"avenant/incorporation",
        modify_policy,
        name="avenant_incorporation",
    ),
    path(
        r"avenant/retrait",
        modify_policy,
        name="avenant_retrait",
    ),
    path("majrecapprimes/", PrimeUpdateAPIView.as_view(), name="maj_recap_primes"),
    path("listecontratperiode/", ContractListView.as_view(), name="liste_contrat_periode"),
    
    # ========================================================================
    # SECTION 1 : ENDPOINTS DE RÉFÉRENCE (complément aux ViewSets)
    # ========================================================================
    # Les routes suivantes sont automatiquement générées par le router :
    # GET /api/mrh/usages/ - Liste des usages
    # GET /api/mrh/usages/{code}/ - Détail d'un usage
    # GET /api/mrh/usages/{code}/parametres/ - Paramètres de calcul
    # GET /api/mrh/usages/{code}/garanties/ - Garanties pour un usage
    # GET /api/mrh/usages/{code}/options/ - Options pour un usage
    #
    # GET /api/mrh/garanties/ - Liste des garanties
    # GET /api/mrh/garanties/{code}/ - Détail d'une garantie
    #
    # GET /api/mrh/garanties-forfait/ - Garanties à forfait
    #
    # GET /api/mrh/options/ - Liste des options
    # GET /api/mrh/options/{code}/ - Détail d'une option
    
    # ========================================================================
    # SECTION 2 : ENDPOINT DE CALCUL (SANS ENREGISTREMENT)
    # ========================================================================
    path(
        'mrh/calcul/maison/',
        CalculMaisonView.as_view(),
        name='calcul-maison'
    ),
    # POST /api/mrh/calcul/maison/ - Calculer prime sans enregistrer
    
    # ========================================================================
    # SECTION 3 : ENDPOINTS DE GESTION DE DEVIS
    # ========================================================================
    # Les routes suivantes sont automatiquement générées par le router :
    # POST /api/mrh/devis/ - Créer un devis vide
    # GET /api/mrh/devis/ - Lister les devis
    # GET /api/mrh/devis/{id}/ - Récupérer un devis
    # DELETE /api/mrh/devis/{id}/ - Supprimer un devis
    
    # ========================================================================
    # SECTION 4 : ENDPOINTS DE GESTION DE MAISONS
    # ========================================================================
    path(
        'mrh/devis/<int:devis_id>/maisons/',
        MaisonViewSet.as_view({'post': 'create'}),
        name='devis-maison-create'
    ),
    # POST /api/mrh/devis/{devis_id}/maisons/ - Ajouter une maison
    
    path( 'mrh/devis/<int:devis_id>/maisons/<int:pk>/',
         MaisonViewSet.as_view({'put': 'update', 'delete': 'destroy'}),
         name='devis-maison'
    ),
    # DELETE /api/mrh/devis/{devis_id}/maisons/{pk}/ - Supprimer une maison
    # PUT /api/mrh/devis/{devis_id}/maisons/{pk}/ - Modifier une maison
    
    # ========================================================================
    # SECTION 5 : ENDPOINTS UTILITAIRES
    # ========================================================================
    path(
        'mrh/validate-parameters/',
        ValidateParametersView.as_view(),
        name='validate-parameters'
    ),
    # POST /api/mrh/validate-parameters/ - Valider paramètres
    
    path(
        'mrh/devis/<int:devis_id>/recalculer/',
        RecalculerDevisView.as_view(),
        name='devis-recalculer'
    ),
    # POST /api/mrh/devis/{devis_id}/recalculer/ - Recalculer totaux
    
     path(
        'mrh/devis/<int:devis_id>/resume-financier/',
        ResumeFinancierDevisView.as_view(),
        name='devis-resume-financier'
    ),
    
    # ========================================================================
    # IMPOSITION DE PRIME MAISON
    # ========================================================================
    
    path(
        'mrh/devis/<int:devis_id>/maisons/<int:maison_id>/imposer-prime/',
        ImposerPrimeMaisonView.as_view(),
        name='mrh-imposer-prime-maison'
    ),
    # POST /api/mrh/devis/123/maisons/456/imposer-prime/
    # Impose la prime d'une maison
    
    path(
        'mrh/devis/<int:devis_id>/maisons/<int:maison_id>/imposition-prime/',
        LeverImpositionView.as_view(),
        name='mrh-lever-imposition-maison'
    ),
    # DELETE /api/mrh/devis/123/maisons/456/imposition-prime/
    # Lève l'imposition d'une maison
    
    # ========================================================================
    # IMPOSITION DE PRIME DEVIS
    # ========================================================================
    
    path(
        'mrh/devis/<int:devis_id>/imposer-prime/',
        ImposerPrimeDevisView.as_view(),
        name='mrh-imposer-prime-devis'
    ),
    # POST /api/mrh/devis/123/imposer-prime/
    # Impose la prime globale du devis
    
    path(
        'mrh/devis/<int:devis_id>/imposition-prime/',
        LeverImpositionView.as_view(),
        name='mrh-lever-imposition-devis'
    ),
    # DELETE /api/mrh/devis/123/imposition-prime/
    # Lève l'imposition du devis
    
    # ========================================================================
    # HISTORIQUE ET STATUT
    # ========================================================================
    
    path(
        'mrh/devis/<int:devis_id>/impositions/',
        HistoriqueImpositionsView.as_view(),
        name='mrh-historique-impositions-devis'
    ),
    # GET /api/mrh/devis/123/impositions/
    # Historique des impositions du devis
    
    path(
        'mrh/devis/<int:devis_id>/maisons/<int:maison_id>/impositions/',
        HistoriqueImpositionsView.as_view(),
        name='mrh-historique-impositions-maison'
    ),
    # GET /api/mrh/devis/123/maisons/456/impositions/
    # Historique des impositions de la maison
    
    path(
        'mrh/devis/<int:devis_id>/statut-imposition/',
        StatutImpositionView.as_view(),
        name='mrh-statut-imposition-devis'
    ),
    # GET /api/mrh/devis/123/statut-imposition/
    # Statut d'imposition du devis
    
    path(
        'mrh/devis/<int:devis_id>/maisons/<int:maison_id>/statut-imposition/',
        StatutImpositionView.as_view(),
        name='mrh-statut-imposition-maison'
    ),
    # GET /api/mrh/devis/123/maisons/456/statut-imposition/
    # Statut d'imposition de la maison
    
    # ====================================================================
    # CONSULTATION MAISON
    # ====================================================================
    
    # Détail complet d'une maison (NOUVEAU)
    path(
        'mrh/devis/<int:devis_id>/maisons/<int:maison_id>/details/',
        DetailMaisonView.as_view(),
        name='mrh-detail-maison'
    ),
    # GET /api/mrh/devis/123/maisons/456/details/
     
    # Endpoint de vérification d'existence (Autocomplete)
    path('cheques/statut/', CheckChequeStatusView.as_view(), name='cheque-statut'),
    
    # Endpoint 1 : Liste filtrée des chèques
    path('cheques/', ChequeListView.as_view(), name='cheque-liste'),
    
    # Endpoint 2 : Détails et opérations d'un chèque
    path('cheques/<int:id_cheque>/operations/', ChequeDetailOperationsView.as_view(), name='cheque-operations'),
    
    # ─── Import d'Assurés ───
    path(
        'importationassureia/',
        ImportAssuresAPIView.as_view(),
        name='import_assures'
    ),
    
    # ─── Vérifier un Fichier ───
    path(
        'verifier-fichier/',
        VerifierFichierAPIView.as_view(),
        name='verifier_fichier'
    ),
    
    # ─── Historique des Imports ───
    path(
        'imports-historique/',
        ImportsHistoriqueListAPIView.as_view(),
        name='imports_historique_list'
    ),
    
    path(
        'imports-historique/<int:pk>/',
        ImportsHistoriqueDetailAPIView.as_view(),
        name='imports_historique_detail'
    ),
    
    # ─── Statistiques ───
    path(
        'imports-statistiques/',
        StatistiquesImportsAPIView.as_view(),
        name='imports_statistiques'
    ),
    
]



"""
Configuration des URLs pour l'API MRH
Multi-Risques Habitation - NSIA

Organisation des routes :
/api/mrh/usages/ - Usages habitation (référence)
/api/mrh/garanties/ - Garanties MRH (référence)
/api/mrh/options/ - Options disponibles (référence)
/api/mrh/calcul/ - Calcul de prime sans enregistrement
/api/mrh/devis/ - Gestion des devis
/api/mrh/devis/{id}/maisons/ - Gestion des maisons dans un devis
"""

"""
RÉSUMÉ DES ROUTES DISPONIBLES
==============================

RÉFÉRENCE (Lecture seule)
--------------------------
GET    /api/mrh/usages/                          Liste des usages habitation
GET    /api/mrh/usages/{code}/                   Détail d'un usage
GET    /api/mrh/usages/{code}/parametres/        Paramètres de calcul
GET    /api/mrh/usages/{code}/garanties/         Sous-Garanties (obligatoires + optionnelles)
GET    /api/mrh/usages/{code}/options/           Options applicables

GET    /api/mrh/garanties/                       Liste des garanties MRH
GET    /api/mrh/garanties/{code}/                Détail d'une garantie

GET    /api/mrh/garanties-forfait/               Garanties optionnelles à forfait

GET    /api/mrh/options/                         Liste des options
GET    /api/mrh/options/{code}/                  Détail d'une option

CALCUL (Sans enregistrement)
-----------------------------
POST   /api/mrh/calcul/maison/                   Calculer prime d'une maison

DEVIS (Gestion)
---------------
POST   /api/mrh/devis/                           Créer un devis vide
GET    /api/mrh/devis/                           Lister les devis
GET    /api/mrh/devis/{id}/                      Récupérer un devis
DELETE /api/mrh/devis/{id}/                      Supprimer un devis

MAISONS (Gestion)
-----------------
POST   /api/mrh/devis/{id}/maisons/              Ajouter une maison au devis
DELETE /api/mrh/devis/{id}/maisons/{maison_id}/  Supprimer une maison

UTILITAIRES
-----------
POST   /api/mrh/validate-parameters/             Valider paramètres sans calculer
POST   /api/mrh/devis/{id}/recalculer/           Recalculer les totaux du devis


EXEMPLES D'UTILISATION
======================

1. Calculer une prime (sans enregistrer)
   POST /api/mrh/calcul/maison/
   {
       "code_usage": "proprietaire_occupant_total",
       "valeur_batiment": 50000000,
       "valeur_contenu": 10000000,
       "options": [{"code_option": "presence_gardien"}],
       "sous_garanties_optionnelles": [{"code_garantie": "RC_MEMBRE"}]
   }

2. Créer un devis complet
   a) POST /api/mrh/devis/
      {
          "idintermediaire": 1,
          "idcompagnie": 2,
          "idproduit": 4,
          "idtarif":81,
          "idoffre": 10,
          "idclient": 123,
          "dateeffet": "2024-01-01T00:00:00Z"
      }
      → Retourne: {"devis_id": 456}
   
   b) POST /api/mrh/devis/456/maisons/
      {
          "maison": {
              "code_usage": "proprietaire_occupant_total",
              "valeur_batiment": 50000000,
              "valeur_contenu": 10000000,
              "options": [{"code_option": "presence_gardien"}],
              "sous_garanties_optionnelles": [{"code_sous_garantie": "RC_MEMBRE"}]
          }
      }
      → Calcule et enregistre la maison, met à jour les totaux

3. Consulter les usages disponibles
   GET /api/mrh/usages/
   → Retourne la liste de tous les usages

4. Voir les détails d'un usage
   GET /api/mrh/usages/proprietaire_occupant_total/
   → Retourne les infos de l'usage

5. Voir les garanties d'un usage
   GET /api/mrh/usages/proprietaire_occupant_total/garanties/
   → Retourne garanties obligatoires et optionnelles

6. Voir les options applicables à un usage
   GET /api/mrh/usages/proprietaire_occupant_total/options/
   → Retourne toutes les options applicables

7. Récupérer un devis complet
   GET /api/mrh/devis/456/
   → Retourne le devis avec toutes ses maisons et totaux

8. Supprimer une maison d'un devis
   DELETE /api/mrh/devis/456/maisons/789/
   → Supprime la maison et recalcule les totaux
"""