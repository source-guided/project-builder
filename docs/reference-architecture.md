# 참조 진입점과 독립 원천

`project-builder`는 하나의 공개 스킬 `start`와 참조 도구를 배포합니다. 기본 원천의 본문과 내부 스킬은 독립 저장소가 소유하며 코어 설치에 포함되지 않습니다. 공통 규약은 코어의 governance 및 usage 참조로 찾습니다.

## 책임

| 모듈 | 책임 |
| --- | --- |
| `reference_address.py` | 로컬·웹·커넥터·상대 주소 해석 |
| `reference_catalog.py` | 무상태 메타데이터 발견과 주소 연결 |
| `reference_io.py`, `reference_http.py` | 파일·HTTP 색인의 허용된 접근 |
| `reference_registry.py` | 발견용 메타데이터 변경과 충돌 검사 |
| `document_store.py`, `document_stores.py` | 저장 위치와 독립적인 문서 계약, 프로필과 어댑터 조합 |
| `document_local.py`, `document_http.py`, 서비스별 `document_*.py` | 파일·DB·원격 서비스 읽기와 조건부 변경 |
| `reference_session.py` | 조회 영수증·관측·메타데이터 캐시와 검토 기록 |
| `reference_trace.py` | 영수증의 로컬 JSONL·문서 저장, 조건부 추가와 명시적 스냅샷 내보내기 |
| `reference_workflow.py` | 공통 규약 초기화와 조회 조합 |
| `source_connections.py` | 소비 프로젝트의 원천 선택과 연결 상태 |
| `references.py`, `sources.py` | CLI 입력·출력 연결 |

## 선택과 연결

```sh
python3 <plugin>/scripts/sources.py offers --query '디자인'
python3 <plugin>/scripts/sources.py show --state .local/project-builder/connections.json
python3 <plugin>/scripts/sources.py select --state .local/project-builder/connections.json --intent design --mode default --candidate design
python3 <plugin>/scripts/sources.py discover --state .local/project-builder/connections.json --intent design --query 'UX'
```

`offers`는 내장 목록의 설명과 주소만 읽고 외부 원천을 방문하지 않습니다. 사용자 선택 전에는 `select`를 실행하지 않습니다. 선택은 본문 복사나 설치가 아니며 접근 성공을 증명하지도 않습니다. 기존 선택을 바꾸려면 `show`의 digest를 `--expected-digest`로 전달합니다. 다른 작업 영역의 선택은 함께 보존됩니다.

사용자 색인은 `--mode custom --index <관측한 색인> --access file|web|connector`로 연결합니다. 색인이 없는 단일 문서·페이지는 `--kind source`를 지정합니다. 기본 원천 대신 일반 방식을 선택하면 `--mode general`로 기록하며, 이 상태에 숨은 기본 원천을 넣거나 다시 선택을 요구하지 않습니다. 스킬 제작 기준도 같은 선택 계약을 사용합니다.

위 `.local` 경로는 예시입니다. 참조 목록과 `--state` 모두 사용자가 선택한 파일 또는 `store://profile/key`에 둘 수 있습니다. `--store-config`로 SQLite·HTTP·GitHub·Supabase·S3·Confluence 프로필을 지정하며, 새 참조/선택 문서는 `init`으로 명시적으로 만듭니다. 영수증의 `--trace`도 파일 또는 저장소 주소를 받으며 첫 기록에서 생성됩니다. 상세 계약과 명령은 [참조 저장소](reference-storage.md)에 있습니다. 공유 참조의 권한, 실제 원천의 권한, 개인별 인증정보는 분리합니다.

일반 커넥터 색인에는 호스트가 `Connections(state, connector_reader=authorized_reader)`로 인증된 색인 어댑터를 주입합니다. 어댑터는 `{document, digest, address}` 관측값을 반환하고 자체 서비스 권한을 유지합니다. 설정된 `store://` 색인은 CLI에서도 내장 저장소 어댑터로 조회·변경합니다. 다른 불투명한 커넥터 식별자에는 여전히 호스트 어댑터가 필요하며, 없으면 탐색 미완료로 보고합니다. 단일 커넥터 원천 본문은 `prepare-read` 후 허가된 호스트 도구가 읽습니다. 저장소 어댑터가 지원하는 JSON 참조 문서와 임의의 DB·Confluence 업무 본문 조회를 혼동하지 않습니다.

## 필요한 내용만 읽기

```sh
python3 <plugin>/scripts/references.py read --index <plugin>/references/governance/index.json --id routing-policy --trace .local/project-builder/session.jsonl
python3 <plugin>/scripts/sources.py prepare-read --state .local/project-builder/connections.json --intent design --id ux --trace .local/project-builder/session.jsonl
```

색인 연결은 내부 항목을 발견한 후 ID를 지정합니다. 하위 색인의 항목이면 발견 결과의 `reference.index`와 `reference.access`를 `--reference-index` 및 `--reference-access`로 전달합니다. 이 색인은 원래 선택한 연결에서 도달 가능한지 검사하며 조회 권한 범위를 넓히지 않습니다. 직접 문서 연결에는 내부 ID를 지정하지 않습니다. 로컬 텍스트에는 `read`를 사용할 수 있고, 외부 본문은 `prepare-read`의 주소를 허가된 호스트 도구로 읽은 뒤 `references.py record --receipt ...`로 기록합니다. 읽기·실패·현재 컨텍스트 재사용은 구분됩니다. 세션 감사는 기록된 전이만 검증하며 미기록 접근의 부재를 보증하지 않습니다.

