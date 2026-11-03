# Product Builder

요구사항을 읽고, 사용자 흐름을 설계하고, 구현과 검증을 끝까지 연결하는 Codex 플러그인입니다. 긴 프롬프트를 반복해서 붙여 넣지 않고 한 번의 시작 지시로 진행하거나 기존 작업을 이어갑니다.

특정 서비스, 기술 스택, 화면 형태를 강제하지 않습니다. 새 제품부터 기존 기능 수정까지 작업 범위에 맞게 줄이거나 확장합니다. 화면이 없는 도구에는 UI를 추가하지 않습니다.

## 설치

Codex CLI의 플러그인 기능이 필요합니다. 로컬 설치 검증 버전은 **0.153.4**입니다.

```sh
codex plugin marketplace add tkddu1591/product-builder --ref v0.1.0
codex plugin add product-builder@tkddu1591-tools
```

새 채팅에서 모델을 **GPT-6.1 Sol**, reasoning effort를 **High**로 선택한 뒤 시작합니다.

```text
$product-builder:start
이 저장소의 요구사항을 읽고 작업해줘. 사용할 수 있는 시간은 4시간이야.
```

기존 작업도 같은 진입점으로 이어갑니다.

```text
$product-builder:start
현재 코드와 작업 기록을 확인해서 남은 구현과 검증을 이어가줘.
```

설치 여부는 다음으로 확인합니다. 이미 열린 채팅의 스킬 목록이 자동으로 갱신됐다고 가정하지 마세요.

```sh
codex plugin list --marketplace tkddu1591-tools --json
```

공개 GitHub 저장소에서 설치하는 패키지이며, OpenAI의 공개 플러그인 디렉터리에 등록됐다는 의미는 아닙니다. 클라이언트별 플러그인 지원 여부와 필요한 도구 접근은 별도입니다.

## 작업 방식

| 스킬 | 맡는 일 |
| --- | --- |
| `start` | 현재 자료·환경·작업 상태를 확인하고 필요한 절차를 연결 |
| `brief` | README·기획·계약·인수 조건을 출처가 있는 요구와 검증 항목으로 정리 |
| `product-ux` | 사용자 과업, 정보 우선순위, 상태와 회복 흐름을 설계·검토 |
| `implementation` | 입력부터 관찰 가능한 결과까지 한 흐름씩 구현 |
| `verification` | 실제 요구에 맞게 기능·예외·UX를 확인하고 증거와 한계를 보고 |

단계마다 승인을 요구하지 않습니다. 자료로 해결할 수 없는 중요한 결정만 질문하고, 이미 허용된 구현·검증은 계속합니다. Git 게시·배포·외부 메시지는 별도 사용자 권한 범위에 따릅니다.

## UX 기준

- 화면 구성 전에 누가 무엇을 완료하려는지 정의합니다.
- 각 정보와 조작을 사용자 판단·행동에 연결합니다.
- 필요성이 없는 통계 카드, 배너, 필터, 개발 설명을 관성적으로 추가하지 않습니다.
- 필요한 오류·접근성 안내·결과의 유효성과 영향을 유지합니다.
- 실제 렌더링과 사용자 흐름으로 확인하고, 미확인 화면은 검증 완료로 보고하지 않습니다.

[적용 조건과 반례](plugins/product-builder/skills/product-ux/references/patterns.md), [다른 도메인의 요구사항 예시](plugins/product-builder/skills/brief/references/examples.md), [제약조건 추출 기준](plugins/product-builder/skills/brief/references/constraints.md)을 포함합니다. 예제의 수치나 기능은 다른 프로젝트의 기본값이 아닙니다.

[실행 가능한 문서 검토 예제](plugins/product-builder/skills/product-ux/assets/document-review/index.html)와 데스크톱·좁은 화면 캡처도 포함합니다. 이 예제는 합성 콘텐츠를 사용하는 화면 흐름 참고 자료이며, 상태는 현재 페이지에서만 유지됩니다.

