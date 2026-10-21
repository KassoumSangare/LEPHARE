"""
Questionnaires prospects (suivi commercial) : modèles à télécharger sous leur titre, questionnaires remplis déposés.

Droits (garde centrale) : consultation et téléchargements « crm.view », dépôt, étapes et suppression « crm.update ».
Le dépôt rattache le questionnaire à un prospect du suivi commercial (créé au besoin) et le fait passer de
« Nouveau » à « Qualifié » ; un questionnaire au stade « Devis établi » fait passer le prospect à « Proposition ».
"""

import datetime
import logging
import os

from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.fichiers import valider_fichier
from core.views import ResultsOnlyPagination
from .models import CrmLead, QuestionnaireProspect
from .questionnaires import (
    EXTENSIONS_DEPOT,
    MODELES,
    PAR_CODE,
    STATUT_A_COMPLETER,
    STATUT_DEVIS,
    STATUT_ETUDE,
    STATUT_RECU,
    STATUTS,
    TAILLE_MAX_DEPOT,
    chemin_modele,
    extension,
    nom_telechargement,
)
from .serializers import CrmLeadSerializer, QuestionnaireProspectSerializer

journal = logging.getLogger(__name__)

# Étapes du prospect que le questionnaire fait avancer (jamais de retour en arrière, jamais au-delà)
ETAPE_APRES_DEPOT = {"Nouveau": "Qualifié"}
ETAPE_APRES_DEVIS = {"Nouveau": "Proposition", "Qualifié": "Proposition"}


def _auteur(request):
    utilisateur = getattr(request, "user", None)
    return (getattr(utilisateur, "name", None) or getattr(utilisateur, "email", None) or "Commercial").strip()


def _maintenant():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _vrai(valeur):
    return str(valeur).strip().lower() in ("1", "true", "oui", "on")


def _fichier(chemin, nom, type_mime=None):
    """Téléchargement sous `nom` (Content-Disposition, accents compris)."""
    try:
        flux = open(chemin, "rb")
    except OSError:
        raise Http404("Fichier introuvable")
    reponse = FileResponse(flux, as_attachment=True, filename=nom, content_type=type_mime)
    reponse["X-Content-Type-Options"] = "nosniff"
    reponse["Cache-Control"] = "private, no-store"
    return reponse


TYPES_MIME = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
}


def reference_prospect():
    """Référence PROSP-<année>-<n° à 3 chiffres> suivant la plus haute de l'année."""
    prefixe = f"PROSP-{datetime.date.today().year}-"
    numeros = [
        int(ref[len(prefixe):])
        for ref in CrmLead.objects.filter(id_lead__startswith=prefixe).values_list("id_lead", flat=True)
        if ref[len(prefixe):].isdigit()
    ]
    return f"{prefixe}{(max(numeros) if numeros else 0) + 1:03d}"


def _avancer_prospect(lead, etapes, auteur, motif):
    """Fait avancer le prospect selon `etapes` ; l'échange est noté dans son historique. Renvoie True si changé."""
    nouvelle = etapes.get(lead.statut)
    if not nouvelle:
        return False
    lead.historique_echanges = (lead.historique_echanges if isinstance(lead.historique_echanges, list) else []) + [{
        "date": datetime.date.today().isoformat(),
        "auteur": auteur,
        "action": f"Transition d'étape : de '{lead.statut}' vers '{nouvelle}' ({motif})",
    }]
    lead.statut = nouvelle
    return True


def _noter_prospect(lead, auteur, action_texte):
    lead.historique_echanges = (lead.historique_echanges if isinstance(lead.historique_echanges, list) else []) + [{
        "date": datetime.date.today().isoformat(), "auteur": auteur, "action": action_texte}]


