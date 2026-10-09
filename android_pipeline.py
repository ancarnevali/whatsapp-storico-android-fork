#!/usr/bin/env python3
"""Android front-end for whatsapp-storico.

Exports an Android WhatsApp database with WhatsApp Chat Exporter (-a), tags
Android system events with the iOS code (message_type 6) so update.py filters
them the same way, then runs update.py in --source json mode.

Inputs (one of):
  --db msgstore.db                      decrypted database (rooted phone / ADB)
  --backup msgstore.db.crypt15 [--key]  E2E backup + 64-hex key or key file
Optional: --wa wa.db (contact names) or --vcf contacts.vcf --cc 34
"""
import argparse, datetime as dt, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent
# Meta records produced by the *regular* Android path: real messages, keep them.
KEEP_META_PREFIXES = ('Message deleted', 'Location shared:', 'The message is binary data')


def exporter():
    # Same interpreter (venv/conda/Windows, no PATH needed), via wce_run.py which
    # guards an upstream crash on orphan vCard rows.
    return [sys.executable, str(ROOT / 'wce_run.py')]


def normalize(src, dst):
    data = json.loads(src.read_text(encoding='utf-8'))
    tagged = 0
    for chat in data.values():
        for m in chat.get('messages', {}).values():
            if not m.get('meta') or m.get('message_type') is None:
                continue  # normal message, or call record (already excluded upstream)
            text = m.get('data') or ''
            if m.get('message_type') == 7 or not str(text).startswith(KEEP_META_PREFIXES):
                m['android_message_type'] = m['message_type']
                m['message_type'] = 6  # iOS system-event code, filtered by update.py
                tagged += 1
    dst.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    return len(data), tagged


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument('--db', help='decrypted msgstore.db')
    src.add_argument('--backup', help='msgstore.db.crypt14/15')
    p.add_argument('--key', help='key file or 64-hex key (crypt15); omit to be prompted')
    p.add_argument('--wa', help='wa.db for contact names')
    p.add_argument('--vcf', help='contacts .vcf for names (if no wa.db)')
    p.add_argument('--cc', help='default country code for --vcf, e.g. 34 or 39')
    p.add_argument('--first-year', default='2014')
    p.add_argument('--no-open', action='store_true')
    a = p.parse_args()

    run = ROOT / 'data/android-runs' / dt.datetime.now().strftime('%Y%m%d-%H%M%S')
    run.mkdir(parents=True)
    raw = run / 'android.json'
    cmd = exporter() + ['-a', '-o', str(run / 'html'), '-j', str(raw), '--no-html', '--no-banner']
    if a.db:
        cmd += ['-d', str(pathlib.Path(a.db).expanduser().resolve())]
    else:
        cmd += ['-b', str(pathlib.Path(a.backup).expanduser().resolve()), '-k'] + ([a.key] if a.key else [])
    if a.wa:
        cmd += ['-w', str(pathlib.Path(a.wa).expanduser().resolve())]
    if a.vcf:
        if not a.cc:
            p.error('--vcf requires --cc')
        cmd += ['--enrich-from-vcards', str(pathlib.Path(a.vcf).expanduser().resolve()), '--default-country-code', a.cc]
    if subprocess.run(cmd, cwd=run).returncode != 0:
        # Do not echo the command: it may contain the backup key.
        sys.exit('Exporter failed (see the messages above). Check key, backup file and --vcf.')
    if not raw.is_file():
        sys.exit('Exporter produced no JSON: check key / database.')

    norm = run / 'android_normalized.json'
    chats, tagged = normalize(raw, norm)
    print(f'{chats} chats exported, {tagged} Android system events tagged.')

    up = [sys.executable, str(ROOT / 'update.py'), '--source', 'json', '--json', str(norm),
          '--archive-db', str(ROOT / 'data/android_archive.sqlite'), '--first-year', a.first_year]
    subprocess.run(up + ([] if a.no_open else ['--open']), check=True)
    print('Dashboard:', ROOT / 'report/dashboard.html')


if __name__ == '__main__':
    main()
