# Rôles et droits de LE PHARE : catalogue des droits, 8 rôles proposés (modifiables dans
# Administration > Rôles) et rattachement des comptes repris d'URANUS.
#
# URANUS ne connaissait qu'un niveau d'accès, is_admin (stdgroupeutilisateur, stdmenu et
# stdutilisateur sont vides) : les administrateurs reçoivent « Administrateur technique », les
# autres comptes « Gestionnaire » (production complète, comme dans URANUS, sans paramétrage).
# Les comptes gardent leur identifiant, leur e-mail de connexion, leur mot de passe (même hachage
# pbkdf2 que Django) et leur état actif / inactif.
# Retour : python manage.py migrate autorisations 0004

from django.db import migrations

from autorisations.catalogue import ROLES_INITIAUX, synchroniser_droits


def installer(apps, schema_editor):
    Droit = apps.get_model("autorisations", "Droit")
    Role = apps.get_model("autorisations", "Role")
    UtilisateurRole = apps.get_model("autorisations", "UtilisateurRole")
    User = apps.get_model("account", "UranusUser")

    synchroniser_droits(Droit)
    roles = {}
    for ordre, (code, libelle, description, droits) in enumerate(ROLES_INITIAUX, start=1):
        role, _ = Role.objects.get_or_create(code=code, defaults=dict(
            libelle=libelle, description=description, ordre=ordre, modifie_par="installation",
        ))
        role.droits.set(Droit.objects.filter(code__in=droits))
        roles[code] = role

    for utilisateur in User.objects.all():
        if UtilisateurRole.objects.filter(utilisateur=utilisateur).exists():
            continue
        code = "ADMIN_TECH" if utilisateur.is_admin else "GESTIONNAIRE"
        UtilisateurRole.objects.create(utilisateur=utilisateur, role=roles[code], attribue_par="reprise URANUS")


def retirer(apps, schema_editor):
    apps.get_model("autorisations", "UtilisateurRole").objects.all().delete()
    apps.get_model("autorisations", "Role").objects.all().delete()
    apps.get_model("autorisations", "Droit").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("autorisations", "0004_roles_droits"),
        ("account", "0003_derogation"),
    ]

    operations = [migrations.RunPython(installer, retirer)]
