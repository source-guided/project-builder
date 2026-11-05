# Project Builder

작업에 필요한 원천을 찾아 연결하는 참조 진입점입니다. 처음에는 이 저장소의 플러그인 하나만 받습니다. 기획·UX·UI·구현·검증·스킬 제작 지침은 각각 독립 원천에 있고, 기본 설치에 본문이나 전문 스킬을 포함하지 않습니다.

## 설치하기

사용할 컴퓨터의 Codex 데스크톱 앱 또는 CLI 환경에 설치합니다. 다른 컴퓨터에서 설치한 로컬 플러그인이 자동으로 함께 설치되는 것은 아닙니다. 처음에는 `project-builder` 하나만 설치하며 전문 원천은 작업 중 필요할 때 선택합니다.

### Codex에 설치 맡기기

설치할 컴퓨터에서 Codex를 열고 아래 요청을 그대로 붙여 넣어도 됩니다.

```text
https://github.com/source-guided/project-builder
이 플러그인을 현재 Codex 환경에 설치해줘.

현재 README를 읽고 Codex의 플러그인 설치 기능과 Git·Python 사용 가능 여부부터 확인해줘.
지원되는 설치 방법으로 project-builder@source-guided를 설치해줘.
기존 product-builder@tkddu1591-tools가 설치돼 있으면 새 플러그인 설치 성공 후 교체해줘.

설치 후 project-builder:start만 이 플러그인의 전역 스킬로 노출되고,
전문 스킬들은 전역에 등록되지 않는지 실제 로딩 목록으로 확인해줘.
다른 플러그인과 설정, 기존 프로젝트의 원천 연결은 보존해줘.
설치한 버전과 확인 결과, 새 채팅을 시작해야 하는지도 알려줘.
```

### 직접 설치하기

**1. 준비 상태 확인**

터미널에서 다음 명령을 실행합니다.

```sh
codex --version
codex plugin --help
git --version
python3 --version
```

- Codex에 `plugin marketplace add`, `plugin add` 명령이 있어야 합니다. `codex`를 찾을 수 없거나 해당 명령이 없으면 현재 환경의 Codex 설치·버전·실행 경로부터 확인합니다.
- Git은 GitHub 마켓플레이스를 가져오는 데 필요합니다. 온라인 설치에는 이 공개 저장소에 접근할 수 있어야 합니다.
- Python 3.9 이상이 참조 도구 실행에 필요합니다. 기본 도구와 파일·SQLite·HTTP·GitHub·Supabase·Confluence 어댑터는 표준 라이브러리를 사용합니다. S3를 선택한 경우에는 Python 3.10 이상의 SDK 환경과 `boto3>=1.35.69`를 사용합니다. Windows에서 Python 명령이 `py -3`이면 해당 명령으로 버전을 확인하고 참조 도구를 실행합니다.
- 로컬 검증은 macOS의 Python 3.9, CI는 Linux의 Python 3.12에서 수행했습니다. 다른 환경의 설치·실행 결과는 해당 환경에서 확인해야 합니다.

**2. 마켓플레이스 등록 및 플러그인 설치**

```sh
codex plugin marketplace add source-guided/project-builder --ref main
codex plugin add project-builder@source-guided
```

`source-guided`는 마켓플레이스 이름이고 `project-builder`는 플러그인 이름입니다. 기본 원천 저장소를 함께 복제하거나 전문 스킬을 전역 설치하지 않습니다.

**3. 설치 확인**

```sh
codex plugin list --marketplace source-guided --json
```

결과의 `installed` 목록에서 `pluginId: "project-builder@source-guided"`, `installed: true`, `enabled: true`와 설치 버전을 확인합니다. 이 명령은 플러그인 설치 상태를 확인하며 개별 스킬 로딩 목록까지 보여주지는 않습니다. 새 세션에서 이 플러그인의 스킬이 `project-builder:start` 하나인지 확인합니다.

예전 `product-builder@tkddu1591-tools`를 사용했다면 새 설치가 성공한 뒤 아래 명령으로 기존 플러그인을 제거합니다. 처음 설치하는 사람은 이 단계를 생략합니다.

```sh
codex plugin remove product-builder@tkddu1591-tools
```

**4. 새 채팅 또는 CLI 세션 시작**

설치 후 새 채팅·CLI 세션을 시작합니다. 데스크톱 앱에서 목록이 갱신되지 않으면 앱을 다시 열고 새 채팅을 시작합니다. 이미 진행 중인 채팅에 주입된 예전 스킬 목록이 소급해서 교체됐다고 가정하지 않습니다.

