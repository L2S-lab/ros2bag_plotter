from __future__ import annotations
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import tempfile
from typing import Dict, List, Iterator, Tuple, Any, Callable
from rosbags.highlevel import AnyReader
from rosbags.typesys import Stores, get_typestore, get_types_from_msg


@dataclass
class TopicInfo:
    name: str
    type: str


class Ros2BagReader:
    def __init__(self, bag_folder: Path):
        self.bag_folder = Path(bag_folder)
        self._store = self._select_store()
        self._custom_schemas: Dict[str, str] = {}
        self.default_typestore = get_typestore(self._store)

    @staticmethod
    def _select_store():
        distro = os.environ.get("ROS_DISTRO", "").strip().lower()
        # Resolve by enum name dynamically so newer ROS distros are supported
        # even when running with older rosbags versions.
        distro_to_store_name = {
            "dashing": "ROS2_DASHING",
            "eloquent": "ROS2_ELOQUENT",
            "foxy": "ROS2_FOXY",
            "galactic": "ROS2_GALACTIC",
            "humble": "ROS2_HUMBLE",
            "iron": "ROS2_IRON",
            "jazzy": "ROS2_JAZZY",
            "kilted": "ROS2_KILTED",
            "lyrical": "ROS2_LYRICAL",
            "rolling": "LATEST",
        }
        store_name = distro_to_store_name.get(distro, "LATEST")
        return getattr(Stores, store_name, Stores.LATEST)

    def _rebuild_typestore(self) -> None:
        store = get_typestore(self._store)
        for type_name, msg_definition in self._custom_schemas.items():
            typs = get_types_from_msg(msg_definition, type_name)
            store.register(typs)
        self.default_typestore = store

    @staticmethod
    def _is_bag_dir(path: Path) -> bool:
        if not path.is_dir():
            return False
        if (path / "metadata.yaml").exists():
            return True
        for x in path.iterdir():
            if not x.is_file():
                continue
            if x.suffix in {".db3", ".mcap"}:
                return True
            # rosbag2 sqlite files can be named like: my_bag.bag_0.db3
            if x.name.endswith(".db3"):
                return True
        return False

    def _reader_path(self) -> Path:
        # Some rosbags versions may misclassify a ".bag" directory as a bag file.
        # Use a neutral symlink path for reading when folder itself ends with ".bag".
        path = self.bag_folder
        if not (path.is_dir() and path.suffix == ".bag"):
            return path
        try:
            target = path.resolve()
            alias_root = Path(tempfile.gettempdir()) / "ros2bag_plotter_aliases"
            alias_root.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha1(str(target).encode("utf-8")).hexdigest()[:12]
            alias = alias_root / f"{path.stem}_{digest}"
            if alias.exists():
                try:
                    if alias.is_symlink() and alias.resolve() == target:
                        return alias
                except Exception:
                    pass
                return path
            alias.symlink_to(target, target_is_directory=True)
            return alias
        except Exception:
            return path

    @staticmethod
    def discover_bag_folders(root: Path) -> List[Path]:
        root = Path(root)
        if not root.exists() or not root.is_dir():
            return []

        bags: List[Path] = []
        # Support selecting the bag folder itself as root.
        if Ros2BagReader._is_bag_dir(root):
            bags.append(root)

        # Support selecting a parent folder containing many bag folders.
        for p in root.iterdir():
            if Ros2BagReader._is_bag_dir(p):
                bags.append(p)

        return sorted(set(bags))

    def _open_reader(self) -> AnyReader:
        return AnyReader([self._reader_path()], default_typestore=self.default_typestore)

    def register_msg_schema(self, type_name: str, msg_definition: str) -> tuple[bool, str | None]:
        prev = dict(self._custom_schemas)
        self._custom_schemas[type_name] = msg_definition
        try:
            self._rebuild_typestore()
            return True, None
        except Exception as exc:
            self._custom_schemas = prev
            self._rebuild_typestore()
            return False, str(exc)

    def decode_raw(self, raw_data: bytes, type_name: str) -> tuple[Any | None, Exception | None]:
        try:
            return self.default_typestore.deserialize_cdr(raw_data, type_name), None
        except Exception as exc:
            return None, exc

    @staticmethod
    def _select_connections(reader: AnyReader, selected_topics: List[str] | None):
        if not selected_topics:
            return list(reader.connections)
        selected = set(selected_topics)
        return [c for c in reader.connections if c.topic in selected]

    def get_topic_type_map(self) -> Dict[str, str]:
        with self._open_reader() as reader:
            return {c.topic: c.msgtype for c in reader.connections}

    def count_messages(self, selected_topics: List[str] | None = None) -> int:
        with self._open_reader() as reader:
            connections = self._select_connections(reader, selected_topics)
            return sum(1 for _ in reader.messages(connections=connections))

    def iter_messages(
        self,
        selected_topics: List[str] | None = None,
        progress_cb: Callable[[int], None] | None = None
    ) -> Iterator[Tuple[str, str, int, bytes, Any, Exception | None]]:
        with self._open_reader() as reader:
            connections = self._select_connections(reader, selected_topics)
            i = 0
            for connection, ts_ns, raw_data in reader.messages(connections=connections):
                err = None
                msg = None
                try:
                    msg = reader.deserialize(raw_data, connection.msgtype)
                except Exception as e:
                    try:
                        msg = self.default_typestore.deserialize_cdr(raw_data, connection.msgtype)
                    except Exception:
                        err = e
                i += 1
                if progress_cb:
                    progress_cb(i)
                yield connection.topic, connection.msgtype, ts_ns, raw_data, msg, err