import zipfile

import numpy as np
import pytest
import soundfile as sf

from core.export import zip_run


@pytest.fixture
def fake_run(tmp_path):
    run = tmp_path / "run_abc12345"
    run.mkdir()
    for i in (1, 2, 3):
        sf.write(run / f"chunk_{i:04d}.wav", np.zeros(100, dtype=np.float32), 24000)
    sf.write(run / "final.wav", np.zeros(100, dtype=np.float32), 24000)
    (run / "manifest.json").write_text('{"chunks": []}')
    return run


def test_zip_contains_all_five(fake_run, tmp_path):
    zpath = zip_run(str(fake_run))
    assert zipfile.is_zipfile(zpath)
    names = zipfile.ZipFile(zpath).namelist()
    assert set(names) == {
        "run_abc12345/manifest.json", "run_abc12345/final.wav",
        "run_abc12345/chunk_0001.wav", "run_abc12345/chunk_0002.wav",
        "run_abc12345/chunk_0003.wav",
    }


def test_zip_missing_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        zip_run(str(tmp_path / "nope"))


def test_zip_empty_dir_raises(tmp_path):
    d = tmp_path / "run_empty"
    d.mkdir()
    with pytest.raises(FileNotFoundError):
        zip_run(str(d))


def test_zip_custom_out_dir(fake_run, tmp_path):
    target = tmp_path / "zips"
    target.mkdir()
    zpath = zip_run(str(fake_run), str(target))
    assert str(target) in zpath and zipfile.is_zipfile(zpath)
