from django.urls import include, path

from rest_framework import routers
from  .views import (MenuViewSet, MenuParentViewSet, GarantieViewSet, UtilisateurViewSet, GroupeUtilisateurViewSet, SousGarantieViewSet, GarantieRisqueViewSet,
                     CategorieViewSet, TarifViewSet, TarifDetailViewSet, BrancheViewSet, RisqueViewSet, EnergieViewSet, CompagnieViewSet, QualiteViewSet,
                     TermeViewSet, SecteurActiviteViewSet, DomaineActiviteRCViewSet, CarrosserieViewSet, ProduitViewSet, AvenantViewSet, CommissionProduitViewSet,
                     IntermediaireViewSet, OffreViewSet, OffreDetailViewSet, OffreGarantieViewSet, MarqueViewSet, SystemeSecuriteViewSet, ModeleVehiculeViewSet,
                     UsageVehiculeViewSet, TypeReductionViewSet, CommuneViewSet, VilleViewSet, PaysViewSet, RegionViewSet, ContinentViewSet, ZoneVoyageViewSet,
                     GenreVehiculeViewSet, TypeVehiculeViewSet, TypeAssureViewSet, TypeSouscripteurViewSet, ProfessionViewSet, ProfessionIaViewSet, QualiteAyantDroitViewSet,
                     CategoriePermisViewSet, QualiteSouscripteurMrhViewSet, BanqueViewSet, ModeEncaissementViewSet, AccessoireViewSet, TauxTaxeGarantieProduitViewSet,
                     AccessoireCourtierParCompagnieViewSet, CollegeSanteViewSet, OffreCollegeSanteViewSet, LienJuridiqueSanteViewSet, ZoneCouvertureSanteViewSet,
                     ReductionFlotteViewSet, FormuleSecuriteRoutiereViewSet, ParametreSiteViewSet, DelaiAvisEcheanceViewSet, SolarScheduleViewSet, IntervalScheduleViewSet,
                     ClockedScheduleViewSet, CrontabScheduleViewSet, PeriodicTaskViewSet, TypeContratSanteViewSet, get_garantie, get_garantie_ia, get_garantie_voyage,
                     get_garantie_mrh, get_garantie_rc, create_offre_garantie, TarifParProduitView, OffreParProduitView, TarifVoyageView, OffreVoyageView, OffreSanteParTarifView,
                     CollegeSanteParOffreView, get_garantie_par_produit, ZoneCouvertureOffreView, FormuleSecuriteRoutiereView, AssistanceAutomobileView, PaysZoneView,
                     get_liste_avenant, IATarifGroupeView, IATarifPersonnaliseView, PrimeCalculationView,
                     )

