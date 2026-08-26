from pathlib import Path


def test_v11_rca_upsample_removed():
    # v1.1'in 24-örneklik upsample'ı RCA 3->2 ve toolcall 75->62 regresyonuna yol açtı.
    # build_tools.py:124 data/sft/tools/*.jsonl glob'ladığı için, silinmezse v1.2 build'ine
    # geri girer ve regresyonu tekrar tetikler.
    assert not Path("data/sft/tools/server_rca_v11_tr.jsonl").exists()
