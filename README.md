# Project Builder

작업에 필요한 원천을 찾아 연결하는 참조 진입점입니다. 처음에는 이 저장소의 플러그인 하나만 받습니다. 기획·UX·UI·구현·검증·스킬 제작 지침은 각각 독립 원천에 있고, 기본 설치에 본문이나 전문 스킬을 포함하지 않습니다.

## 시작하기

```sh
codex plugin marketplace add source-guided/project-builder --ref main
codex plugin add project-builder@source-guided
```

새 채팅에서 현재 작업을 말하거나 명시적으로 참조 진입점을 부릅니다. 모델과 추론 강도는 사용하는 환경에서 선택합니다.

```text
$project-builder:start
이 프로젝트의 프론트를 수정하려고 해. 관련 원천과 기존 결정을 찾아줘.
```

먼저 프로젝트에 연결된 자료를 확인합니다. 필요한 원천이 없을 때만 작업 문맥에서 선택을 제안합니다.

> 디자인 기준은 아직 연결돼 있지 않습니다. 기본 UX·UI 원천을 사용할까요? 가지고 있는 로컬 문서나 Figma·Confluence 등의 원천을 연결할 수도 있습니다.

선택을 해당 프로젝트에 기록하고, 필요한 내용만 참조를 통해 읽습니다. 연결은 전체 다운로드나 전역 스킬 설치를 뜻하지 않습니다. 이미 선택한 범위는 다시 묻지 않으며, 새 질문이나 변경이 생기면 관련 참조로 돌아갑니다.

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
- 소비 프로젝트: 원천 선택과 프로젝트 고유 자료·결정·진행 상태

원천 스킬은 `capabilities/`에 두고 원천의 참조를 거쳐 문맥에 맞게 읽습니다. 이 플러그인에 전문 스킬을 합치거나 사용자의 전역 스킬 목록에 자동 등록하지 않습니다. 각 원천은 자기 `source.json`과 참조 색인, 공개 파일 목록을 관리합니다.

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