# ---------------------------------------------------------------- modèles à télécharger
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def modeles(request):
    """GET crm/questionnaires/modeles/ : catalogue, avec le nombre de questionnaires reçus de chaque modèle."""
    comptes = {
        ligne["modele"]: ligne
        for ligne in QuestionnaireProspect.objects.values("modele").annotate(
            recus=Count("id"), a_traiter=Count("id", filter=Q(statut__in=(STATUT_RECU, STATUT_ETUDE))))
    }
    resultat = []
    for m in MODELES:
        chemin = chemin_modele(m)
        resultat.append({
            **{k: m[k] for k in ("code", "titre", "format", "origine", "branche", "compagnie", "description",
                                 "rubriques", "route_devis")},
            "extension": extension(m["fichier"]),
            "nom_fichier": nom_telechargement(m),
            "taille": os.path.getsize(chemin) if os.path.exists(chemin) else None,
            "recus": comptes.get(m["code"], {}).get("recus", 0),
            "a_traiter": comptes.get(m["code"], {}).get("a_traiter", 0),
        })
    return Response({"modeles": resultat, "statuts": STATUTS, "extensions": EXTENSIONS_DEPOT,
                     "taille_max": TAILLE_MAX_DEPOT})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def telecharger_modele(request, code):
    """GET crm/questionnaires/modeles/<code>/fichier/ : le questionnaire vierge, nommé d'après son titre."""
    modele = PAR_CODE.get(code)
    if not modele:
        raise Http404("Questionnaire inconnu")
    return _fichier(chemin_modele(modele), nom_telechargement(modele), TYPES_MIME.get(extension(modele["fichier"])))


# ---------------------------------------------------------------- lecture avant dépôt
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def analyser_questionnaire(request):
    """POST crm/questionnaires/analyse/ (fichier, modele facultatif) : rien n'est enregistré. Le questionnaire est
    reconnu d'après son contenu et lu, pour montrer avant le dépôt ce qui passera dans le devis."""
    from .lecture_questionnaires import analyser

    fichier = QuestionnaireProspectViewSet._fichier_valide(request)
    try:
        return Response(analyser(fichier.read(), fichier.name, request.data.get("modele") or ""))
    except Exception:  # noqa: BLE001 - l'analyse est une aide : le dépôt reste possible
        journal.exception("Analyse du questionnaire %s impossible", fichier.name)
        return Response({"reconnu": None, "lisible": False, "resume": "", "souscripteur": {}, "avertissements": [],
                         "reponses": 0, "lignes": 0, "devis": None,
                         "message": "Le contenu n'a pas pu être lu : le questionnaire peut quand même être déposé."})


