from app.nlp.parser import parse_quick_task


def test_parser_extracts_tags_and_priority():
    r = parse_quick_task("Email Joel re SOW tomorrow 4pm #Acme @email +Joel p1")
    assert r["priority"] == "P1"
    assert r["project"] == "Acme"
    assert r["context"] == ["email"]
    assert r["people"] == ["Joel"]
    # due may vary by timezone parsing; assert it's set to something
    assert r["due"] is not None


def test_parser_handles_minimal_text():
    r = parse_quick_task("Buy milk")
    assert r["title"].lower().startswith("buy milk")
