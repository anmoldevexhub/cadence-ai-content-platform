import json
import os

filepath = 'sqlite_dump.json'

print("Reading dump...")
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace NUL characters in JSON string
if '\u0000' in content or '\\u0000' in content:
    print("Found NUL characters! Cleaning...")
    content = content.replace('\u0000', '')
    content = content.replace('\\u0000', '')
else:
    print("No NUL characters found in direct string scan. Let's load as JSON to be sure.")

print("Writing clean dump...")
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Cleaned successfully.")
