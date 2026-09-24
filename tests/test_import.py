def test_package_import() -> None:
    import deprecated_api

    assert deprecated_api.__version__ == "0.1.0"
