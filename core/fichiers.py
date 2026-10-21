"""
Fichiers envoyés (GED, pièces jointes des devis et contrats, pièces d'identité Santé, détails de commission) :
liens signés et contrôle des envois.

- Les fichiers de MEDIA_ROOT ne sont plus servis librement sous /media/ (auparavant en DEBUG, sans aucun
  contrôle : quiconque connaissait ou devinait l'adresse lisait la pièce). Chaque adresse produite par l'API
  (FileField.url) porte une signature à durée limitée (MEDIA_SIGNATURE_DUREE, 2 h par défaut), délivrée
  seulement dans une réponse que la garde centrale a autorisée ; servir_media refuse toute adresse sans
  signature valide. Les écrans continuent d'ouvrir les liens tels quels.
- valider_fichier : extension autorisée, taille maximale et contenu réel (signature binaire du format), pour
  qu'un fichier HTML, SVG ou exécutable renommé en .pdf ne soit pas accepté (questionnaires prospects : Word et
  Excel compris).
"""

import mimetypes
import posixpath

from django.conf import settings
from django.core import signing
from django.core.files.storage import FileSystemStorage
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.utils._os import safe_join

SEL_SIGNATURE = "lephare.media"
TAILLE_MAX_DEFAUT = 20 * 1024 * 1024
# Formats affichés dans le navigateur ; tout autre fichier est proposé au téléchargement
AFFICHABLES = {"application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp"}
# Début du contenu attendu pour chaque extension
SIGNATURES = {
    "pdf": (b"%PDF-",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "gif": (b"GIF87a", b"GIF89a"),
    "webp": (b"RIFF",),
    # Office : .docx / .xlsx sont des archives ZIP, .doc / .xls des documents composés OLE
    "docx": (b"PK\x03\x04",),
    "xlsx": (b"PK\x03\x04",),
    "doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    "xls": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
}


def _duree_signature():
    return int(getattr(settings, "MEDIA_SIGNATURE_DUREE", 2 * 3600))


def _signataire():
    return signing.TimestampSigner(salt=SEL_SIGNATURE)


def _nom_normalise(nom):
    return posixpath.normpath(str(nom).replace("\\", "/")).lstrip("/")


def signer(nom):
    """Signature horodatée du chemin relatif d'un fichier de MEDIA_ROOT."""
    nom = _nom_normalise(nom)
    return _signataire().sign(nom)[len(nom) + 1:]


def signature_valide(nom, signature):
    if not signature:
        return False
    nom = _nom_normalise(nom)
    try:
        return _signataire().unsign(f"{nom}:{signature}", max_age=_duree_signature()) == nom
    except signing.BadSignature:  # signature fausse ou expirée (SignatureExpired en hérite)
        return False


class StockageSigne(FileSystemStorage):
    """Stockage par défaut : adresses des fichiers signées (voir servir_media)."""

    def url(self, name):
        adresse = super().url(name)
        if name is None:
            return adresse
        return f"{adresse}{'&' if '?' in adresse else '?'}signature={signer(name)}"


def servir_media(request, chemin):
    """GET /media/<chemin>?signature=… : fichier envoyé, seulement avec une signature valide et non expirée."""
    if not signature_valide(chemin, request.GET.get("signature")):
        return HttpResponseForbidden("Lien de fichier invalide ou expiré : rouvrez le document depuis l'application.")
    try:
        complet = safe_join(settings.MEDIA_ROOT, _nom_normalise(chemin))
    except Exception:  # sortie de MEDIA_ROOT (« .. »)
        raise Http404("Fichier introuvable")
    try:
        fichier = open(complet, "rb")
    except OSError:
        raise Http404("Fichier introuvable")
    type_mime = mimetypes.guess_type(complet)[0] or "application/octet-stream"
    reponse = FileResponse(fichier, content_type=type_mime, as_attachment=type_mime not in AFFICHABLES,
                           filename=posixpath.basename(_nom_normalise(chemin)))
    reponse["X-Content-Type-Options"] = "nosniff"
    reponse["Cache-Control"] = "private, max-age=300"
    return reponse


def valider_fichier(fichier, extensions, taille_max=TAILLE_MAX_DEFAUT):
    """Contrôle d'un fichier envoyé : extension parmi `extensions`, taille au plus `taille_max`, contenu
    conforme à l'extension. Lève serializers.ValidationError ; renvoie le fichier."""
    from rest_framework import serializers

    if not fichier:
        return fichier
    nom = getattr(fichier, "name", "") or ""
    extension = nom.rsplit(".", 1)[-1].lower() if "." in nom else ""
    if extension not in extensions:
        raise serializers.ValidationError(
            f"Format non autorisé ({extension or 'sans extension'}) : {', '.join(e.upper() for e in extensions)} seulement.")
    taille = getattr(fichier, "size", None) or 0
    if taille > taille_max:
        raise serializers.ValidationError(f"Fichier trop volumineux : {taille_max // (1024 * 1024)} Mo au plus.")
    if taille == 0:
        raise serializers.ValidationError("Fichier vide.")
    debut = b""
    try:
        position = fichier.tell()
        debut = fichier.read(16)
        fichier.seek(position)
    except Exception:
        pass
    attendus = SIGNATURES.get(extension)
    if attendus and not any(debut.startswith(s) for s in attendus):
        raise serializers.ValidationError(f"Le contenu du fichier ne correspond pas à un fichier {extension.upper()}.")
    if extension == "webp" and debut[8:12] != b"WEBP":
        raise serializers.ValidationError("Le contenu du fichier ne correspond pas à un fichier WEBP.")
    return fichier