[편집 방식 선택과 화면 위치 유지 기준](plugins/product-builder/skills/product-ux/references/interaction-patterns.md)은 인라인 편집·모달·별도 페이지의 적용 조건과 레퍼런스를 정리합니다. 레이아웃 이동을 가리기 위해 팝업을 기본값으로 선택하지 않습니다.

## 도구와 모델

기본 패키지는 스킬·예시·스크립트로 구성되며 자체 MCP 서버나 별도 서비스 인증을 요구하지 않습니다. 사용 중인 환경에 브라우저, Figma, 저장소 도구가 있으면 필요한 작업에 사용합니다. 도구가 없으면 가능한 확인을 수행하고 미검증 범위를 남깁니다.

검증 대상 설정은 **GPT-6.1 Sol / High**입니다. 플러그인은 모델 설정을 바꾸거나 다른 모델로 전환하지 않습니다. 설치와 모델 접근 권한은 별개입니다. 테스트한 ChatGPT 계정의 CLI는 `gpt-6.1-sol` 호출을 거부했으므로, 해당 환경의 행동 검증은 앱에서 명시적으로 Sol / High를 선택해 수행합니다. [검증 방법과 결과](docs/validation.md)를 확인하세요.

## 프로젝트 기록과 비공개 자료

공통 절차는 플러그인에, 실제 프로젝트의 요구사항·결정·검증·진행 상태는 해당 프로젝트에 둡니다. 기존 owner 문서가 있으면 이를 사용하고 중복 원본을 만들지 않습니다.

민감한 기록에 사용할 `.local/product-builder/`를 준비하는 선택적 스크립트가 포함되어 있습니다. 기존 기록을 덮어쓰지 않고 `.gitignore`에 `/.local/`를 추가합니다. 이미 추적 중인 파일까지 추적 해제하지는 않습니다.

이 저장소의 `.local/` 내용은 공개 패키지에 들어가지 않습니다. 배포 ZIP은 플러그인 디렉터리의 허용 파일만 포함합니다. 원천 자료를 외부로 보내거나 자동 업로드하는 기능은 없습니다.

## 개발과 검증

Python 3.9 이상, 표준 라이브러리와 Git으로 패키지 검사를 실행할 수 있습니다.

```sh
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
python3 scripts/package.py
```

공개 UX 예제의 브라우저 회귀 검사에는 Node.js 22와 Playwright 개발 의존성을 사용합니다. 플러그인을 사용하는 프로젝트에 이 의존성을 설치할 필요는 없습니다.

```sh
npm ci
npx playwright install chromium
npm run test:ui
```

실제 viewport 4종에서 편집·오류·취소 전후 주요 영역 위치, 스크롤·포커스, 리비전별 승인, 키보드와 긴 내용을 확인합니다. 이 예제의 위치 허용치는 1px이며 모든 제품의 레이아웃을 고정하는 규칙이 아닙니다.

모델 행동 평가는 [evals](evals/README.md)를 따릅니다. 패키지 검사 통과, 모델의 작업 결과, 제품 런타임 검사, 실제 배포·사용자 인수는 각각 구분합니다. 한 번의 평가로 모든 도메인에서의 품질을 보장하지 않습니다.

## 구조

```text
.agents/plugins/marketplace.json   # GitHub 배포 소스
plugins/product-builder/
  plugin.json                     # 설치 패키지
  skills/                         # 공통 절차·참고 자료·템플릿
evals/                            # 공개 합성 시나리오와 검토 기준
scripts/                          # 구조·배포·평가 준비 도구
tests/                            # 파일 보존·배포 경계 등의 검사
.local/                           # 비공개 기록·실행 증거, Git 제외
```

패키징 형식은 [OpenAI 공식 문서](https://developers.openai.com/plugins/build/plugins)를 따릅니다. MIT License.
