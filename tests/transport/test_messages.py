"""Tests for classical channel message types."""

from shorkin.transport._messages import (
    BasisAnnouncement,
    ErrorEstimationRequest,
    ErrorEstimationResponse,
    KeyConfirmation,
    KeyExchangeInit,
    SiftingResult,
    deserialize,
    serialize,
)


class TestKeyExchangeInit:
    def test_to_dict(self):
        msg = KeyExchangeInit(
            session_id="s1", protocol="bb84", num_qubits=4096,
            target_key_bits=256, peer_id="peer1"
        )
        d = msg.to_dict()
        assert d["session_id"] == "s1"
        assert d["protocol"] == "bb84"
        assert d["num_qubits"] == 4096

    def test_from_dict(self):
        msg = KeyExchangeInit.from_dict({
            "session_id": "s1", "protocol": "e91",
            "num_qubits": 8000, "target_key_bits": 128, "peer_id": "p"
        })
        assert msg.protocol == "e91"
        assert msg.num_qubits == 8000

    def test_roundtrip_json(self):
        msg = KeyExchangeInit(protocol="b92", num_qubits=2000)
        json_str = serialize(msg)
        restored = deserialize(json_str, KeyExchangeInit)
        assert restored.protocol == "b92"
        assert restored.num_qubits == 2000

    def test_auto_session_id(self):
        msg1 = KeyExchangeInit()
        msg2 = KeyExchangeInit()
        assert msg1.session_id != msg2.session_id  # UUIDs differ


class TestBasisAnnouncement:
    def test_roundtrip(self):
        msg = BasisAnnouncement(session_id="s1", bases=[0, 1, 0, 1])
        restored = deserialize(serialize(msg), BasisAnnouncement)
        assert restored.bases == [0, 1, 0, 1]


class TestSiftingResult:
    def test_roundtrip(self):
        msg = SiftingResult(session_id="s1", matching_indices=[0, 3, 5])
        restored = deserialize(serialize(msg), SiftingResult)
        assert restored.matching_indices == [0, 3, 5]


class TestErrorEstimation:
    def test_request_roundtrip(self):
        msg = ErrorEstimationRequest(
            session_id="s1", sample_indices=[1, 4], sample_values=[0, 1]
        )
        restored = deserialize(serialize(msg), ErrorEstimationRequest)
        assert restored.sample_values == [0, 1]

    def test_response_roundtrip(self):
        msg = ErrorEstimationResponse(
            session_id="s1", sample_values=[1, 0], qber=0.05
        )
        restored = deserialize(serialize(msg), ErrorEstimationResponse)
        assert restored.qber == 0.05


class TestKeyConfirmation:
    def test_roundtrip(self):
        msg = KeyConfirmation(session_id="s1", key_hash="abc123", status="ok")
        restored = deserialize(serialize(msg), KeyConfirmation)
        assert restored.key_hash == "abc123"
        assert restored.status == "ok"
