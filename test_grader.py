"""Offline tests: scoring logic and request shape, using a fake client (no network)."""
from types import SimpleNamespace

from PIL import Image

import grader


def fake_client(payload):
    calls = []

    def create(**kw):
        calls.append(kw)
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="submit_grade", input=payload)])

    return SimpleNamespace(messages=SimpleNamespace(create=create)), calls


def test_total_is_summed_and_clamped():
    r = grader.parse_tool_input({"readable": True, "requested_score": 80, "correctness_score": 20,
                                 "algorithm_score": -5})
    assert (r.requested, r.correctness, r.algorithm, r.total) == (50, 20, 0, 70)


def test_unreadable_gives_no_grade():
    r = grader.parse_tool_input({"readable": False, "retake_advice": "too dark"})
    assert not r.readable and r.total == 0 and r.retake_advice == "too dark"


def test_missing_scores_raise():
    try:
        grader.parse_tool_input({"readable": True, "requested_score": 10})
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_grade_image_request_shape_and_downscale():
    client, calls = fake_client({"readable": True, "requested_score": 50, "correctness_score": 25,
                                 "algorithm_score": 25})
    r = grader.grade_image(Image.new("RGB", (4000, 3000), "white"), client=client)
    assert r.total == 100
    kw = calls[0]
    assert kw["tool_choice"] == {"type": "tool", "name": "submit_grade"}
    assert kw["messages"][0]["content"][0]["source"]["media_type"] == "image/jpeg"


def test_prepare_image_caps_edge():
    import base64, io
    _, b64 = grader.prepare_image(Image.new("RGB", (4000, 3000)))
    assert max(Image.open(io.BytesIO(base64.b64decode(b64))).size) == grader.MAX_EDGE
