from support import make_release


def test_is_newer_than() -> None:
    release = make_release('2.0.0')

    assert release.is_newer_than('1.0.0')
    assert not release.is_newer_than('2.0.0')
    assert not release.is_newer_than('3.0.0')
