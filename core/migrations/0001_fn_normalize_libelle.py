# migrations/000X_create_trigger_function.py
from django.db import migrations

trigger_function = """
CREATE OR REPLACE FUNCTION fn_normalize_libelle()
RETURNS TRIGGER AS $$
BEGIN
    NEW.libelle := upper(regexp_replace(trim(NEW.libelle), '\\s+', ' ', 'g'));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

def create_function(apps, schema_editor):
    schema_editor.execute(trigger_function)

def drop_function(apps, schema_editor):
    schema_editor.execute("DROP FUNCTION IF EXISTS fn_normalize_libelle();")

class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunPython(create_function, reverse_code=drop_function),
    ]
