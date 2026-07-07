from agent.cli import run_demo


def test_demo_runs_end_to_end():
    transcript = run_demo(scope=["10.10.10.0/24"])
    assert "nmap" in transcript
    assert "ARAÇ ÇIKTISI" in transcript or "10.10.10.5" in transcript
    assert transcript.strip().endswith("(demo bitti)")
