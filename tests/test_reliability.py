from app.core.enums import EvidenceSource
from app.core.reliability import load_reliability, reliability_for


def test_reliability_comes_from_yaml_not_engine_code():
    table = load_reliability()
    assert table["ASSESSMENT"] == 0.90
    assert table["SELF_REPORT"] == 0.35
    assert reliability_for(EvidenceSource.RESUME) == 0.65
    assert reliability_for(EvidenceSource.PROJECT) == 0.80
