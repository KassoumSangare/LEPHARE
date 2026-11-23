"""
Serveur de production de l'API LE PHARE (demande du 2026-11-23 : « l'application est très lente en production »).

`python manage.py runserver` est un serveur de développement : il recharge le code, vérifie les fichiers à chaque
modification et ne tient pas la charge de plusieurs postes. Ici l'API tourne sous waitress (serveur WSGI de production,
compatible Windows), avec plusieurs fils d'exécution pour servir les postes en parallèle.

Installation (une fois) :   pip install waitress
Lancement :                 python serveur_production.py            (127.0.0.1:8000, 16 fils)
Options :                   python serveur_production.py --port 8000 --hote 0.0.0.0 --fils 24

Le frontend (vite preview, voir LISEZMOI_PRODUCTION.md) renvoie /api vers 127.0.0.1:8000 : l'hôte par défaut suffit.
"""
import argparse
import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent
# settings.py lit .env dans le dossier courant (dotenv_values(".env")) : on se place à la racine du projet
os.chdir(RACINE)
sys.path.insert(0, str(RACINE))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uranus.settings")


def main():
    parametres = argparse.ArgumentParser(description="API LE PHARE en production (waitress)")
    parametres.add_argument("--hote", default=os.environ.get("LEPHARE_HOTE", "127.0.0.1"))
    parametres.add_argument("--port", type=int, default=int(os.environ.get("LEPHARE_PORT", "8000")))
    parametres.add_argument("--fils", type=int, default=int(os.environ.get("LEPHARE_FILS", "16")),
                            help="requêtes traitées en même temps (une connexion PostgreSQL par fil)")
    args = parametres.parse_args()

    try:
        from waitress import serve
    except ImportError:
        print("waitress n'est pas installé : lancez  pip install waitress  puis relancez ce script.")
        sys.exit(1)

    from django.conf import settings
    from uranus.wsgi import application

    if settings.DEBUG:
        print("ATTENTION : DEBUG est actif dans .env (DEBUG=1). En production, mettez DEBUG=0 : en DEBUG, Django garde "
              "chaque requête SQL en mémoire et l'application ralentit au fil de la journée.")
    print(f"API LE PHARE sur http://{args.hote}:{args.port}/api/ ({args.fils} fils). Ctrl+C pour arrêter.")
    serve(
        application,
        host=args.hote,
        port=args.port,
        threads=args.fils,
        # Exports Excel, bordereaux, imports de fichiers : réponses qui peuvent dépasser la minute
        channel_timeout=300,
        connection_limit=500,
        # Fichiers importés (classeurs, pièces jointes)
        max_request_body_size=200 * 1024 * 1024,
        ident="LEPHARE",
    )


if __name__ == "__main__":
    main()
