import datetime
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.db.models import Sum, Count, Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView
from core.views import ResultsOnlyPagination

from .models import (
    CrmLead,
    CrmInteraction,
    SinistreDelegue,
    ConventionAssureur,
    DocumentGED,
    AuditLogCima,
    QuittanceCima,
    BordereauReversement
)
from .serializers import (
    CrmLeadSerializer,
    CrmInteractionSerializer,
    SinistreDelegueSerializer,
    ConventionAssureurSerializer,
    DocumentGEDSerializer,
    AuditLogCimaSerializer,
    QuittanceCimaSerializer,
    BordereauReversementSerializer,
    STATUT_REGLE,
    STATUTS_SANS_REGLEMENT,
    indemnite_reglee,
    plafond_delegation,
    sinistre_regle,
)
from autorisations.journal import completer_audit

# Optional import of core Uranus models for 360 view
try:
    from customer.models import Client
except Exception:
    Client = None

try:
    from production.models import Contrat, Devis, Encaissement
except Exception:
    Contrat = None
    Devis = None
    Encaissement = None


# Les données de démonstration ne sont plus insérées par les consultations : voir institutionnel/demo.py
# (commande semer_demo_institutionnel).


# =========================================================================
# 1. CRM PIPELINE & LEADS
# =========================================================================
class CrmLeadViewSet(viewsets.ModelViewSet):
    """Prospects du suivi commercial : réservés aux utilisateurs connectés (écriture comprise)."""

    queryset = CrmLead.objects.all().order_by("-date_creation")
    serializer_class = CrmLeadSerializer
    pagination_class = ResultsOnlyPagination
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Référence PROSP-<année>-<n° à 3 chiffres> suivant la plus haute de l'année (jamais
        # calculée par l'écran, qui la dupliquait après une suppression)
        prefixe = f"PROSP-{datetime.date.today().year}-"
        numeros = [
            int(ref[len(prefixe):])
            for ref in CrmLead.objects.filter(id_lead__startswith=prefixe).values_list("id_lead", flat=True)
            if ref[len(prefixe):].isdigit()
        ]
        serializer.save(id_lead=f"{prefixe}{(max(numeros) if numeros else 0) + 1:03d}")

    @action(detail=True, methods=["post", "patch"])
    def changer_statut(self, request, pk=None):
        lead = self.get_object()
        nouveau_statut = request.data.get("statut")
        if not nouveau_statut:
            return Response({"error": "Paramètre 'statut' obligatoire"}, status=status.HTTP_400_BAD_REQUEST)
        if nouveau_statut not in CrmLead.STATUTS:
            return Response(
                {"error": f"Étape inconnue : {nouveau_statut} (attendu : {', '.join(CrmLead.STATUTS)})"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ancien_statut = lead.statut
        lead.statut = nouveau_statut
        
        # Ajout automatique à l'historique
        if not isinstance(lead.historique_echanges, list):
            lead.historique_echanges = []
        
        lead.historique_echanges.append({
            "date": datetime.date.today().isoformat(),
            "auteur": request.user.username if request.user and request.user.is_authenticated else "Conseiller Commercial",
            "action": f"Transition d'étape : de '{ancien_statut}' vers '{nouveau_statut}'"
        })
        lead.save()
        return Response(CrmLeadSerializer(lead).data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        total_leads = CrmLead.objects.count()
        total_valeur = CrmLead.objects.aggregate(total=Sum("prime_estimee"))["total"] or 0
        gagnes = CrmLead.objects.filter(statut="Gagné")
        valeur_gagnee = gagnes.aggregate(total=Sum("prime_estimee"))["total"] or 0
        tx_conversion = round((gagnes.count() / total_leads * 100), 1) if total_leads > 0 else 0

        par_etape = dict(CrmLead.objects.values("statut").annotate(count=Count("id")).values_list("statut", "count"))

        return Response({
            "total_leads": total_leads,
            "total_valeur_pipeline": total_valeur,
            "valeur_gagnee": valeur_gagnee,
            "taux_conversion": tx_conversion,
            "par_etape": par_etape
        })


class CrmInteractionViewSet(viewsets.ModelViewSet):
    queryset = CrmInteraction.objects.all().order_by("-date_interaction")
    serializer_class = CrmInteractionSerializer
    pagination_class = ResultsOnlyPagination
    permission_classes = [permissions.AllowAny]


# =========================================================================
# 2. VUE CONSOLIDÉE CLIENT 360°
# =========================================================================
class Customer360View(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, client_id=None):
        client_data = {
            "id": client_id or 1,
            "codeclient": f"CLI-2024-{str(client_id or 1).zfill(3)}",
            "nom": "KOUAME Jean-Baptiste",
            "typeclient": "Particulier",
            "telephone": "+225 07 07 12 34 56",
            "email": "jb.kouame@gmail.com",
            "adresse": "Cocody Deux-Plateaux Vallons",
            "ville": "Abidjan",
            "profession": "Chef d'Entreprise",
            "vip": True,
            "solde": 0,
            "statut": "Actif"
        }

        # Si le modèle Client existe en base
        if Client and client_id:
            try:
                db_client = Client.objects.filter(IdClient=client_id).first()
                if db_client:
                    client_data.update({
                        "id": db_client.IdClient,
                        "nom": f"{db_client.Nom} {db_client.Prenoms or ''}".strip(),
                        "telephone": db_client.Telephone or db_client.Mobile or client_data["telephone"],
                        "email": db_client.Email or client_data["email"],
                        "ville": "Abidjan",
                        "solde": float(db_client.Solde or 0)
                    })
            except Exception:
                pass

        # Récupération des polices et sinistres associés
        sinistres = list(SinistreDelegue.objects.filter(assure_nom__icontains=client_data["nom"][:8]).values())
        if not sinistres:
            sinistres = list(SinistreDelegue.objects.all()[:2].values())

        contrats = [
            {
                "id": 101,
                "numeropolice": "POL-2026-001",
                "produit": "Automobile Tous Risques",
                "compagnie": "NSIA Assurances",
                "date_effet": "2026-01-01",
                "date_echeance": "2026-12-31",
                "prime_totale": 450000,
                "statut": "Actif"
            },
            {
                "id": 102,
                "numeropolice": "POL-2026-003",
                "produit": "Multi-Risques Habitation (MRH)",
                "compagnie": "SUNU Assurances",
                "date_effet": "2026-02-15",
                "date_echeance": "2027-02-14",
                "prime_totale": 280000,
                "statut": "Actif"
            }
        ]

        interactions = list(CrmInteraction.objects.filter(client_id=client_id).values())
        if not interactions:
            interactions = [
                {
                    "date_interaction": "2026-09-02T10:30:00Z",
                    "type_interaction": "Appel",
                    "auteur": "Koffi Serge",
                    "resume": "Point d'étape annuel de renouvellement de la police automobile. Client très satisfait de la réactivité sur le sinistre d'août."
                },
                {
                    "date_interaction": "2026-08-30T14:15:00Z",
                    "type_interaction": "Rendez-vous",
                    "auteur": "Amina Diallo",
                    "resume": "Réception des pièces justificatives originales pour le dossier de sinistre collision."
                }
            ]

        return Response({
            "client": client_data,
            "contrats": contrats,
            "sinistres": sinistres,
            "interactions": interactions,
            "devis_recents": [
                {
                    "id": 201,
                    "numerodevis": "DEV-2026-089",
                    "produit": "Individuelle Accident Famille",
                    "prime_totale": 125000,
                    "statut": "Proposition émise"
                }
            ],
            "statistiques": {
                "total_primes_cumulees": 855000,
                "nombre_contrats_actifs": len(contrats),
                "nombre_sinistres": len(sinistres),
                "ratio_sinistre_prime": "25.4%"
            }
        })


# =========================================================================
# 3. SINISTRES DÉLÉGUÉS CIMA
# =========================================================================
class Conflit(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflit"


def _erreur(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=code)


def _evenement(sinistre, action):
    """Ajoute une ligne datée au journal chronologique du dossier (sans l'enregistrer)."""
    if not isinstance(sinistre.historique_evenements, list):
        sinistre.historique_evenements = []
    sinistre.historique_evenements.append({"date": datetime.date.today().isoformat(), "action": action})


def _etat_reglement(sinistre):
    return {
        "numero_sinistre": sinistre.numero_sinistre, "statut": sinistre.statut,
        "montant_indemnise": float(sinistre.montant_indemnise or 0),
        "quittance_subrogative_emise": sinistre.quittance_subrogative_emise,
    }


class SinistreDelegueViewSet(viewsets.ModelViewSet):
    """Sinistres délégués. Le montant indemnisé, le statut « Réglé », la quittance subrogative, l'accord préalable
    et le respect du plafond ne sont posés que par le serveur : actions règlement (droit « Régler un sinistre »,
    plafond de la convention), demande d'accord et quittance subrogative ; une modification générique ne peut
    ni les écrire (SinistreDelegueSerializer) ni rouvrir un dossier réglé."""

    queryset = SinistreDelegue.objects.all().order_by("-date_declaration")
    serializer_class = SinistreDelegueSerializer
    pagination_class = ResultsOnlyPagination
    permission_classes = [permissions.AllowAny]

    def _verrouiller(self):
        """Verrou de la ligne jusqu'à la fin de la transaction : un règlement enregistré entre-temps n'est ni
        réécrit ni contourné par l'opération en cours (l'objet est relu après le verrou)."""
        list(SinistreDelegue.objects.select_for_update().filter(pk=self.get_object().pk).values_list("pk", flat=True))

    def perform_create(self, serializer):
        donnees = serializer.validated_data
        serializer.save(
            delegation_respectee=Decimal(donnees.get("montant_reclame") or 0) <= plafond_delegation(donnees.get("compagnie")),
            historique_evenements=[{"date": datetime.date.today().isoformat(), "action": "Déclaration enregistrée dans le système"}],
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        self._verrouiller()
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        sinistre, donnees = serializer.instance, serializer.validated_data
        champs = {}
        if not sinistre_regle(sinistre) and {"montant_reclame", "compagnie"} & set(donnees):
            montant = donnees.get("montant_reclame", sinistre.montant_reclame)
            champs["delegation_respectee"] = Decimal(montant or 0) <= plafond_delegation(donnees.get("compagnie", sinistre.compagnie))
        nouveau = donnees.get("statut")
        if nouveau and nouveau != sinistre.statut:
            _evenement(sinistre, f"Statut modifié : « {sinistre.statut} » → « {nouveau} » "
                                 f"({getattr(self.request.user, 'email', '') or 'utilisateur'})")
            champs["historique_evenements"] = sinistre.historique_evenements
        serializer.save(**champs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        self._verrouiller()
        return super().destroy(request, *args, **kwargs)

    def perform_destroy(self, instance):
        if sinistre_regle(instance):
            raise Conflit({"error": f"Le sinistre {instance.numero_sinistre} est réglé : il ne peut pas être supprimé."})
        instance.delete()

    @action(detail=True, methods=["post"])
    def reglement(self, request, pk=None):
        """Règlement d'un sinistre sous mandat de gestion déléguée : indemnité positive, au plus égale au montant
        réclamé et au plafond de délégation de la convention ; un seul règlement par dossier (ligne verrouillée).
        La quittance subrogative est émise avec le règlement."""
        with transaction.atomic():
            self._verrouiller()
            sinistre = self.get_object()
            if sinistre.statut in STATUTS_SANS_REGLEMENT or sinistre_regle(sinistre):
                return _erreur(f"Le sinistre {sinistre.numero_sinistre} est déjà au statut « {sinistre.statut} » : "
                               "nouveau règlement refusé.", status.HTTP_409_CONFLICT)
            brut = request.data.get("montant_indemnise")
            try:
                montant = (Decimal(str(brut).replace(" ", "").replace(",", ".")) if brut not in (None, "")
                           else Decimal(sinistre.montant_reclame or 0))
            except (InvalidOperation, ValueError):
                return _erreur("Montant de l'indemnité invalide.")
            if not montant.is_finite() or montant <= 0:
                return _erreur("Le montant de l'indemnité doit être supérieur à zéro.")
            montant = montant.quantize(Decimal("0.01"))
            if sinistre.montant_reclame and montant > sinistre.montant_reclame:
                return _erreur(f"L'indemnité ({montant:,.0f} FCFA) dépasse le montant réclamé "
                               f"({sinistre.montant_reclame:,.0f} FCFA).")
            plafond = plafond_delegation(sinistre.compagnie)
            if montant > plafond:
                return _erreur(f"Le montant ({montant:,.0f} FCFA) dépasse le plafond de délégation conventionnelle "
                               f"({plafond:,.0f} FCFA). Un mandat exprès de la compagnie est requis.")

            avant = _etat_reglement(sinistre)
            sinistre.montant_indemnise = montant
            sinistre.statut = STATUT_REGLE
            sinistre.delegation_respectee = True
            sinistre.quittance_subrogative_emise = True
            _evenement(sinistre, f"Règlement ordonnancé pour un montant de {montant:,.0f} FCFA sous mandat de délégation approuvé.")
            _evenement(sinistre, f"Quittance d'indemnité subrogative QT-SUB-{sinistre.numero_sinistre} émise (Art. 54 CIMA).")
            sinistre.save()

        completer_audit(
            request,
            description=f"Règlement ordonnancé sur le sinistre {sinistre.numero_sinistre} pour {montant:,.0f} FCFA "
                        f"(Assuré : {sinistre.assure_nom}) et émission de la quittance subrogative",
            objet_type="sinistre", objet_id=sinistre.pk, avant=avant,
            apres={**_etat_reglement(sinistre), "compagnie": sinistre.compagnie, "plafond": float(plafond)},
        )
        return Response(SinistreDelegueSerializer(sinistre).data)

    @action(detail=True, methods=["post"])
    def demande_accord(self, request, pk=None):
        """Transmission du dossier pour accord préalable / mandat spécial compagnie (hors plafond)"""
        with transaction.atomic():
            self._verrouiller()
            sinistre = self.get_object()
            if sinistre.statut in STATUTS_SANS_REGLEMENT or sinistre_regle(sinistre):
                return _erreur(f"Le sinistre {sinistre.numero_sinistre} est au statut « {sinistre.statut} » : "
                               "demande d'accord sans objet.", status.HTTP_409_CONFLICT)
            motif = request.data.get("motif") or "Montant réclamé supérieur au plafond de délégation conventionnelle."
            sinistre.accord_prealable_requis = True
            sinistre.statut = "En attente accord compagnie"
            _evenement(sinistre, f"Dossier transmis au siège de {sinistre.compagnie} pour accord préalable / dérogation CIMA : {motif}")
            sinistre.save()
        completer_audit(
            request,
            description=f"Transmission pour accord préalable compagnie sur {sinistre.numero_sinistre} ({sinistre.montant_reclame:,.0f} FCFA vs plafond)",
            apres={"numero_sinistre": sinistre.numero_sinistre, "compagnie": sinistre.compagnie},
        )
        return Response(SinistreDelegueSerializer(sinistre).data)

    @action(detail=True, methods=["get", "post"])
    def quittance_subrogative(self, request, pk=None):
        """Quittance d'indemnité subrogative (Art. 54 du Code CIMA) d'un sinistre réglé.

        GET : consultation seule, aucune écriture. POST (droit « Régler un sinistre », garde centrale) : marque
        la quittance émise pour un sinistre réglé avant que le règlement ne l'émette lui-même ; sans effet si
        elle l'est déjà. Un sinistre non réglé n'a pas de quittance (409)."""
        sinistre = self.get_object()
        if not indemnite_reglee(sinistre):
            return _erreur(f"Le sinistre {sinistre.numero_sinistre} n'est pas réglé : aucune quittance subrogative "
                           "ne peut être établie.", status.HTTP_409_CONFLICT)
        if request.method == "POST" and not sinistre.quittance_subrogative_emise:
            with transaction.atomic():
                self._verrouiller()
                sinistre = self.get_object()
                avant = _etat_reglement(sinistre)
                if not sinistre.quittance_subrogative_emise:
                    sinistre.quittance_subrogative_emise = True
                    _evenement(sinistre, f"Quittance d'indemnité subrogative QT-SUB-{sinistre.numero_sinistre} émise (Art. 54 CIMA).")
                    sinistre.save(update_fields=["quittance_subrogative_emise", "historique_evenements", "date_maj"])
            completer_audit(
                request, description=f"Émission de la quittance subrogative QT-SUB-{sinistre.numero_sinistre}",
                objet_type="sinistre", objet_id=sinistre.pk, avant=avant, apres=_etat_reglement(sinistre),
            )
        montant = sinistre.montant_indemnise or sinistre.montant_reclame
        data = {
            "numero_quittance": f"QT-SUB-{sinistre.numero_sinistre}",
            "numero_sinistre": sinistre.numero_sinistre,
            "assure_nom": sinistre.assure_nom,
            "police_num": sinistre.police_num,
            "compagnie": sinistre.compagnie,
            "montant_indemnise": float(montant),
            "date_reglement": datetime.date.today().isoformat(),
            "clause_subrogative": f"Le soussigné {sinistre.assure_nom} reconnaît avoir reçu de LE PHARE, agissant au nom et pour le compte de {sinistre.compagnie}, la somme de {float(montant):,.0f} FCFA en règlement intégral et définitif du sinistre N° {sinistre.numero_sinistre}. Conformément à l'Article 54 du Code CIMA, l'assureur est subrogé jusqu'à concurrence de cette indemnité dans les droits et actions de l'assuré contre les tiers responsables.",
            "emetteur": "Direction Sinistres LE PHARE"
        }
        return Response(data)

    @action(detail=True, methods=["post"])
    def maj_pieces(self, request, pk=None):
        """Liste de contrôle des pièces : [{ nom, recu }] (au plus 50 pièces)."""
        sinistre = self.get_object()
        pieces = request.data.get("pieces_justificatives")
        if pieces is not None:
            if (not isinstance(pieces, list) or len(pieces) > 50
                    or not all(isinstance(p, dict) and str(p.get("nom") or "").strip() for p in pieces)):
                return _erreur("Pièces justificatives : liste de pièces { nom, recu } attendue (50 au plus).")
            sinistre.pieces_justificatives = [
                {"nom": str(p["nom"]).strip()[:150], "recu": bool(p.get("recu"))} for p in pieces
            ]
            sinistre.save(update_fields=["pieces_justificatives", "date_maj"])
        return Response(SinistreDelegueSerializer(sinistre).data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        total = SinistreDelegue.objects.count()
        total_reclame = SinistreDelegue.objects.aggregate(total=Sum("montant_reclame"))["total"] or 0
        total_indemnise = SinistreDelegue.objects.aggregate(total=Sum("montant_indemnise"))["total"] or 0
        regles = SinistreDelegue.objects.filter(statut="Réglé").count()
        en_cours = SinistreDelegue.objects.exclude(statut__in=["Réglé", "Clôturé", "Rejeté"]).count()
        respect_delegation_pct = round(SinistreDelegue.objects.filter(delegation_respectee=True).count() / total * 100, 1) if total > 0 else 100

        return Response({
            "total_sinistres": total,
            "total_montant_reclame": total_reclame,
            "total_montant_indemnise": total_indemnise,
            "sinistres_regles": regles,
            "sinistres_en_cours": en_cours,
            "conformite_delegation_pourcentage": respect_delegation_pct
        })


# =========================================================================
# 4. CONVENTIONS ASSUREURS
# =========================================================================
class ConventionAssureurViewSet(viewsets.ModelViewSet):
    queryset = ConventionAssureur.objects.all().order_by("compagnie")
    serializer_class = ConventionAssureurSerializer
    pagination_class = ResultsOnlyPagination
    permission_classes = [permissions.AllowAny]



# =========================================================================
# 5. GED PROBANTE LE PHARE
# =========================================================================
class DocumentGEDViewSet(viewsets.ModelViewSet):
    queryset = DocumentGED.objects.all().order_by("-date_upload")
    serializer_class = DocumentGEDSerializer
    pagination_class = ResultsOnlyPagination
    permission_classes = [permissions.AllowAny]



# =========================================================================
# 6. CONFORMITÉ & AUDIT TRAIL CIMA
# =========================================================================
class AuditLogCimaViewSet(viewsets.ReadOnlyModelViewSet):
    # Journal en lecture seule (écriture : autorisations/journal.py ; la table refuse toute
    # modification ou suppression)
    queryset = AuditLogCima.objects.all().order_by("-date_creation")
    serializer_class = AuditLogCimaSerializer
    pagination_class = ResultsOnlyPagination
    permission_classes = [permissions.IsAuthenticated]


    @action(detail=False, methods=["get"])
    def kpis(self, request):
        return Response({
            "agrement_courtier": "N° 021/MEF/DGTCP/DA - République de Côte d'Ivoire",
            "caution_financiere_montant": 50000000,
            "caution_banque": "Société Générale Côte d'Ivoire (SGCI)",
            "caution_statut": "Valide & Conforme CIMA",
            "delai_moyen_reversement_jours": 22.4,
            "delai_reglementaire_max_jours": 30,
            "taux_conformite_art13": "100%",
            "taux_respect_plafonds_delegation": "98.5%",
            "alertes_actives": 0
        })

    @action(detail=False, methods=["get"])
    def etats_cima(self, request):
        """Production des états statistiques normalisés C1, C2, C3 pour l'autorité de contrôle CIMA"""
        return Response({
            "etat_c1": {
                "titre": "État C1 - Bordereau Annuel des Émissions et Recouvrements de Primes (Art. 13 CIMA)",
                "exercice": 2026,
                "courtier": "LE PHARE COURTAGE & GESTION DÉLÉGUÉE",
                "agrement": "021/MEF/DGTCP/DA",
                "lignes": [
                    {"branche": "Automobile", "primes_emises": 65000000, "primes_encaissees": 62500000, "taux_recouvrement": "96.2%", "commissions_dues": 6500000},
                    {"branche": "Santé Groupe", "primes_emises": 82000000, "primes_encaissees": 80000000, "taux_recouvrement": "97.5%", "commissions_dues": 8200000},
                    {"branche": "IARD & Risques Divers", "primes_emises": 45000000, "primes_encaissees": 43500000, "taux_recouvrement": "96.7%", "commissions_dues": 6750000},
                    {"branche": "Transport Facultés", "primes_emises": 28000000, "primes_encaissees": 28000000, "taux_recouvrement": "100.0%", "commissions_dues": 2800000},
                ],
                "total_primes_encaissees": 214000000,
                "total_commissions": 24250000,
                "statut_art13": "100% Conforme - Aucune attestation émise sans encaissement"
            },
            "etat_c2": {
                "titre": "État C2 - Registre des Sinistres Sous Mandat Délégué (Code CIMA Livre V)",
                "exercice": 2026,
                "sinistres_declares": SinistreDelegue.objects.count(),
                "montant_reclame_total": float(SinistreDelegue.objects.aggregate(t=Sum("montant_reclame"))["t"] or 0),
                "montant_indemnise_total": float(SinistreDelegue.objects.aggregate(t=Sum("montant_indemnise"))["t"] or 0),
                "delai_moyen_reglement_jours": 14.5,
                "delai_legal_cima_jours": 30,
                "taux_respect_plafonds": "98.5%"
            },
            "etat_c3": {
                "titre": "État C3 - Registre des Rétrocessions et Commissions d'Apporteurs (Plafonds CIMA)",
                "exercice": 2026,
                "apporteurs_actifs": 18,
                "total_commissions_versees": 11450000,
                "conformite_plafonds_cima": "Conforme (Taux maximum légal respecté sur toutes les branches)"
            }
        })


# =========================================================================
# 7. QUITTANCES OFFICIELLES CIMA (ARTICLE 13)
# =========================================================================
class QuittanceCimaViewSet(viewsets.ModelViewSet):
    queryset = QuittanceCima.objects.all().order_by("-date_encaissement")
    serializer_class = QuittanceCimaSerializer
    pagination_class = ResultsOnlyPagination
    permission_classes = [permissions.AllowAny]


    def create(self, request, *args, **kwargs):
        count = QuittanceCima.objects.count() + 1
        num = f"QUIT-CIMA-2026-{str(count).zfill(3)}"
        data = request.data.copy()
        data["numero_quittance"] = num
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Log in Audit Trail
        completer_audit(
            request,
            description=f"Émission Quittance CIMA {num} pour {serializer.data.get('souscripteur')} ({serializer.data.get('montant_encaisse')} FCFA)",
            apres={"numero_quittance": num, "police": serializer.data.get("police_num")},
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# =========================================================================
# 8. BORDEREAUX DE REVERSEMENT ASSUREURS (DÉLAI 30 JOURS CIMA)
# =========================================================================
class BordereauReversementViewSet(viewsets.ModelViewSet):
    queryset = BordereauReversement.objects.all().order_by("-date_generation")
    serializer_class = BordereauReversementSerializer
    pagination_class = ResultsOnlyPagination
    permission_classes = [permissions.AllowAny]


    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        bordereau = self.get_object()
        bordereau.statut = "Validé"
        bordereau.ordre_virement_ref = f"OV-SGCI-2026-{str(bordereau.id).zfill(4)}"
        bordereau.save()

        completer_audit(
            request,
            description=f"Validation bordereau {bordereau.reference} vers {bordereau.compagnie} ({bordereau.net_a_reverser:,.0f} FCFA) - Réf virement {bordereau.ordre_virement_ref}",
            apres={"reference": bordereau.reference, "compagnie": bordereau.compagnie},
        )
        return Response(BordereauReversementSerializer(bordereau).data)

