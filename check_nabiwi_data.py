#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('data/gridledger.db')
cursor = conn.cursor()

# Check sms_raw table schema
cursor.execute('PRAGMA table_info(sms_raw)')
print('SMS Raw table schema:')
for row in cursor.fetchall():
    print(row)

# Check all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('\nAll tables:', [t[0] for t in tables])

# Check if phone +265998265527 exists in sms_raw
cursor.execute('SELECT COUNT(*) FROM sms_raw WHERE phone_number = ?', ('+265998265527',))
count = cursor.fetchone()[0]
print(f'\nSMS messages from +265998265527: {count}')

# Check some sample messages
cursor.execute('SELECT phone_number, content, timestamp FROM sms_raw WHERE phone_number = ? LIMIT 3', ('+265998265527',))
print('\nSample messages:')
for row in cursor.fetchall():
    print(f'Phone: {row[0]}, Content: {row[1][:50]}..., Time: {row[2]}')

conn.close()