CLI에서 `/plugins`를 입력하거나 데스크톱 앱의 Plugins 화면에서 설치 상태를 확인할 수도 있습니다. 자세한 호스트 사용법은 [공식 플러그인 안내](https://learn.chatgpt.com/docs/plugins#plugin-directory-in-codex-cli)를 참고합니다.

### GitHub에 직접 접근할 수 없는 경우

허용된 반입 경로로 **이 저장소 전체**를 받아 압축을 풉니다. 저장소 루트에 `.agents/plugins/marketplace.json`과 `plugins/project-builder/`가 함께 있어야 합니다. `scripts/package.py`로 만든 플러그인 전용 ZIP에는 마켓플레이스 파일이 없으므로 아래 명령의 입력으로 사용할 수 없습니다.

예를 들어 GitHub에서 받은 저장소 ZIP을 풀어 `project-builder-main` 폴더가 생겼다면, 그 폴더의 상위 디렉터리에서 실행합니다.

```sh
codex plugin marketplace add ./project-builder-main
codex plugin add project-builder@source-guided
```

실제 폴더 이름이 다르면 첫 명령의 경로를 바꿉니다. 기존에 같은 이름의 Git 마켓플레이스를 등록했다면 별도 이름으로 중복 등록하거나 설정을 덮어쓰지 말고 현재 등록 위치를 먼저 확인합니다.

이 방식은 GitHub에서 설치 파일을 가져오는 과정을 대체합니다. Codex 자체의 사용 연결이나 이후 선택할 외부 원천의 접근까지 오프라인으로 만드는 것은 아닙니다. 기본 원천의 원격 주소에 접근할 수 없으면 작업 중 접근 가능한 로컬·사내 원천을 연결하거나 별도 원천 없는 일반 방식을 선택합니다. [공식 로컬 마켓플레이스 등록 안내](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli)

## 처음 사용하기

작업할 프로젝트를 열고 새 채팅에서 아래처럼 참조 진입점을 명시적으로 호출합니다. 모델과 추론 강도는 사용하는 환경에서 선택합니다.

```text
$project-builder:start
이 프로젝트의 프론트를 수정하려고 해. 관련 원천과 기존 결정을 찾아줘.
```

새 채팅을 여는 것만으로 모든 요청이 이 진입점을 반드시 거치는 것은 아닙니다. 참조 흐름을 사용하려는 작업에서는 위처럼 호출합니다. 현재 프로젝트의 `AGENTS.md`와 실행 환경의 권한도 함께 적용됩니다.

먼저 프로젝트에 연결된 자료를 확인합니다. 필요한 원천이 없을 때만 작업 문맥에서 선택을 제안합니다.

> 디자인 기준은 아직 연결돼 있지 않습니다. 기본 UX·UI 원천을 사용할까요? 가지고 있는 로컬 문서나 Figma·Confluence 등의 원천을 연결할 수도 있습니다.

선택을 해당 프로젝트에 기록하고, 필요한 내용만 참조를 통해 읽습니다. 연결은 전체 다운로드나 전역 스킬 설치를 뜻하지 않습니다. 이미 선택한 범위는 다시 묻지 않으며, 새 질문이나 변경이 생기면 관련 참조로 돌아갑니다.

## 참조를 어디에 둘 수 있나요?

**참조 목록, 프로젝트의 원천 선택 상태, 조회 영수증을 각각 원하는 저장소에 둘 수 있습니다.** `.local/`은 로컬 보관 예시이며 필수 위치가 아닙니다.

- 개인용: 본인만 접근하는 파일·SQLite·비공개 저장소·클라우드 문서
- 팀용: 팀이 접근하는 GitHub 저장소·Supabase DB·S3 버킷·Confluence 페이지 등
- 다른 서비스: 조건부 변경을 지원하는 HTTP 저장소 또는 호스트가 제공하는 어댑터

파일 경로는 그대로 사용하고, 설정한 저장소는 `store://team/references`처럼 연결합니다. 프로젝트의 선택 상태는 `store://team/project-a`, 조회 영수증은 `store://team/receipts/alice/run-001`처럼 서로 다른 문서에 둘 수 있으며 로컬 복사본을 필수로 만들지 않습니다. 저장소 프로필은 연결 정보만 담고 인증정보는 각 사용자의 실행 환경에서 제공합니다.

공유 범위는 해당 저장소의 실제 계정·권한이 결정합니다. 참조 목록을 공유한다고 대상 문서의 권한까지 공유되는 것은 아니며, 이 플러그인이 서비스 권한을 자동으로 변경하지 않습니다. 동시 수정은 저장소의 리비전·ETag·SHA 조건으로 충돌을 확인합니다.

[개인·팀 저장소 설정과 실제 명령](docs/reference-storage.md)에서 SQLite 시작 예제, 서비스별 프로필, Supabase 개인용 테이블 예제와 검증 범위를 확인할 수 있습니다.

조회 영수증도 같은 저장소 프로필을 사용합니다. `--trace`에 저장 주소를, `--scope`에 해당 사용자의 조회 맥락을 명시합니다. 아래 예제의 `team`, `alice-work`, 기록 키는 실제 선택한 프로필과 맥락으로 바꿉니다.

```sh
python3 <plugin>/scripts/references.py read --index <plugin>/references/governance/index.json --id routing-policy --trace store://team/receipts/alice/run-001 --scope alice-work --store-config stores.json
python3 <plugin>/scripts/references.py audit --trace store://team/receipts/alice/run-001 --scope alice-work --store-config stores.json
```

개인용은 본인만 접근하는 저장소에, 팀 공유용은 구성원이 읽을 수 있는 저장소에 기록합니다. 조회 맥락이 다른 사용자는 별도 기록 키를 사용하며 다른 사람의 영수증을 자신의 조회로 간주하지 않습니다. `trace-show`로 상세 기록을 보고, 필요한 경우에만 `trace-export`로 JSONL 스냅샷을 내보낼 수 있습니다. 영수증에는 원천 주소·발견 메타데이터가 포함되며 실제 원천 본문과 인증정보는 복제하지 않습니다.

## 별도로 관리되는 기본 원천

| 원천 | 책임 |
| --- | --- |
| [product-sources](https://github.com/source-guided/product-sources) | 요구사항·제품 정책·제약 해석 |
| [design-sources](https://github.com/source-guided/design-sources) | UX·UI·접근성·화면 예제와 검증 |
| [engineering-sources](https://github.com/source-guided/engineering-sources) | 구현과 기술 판단 |
| [work-sources](https://github.com/source-guided/work-sources) | 작업 재개·결정·증거·독립 검토 |
| [skill-authoring-sources](https://github.com/source-guided/skill-authoring-sources) | 원천 내부 스킬의 제작·개선 방법 |

코어에는 이 원천들의 발견용 설명과 주소만 있습니다. 각 원천은 다른 기본 원천을 필수 의존성으로 설치하지 않습니다. 사용자 원천과 함께 쓰거나 교체할 수 있습니다.

스킬 제작 기준이 연결돼 있지 않다면 **기본 제작 원천, 사용자 제작 원천, 별도 제작 원천 없이 AI의 일반적인 방식** 중 선택합니다. 일반 방식을 선택해도 사용자의 요구와 참조 체계의 공통 참여 규약은 유지합니다.

## 소유 경계

- `project-builder`: 참조 진입·탐색·연결·메타데이터·세션 기록과 공통 참여 계약
- 각 원천: 내부 스킬, 분야별 기준, 예제, 해당 분야의 검증
- 소비 프로젝트: 사용자가 선택한 로컬·원격 저장소의 참조 목록, 원천 선택과 프로젝트 고유 자료·결정·진행 상태

원천 스킬은 `capabilities/`에 두고 원천의 참조를 거쳐 문맥에 맞게 읽습니다. 이 플러그인에 전문 스킬을 합치거나 사용자의 전역 스킬 목록에 자동 등록하지 않습니다. 각 원천은 자기 `source.json`과 참조 색인, 공개 파일 목록을 관리합니다.

새 원천과 프로젝트 자료는 본문과 참조를 함께 분야·책임별로 구조화합니다. 담당자 질문·답변과 스펙을 루트에 계속 쌓는 대신 소유 영역 아래에 두고, 각 영역의 색인으로 탐색합니다. 각 영역 안에서도 같은 판단을 반복해 하나의 책임은 함께 두고 독립적으로 바뀌는 하위 책임은 더 나눕니다. 다른 원천을 받지 않는 일반 방식에도 적용되며, 특정 폴더 이름이나 불필요한 깊이는 강제하지 않습니다. 자세한 기준은 [공통 참여 계약](plugins/project-builder/sources/source-contract.md)의 자료 구성 절에서 확인합니다.

로컬 파일과 HTTP 색인은 기본 도구로 탐색합니다. Confluence·DB 등은 관측한 주소와 접근 방식을 연결하고 사용 중인 호스트의 허가된 도구로 읽습니다. 이 플러그인이 별도 계정이나 모든 서비스의 인증·조회 기능을 제공하는 것은 아닙니다.

[참조와 연결 사용법](docs/reference-architecture.md) · [공통 참여 계약](plugins/project-builder/sources/source-contract.md)

## 유지보수자 검증

일반 사용자에게 아래 절차나 작업 시간 제한을 요구하지 않습니다.

```sh
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
python3 scripts/package.py
python3 scripts/validate_source.py --source /path/to/selected-source
```

코어 검사는 단일 공개 스킬과 원천 본문 비포함, 참조·연결 동작을 확인합니다. 도메인별 검사는 원천 저장소가 소유하며, UI 예제의 개발 의존성과 브라우저 검사는 `design-sources`에 있습니다.

[검증의 범위](docs/validation.md) · [새 맥락에서의 검증](docs/forward-testing.md)

실제 과제·데이터·답안·실행 증거·소비 프로젝트 참조는 공개 저장소에 넣지 않습니다. MIT License.
