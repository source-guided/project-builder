# 발견·원천·세션의 책임

이 문서는 구현 구조와 사용 방법입니다. 관리 원칙은 [governance 참조](../plugins/product-builder/references/governance/index.json)가 가리키는 원천이 소유합니다.

## 책임과 실제 모듈

| 계층 | 책임 | 구현 |
| --- | --- | --- |
| 발견·주소 해석 | 메타데이터 검증, 다중 색인 탐색, 검색 단서 매칭, 주소 해석 | `reference_catalog.py` |
| 주소 계약 | 로컬 경로·파일 URI·웹·커넥터 주소의 공통 해석 | `reference_address.py` |
| 원천 접근 어댑터 | 로컬 파일 또는 명시한 HTTP 색인 읽기, 기존 접근 제한 유지 | `reference_io.py`, `reference_http.py` |
| 참조 관리 | 발견용 메타데이터 추가·수정·삭제, 충돌 방지 | `reference_registry.py` |
| 진입점 세션 | 참조 영수증, 관측, 참조 캐시, 검토 기록, 접근 맥락 분리 | `reference_session.py` |
| Product Builder 실행 정책 | 원칙 원천 초기화, 읽기 조합, 제한된 병렬 실행 | `reference_workflow.py` |
| 명령 진입점 | 입력과 출력의 연결 | `references.py` |
| 전문 원천·AI | 과업별 기준, 근거 대조, 판단과 완료 조건 | 각 스킬의 소유 원천 |

발견 모듈은 세션이나 Product Builder 초기화 규칙을 알지 못합니다. `Catalog`는 색인 reader를 주입받습니다. 기본 CLI는 파일 및 명시한 HTTP origin의 JSON 색인을 지원하고, 다른 연결 방식은 호스트의 어댑터가 담당합니다. 커넥터 식별자는 불투명한 값 그대로 전달하며 파일 경로로 바꾸지 않습니다. 커넥터 색인을 읽을 호스트 어댑터가 없으면 그 분기만 조회 불가로 반환합니다. 업무 시스템의 검색·인증을 새로 구현한 것은 아닙니다.

## 참조 데이터

참조는 식별자, 위치, 표시명, 선택적 description, 주제, 접근 방법과 다음 참조를 담습니다. description은 원천을 찾기 위한 짧은 설명입니다. 정책 값·규칙 본문·판단 결과·권위 있는 버전 값을 넣지 않습니다. 버전과 소유 정보는 각각의 실제 원천에서 확인합니다.

관련도는 현재 구현에서 메타데이터에 일치한 검색어 목록입니다. 확률·신뢰도·정책 우선순위가 아닙니다. 모델이나 검색 공급자가 다른 관련성 표현을 제공할 수 있지만 원천의 권위를 결정하지 않습니다.

공통 참조에는 재사용 가능한 원천의 위치만, 프로젝트별 참조에는 해당 프로젝트의 실제 기획·계약·디자인·코드 위치를 둡니다. 동일 원천을 여러 참조가 가리킬 수 있으며, 탐색 상태를 중앙 조직 메모리로 합치지 않습니다.

## 발견과 원천 읽기

```sh
python3 plugins/product-builder/scripts/references.py discover \
  --index plugins/product-builder/references/index.json \
  --query 'keyboard selection'
python3 plugins/product-builder/scripts/references.py resolve \
  --index plugins/product-builder/references/design/ux/index.json --id task-navigation
```

이 명령들은 세션 없이 메타데이터를 반환하며 본문을 읽지 않습니다. 파일 색인 여러 개 또는 HTTP 색인 주소 여러 개를 root로 줄 수 있습니다. 로컬 색인은 명시한 root의 디렉터리 트리 안에서, HTTP 색인은 명시한 origin 안에서 탐색합니다. HTTP 링크만으로 로컬 파일 읽기 범위를 얻을 수 없습니다. 다른 경계의 색인은 새 root로 명시해야 합니다. 인증 실패를 우회하지 않습니다. 허용된 리다이렉트 이후 상대 참조는 최종 색인 주소를 기준으로 해석합니다. 잘못된 root와 전송 중단을 포함한 개별 색인 오류는 다른 정상 분기를 중단하지 않습니다.

발견 결과에는 정상 후보, 실패한 분기, 탐색 한도로 남은 분기가 구분됩니다. 원천 후보가 없다는 사실과 탐색을 완료하지 못했다는 사실은 다릅니다. 패키지 검증은 별도로 모든 내부 참조의 유효성을 요구합니다.

