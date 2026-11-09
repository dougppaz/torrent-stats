from unittest.mock import MagicMock, patch

from torrent_stats.__main__ import main
from torrent_stats.db.models import WorkerKey


@patch("torrent_stats.__main__.WorkerKeyRepository")
def test_cli_workers_create(mock_repo_cls, capsys):
    mock_repo = MagicMock()
    mock_repo_cls.return_value = mock_repo
    mock_repo.save_key.return_value = WorkerKey(
        _id="abc123hash", key_hash="abc123hash", description="Test Worker"
    )

    test_args = ["torrent_stats", "workers", "create", "--description", "Test Worker"]
    with patch("sys.argv", test_args):
        code = main()

    assert code == 0
    captured = capsys.readouterr()
    assert "Worker key created successfully!" in captured.out
    assert "abc123hash" in captured.out


@patch("torrent_stats.__main__.WorkerKeyRepository")
def test_cli_workers_list(mock_repo_cls, capsys):
    mock_repo = MagicMock()
    mock_repo_cls.return_value = mock_repo
    mock_db = MagicMock()
    mock_repo.client.get_db.return_value = mock_db
    mock_db.__iter__.return_value = ["abc123hash"]
    mock_db.get.return_value = {
        "_id": "abc123hash",
        "key_hash": "abc123hash",
        "description": "Test Worker",
        "created_at": "2026-11-07T00:00:00Z",
    }

    test_args = ["torrent_stats", "workers", "list"]
    with patch("sys.argv", test_args):
        code = main()

    assert code == 0
    captured = capsys.readouterr()
    assert "abc123hash" in captured.out
    assert "Test Worker" in captured.out


@patch("torrent_stats.__main__.WorkerKeyRepository")
def test_cli_workers_list_empty(mock_repo_cls, capsys):
    mock_repo = MagicMock()
    mock_repo_cls.return_value = mock_repo
    mock_db = MagicMock()
    mock_repo.client.get_db.return_value = mock_db
    mock_db.__iter__.return_value = []

    test_args = ["torrent_stats", "workers", "list"]
    with patch("sys.argv", test_args):
        code = main()

    assert code == 0
    captured = capsys.readouterr()
    assert "No worker keys found." in captured.out


@patch("torrent_stats.__main__.WorkerKeyRepository")
def test_cli_workers_delete(mock_repo_cls, capsys):
    mock_repo = MagicMock()
    mock_repo_cls.return_value = mock_repo
    mock_db = MagicMock()
    mock_repo.client.get_db.return_value = mock_db
    mock_db.__contains__.return_value = True
    mock_db.get.return_value = {"_id": "abc123hash"}

    test_args = ["torrent_stats", "workers", "delete", "abc123hash"]
    with patch("sys.argv", test_args):
        code = main()

    assert code == 0
    captured = capsys.readouterr()
    assert "deleted successfully" in captured.out


@patch("torrent_stats.__main__.WorkerKeyRepository")
def test_cli_workers_delete_not_found(mock_repo_cls, capsys):
    mock_repo = MagicMock()
    mock_repo_cls.return_value = mock_repo
    mock_db = MagicMock()
    mock_repo.client.get_db.return_value = mock_db
    mock_db.__contains__.return_value = False

    test_args = ["torrent_stats", "workers", "delete", "nonexistent"]
    with patch("sys.argv", test_args):
        code = main()

    assert code == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err


def test_cli_no_args():
    test_args = ["torrent_stats"]
    with patch("sys.argv", test_args):
        try:
            main()
        except SystemExit as e:
            assert e.code != 0
