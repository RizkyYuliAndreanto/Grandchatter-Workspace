from core.chunker import chunk_text, chunks_with_index


def test_normalized_price_stays_together():
    # Output of the T04 normalizer: no thousands dots left, ~70 chars.
    text = "Harga lima puluh ribu rupiah pada tahun dua ribu dua puluh enam."
    chunks = chunk_text(text)
    assert chunks == [text]  # one chunk, untouched


def test_sentence_split_keeps_punctuation():
    text = "Kalimat pertama di sini. Kalimat kedua? Kalimat ketiga: selesai!"
    chunks = chunk_text(text)
    assert chunks == [
        "Kalimat pertama di sini.",
        "Kalimat kedua?",
        "Kalimat ketiga: selesai!",
    ]


def test_long_sentence_splits_at_comma():
    text = ("Posisi ini menuntut penyusunan strategi konten harian, penulisan skrip narasi, "
            "pengambilan gambar lapangan, penyuntingan video, pembuatan desain grafis, "
            "pengelolaan anggaran iklan digital yang kompleks, hingga koordinasi lintas "
            "divisi untuk semua saluran media sosial perusahaan tanpa kecuali sedikit pun.")
    assert len(text) > 250
    chunks = chunk_text(text)
    assert len(chunks) > 1  # genuinely split
    assert all(len(c) <= 250 for c in chunks)
    # content preserved (order + words)
    assert " ".join(chunks).split() == text.split()


def test_no_comma_falls_back_to_words():
    text = "kata " * 80  # 400 chars, single "sentence", no punctuation at all
    chunks = chunk_text(text.strip())
    assert all(len(c) <= 250 for c in chunks)
    assert all(not c.startswith(" ") for c in chunks)
    # no word cut in half
    assert all(c.split() for c in chunks)


def test_random_5000_chars_bounded():
    text = ("Ini kalimat pengisi yang cukup panjang untuk melewati batas karakter. " * 80)
    assert len(text) > 5000
    chunks = chunk_text(text)
    assert chunks
    assert all(len(c) <= 250 for c in chunks)


def test_empty_and_whitespace():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_chunks_with_index_one_based():
    pairs = chunks_with_index(["a", "b", "c"])
    assert pairs[0][0] == 1 and pairs[2][0] == 3