router = routers.DefaultRouter()
router.register(r"menu", MenuViewSet)
router.register(r"menuparent", MenuParentViewSet)
router.register(r"garantie", GarantieViewSet)
router.register(r"utilisateur", UtilisateurViewSet)
router.register(r"groupeutilisateur", GroupeUtilisateurViewSet)
router.register(r"sousgarantie", SousGarantieViewSet)
router.register(r"garantierisque", GarantieRisqueViewSet)
router.register(r"categorie", CategorieViewSet)
router.register(r"tarif", TarifViewSet)
router.register(r"tarifdetail", TarifDetailViewSet)
router.register(r"branche", BrancheViewSet)
router.register(r"risque", RisqueViewSet)
router.register(r"energie", EnergieViewSet)
router.register(r"compagnie", CompagnieViewSet)
router.register(r"qualite", QualiteViewSet)
router.register(r"terme", TermeViewSet, basename="terme_contrat")
router.register(r"secteuractivite", SecteurActiviteViewSet)
router.register(r"domaineactiviterc", DomaineActiviteRCViewSet)
router.register(r"carrosserie", CarrosserieViewSet)
router.register(r"produit", ProduitViewSet)
router.register(r"avenant", AvenantViewSet)
router.register(r"commissionproduit", CommissionProduitViewSet)
router.register(r"intermediaire", IntermediaireViewSet)
router.register(r"offre", OffreViewSet)
router.register(r"offredetail", OffreDetailViewSet)
router.register(r"offregarantie", OffreGarantieViewSet)
router.register(r"marque", MarqueViewSet)
router.register(r"systemesecurite", SystemeSecuriteViewSet)
router.register(r"modele", ModeleVehiculeViewSet)
router.register(r"usage", UsageVehiculeViewSet)
router.register(r"typereduction", TypeReductionViewSet)
router.register(r"commune", CommuneViewSet)
router.register(r"ville", VilleViewSet)
router.register(r"pays", PaysViewSet)
router.register(r"region", RegionViewSet)
router.register(r"continent", ContinentViewSet)
router.register(r"zonevoyage", ZoneVoyageViewSet)
router.register(r"genrevehicule", GenreVehiculeViewSet)
router.register(r"typevehicule", TypeVehiculeViewSet)
router.register(r"typeassure", TypeAssureViewSet)
router.register(r"typesouscripteur", TypeSouscripteurViewSet)
router.register(r"profession", ProfessionViewSet)
router.register(r"professionia", ProfessionIaViewSet)
router.register(r"qualiteayantdroit", QualiteAyantDroitViewSet)
router.register(r"categoriepermis", CategoriePermisViewSet)
router.register(r"qualitesouscripteur", QualiteSouscripteurMrhViewSet)
router.register(r"banque", BanqueViewSet)
router.register(r"modeencaissement", ModeEncaissementViewSet)
router.register(r"accessoire", AccessoireViewSet)
router.register(r"tauxtaxegarantie", TauxTaxeGarantieProduitViewSet)
router.register(r"accessoirecourtier", AccessoireCourtierParCompagnieViewSet)
router.register(r"collegesante", CollegeSanteViewSet)
router.register(r"offrecollegesante", OffreCollegeSanteViewSet)
router.register(r"lienjuridiquesante", LienJuridiqueSanteViewSet)
router.register(r"zonecouverturesante", ZoneCouvertureSanteViewSet)
router.register(r"reductionflotte", ReductionFlotteViewSet)
router.register(r"formulesecuriteroutiere", FormuleSecuriteRoutiereViewSet)
router.register(r"parametresite", ParametreSiteViewSet)
router.register(r"delaiavisecheance", DelaiAvisEcheanceViewSet)
router.register(r"solarschedule", SolarScheduleViewSet)
router.register(r"intervalschedule", IntervalScheduleViewSet)
router.register(r"clockedschedule", ClockedScheduleViewSet)
router.register(r"crontabschedule", CrontabScheduleViewSet)
router.register(r"periodictaskschedule", PeriodicTaskViewSet)
router.register(r"typecontratsante", TypeContratSanteViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path(r"offregarantie", get_garantie, name="offre_garantie_auto"),
    path(r"offregarantieia", get_garantie_ia, name="offre_garantie_ia"),
    path(r"offregarantievoyage", get_garantie_voyage, name="offre_garantie_voyage"),
    path(
        r"offregarantiemrh",
        get_garantie_mrh,
        name="offre_garantie_mrh",
    ),
    path(
        r"offregarantierc",
        get_garantie_rc,
        name="offre_garantie_rc",
    ),
    path(
        r"enregistrementoffregarantie",
        create_offre_garantie,
        name="enregistrement_offre_garantie",
    ),
    path(
        r"tarifparproduit/<int:idproduit>",
        TarifParProduitView.as_view(),
        name="tarif_par_produit",
    ),
    path(
        r"offreparproduit/",
        OffreParProduitView.as_view(),
        name="offre_par_produit",
    ),
    path(
        r"tarifvoyage/<int:idcompagnie>",
        TarifVoyageView.as_view(),
        name="tarif_par_produit",
    ),
    path(
        r"offrevoyage/",
        OffreVoyageView.as_view(),
        name="offre_voyage_par_compagnie_tarif",
    ),
    path(
        r"offresantepartarif/<int:idtarif>",
        OffreSanteParTarifView.as_view(),
        name="offre_sante_par_tarif",
    ),
    path(
        r"collegesanteparoffre/<int:idoffre>",
        CollegeSanteParOffreView.as_view(),
        name="college_sante_par_offre",
    ),
    path(
        r"garantieparproduit",
        get_garantie_par_produit,
        name="garantie_par_produit",
    ),
    path(
        r"zonecouvertureoffre/<int:idzone>",
        ZoneCouvertureOffreView.as_view(),
        name="zone_couverture_offre",
    ),
    path(
        r"securiteroutiereparcompagnie/<int:idcompagnie>",
        FormuleSecuriteRoutiereView.as_view(),
        name="formule_securite_routiere_par_compagnie",
    ),
    path(
        r"assistanceautomobile/<int:idcompagnie>",
        AssistanceAutomobileView.as_view(),
        name="formule_assistance_automobile_par_compagnie",
    ),
    path(
        r"payszone/<int:idcompagnie>",
        PaysZoneView.as_view(),
        name="pays_zone_par_compagnie",
    ),
    path(
        r"avenant/avenantparproduit",
        get_liste_avenant,
        name="avenant_par_produit",
    ),
    path(r'esttarifiagroupe/<int:idtarif>/', IATarifGroupeView.as_view(), name='est-tarif-ia-groupe'),
    path(r'esttarifiapersonnalise/<int:idtarif>/', IATarifPersonnaliseView.as_view(), name='est-tarif-ia-personnalise'),
    path(r"calculprime/", PrimeCalculationView.as_view(), name="calcul-prime"),
]