# ---------------------------------------------------------------- questionnaires remplis
class QuestionnaireProspectViewSet(viewsets.ModelViewSet):
    """crm/questionnaires/recus/ : dépôt (POST multipart), liste, étape et note (PATCH), suppression,
    nouvelle version (POST <id>/version/) et téléchargement du fichier reçu (GET <id>/fichier/)."""

    serializer_class = QuestionnaireProspectSerializer
    pagination_class = ResultsOnlyPagination
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filter_backends = []

    def get_queryset(self):
        qs = QuestionnaireProspect.objects.select_related("lead").order_by("-date_depot", "-id")
        parametres = self.request.query_params
        if parametres.get("lead"):
            qs = qs.filter(lead_id=parametres["lead"])
        if parametres.get("statut"):
            qs = qs.filter(statut=parametres["statut"])
        if parametres.get("modele"):
            qs = qs.filter(modele=parametres["modele"])
        return qs

    @staticmethod
    def _fichier_valide(request):
        fichier = request.FILES.get("fichier")
        if not fichier:
            raise ValidationError({"fichier": "Joignez le questionnaire rempli."})
        try:
            valider_fichier(fichier, EXTENSIONS_DEPOT, TAILLE_MAX_DEPOT)
        except serializers.ValidationError as erreur:
            raise ValidationError({"fichier": erreur.detail})
        return fichier

    def create(self, request, *args, **kwargs):
        modele = PAR_CODE.get(request.data.get("modele") or "")
        if not modele:
            raise ValidationError({"modele": "Choisissez le questionnaire déposé."})
        fichier = self._fichier_valide(request)
        auteur = _auteur(request)
        note = (request.data.get("note") or "").strip()
        lead_id = request.data.get("lead")

        with transaction.atomic():
            if lead_id:
                lead = CrmLead.objects.select_for_update().filter(pk=lead_id).first()
                if not lead:
                    raise ValidationError({"lead": "Prospect introuvable : il a peut-être été supprimé."})
                lead_cree = False
            else:
                nom = (request.data.get("prospect_nom") or "").strip()
                if not nom:
                    raise ValidationError({"prospect_nom": "Choisissez le prospect ou saisissez le nom du nouveau prospect."})
                donnees = {
                    "nom_prospect": nom,
                    "contact": (request.data.get("contact") or "").strip(),
                    "telephone": (request.data.get("telephone") or "").strip(),
                    "email": (request.data.get("email") or "").strip(),
                    "branche": modele["branche"],
                    "commercial_attribue": "",
                    "statut": "Nouveau",
                }
                verification = CrmLeadSerializer(data=donnees)
                verification.is_valid(raise_exception=True)
                lead = verification.save(id_lead=reference_prospect(), historique_echanges=[{
                    "date": datetime.date.today().isoformat(), "auteur": auteur,
                    "action": f"Création de l'opportunité (questionnaire « {modele['titre']} » reçu)"}])
                lead_cree = True

            _noter_prospect(lead, auteur, f"Questionnaire reçu : {modele['titre']} ({fichier.name})")
            avance = _vrai(request.data.get("qualifier", "1")) and _avancer_prospect(
                lead, ETAPE_APRES_DEPOT, auteur, "questionnaire reçu")
            lead.save()

            questionnaire = QuestionnaireProspect.objects.create(
                modele=modele["code"], titre=modele["titre"], branche=modele["branche"], lead=lead,
                prospect_nom=lead.nom_prospect, fichier=fichier, nom_original=fichier.name[:255],
                taille=fichier.size or 0, statut=STATUT_RECU, note=note,
                depose_par=request.user if getattr(request.user, "is_authenticated", False) else None,
                depose_par_nom=auteur,
                historique=[{"date": _maintenant(), "auteur": auteur, "action": f"Dépôt de {fichier.name}"}],
            )
        return Response({
            "questionnaire": QuestionnaireProspectSerializer(questionnaire).data,
            "prospect": CrmLeadSerializer(lead).data,
            "prospect_cree": lead_cree,
            "prospect_avance": bool(avance),
        }, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        questionnaire = self.get_object()
        serializer = self.get_serializer(questionnaire, data={k: request.data[k] for k in ("statut", "note") if k in request.data},
                                         partial=True)
        serializer.is_valid(raise_exception=True)
        # Reclassement : le fichier est celui d'un autre questionnaire (reconnu d'après son contenu)
        reclasse = None
        if request.data.get("modele") and request.data["modele"] != questionnaire.modele:
            reclasse = PAR_CODE.get(request.data["modele"])
            if not reclasse:
                raise ValidationError({"modele": "Questionnaire inconnu."})
        auteur = _auteur(request)
        ancien, nouveau = questionnaire.statut, serializer.validated_data.get("statut", questionnaire.statut)
        prospect_avance = False
        with transaction.atomic():
            evenements = []
            if reclasse:
                evenements.append(f"Reclassé : {questionnaire.titre} → {reclasse['titre']}")
                questionnaire.modele, questionnaire.titre, questionnaire.branche = reclasse["code"], reclasse["titre"], reclasse["branche"]
            if nouveau != ancien:
                evenements.append(f"Étape : {ancien} → {nouveau}")
            if "note" in serializer.validated_data and serializer.validated_data["note"] != questionnaire.note:
                evenements.append("Note modifiée")
            questionnaire = serializer.save(historique=list(questionnaire.historique or []) + [
                {"date": _maintenant(), "auteur": auteur, "action": e} for e in evenements])
            lead = CrmLead.objects.select_for_update().filter(pk=questionnaire.lead_id).first()
            if lead and nouveau != ancien:
                texte = {STATUT_A_COMPLETER: "à compléter par le client", STATUT_DEVIS: "devis établi",
                         STATUT_ETUDE: "en étude", STATUT_RECU: "reçu"}[nouveau]
                _noter_prospect(lead, auteur, f"Questionnaire {questionnaire.titre} : {texte}")
                if nouveau == STATUT_DEVIS:
                    prospect_avance = _avancer_prospect(lead, ETAPE_APRES_DEVIS, auteur, "devis établi")
                lead.save()
        return Response({**QuestionnaireProspectSerializer(questionnaire).data, "prospect_avance": prospect_avance,
                         "lead_statut": lead.statut if lead else None})

    def update(self, request, *args, **kwargs):
        if not kwargs.get("partial"):
            return Response({"detail": "Modification par PATCH seulement (étape, note)."},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return self.partial_update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        fichier = instance.fichier
        with transaction.atomic():
            if instance.lead_id:
                lead = CrmLead.objects.select_for_update().filter(pk=instance.lead_id).first()
                if lead:
                    _noter_prospect(lead, _auteur(self.request), f"Questionnaire retiré : {instance.titre} ({instance.nom_original})")
                    lead.save()
            instance.delete()
        # Fichiers des versions précédentes compris
        for chemin in [fichier.name] + [e.get("fichier") for e in instance.historique or [] if e.get("fichier")]:
            try:
                fichier.storage.delete(chemin)
            except Exception:
                pass

    @action(detail=True, methods=["post"])
    def version(self, request, pk=None):
        """POST <id>/version/ : le client renvoie le questionnaire complété ; le précédent reste dans l'historique."""
        questionnaire = self.get_object()
        fichier = self._fichier_valide(request)
        auteur = _auteur(request)
        with transaction.atomic():
            ancien_nom, ancien_chemin = questionnaire.nom_original, questionnaire.fichier.name
            questionnaire.fichier = fichier
            questionnaire.nom_original = fichier.name[:255]
            questionnaire.taille = fichier.size or 0
            questionnaire.version += 1
            ancien_statut = questionnaire.statut
            questionnaire.statut = STATUT_RECU
            questionnaire.historique = list(questionnaire.historique or []) + [{
                "date": _maintenant(), "auteur": auteur, "fichier": ancien_chemin,
                "action": f"Version {questionnaire.version} déposée : {fichier.name} (remplace {ancien_nom}"
                          f"{', étape ' + ancien_statut if ancien_statut != STATUT_RECU else ''})"}]
            questionnaire.save()
            lead = CrmLead.objects.select_for_update().filter(pk=questionnaire.lead_id).first()
            if lead:
                _noter_prospect(lead, auteur, f"Questionnaire {questionnaire.titre} : version {questionnaire.version} reçue")
                lead.save()
        return Response(QuestionnaireProspectSerializer(questionnaire).data)

    @action(detail=True, methods=["get"])
    def lecture(self, request, pk=None):
        """GET <id>/lecture/ : contenu lu du questionnaire rempli (souscripteur, réponses, tableaux, données du devis)."""
        from .lecture_questionnaires import lire

        questionnaire = self.get_object()
        try:
            return Response(lire(questionnaire))
        except Exception:  # noqa: BLE001 - une lecture défaillante ne bloque pas le dossier : le fichier reste téléchargeable
            journal.exception("Lecture du questionnaire %s impossible", questionnaire.pk)
            return Response({"modele": questionnaire.modele, "titre": questionnaire.titre, "branche": questionnaire.branche,
                             "lisible": False, "souscripteur": {"nom": questionnaire.prospect_nom}, "sections": [],
                             "tableaux": [], "devis": None, "avertissements": [], "resume": "", "reponses": 0,
                             "message": "Le contenu n'a pas pu être lu : ouvrez le fichier et reprenez les informations à la main."})

    @action(detail=True, methods=["get"])
    def fichier(self, request, pk=None):
        """GET <id>/fichier/ : le questionnaire reçu, nommé « <titre> - <prospect>.<ext> »."""
        questionnaire = self.get_object()
        nom = QuestionnaireProspectSerializer(questionnaire).data["nom_telechargement"]
        try:
            chemin = questionnaire.fichier.path
        except Exception:
            raise Http404("Fichier introuvable")
        return _fichier(chemin, nom, TYPES_MIME.get(extension(questionnaire.fichier.name)))
