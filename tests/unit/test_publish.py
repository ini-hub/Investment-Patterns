import json

import pytest

from scanner.config import load_config
from scanner.publish import FORBIDDEN, _write, publish
from tests.conftest import seasonal_series


@pytest.fixture
def site(tmp_path):
    uni = {
        "AAA": seasonal_series(),
        "BBB": seasonal_series(up_months=(5, 6), start=20.0),
        "CCC": seasonal_series(up_months=(3,), up=-0.08, down=0.01),
    }
    cfg = load_config(overrides={"significance": {"runs": 5}})
    index = publish(tmp_path, uni, cfg, log=lambda *_: None)
    return tmp_path, index


def test_publish_writes_index_and_one_file_per_stock(site):
    out, index = site
    assert sorted(p.stem for p in (out / "stocks").glob("*.json")) == ["AAA", "BBB", "CCC"]
    assert [s["ticker"] for s in index["stocks"]] == ["AAA", "BBB", "CCC"]
    assert json.loads((out / "index.json").read_text())["permutation"]["runs"] == 5
    doc = json.loads((out / "stocks" / "AAA.json").read_text())
    assert len(doc["windows"]) == 37 and doc["years"]["Dec"]


def test_publish_never_contains_prices(site):
    out, _ = site
    for f in [out / "index.json", *(out / "stocks").glob("*.json")]:
        text = f.read_text()
        assert not [k for k in FORBIDDEN if f'"{k}"' in text], f


def test_write_refuses_price_fields(tmp_path):
    with pytest.raises(RuntimeError, match="entry_price"):
        _write(tmp_path / "x.json", {"entry_price": 1.0})


def test_summary_marks_rising_stock(site):
    _, index = site
    aaa = next(s for s in index["stocks"] if s["ticker"] == "AAA")
    assert aaa["best"] is not None and aaa["classified"]
