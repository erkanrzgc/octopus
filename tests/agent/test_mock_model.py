from agent.backends.mock_model import ScriptedModel
from agent.messages import Message


def test_returns_replies_in_order():
    m = ScriptedModel(["birinci", "ikinci"])
    assert m([Message("user", "x")]) == "birinci"
    assert m([Message("user", "x")]) == "ikinci"


def test_exhausted_returns_default():
    m = ScriptedModel([])
    assert isinstance(m([Message("user", "x")]), str)