```sh
python3 plugins/product-builder/scripts/references.py read \
  --index plugins/product-builder/references/governance/index.json --id routing-policy \
  --trace .local/product-builder/session.jsonl --scope workspace-account
python3 plugins/product-builder/scripts/references.py prepare-read \
  --index plugins/product-builder/references/design/ux/index.json --id wai-combobox \
  --trace .local/product-builder/session.jsonl --scope workspace-account
# 반환된 address를 허용된 도구로 읽은 뒤 해당 receipt를 기록한다.
python3 plugins/product-builder/scripts/references.py record \
  --trace .local/product-builder/session.jsonl --scope workspace-account --receipt RECEIPT
```

로컬 텍스트는 `read`, 독립적인 여러 로컬 텍스트는 `read-many --requests <index/id 배열 JSON> --workers 4`로 읽습니다. 외부 도구는 여러 `prepare-read` 후 독립 조회를 병렬 실행하고 각 receipt로 완료를 기록할 수 있습니다. 완료 순서는 자유롭지만 미발급·중복 영수증은 거부합니다. 실패도 해당 영수증의 관측으로 남겨 다른 결과를 보존합니다.

HTTP 또는 커넥터 색인이 로컬 파일 본문을 가리키는 경우에도 그 링크가 읽기 권한을 부여하지 않습니다. 로컬 자료를 읽으려는 호출자가 `--source-root <허용한 로컬 디렉터리>`를 명시해야 합니다. 이 범위는 호출마다 확인하며 이전 성공이나 참조 캐시로 권한을 물려받지 않습니다. 사용자가 선택한 로컬 색인의 파일 바인딩은 기존 로컬 파일 접근 권한 안에서 읽습니다.

## 세션과 재사용

각 진입점은 자신의 trace와 `--scope`를 선택합니다. scope가 바뀐 trace를 재사용할 수 없습니다. 이 값은 상태를 구분하는 호출자 선언이며 인증이나 권한 부여 수단이 아닙니다.

세션은 발견 메타데이터만 캐시하고 로컬 색인의 변경을 감지해 무효화합니다. HTTP 색인의 응답 캐시는 아직 구현하지 않았습니다. 이전 본문을 현재 AI 컨텍스트에서 사용할 때는 기존 실제 읽기의 receipt에 연결한 `reused-from-current-context`로 기록할 수 있습니다. 이것을 최신 원천 조회로 세지 않습니다. 현재 상태가 필요하면 원천을 다시 읽습니다.

캐시에는 원래 locator를 포함한 발견 메타데이터를 보존합니다. 본문 조회를 준비할 때 현재 주소를 다시 해석하므로, 색인은 그대로여도 심볼릭 링크가 다른 원천을 가리키거나 끊어지면 현재 연결을 사용합니다. 발견·조회·등록·수정은 같은 주소 계약을 사용하며 공백이나 한글이 인코딩된 파일 URI도 동일하게 처리합니다.

trace는 본문 없이 참조·관측·메타데이터 검토 기록을 남깁니다. 동시 기록은 같은 사용자 범위의 프로세스 잠금으로 보호합니다. 일반 세션 감사와 Product Builder의 현재 원칙 원천 확인은 별개 결과입니다. 원칙이 바뀌면 해당 새 원천을 다시 읽어야 합니다.

## 관리 절차

`list`가 반환한 `index_digest`를 보존하고, `update --patch <메타데이터 JSON> --expected-digest <값>` 또는 `remove --expected-digest <값>`에 사용합니다. 중간 변경이 있으면 다시 확인하도록 거부하므로 동료의 변경을 덮어쓰지 않습니다. 주소 이동은 확인된 새 locator로 갱신하고, 삭제는 명시적인 관리 작업으로 처리합니다.

원천 변경 뒤에는 `metadata-status --refresh`로 관측을 갱신합니다. 관리자가 description·주제·주소의 적절성을 판단하고 필요한 메타데이터를 바꾼 뒤 `metadata-review --receipt <실제 읽기 영수증>`으로 확인을 기록합니다. 검토한 원천 리비전 또는 참조 바인딩이 달라지면 다시 검토가 필요합니다. 이 확인 정보는 관리 세션에 남고 참조 항목의 정책 값으로 들어가지 않습니다. 원격 원천의 상시 감시나 자동 의미 동기화를 제공한다는 뜻은 아닙니다.

## 한계와 호환성

v2 trace는 독립 영수증과 세션 scope를 사용합니다. 과거 trace·검토 보고서는 당시의 동결 패키지와 하네스로 읽습니다. 새로운 형식으로 조용히 재해석하지 않습니다.

현재는 파일·HTTP 메타데이터 원천을 연결하는 발견 구현과 로컬 세션 실행입니다. 원격 원천의 의미를 판단하거나 조직 전체 검색 인덱스를 운영하지 않습니다. 실제 연결 서비스의 인증, rate limit과 배포는 호스트·원천 어댑터의 책임입니다. trace와 실행 영수증은 재현 근거이며 모든 도구를 강제하는 보안 샌드박스나 증거의 진실성 보증은 아닙니다.
