import sqlite3

conn = sqlite3.connect('creative_automation.db')

print('=== CAMPAIGNS ===')
cursor = conn.execute('SELECT id, status, product_ids FROM campaigns')
for row in cursor.fetchall():
    print(f'{row[0]} - Status: {row[1]} - Products: {row[2]}')

print('\n=== VARIANTS ===')
cursor = conn.execute('SELECT campaign_id, product_id, aspect_ratio FROM variants')
variants = cursor.fetchall()
for row in variants:
    print(f'{row[0]} / {row[1]} / {row[2]}')

print(f'\nTotal: {len(variants)} variants')

print('\n=== ERRORS ===')
cursor = conn.execute('SELECT COUNT(*) FROM errors')
error_count = cursor.fetchone()[0]
print(f'Total errors: {error_count}')

print('\n=== ALERTS ===')
cursor = conn.execute('SELECT campaign_id, issue_type, recipient, sent_at FROM alerts ORDER BY sent_at DESC LIMIT 5')
alerts = cursor.fetchall()
if alerts:
    for row in alerts:
        print(f'{row[0]} - {row[1]} - To: {row[2]} - Sent: {row[3]}')
    print(f'\nTotal alerts: {len(list(conn.execute("SELECT * FROM alerts")))}')
else:
    print('No alerts generated yet')

print('\n=== CAMPAIGN STATUS ===')
cursor = conn.execute('SELECT id, status FROM campaigns WHERE status != "completed"')
active = cursor.fetchall()
for row in active:
    print(f'{row[0]} - Status: {row[1]}')


conn.close()
