# Règles des garanties Automobile lues par le barème (production 0164, fn_lephare_regle_auto) : case « Appliquée aussi
# par le barème ». Amorcée pour les trois règles que le moteur NSIA d'URANUS codait en dur, alignées sur lui pour que
# les primes ne changent pas :
#   - défense-recours 4 200 F avec les dommages ou la collision : catégorie 203 ajoutée (le moteur l'applique aux
#     tous risques catégorie 3 ; CP URANUS du devis 118620326D4480X : recours 420 F sur un mois) ;
#   - bris de glace offert avec les dommages ou la collision (et non les seuls dommages : offre tierce collision) ;
#   - recours anticipé offert avec les dommages ou la collision.
# La collision offerte avec les dommages reste à l'écran seulement : URANUS la facture dans les offres VTC.
# Retour : python manage.py migrate configuration_api 0090

from django.db import migrations, models

NSIA = 1


def amorcer(apps, schema_editor):
    Regle = apps.get_model("configuration_api", "AutoRegleInteraction")
    regles = Regle.objects.filter(IdCompagnie=NSIA)
    dr = regles.filter(IdSousGarantie=4, Type="PRIME_SI").first()
    if dr:
        categories = [c for c in dr.Categories.split(",") if c]
        if "203" not in categories:
            dr.Categories = ",".join(sorted(categories + ["203"]))
        dr.AppliqueeBareme = True
        dr.save(update_fields=["Categories", "AppliqueeBareme"])
    bdg = regles.filter(IdSousGarantie=9, Type="OFFERTE_SI").first()
    if bdg:
        bdg.Liees = "7,8"
        bdg.AppliqueeBareme = True
        bdg.Commentaire = "Bris de glace attribué sans prime avec les dommages au véhicule ou la collision (compris dans leur taux)."
        bdg.save(update_fields=["Liees", "AppliqueeBareme", "Commentaire"])
    regles.filter(IdSousGarantie=5, Type="OFFERTE_SI").update(AppliqueeBareme=True)


class Migration(migrations.Migration):

    dependencies = [
        ("configuration_api", "0090_auto_regles_interactions"),
    ]

    operations = [
        migrations.AddField(
            model_name="autoregleinteraction",
            name="AppliqueeBareme",
            field=models.BooleanField(db_column="appliqueebareme", default=False),
        ),
        migrations.RunPython(amorcer, migrations.RunPython.noop),
    ]
