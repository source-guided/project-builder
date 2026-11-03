"""소비 프로젝트의 원천 선택과 연결 상태. 원천 본문이나 설치는 소유하지 않는다."""

import hashlib
import json
from pathlib import Path

from reference_address import index_access, index_address
from reference_catalog import Catalog, validate_index
from reference_http import IndexReader
from reference_io import load_index, locked, write_json
from reference_workflow import Workflow


DEFAULTS = Path(__file__).resolve().parents[1] / "catalog/defaults.json"


def offers(query="", *, catalog=DEFAULTS):
    # 후보 목록의 메타데이터만 읽으며 연결 대상은 조회하지 않는다.
    document = validate_index(load_index(catalog)["document"])
    terms = query.casefold().split()
    return [item for item in document["entries"]
            if not terms or any(term in " ".join([item["id"],item["label"],item.get("description", ""),*item["topics"]]).casefold() for term in terms)]


class Connections:
    def __init__(self, state, *, connector_reader=None):
        self.connector_reader = connector_reader
        self.path = Path(state).absolute()

    def _load(self):
        if self.path.is_symlink():
            raise ValueError("Connection state must not be a symlink")
        if not self.path.exists():
            return {"format":1,"selections":{}}, None
        raw = self.path.read_bytes(); data = json.loads(raw)
        if not isinstance(data, dict) or set(data) != {"format","selections"} or data["format"] != 1 or not isinstance(data["selections"], dict):
            raise ValueError("Invalid connection state")
        for intent, selection in data["selections"].items():
            if not isinstance(intent, str) or not intent.strip() or not isinstance(selection, dict):
                raise ValueError("Invalid intent selection")
            mode = selection.get("mode")
            if mode == "general":
                if set(selection) != {"mode"}:
                    raise ValueError("General mode has no authored source binding")
            elif mode in {"default","custom"}:
                expected = {"mode","binding","candidate"} if mode == "default" else {"mode","binding"}
                if set(selection) != expected or (mode == "default" and (not isinstance(selection["candidate"],str) or not selection["candidate"])):
                    raise ValueError("Invalid selection metadata")
                binding = selection.get("binding")
                if not isinstance(binding, dict) or set(binding) != {"index","access","kind"} or binding["access"] not in {"file","web","connector"} or binding["kind"] not in {"reference","source"}:
                    raise ValueError("Invalid source binding")
                index_address(binding["index"], binding["access"])
            else:
                raise ValueError("Unsupported source selection mode")
        return data, hashlib.sha256(raw).hexdigest()

    def show(self):
        with locked(self.path):
            data, digest = self._load()
        return {**data,"digest":digest}

    def select(self, intent, mode, *, candidate=None, index=None, access=None, kind="reference", catalog=DEFAULTS, expected_digest=None):
        if not isinstance(intent,str) or not intent.strip():
            raise ValueError("Intent must be nonempty")
        selection = {"mode":mode}
        if mode == "general":
            if candidate is not None or index is not None or access is not None:
                raise ValueError("General mode does not connect a source")
        elif mode == "default":
            if not candidate or index is not None or access is not None:
                raise ValueError("Default mode needs a candidate, not an implicit custom location")
            matches = [entry for entry in offers(catalog=catalog) if entry["id"] == candidate]
            if len(matches) != 1:
                raise ValueError("Unknown default candidate")
            item = matches[0]
            method = item["access"]
            if method == "relative":
                method = "file"
                index = str((Path(catalog).resolve().parent / item["locator"]).resolve())
            else:
                index = item["locator"]
            selection.update(candidate=candidate,binding={"index":index_address(index,method),"access":method,"kind":item["kind"]})
        elif mode == "custom":
            if not index or candidate is not None or kind not in {"reference","source"}:
                raise ValueError("Custom mode needs an observed source/index location")
            method = access or index_access(index)
            selection["binding"] = {"index":index_address(index,method),"access":method,"kind":kind}
        else:
            raise ValueError("Mode must be default, custom or general")
        with locked(self.path):
            data, digest = self._load()
            if expected_digest is not None and expected_digest != digest:
                raise ValueError("Connections changed since inspection")
            previous = data["selections"].get(intent)
            if previous is not None and previous != selection and expected_digest is None:
                raise ValueError("An existing choice needs its observed digest before replacement")
            if previous != selection:
                data["selections"][intent] = selection
                self.path.parent.mkdir(parents=True,exist_ok=True)
                write_json(self.path,data)
        return self.show()

    def selected(self, intent):
        selection = self.show()["selections"].get(intent)
        if selection is None:
            raise ValueError("No choice for this intent; ask about default, custom or general mode")
        return selection

    def discover(self, intent, query=""):
        selection = self.selected(intent)
        if selection["mode"] == "general":
            return {"mode":"general","references":[],"complete":True}
        binding = selection["binding"]
        if binding["kind"] == "source":
            return {"mode":selection["mode"],"references":[{"id":intent,**binding}],"complete":True}
        root = {"index":binding["index"],"access":binding["access"]}
        return Catalog(IndexReader([root]),connector_reader=self.connector_reader).discover([root],query)

    def access(self, intent, trace, *, identifier=None, reference_index=None, reference_access=None, prepare_only=False, scope="local", source_roots=()):
        selection = self.selected(intent)
        if selection["mode"] == "general":
            raise ValueError("General mode has no authored source to read")
        binding = selection["binding"]
        if binding["kind"] == "reference":
            if not identifier:
                raise ValueError("Discover the selected source index and supply the source ID")
            index, method = binding["index"], binding["access"]
            root = {"index":index,"access":method}
            catalog = Catalog(IndexReader([root]),connector_reader=self.connector_reader)
            if reference_index is not None:
                method = reference_access or index_access(reference_index)
                index = index_address(reference_index,method)
                graph = catalog.walk([root])
                if not any(item["index"] == index and item["access"] == method for item in graph["indexes"]):
                    raise ValueError("Reference index is not reachable from the selected source")
            elif reference_access is not None:
                raise ValueError("Reference access requires its observed index")
        else:
            if identifier is not None or reference_index is not None or reference_access is not None:
                raise ValueError("Direct source connections do not take a nested reference")
            # 선택 상태에서 재생성하는 발견 메타데이터이며 본문은 복사하지 않는다.
            index = self.path.parent / (self.path.name + ".references") / (hashlib.sha256(intent.encode()).hexdigest() + ".json")
            index.parent.mkdir(parents=True,exist_ok=True)
            entry = {"id":intent,"label":intent,"topics":[intent],"kind":"source","access":binding["access"],"locator":binding["index"]}
            with locked(index):
                write_json(index,{"format":1,"entries":[entry]})
            identifier, method = intent, "file"
        if binding["kind"] == "source":
            root = {"index":str(index),"access":method}
            catalog = Catalog(IndexReader([root]),connector_reader=self.connector_reader)
        workflow = Workflow(trace,scope=scope,catalog=catalog,source_roots=source_roots)
        operation = workflow.prepare if prepare_only else workflow.read
        return operation(index,identifier,access=method)
