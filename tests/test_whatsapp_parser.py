import tempfile
from src.ingestion.whatsapp_parser import parse_whatsapp_chat

def test_parser_basic():
    sample = "24/08/25, 10:15 - Jane Doe: Hiring for Backend Dev. Email us."
    with tempfile.NamedTemporaryFile('w+', delete=False) as tf:
        tf.write(sample)
        tf.flush()
        msgs = parse_whatsapp_chat(tf.name)
        assert len(msgs) == 1
        assert msgs[0]["sender"] == "Jane Doe"
        assert "Hiring" in msgs[0]["message"]