원천의 `access: relative` 참조는 로컬 색인에서는 파일로, HTTP 색인에서는 웹 주소로 해석됩니다. 따라서 원천 저장소를 복제하거나 같은 색인을 원격에서 읽어도 내부 참조 구조를 다시 작성할 필요가 없습니다. 커넥터 식별자는 불투명한 값으로 유지하며, 상대 경로를 지원하려면 해당 호스트의 명시적 방식이 필요합니다.

원천 내부 스킬은 참조를 통해 읽고 현재 작업에 적용합니다. 전역 등록·설치는 수행하지 않습니다. 다른 원천이 필요해지면 현재 프로젝트의 선택으로 돌아갑니다.

## 작성한 자료의 구조

원천이나 프로젝트 지식 자료를 만들 때는 공통 참여 계약에 따라 본문과 참조를 모두 분야·책임별로 구성합니다. 담당자 질문·답변, 요구사항, 스펙, 결정, 검증 자료는 해당 소유 영역 아래에 두고, 영역별 참조 색인이 필요한 하위 영역과 본문을 안내합니다. 파일 기반 원천의 영역별 참조는 `references/<영역>/index.json`처럼 자기 폴더에 두며, 여러 영역의 JSON을 `references/` 바로 아래에 나열하는 것으로 대신하지 않습니다. 루트의 안내·관리 문서는 유지할 수 있지만 서로 다른 업무의 본문을 루트나 한 개의 `docs/` 폴더에 계속 나열하지 않습니다.

수평 탐색은 관련 영역 사이를 참조로 이동한다는 뜻입니다. 평면 파일 목록이나 고정 실행 순서를 뜻하지 않습니다. 책임이 하나인 작은 영역에는 얕은 색인을 사용할 수 있으며 빈 폴더나 일정한 깊이를 강제하지 않습니다. 일반 방식을 선택해도 이 구조 기준은 적용됩니다. 참여 계약 검사의 통과와 실제 소유 영역·탐색 경로의 적절성 검토는 별도로 확인합니다.

분리 판단은 각 영역 안에서도 반복합니다. 하나의 책임을 함께 설명하고 변경하는 질문·스펙·검증은 나란히 둘 수 있습니다. 독립적으로 바뀌는 정책·입력·상태 흐름·소유자가 섞이면 해당 부분을 하위 영역으로 나누고 그 부분의 질문·스펙·검증을 함께 옮깁니다. 상위 공통 계약은 한 곳에 유지하고 하위에서 참조합니다. 모든 가지의 깊이를 맞추거나 문서 종류마다 무조건 폴더를 만드는 방식은 사용하지 않습니다. 검사기는 경로·참조 경계를 확인하며, 책임이 응집되어 있는지는 실제 내용과 변경 시나리오로 별도 검토합니다.

## 상태와 관리

기존 참조 CLI의 독립 영수증, 병렬 완료, 부분 실패, 탐색 한도와 변경 충돌 검사를 유지합니다. 발견 결과가 없다는 사실과 탐색하지 못한 분기는 구분합니다. 원천 의미와 주소가 달라졌다면 관리자가 발견 메타데이터를 점검하고 관측한 리비전에 대한 검토 기록을 남깁니다.

영수증 저장은 이벤트 검증과 분리합니다. 로컬 JSONL은 잠금 안에서 추가하고, 문서 저장소는 관측 리비전 조건으로 추가합니다. 충돌 시 최신 이벤트를 다시 검증한 뒤 독립 기록만 병합하므로 중복 완료나 맥락 변경은 통과하지 않습니다. 원격 trace에는 명시적 `--scope`가 필요하며 서로 다른 조회 맥락은 다른 기록 키를 사용합니다. 같은 팀 저장소를 사용한다고 하나의 인증 맥락이 되는 것은 아닙니다.

캐시는 원래 발견 메타데이터를 보존하고 현재 원천 연결을 다시 해석합니다. 색인이 그대로여도 심볼릭 링크 변경·단절은 반영됩니다. HTTP 또는 커넥터 색인이 로컬 파일을 가리킨다는 사실만으로 읽기 범위를 얻지 않습니다. 필요한 로컬 범위는 호출자가 `--source-root`로 지정합니다.

연결 상태는 소비 프로젝트가 선택한 파일·DB·원격 문서에 저장합니다. 파일 연결의 직접 원천 참조는 상태 옆에 intent별 메타데이터로 재생성하며, 저장소 연결은 메모리의 참조 관측을 사용합니다. 원천 본문이나 자격 증명을 복제하지 않습니다. 공유 연결이 로컬 파일을 가리켜도 명시한 `--source-root` 없이 로컬 접근을 얻지 않습니다. 원천 선택은 인증을 대신하지 않습니다. 과거 실행은 당시 동결한 패키지와 하네스로 검토합니다.
