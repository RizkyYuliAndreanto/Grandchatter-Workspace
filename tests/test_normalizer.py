import re

from core.normalizer import normalize

DIGIT = re.compile(r"\d")


def test_currency_year_percent():
    out = normalize("Harga Rp 50.000 pada tahun 2026, naik 3.5%.")
    assert "lima puluh ribu rupiah" in out
    assert "dua ribu dua puluh enam" in out
    assert "tiga koma lima persen" in out
    assert not DIGIT.search(out)
    assert out.count(".") == 1  # only the sentence dot survives


def test_phone_per_digit():
    out = normalize("Hubungi 081234567890 segera.")
    assert "nol delapan satu dua tiga empat lima enam tujuh delapan sembilan nol" in out
    assert not DIGIT.search(out)


def test_time():
    out = normalize("Pukul 14:30 WIB rapat dimulai.")
    assert "empat belas setengah" in out  # 14:30 -> "lewat setengah" form
    assert "W I B" in out


def test_acronyms_and_abbrev():
    out = normalize("Daftar BPJS, KTP, dll. dibawa.")
    assert "B P J S" in out
    assert "K T P" in out
    assert "dan lain-lain" in out
    # whitelist untouched
    out2 = normalize("Kantor HRD dan PT ini buka.")
    assert "HRD" in out2 and "PT" in out2


def test_thousands_vs_sentence_dot():
    out = normalize("Harga Rp 50.000. Selesai.")
    assert "lima puluh ribu rupiah" in out
    assert out.count(".") == 2  # both sentence dots intact


def test_idr():
    out = normalize("IDR 2.500 saja.")
    assert "dua ribu lima ratus rupiah" in out


def test_decimal_comma():
    out = normalize("berat 3,5 kg")
    assert "tiga koma lima" in out


def test_generic_int():
    out = normalize("ada 21 lowongan")
    assert "dua puluh satu lowongan" in out


def test_informal_abbrev():
    out = normalize("yg dgn kpd utk krn")
    for w in ("yang", "dengan", "kepada", "untuk", "karena"):
        assert w in out


def test_idempotent():
    raw = "Harga Rp 50.000 pada tahun 2026, naik 3.5%. Hubungi 081234567890. Pukul 14:30 WIB."
    once = normalize(raw)
    assert normalize(once) == once
