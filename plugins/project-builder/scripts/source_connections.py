"""소비 프로젝트의 원천 선택과 연결 상태. 원천 본문이나 설치는 소유하지 않는다."""

import hashlib
from pathlib import Path

from reference_address import index_access, index_address, local_path
from reference_catalog import validate_index
from reference_io import load_index, locked, write_json
from reference_workflow import Workflow
from document_store import MissingDocument
from document_stores import Stores


DEFAULTS = Path(__file__).resolve().parents[1] / "catalog/defaults.json"


def offers(query="", *, catalog=DEFAULTS):
    # 후보 목록의 메타데이터만 읽으며 연결 대상은 조회하지 않는다.
    document = validate_index(load_index(catalog)["document"])
    terms = query.casefold().split()
    return [item for item in document["entries"]
            if not terms or any(term in " ".join([item["id"],item["label"],item.get("description", ""),*item["topics"]]).casefold() for term in terms)]


class Connections:
    def __init__(self, state, *, connector_reader=None, stores=None):
        self.connector_reader = connector_reader
        self.stores = stores or Stores()
        self.address = str(state) if index_access(state) == "file" else index_address(state, index_access(state))
        self.path = local_path(state) if index_access(state) == "file" else None

    def _load(self):
        try:
            observed = self.stores.read(self.address)
        except MissingDocument:
            if self.path is None:
                raise
            return {"format":1,"selections":{}}, None, None
        data = observed["document"]
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
        return data, observed["digest"], observed["revision"]

    def show(self):
        data, digest, revision = self._load()
        return {**data,"digest":digest,"revision":revision}

    def initialize(self):
        self.stores.write(self.address,{"format":1,"selections":{}},expected_revision=None)
        return self.show()

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
        data, digest, revision = self._load()
        if expected_digest is not None and expected_digest != digest:
            raise ValueError("Connections changed since inspection")
        previous = data["selections"].get(intent)
        if previous is not None and previous != selection and expected_digest is None:
            raise ValueError("An existing choice needs its observed digest before replacement")
        if previous != selection:
            if digest is not None and revision is None:
                raise ValueError("Connection store has no conditional-write revision")
            data["selections"][intent] = selection
            self.stores.write(self.address,data,expected_revision=revision)
        return self.show()

    def selected(self, intent):
        selection = self.show()["selections"].get(intent)
        if selection is None:
            raise ValueError("No choice for this intent; ask about default, custom or general mode")
        return selection

    def _check_local_binding(self, binding, source_roots):
        if self.path is None and binding["access"] == "file":
            target = local_path(binding["index"])
            if not any(target.is_relative_to(Path(root).resolve()) for root in source_roots):
                raise PermissionError("Shared connection state cannot authorize local file access; explicitly supply its source root")

    def discover(self, intent, query="", *, source_roots=()):
        selection = self.selected(intent)
        if selection["mode"] == "general":
            return {"mode":"general","references":[],"complete":True}
        binding = selection["binding"]
        self._check_local_binding(binding, source_roots)
        if binding["kind"] == "source":
            return {"mode":selection["mode"],"references":[{"id":intent,**binding}],"complete":True}
        root = {"index":binding["index"],"access":binding["access"]}
        return self.stores.catalog([root],connector_reader=self.connector_reader).discover([root],query)

    def access(self, intent, trace, *, identifier=None, reference_index=None, reference_access=None, prepare_only=False, scope=None, source_roots=()):
        selection = self.selected(intent)
        if selection["mode"] == "general":
            raise ValueError("General mode has no authored source to read")
        binding = selection["binding"]
        self._check_local_binding(binding, source_roots)
        if binding["kind"] == "reference":
            if not identifier:
                raise ValueError("Discover the selected source index and supply the source ID")
            index, method = binding["index"], binding["access"]
            root = {"index":index,"access":method}
            catalog = self.stores.catalog([root],connector_reader=self.connector_reader)
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
            entry = {"id":intent,"label":intent,"topics":[intent],"kind":"source","access":binding["access"],"locator":binding["index"]}
            if self.path is not None:
                # 로컬 선택의 발견 메타데이터만 재생성하며 원천 본문은 복사하지 않는다.
                index = self.path.parent / (self.path.name + ".references") / (hashlib.sha256(intent.encode()).hexdigest() + ".json")
                index.parent.mkdir(parents=True,exist_ok=True)
                with locked(index):
                    write_json(index,{"format":1,"entries":[entry]})
                identifier, method = intent, "file"
                catalog = self.stores.catalog([{"index":str(index),"access":method}],connector_reader=self.connector_reader)
            else:
                # 공유 선택을 로컬 파일로 위장하지 않는다. 원격 색인의 로컬 접근 제한을 유지한다.
                from reference_catalog import Catalog
                from document_store import encode
                index = "connection:" + hashlib.sha256((self.address + intent).encode()).hexdigest()
                document = {"format":1,"entries":[entry]}
                def read_connection(address):
                    if address != index:
                        raise ValueError("Unexpected connection metadata request")
                    return {"document":document,"digest":hashlib.sha256(encode(document)).hexdigest(),"address":index}
                catalog = Catalog(read_connection,connector_reader=read_connection)
                identifier, method = intent, "connector"
        workflow = Workflow(trace,scope=scope,catalog=catalog,source_roots=source_roots,stores=self.stores,
                            restrict_local_sources=self.path is None)
        operation = workflow.prepare if prepare_only else workflow.read
        return operation(index,identifier,access=method)
