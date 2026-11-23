# Informations visibles du cockpit et du tableau de bord par famille (8 droits « tableaux.* », 2026-11-23), appliquée en local
# le 2026-11-23 puis remplacée le même jour par un droit par bloc (migration 0017, demande : « chaque bloc du cockpit et du
# tableau de bord visible par un utilisateur qu'avec des droits »). Sans effet désormais : 0017 crée les droits des blocs,
# reprend les 8 anciens droits là où ils existent et les supprime.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("autorisations", "0015_rafas"),
    ]

    operations = [migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop)]
