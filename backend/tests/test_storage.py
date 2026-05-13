from app.services import storage


def test_path_builders():
    assert storage.submission_path("a1", "s1", "proof.pdf") == "submissions/a1/s1/proof.pdf"
    assert storage.submission_path("a1", "s1", "../etc/passwd") == "submissions/a1/s1/passwd"
    assert storage.submission_path("a1", "s1", "x\\y.png") == "submissions/a1/s1/x_y.png"
    assert storage.solution_path("a1") == "solutions/a1.md"


def test_local_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_LOCAL_ROOT", tmp_path)
    monkeypatch.setattr(storage, "_supabase_configured", lambda: False)
    key = storage.upload_bytes("submissions", "submissions/a/s/x.txt", b"hello", "text/plain")
    assert key == "submissions/a/s/x.txt"
    assert storage.read_bytes("submissions", key) == b"hello"
    assert storage.signed_url("submissions", key).startswith("/api/files/")
