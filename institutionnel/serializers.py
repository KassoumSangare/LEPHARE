from decimal import Decimal

from rest_framework import serializers

from core.fichiers import valider_fichier
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


class CrmLeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrmLead
        fields = "__all__"
        # Référence attribuée par le serveur à la création (CrmLeadViewSet.perform_create)
        read_only_fields = ("id_lead", "date_creation", "date_maj")
        # « — À attribuer — » dans l'écran : un prospect peut ne pas encore avoir de commercial
        extra_kwargs = {"commercial_attribue": {"allow_blank": True}}

    def validate_statut(self, valeur):
        if valeur not in CrmLead.STATUTS:
            raise serializers.ValidationError(f"Étape inconnue (attendu : {', '.join(CrmLead.STATUTS)}).")
        return valeur


class CrmInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrmInteraction
        fields = "__all__"


# ---------------------------------------------------------------- règles des sinistres délégués
STATUT_REGLE = "Réglé"
STATUT_CLOTURE = "Clôturé"
# Statuts qui excluent un (nouveau) règlement
STATUTS_SANS_REGLEMENT = (STATUT_REGLE, STATUT_CLOTURE, "Rejeté")
# Données d'un dossier réglé qui ne changent plus
CHAMPS_FIGES_APRES_REGLEMENT = ("numero_sinistre", "police_num", "assure_nom", "compagnie", "montant_reclame")
PLAFOND_DELEGATION_DEFAUT = Decimal("5000000")


def plafond_delegation(compagnie):
    """Plafond de délégation de la convention de la compagnie : convention active du même nom d'abord, puis
    rapprochement sur le début du nom (règle historique), 5 000 000 F à défaut de convention."""
    nom = (compagnie or "").strip()
    convention = None
    if nom:
        conventions = ConventionAssureur.objects.all()
        convention = (conventions.filter(compagnie__iexact=nom, statut="Actif").first()
                      or conventions.filter(compagnie__iexact=nom).first()
                      or conventions.filter(compagnie__icontains=nom[:6]).first())
    return Decimal(convention.plafond_delegation_sinistre) if convention else PLAFOND_DELEGATION_DEFAUT


def sinistre_regle(sinistre):
    """Dossier réglé (indemnité versée ou quittance émise) : plus de règlement, de réouverture ni de suppression."""
    return (sinistre.statut == STATUT_REGLE or sinistre.quittance_subrogative_emise
            or (sinistre.montant_indemnise or 0) > 0)


def indemnite_reglee(sinistre):
    """Règlement effectivement enregistré : seule condition d'établissement d'une quittance subrogative."""
    return sinistre.statut in (STATUT_REGLE, STATUT_CLOTURE) and (sinistre.montant_indemnise or 0) > 0


class SinistreDelegueSerializer(serializers.ModelSerializer):
    class Meta:
        model = SinistreDelegue
        fields = "__all__"
        # Posés par le serveur (actions règlement, demande d'accord, quittance subrogative ; plafond de la
        # convention ; journal du dossier) : une création ou une modification générique ne les écrit pas
        read_only_fields = (
            "montant_indemnise", "quittance_subrogative_emise", "accord_prealable_requis", "delegation_respectee",
            "historique_evenements", "date_creation", "date_maj",
        )

    def validate_montant_reclame(self, valeur):
        if valeur is not None and valeur < 0:
            raise serializers.ValidationError("Le montant réclamé ne peut pas être négatif.")
        return valeur

    def validate(self, data):
        sinistre, statut = self.instance, data.get("statut")
        if sinistre is None:
            if statut in (STATUT_REGLE, STATUT_CLOTURE):
                raise serializers.ValidationError(
                    {"statut": "Un sinistre est déclaré avant d'être réglé : le règlement passe par l'action dédiée."})
            return data
        if statut == STATUT_REGLE and sinistre.statut != STATUT_REGLE:
            raise serializers.ValidationError(
                {"statut": "Le statut « Réglé » est posé par l'action de règlement (contrôle du plafond de délégation)."})
        if sinistre_regle(sinistre):
            if statut is not None and statut not in (sinistre.statut, STATUT_CLOTURE):
                raise serializers.ValidationError(
                    {"statut": f"Sinistre réglé : seul le passage au statut « {STATUT_CLOTURE} » est possible."})
            for champ in CHAMPS_FIGES_APRES_REGLEMENT:
                if champ in data and data[champ] != getattr(sinistre, champ):
                    raise serializers.ValidationError({champ: "Sinistre réglé : cette donnée n'est plus modifiable."})
        return data


class ConventionAssureurSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConventionAssureur
        fields = "__all__"


class DocumentGEDSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentGED
        fields = "__all__"

    def validate_fichier(self, value):
        if value:
            name = getattr(value, "name", "")
            if not name.lower().endswith(".pdf"):
                raise serializers.ValidationError("Format non autorisé : Le fichier doit impérativement être un document au format PDF (.pdf).")
            # Contenu réellement PDF et taille bornée (core/fichiers.py)
            valider_fichier(value, ("pdf",))
        return value


class AuditLogCimaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLogCima
        fields = "__all__"


class QuittanceCimaSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuittanceCima
        fields = "__all__"


class BordereauReversementSerializer(serializers.ModelSerializer):
    jours_restants_cima = serializers.SerializerMethodField()
    statut_delai_cima = serializers.SerializerMethodField()

    class Meta:
        model = BordereauReversement
        fields = "__all__"

    def get_jours_restants_cima(self, obj):
        import datetime
        if not obj.date_echeance_30j:
            return 30
        today = datetime.date.today()
        diff = (obj.date_echeance_30j - today).days
        return diff

    def get_statut_delai_cima(self, obj):
        jours = self.get_jours_restants_cima(obj)
        if jours < 0:
            return "HORS_DELAI"
        elif jours <= 5:
            return "ALERTE_IMMINENTE"
        return "CONFORME"
