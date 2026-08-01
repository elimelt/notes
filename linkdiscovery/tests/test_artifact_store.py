"""Artifact store tests: round trips, key safety, atomic publishing."""

from __future__ import annotations

from pathlib import Path

import pytest

from linkdiscovery.artifacts import ArtifactStore
from linkdiscovery.contracts import ArtifactRef
from linkdiscovery.errors import ArtifactError


class TestJsonRoundTrip:
    def test_put_get_json(self, store: ArtifactStore) -> None:
        payload = {"b": [1, 2], "a": {"nested": True}}
        ref = store.put_json("proposals", "sha256:abc", payload)
        assert store.get_json("proposals", "sha256:abc") == payload
        assert ref.group == "proposals"
        assert ref.key == "sha256:abc"
        assert ref.path == "proposals/sha256:abc"
        assert ref.fingerprint.startswith("sha256:")
        assert ref.size > 0

    def test_canonical_encoding_makes_refs_deterministic(self, store: ArtifactStore) -> None:
        ref_one = store.put_json("runs", "run-1", {"a": 1, "b": 2})
        ref_two = store.put_json("runs", "run-2", {"b": 2, "a": 1})
        assert ref_one.fingerprint == ref_two.fingerprint
        assert ref_one.size == ref_two.size

    def test_non_json_safe_payload_rejected(self, store: ArtifactStore) -> None:
        with pytest.raises(ArtifactError, match="not JSON-safe"):
            store.put_json("runs", "run-1", {"bad": {1, 2}})

    def test_non_dict_payload_rejected(self, store: ArtifactStore) -> None:
        with pytest.raises(ArtifactError, match="must be a dict"):
            store.put_json("runs", "run-1", [1, 2])  # type: ignore[arg-type]

    def test_corrupt_json_raises(self, store: ArtifactStore) -> None:
        store.put_bytes("runs", "run-1", b"{not json")
        with pytest.raises(ArtifactError, match="not valid JSON"):
            store.get_json("runs", "run-1")

    def test_non_object_json_raises(self, store: ArtifactStore) -> None:
        store.put_bytes("runs", "run-1", b"[1, 2]")
        with pytest.raises(ArtifactError, match="expected a JSON object"):
            store.get_json("runs", "run-1")


class TestBytesRoundTrip:
    def test_put_get_bytes(self, store: ArtifactStore) -> None:
        ref = store.put_bytes("embeddings", "vec-1", b"\x00\x01\x02")
        assert store.get_bytes("embeddings", "vec-1") == b"\x00\x01\x02"
        assert ref.size == 3

    def test_non_bytes_rejected(self, store: ArtifactStore) -> None:
        with pytest.raises(ArtifactError, match="must be bytes"):
            store.put_bytes("embeddings", "vec-1", "text")  # type: ignore[arg-type]

    def test_overwrite_replaces_content(self, store: ArtifactStore) -> None:
        store.put_bytes("embeddings", "vec-1", b"old")
        store.put_bytes("embeddings", "vec-1", b"new")
        assert store.get_bytes("embeddings", "vec-1") == b"new"


class TestKeysAndGroups:
    def test_unknown_group_rejected(self, store: ArtifactStore) -> None:
        with pytest.raises(ArtifactError, match="unknown artifact group 'secrets'"):
            store.put_bytes("secrets", "k", b"")

    @pytest.mark.parametrize(
        "key",
        ["../escape", "a/b", "a\\b", "", ".hidden", "..", "-flag"],
        ids=[
            "dotdot-slash",
            "slash",
            "backslash",
            "empty",
            "leading-dot",
            "dotdot",
            "leading-dash",
        ],
    )
    def test_unsafe_keys_rejected(self, store: ArtifactStore, key: str) -> None:
        with pytest.raises(ArtifactError, match="unsafe artifact key"):
            store.put_bytes("runs", key, b"")

    def test_fingerprint_keys_are_valid(self, store: ArtifactStore) -> None:
        # Content-addressed keys (algorithm:hex) must be accepted verbatim.
        store.put_bytes("embeddings", "sha256:0a1b2c", b"vector")
        assert store.exists("embeddings", "sha256:0a1b2c")

    def test_exists_and_missing(self, store: ArtifactStore) -> None:
        assert not store.exists("runs", "absent")
        with pytest.raises(ArtifactError, match="does not exist"):
            store.get_bytes("runs", "absent")


class TestOpenPath:
    def test_open_path_resolves_published_artifact(self, store: ArtifactStore) -> None:
        ref = store.put_bytes("indexes", "idx-1", b"data")
        path = store.open_path(ref)
        assert path.is_absolute()
        assert path.read_bytes() == b"data"

    def test_escaping_ref_rejected(self, store: ArtifactStore) -> None:
        ref = ArtifactRef(group="runs", key="k", path="../outside", fingerprint="sha256:x", size=0)
        with pytest.raises(ArtifactError, match="escapes the store root"):
            store.open_path(ref)

    def test_missing_ref_rejected(self, store: ArtifactStore) -> None:
        ref = ArtifactRef(
            group="runs", key="gone", path="runs/gone", fingerprint="sha256:x", size=0
        )
        with pytest.raises(ArtifactError, match="does not exist"):
            store.open_path(ref)


class TestAtomicPublish:
    def test_failed_publish_leaves_no_artifact_and_no_temp_files(
        self, store: ArtifactStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(self: Path, target: Path) -> Path:
            raise OSError("simulated crash during rename")

        monkeypatch.setattr(Path, "replace", boom)
        with pytest.raises(ArtifactError, match=r"atomic write .* failed"):
            store.put_bytes("candidates", "pair-1", b"payload")
        monkeypatch.undo()

        assert not store.exists("candidates", "pair-1")
        leftovers = list(store.root.rglob("*.tmp")) + list(store.root.rglob(".partial-*"))
        assert leftovers == []

    def test_failed_write_does_not_clobber_previous_version(
        self, store: ArtifactStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store.put_bytes("candidates", "pair-1", b"version-1")

        def boom(self: Path, target: Path) -> Path:
            raise OSError("simulated crash during rename")

        monkeypatch.setattr(Path, "replace", boom)
        with pytest.raises(ArtifactError):
            store.put_bytes("candidates", "pair-1", b"version-2")
        monkeypatch.undo()

        assert store.get_bytes("candidates", "pair-1") == b"version-1"

    def test_successful_writes_leave_no_temp_files(self, store: ArtifactStore) -> None:
        for index in range(5):
            store.put_json("runs", f"run-{index}", {"index": index})
        leftovers = [
            path
            for path in store.root.rglob("*")
            if path.is_file() and path.name.startswith(".partial-")
        ]
        assert leftovers == []


class TestRoot:
    def test_root_created_on_demand(self, tmp_path: Path) -> None:
        root = tmp_path / "deep" / "nested" / "artifacts"
        store = ArtifactStore(root)
        assert store.root.is_dir()

    def test_root_conflicting_with_file_rejected(self, tmp_path: Path) -> None:
        blocker = tmp_path / "blocked"
        blocker.write_text("i am a file", encoding="utf-8")
        with pytest.raises(ArtifactError):
            ArtifactStore(blocker)
