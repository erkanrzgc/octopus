"""D1 — loop nihai cevabinda dusunce strip: gecmiste ham, kullaniciya temiz."""
from agent.loop import run_tool_loop
from agent.messages import Message
from agent.registry import ToolRegistry


def test_final_dusunce_icermez():
    # arac cagirmayan, dusunce+cevap ureten sahte model
    def fake_generate(messages):
        return "```dusunce\nBasit soru, arac gerekmez.\n```\nCevap: 42."

    res = run_tool_loop([Message("user", "kac eder?")], fake_generate,
                        ToolRegistry.default(), max_steps=1)
    assert res.final == "Cevap: 42."
    assert "dusunce" not in res.final


def test_gecmis_ham_dusunce_korur():
    # messages gecmisi HAM reply'i (dusunce dahil) tutmali — model kendi muhakemesini gorsun
    msgs = [Message("user", "kac eder?")]

    def fake_generate(messages):
        return "```dusunce\nIc muhakeme.\n```\nCevap: 42."

    run_tool_loop(msgs, fake_generate, ToolRegistry.default(), max_steps=1)
    assert any("```dusunce" in m.content for m in msgs if m.role == "assistant")
