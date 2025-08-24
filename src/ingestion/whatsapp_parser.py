# src/pasa/ingestion/whatsapp_parser.py

import re
from datetime import datetime
from typing import List, Dict

# Regex to match message starts including multiline support
MESSAGE_REGEX = re.compile(
    r'^(\d{1,2}/\d{1,2}/\d{2,4}),?\s*"?(?P<time>\d{1,2}:\d{2}(?:\s?[apAP]\.?m\.?)?)"?\s*-\s*(?P<sender>.*?):\s*(?P<msg>.*)',
    re.MULTILINE
)

def parse_whatsapp_chat(filepath: str) -> List[Dict]:
    messages = []
    buffer = None

    with open(filepath, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            match = MESSAGE_REGEX.match(line)
            if match:
                # Save previous buffered message
                if buffer:
                    messages.append(buffer)
                date_str, time_str = match.group(1), match.group('time')
                ts = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%y %I:%M").isoformat(sep=' ')
                buffer = {
                    "timestamp": ts,
                    "sender": match.group('sender'),
                    "message": match.group('msg').strip()
                }
            else:
                # Continuation line for multiline message
                if buffer:
                    buffer["message"] += "\n" + line.strip()

    if buffer:
        messages.append(buffer)
    return messages
