import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uranus.settings')
django.setup()

from django.db import connection

sql_file = 'seed_voyage_data.sql'
with open(sql_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Execute COPY statements using psycopg
with connection.cursor() as cursor:
    # Split by COPY
    parts = content.split('COPY ')
    for part in parts:
        if not part.strip():
            continue
        full_stmt = 'COPY ' + part.strip()
        lines = full_stmt.split('\n')
        header = lines[0] # e.g. COPY public.stdpays (...) FROM stdin;
        data_lines = []
        for l in lines[1:]:
            if l.strip() == '\\.':
                break
            data_lines.append(l)
        
        data_text = '\n'.join(data_lines) + '\n'
        
        # Use psycopg copy
        raw_conn = connection.connection
        # header format: COPY table (cols) FROM stdin;
        copy_sql = header.replace('FROM stdin;', 'FROM STDIN')
        try:
            with raw_conn.cursor() as raw_cur:
                with raw_cur.copy(copy_sql) as copy:
                    copy.write(data_text)
            raw_conn.commit()
            print("Successfully loaded:", header[:50])
        except Exception as e:
            print("Error loading", header[:50], ":", e)
            raw_conn.rollback()

print("Done seeding voyage data!")
