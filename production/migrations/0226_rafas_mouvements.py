# RAFAS : incorporations et retraits de familles en cours d'exercice (demande du 2026-11-20 : « permet l'incorporation et le retrait en
# RAFAS »). Un mouvement fait entrer des familles dans un collège de l'exercice ou les en fait sortir, à une date d'effet ; il ajuste les
# cotisations de l'exercice (cotisation annuelle par famille x familles, au prorata des jours restants si demandé), donc les honoraires du
# gestionnaire, la commission du cabinet et l'enveloppe des sinistres (sante/rafas.py, budget_ajuste). Annulé avec un motif, jamais effacé.
# Retour : python manage.py migrate production 0225

from django.db import migrations

CREATION = """
CREATE TABLE IF NOT EXISTS public.lephare_rafas_mouvement (
    idmouvement serial PRIMARY KEY,
    idexercice integer NOT NULL REFERENCES public.lephare_rafas_exercice (idexercice) ON DELETE CASCADE,
    numero varchar(20) NOT NULL,
    nature varchar(13) NOT NULL CHECK (nature IN ('INCORPORATION', 'RETRAIT')),
    code_college varchar(40) NOT NULL,
    date_effet date NOT NULL,
    familles integer NOT NULL CHECK (familles > 0),
    personnes integer,
    adherents jsonb NOT NULL DEFAULT '[]'::jsonb,
    cotisation numeric(15, 2) NOT NULL,
    prorata boolean NOT NULL DEFAULT false,
    fraction numeric(9, 6) NOT NULL DEFAULT 1,
    montant numeric(15, 2) NOT NULL,
    motif text NOT NULL DEFAULT '',
    idoperateur integer,
    operateur varchar(150) NOT NULL DEFAULT '',
    date_saisie timestamptz NOT NULL DEFAULT now(),
    annule boolean NOT NULL DEFAULT false,
    motif_annulation text NOT NULL DEFAULT '',
    date_annulation timestamptz
);
CREATE INDEX IF NOT EXISTS lephare_rafas_mouvement_exercice ON public.lephare_rafas_mouvement (idexercice);
"""


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0225_encaissement_ristourne"),
    ]

    operations = [
        migrations.RunSQL(CREATION, "DROP TABLE IF EXISTS public.lephare_rafas_mouvement;"),
    ]
