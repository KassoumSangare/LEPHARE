import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uranus.settings')
django.setup()

from django.db import connection

def load_file(sql_file):
    if not os.path.exists(sql_file):
        print("File not found:", sql_file)
        return
    with open(sql_file, 'r', encoding='utf-8') as f:
        content = f.read()

    connection.ensure_connection()
    raw_conn = connection.connection
    with raw_conn.cursor() as cur:
        cur.execute("SET session_replication_role = 'replica';")
    
    parts = content.split('COPY ')
    for part in parts:
        if not part.strip():
            continue
        full_stmt = 'COPY ' + part.strip()
        lines = full_stmt.split('\n')
        header = lines[0]
        data_lines = []
        for l in lines[1:]:
            if l.strip() == '\\.':
                break
            data_lines.append(l)
        
        data_text = '\n'.join(data_lines) + '\n'
        copy_sql = header.replace('FROM stdin;', 'FROM STDIN')
        try:
            with raw_conn.cursor() as raw_cur:
                with raw_cur.copy(copy_sql) as copy:
                    copy.write(data_text)
            raw_conn.commit()
            print("Successfully loaded:", header[:60])
        except Exception as e:
            print("Error loading", header[:60], ":", e)
            raw_conn.rollback()

    with raw_conn.cursor() as cur:
        cur.execute("SET session_replication_role = 'origin';")
    raw_conn.commit()

print("--- Loading Parent References ---")
load_file('seed_refs.sql')
print("--- Loading Voyage Data ---")
load_file('seed_voyage_data.sql')
print("All Seeds Finished!")
