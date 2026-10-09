#!/usr/bin/env python3
"""Run WhatsApp Chat Exporter 0.13.0 with a guard for orphan vCard rows.

On some Android databases a vCard message references a chat that the exporter
did not load (status, broadcast, deleted chat). Upstream then crashes with
AttributeError: 'NoneType' object has no attribute 'get_message'. The vCard
step only rewrites display text of messages already exported, so skipping
those rows changes no message counts.
"""
import sys

from Whatsapp_Chat_Exporter import __main__ as wce_main
from Whatsapp_Chat_Exporter import android_handler

_original = android_handler._process_vcard_row
skipped = 0


def _guarded(row, path, data):
    global skipped
    chat = data.get_chat(row["key_remote_jid"])
    if chat is None or chat.get_message(row["message_row_id"]) is None:
        skipped += 1
        return
    _original(row, path, data)


android_handler._process_vcard_row = _guarded

if __name__ == "__main__":
    sys.argv[0] = "wtsexporter"
    try:
        wce_main.main()
    finally:
        if skipped:
            print(f"[INFO] Skipped {skipped} vCard rows whose chat/message was not exported")
