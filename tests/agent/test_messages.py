from agent.messages import Message


def test_roundtrip_dict():
    m = Message(role="user", content="selam")
    assert m.to_dict() == {"role": "user", "content": "selam"}
    assert Message.from_dict({"role": "user", "content": "selam"}) == m
