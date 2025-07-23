from gateway.core.logging import setup_logging, get_logger


def test_structlog_factory(capsys):
    setup_logging(debug=True)
    log = get_logger("test")
    log.info("hello", foo=1)
    out, _ = capsys.readouterr()
    assert "hello" in out and "foo" in out
