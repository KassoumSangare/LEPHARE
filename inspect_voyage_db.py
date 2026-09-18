import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uranus.settings')
django.setup()

from django.db import connection

with connection.cursor() as c:
    c.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema='public' 
        AND (table_name LIKE '%pays%' OR table_name LIKE '%voyage%' OR table_name LIKE '%zone%')
        ORDER BY table_name;
    """)
    rows = c.fetchall()
    print("Tables trouvées:")
    for r in rows:
        print(" -", r[0])

    c.execute("""
        SELECT routine_name 
        FROM information_schema.routines 
        WHERE routine_schema='public' 
        AND (routine_name LIKE '%voyage%' OR routine_name LIKE '%pays%')
        ORDER BY routine_name;
    """)
    procs = c.fetchall()
    print("\nProcédures stockées:")
    for p in procs:
        print(" -", p[0])
