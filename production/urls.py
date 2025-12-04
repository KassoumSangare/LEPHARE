from django.urls import include, path

from rest_framework import routers

from .views import DevisViewSet, DevisDetailViewSet, DevisDetGarantieViewSet
from .views import TarifEcranViewSet, ContratViewSet, ContratDetailViewSet
from .views import (
    ContratDetGarantieViewSet,
    QuittancePropositionView,
    QuittanceContratView,
    AyantDroitIaView,
    AyantDroitMineneView,
    LogRecordView,
    ExtendedQuotationInfoView,
    QuittanceViewSet,
    DetailQuittanceViewSet,
    EncaissementViewSet,
    DetailEncaissementViewSet,
    NumeroViewSet,
    GarantieContratView,
    ListeVehiculeContratView,
    ListeVehiculeDevisView,
    ContractForPremiumCollectionView,
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
)
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
    cancel_premium_collection,
    get_contracts_for_pc,
    remit_premium,
    create_insured_ia,
    change_plate_number,
    modify_policy,
    quote_unarchival,
)

router = routers.DefaultRouter()
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
router.register(r"detailreversement", DetailReversementViewSet)
router.register(r"numero", NumeroViewSet)
router.register(
    r"importationassureia",
    ImportationAssureIaViewSet,
    basename="importationassureia",
)

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
    path(
        r"annulationencaissement",
        cancel_premium_collection,
        name="annulation_encaissement",
    ),
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
]
