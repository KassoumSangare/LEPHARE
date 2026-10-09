"""
Journal d'audit centralisé (table institutionnel_auditlogcima, en ajout seul).

journaliser() est le seul point d'écriture : la garde centrale (garde.py) l'appelle pour chaque
opération d'écriture de l'API, chaque refus et chaque connexion ; les écrans qui veulent tracer un
évènement particulier l'appellent aussi. Une erreur d'écriture du journal n'interrompt jamais
l'opération métier (elle est signalée dans les journaux du serveur).
"""

import json
import logging
import re
from datetime import date, datetime
from decimal import Decimal

logger = logging.getLogger("lephare.audit")

RESULTAT_SUCCES = "SUCCES"
RESULTAT_ECHEC = "ECHEC"
RESULTAT_REFUS = "REFUS"

# Champs jamais recopiés dans le journal
CLES_SECRETES = re.compile(r"pass|mot_?de_?passe|token|secret|jeton_code|code_acces", re.I)
TAILLE_MAX = 30000


def adresse_ip(request):
    if request is None:
        return None
    meta = getattr(request, "META", {}) or {}
    for cle in ("HTTP_CF_CONNECTING_IP", "HTTP_X_FORWARDED_FOR", "HTTP_X_REAL_IP", "REMOTE_ADDR"):
        valeur = (meta.get(cle) or "").split(",")[0].strip()
        if valeur:
            return valeur[:45]
    return None


def nettoyer(valeur, profondeur=0):
    """Valeur enregistrable en JSON, sans secret, bornée en taille."""
    if profondeur > 6:
        return "…"
    if isinstance(valeur, dict) or hasattr(valeur, "items"):
        try:
            elements = valeur.items()
        except Exception:
            return str(valeur)[:500]
        return {
            str(k): ("***" if CLES_SECRETES.search(str(k)) else nettoyer(v, profondeur + 1))
            for k, v in elements
        }
    if isinstance(valeur, (list, tuple, set)):
        liste = list(valeur)
        resultat = [nettoyer(v, profondeur + 1) for v in liste[:200]]
        if len(liste) > 200:
            resultat.append(f"… {len(liste) - 200} élément(s) de plus")
        return resultat
    if isinstance(valeur, Decimal):
        return float(valeur)
    if isinstance(valeur, (datetime, date)):
        return valeur.isoformat()
    if valeur is None or isinstance(valeur, (bool, int, float)):
        return valeur
    if hasattr(valeur, "name") and hasattr(valeur, "read"):  # fichier envoyé
        return f"fichier : {getattr(valeur, 'name', '')}"
    texte = str(valeur)
    return texte if len(texte) <= 2000 else texte[:2000] + "…"


def _borner(valeur):
    if valeur is None:
        return None
    propre = nettoyer(valeur)
    if len(json.dumps(propre, default=str)) > TAILLE_MAX:
        return {"tronque": True, "extrait": json.dumps(propre, default=str)[:TAILLE_MAX]}
    return propre


def journaliser(*, request=None, utilisateur=None, auteur="", module="", action="", description="",
                objet_type="", objet_id="", resultat=RESULTAT_SUCCES, avant=None, apres=None, motif="",
                statut_http=None, details=None, type_operation=""):
    from institutionnel.models import AuditLogCima

    if utilisateur is None and request is not None:
        candidat = getattr(request, "user", None)
        if candidat is not None and getattr(candidat, "is_authenticated", False):
            utilisateur = candidat
    if not auteur:
        auteur = (getattr(utilisateur, "email", "") or "anonyme") if utilisateur else "anonyme"
    try:
        AuditLogCima.objects.create(
            type_operation=(type_operation or module or "SECURITE").upper()[:60],
            description=(description or action or "")[:4000],
            auteur=str(auteur)[:100],
            statut_conformite="CONFORME" if resultat == RESULTAT_SUCCES else resultat,
            reference_reglementaire="Journal d'audit LE PHARE",
            details_json=_borner(details) or {},
            utilisateur=utilisateur if utilisateur and getattr(utilisateur, "pk", None) else None,
            module=(module or "")[:40],
            action=(action or "")[:80],
            objet_type=(objet_type or "")[:60],
            objet_id=str(objet_id or "")[:80],
            resultat=resultat,
            adresse_ip=adresse_ip(request),
            methode=(getattr(request, "method", "") or "")[:8],
            chemin=(getattr(request, "path", "") or "")[:255],
            statut_http=statut_http,
            valeur_avant=_borner(avant),
            valeur_apres=_borner(apres),
            motif=(motif or "")[:2000],
        )
    except Exception:  # le journal ne doit jamais bloquer l'opération
        logger.exception("Écriture du journal d'audit impossible (%s %s)", module, action)


def completer_audit(request, **valeurs):
    """Précise la ligne que la garde écrira pour cette requête (description, objet, avant / après).
    Hors garde (appel interne), écrit directement une ligne."""
    contexte = getattr(request, "_lephare_audit", None)
    if contexte is not None:
        contexte.setdefault("complements", {}).update({k: v for k, v in valeurs.items() if v is not None})
        return
    journaliser(request=request, **valeurs)
