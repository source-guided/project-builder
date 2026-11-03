# 개인·팀 참조 저장소

참조 목록과 실제 데이터 원천은 서로 다른 곳에 있어도 됩니다. `.local/`은 로컬 작업 기록의 예시이며 저장 위치 제약이 아닙니다. 참조 목록, 프로젝트의 원천 선택 상태, 실제 데이터, 개인 인증정보를 구분해 관리합니다.

```text
사용자 환경의 저장소 프로필
  → 개인 또는 팀 참조 목록
  → 참조가 가리키는 실제 원천
```

| 대상 | 저장 방식 | 권한의 원천 |
| --- | --- | --- |
| 참조 목록 | 파일·SQLite·HTTP·GitHub·Supabase·S3·Confluence 또는 호스트 어댑터 | 선택한 저장소의 실제 권한 |
| 프로젝트 원천 선택 | 위와 같은 문서 저장소, 참조 목록과 별도 문서 | 선택한 저장소의 실제 권한 |
| 실제 데이터·문서 | 사용자가 선택한 기존 원천 | 해당 원천의 계정·권한 |
| 인증정보 | 실행 환경의 환경변수·AWS 자격 증명 체계·호스트의 승인된 계정 | 해당 인증 제공자 |
| 조회 영수증·실행 흔적 | 현재 구현은 호출자가 지정한 로컬 `--trace` 파일 | 실행 환경의 파일 권한 |

참조를 공유해도 그 참조가 가리키는 문서의 권한까지 공유되지는 않습니다. `personal`, `team` 같은 프로필 이름이나 `writable` 설정은 ACL이 아닙니다. 개인 저장소는 본인 계정만 허용하고, 팀 저장소는 지정한 구성원에게 읽기·수정 권한을 부여하는 등 실제 설정을 해당 서비스에서 관리합니다. 이 클라이언트는 공유 범위를 임의 변경하지 않습니다.

## 공통 주소와 프로필

로컬 JSON 파일은 기존 경로를 그대로 사용합니다. 다른 저장소는 `store://프로필/문서키`로 지정합니다. 다음은 별도 Python 의존성이 없는 SQLite 예시입니다. `stores.json` 파일 자체도 `.local`에 둘 필요는 없습니다.

```json
{
  "format": 1,
  "profiles": {
    "team": {
      "driver": "sqlite",
      "path": "./team-references.db",
      "writable": true
    }
  }
}
```

SQLite 상대 경로는 `stores.json`이 있는 폴더를 기준으로 해석합니다. 아래 `<plugin>`은 설치 도구가 반환한 `installedPath` 또는 저장소의 `plugins/project-builder` 디렉터리로 바꿉니다. `<조회한 digest>`는 바로 앞 조회 결과의 실제 값으로 바꿉니다.

```sh
python3 <plugin>/scripts/references.py init --index store://team/references --store-config stores.json
python3 <plugin>/scripts/references.py add --index store://team/references --store-config stores.json --id requirements --label 요구사항 --access web --locator https://example.com/your-actual-document
python3 <plugin>/scripts/references.py list --index store://team/references --store-config stores.json
```

예제 URL은 설명용입니다. `add`할 때는 사용자가 실제로 확인한 문서 주소로 바꿉니다. `init`은 새 문서를 만들며 같은 키가 이미 있으면 덮어쓰지 않고 실패합니다. 기존 참조를 연결할 때는 `init` 없이 조회합니다.

프로젝트의 선택 상태도 같은 DB 또는 다른 저장소에 둘 수 있습니다.

```sh
python3 <plugin>/scripts/sources.py init --state store://team/project-a --store-config stores.json
python3 <plugin>/scripts/sources.py select --state store://team/project-a --store-config stores.json --intent requirements --mode custom --index store://team/references --access connector
python3 <plugin>/scripts/sources.py discover --state store://team/project-a --store-config stores.json --intent requirements
```

다른 사용자는 같은 저장소를 가리키는 자신의 프로필과 계정을 사용합니다. 개인 토큰을 설정 파일과 함께 공유하지 않습니다. 로컬 DB 경로를 공유한다고 다른 컴퓨터에서 자동 접근되는 것은 아닙니다. 여러 컴퓨터에서 공동으로 사용하려면 실제 공용 서비스나 허용된 공유 저장소를 선택합니다.

`store://` 색인 안에서는 각 원천·하위 색인의 주소와 접근 방식을 명시합니다. 불투명한 DB 키에 파일 상대 경로 의미를 부여하지 않습니다. 예를 들어 하위 색인은 `access: "connector"`, `locator: "store://team/design"`으로 연결합니다. 다른 프로필을 발견했다고 그 프로필의 접근 범위를 얻지는 않습니다.

## 서비스별 연결

[프로필 예제](../plugins/project-builder/examples/storage-profiles.json)에서 사용할 항목만 복사하고 실제 저장소 정보로 바꿉니다. 예제는 기본적으로 읽기 전용입니다. 허가된 쓰기 작업에 사용할 프로필만 `writable: true`로 설정합니다. 조회 자체는 테이블·버킷·페이지를 생성하지 않습니다.

| 드라이버 | 문서키의 의미 | 변경 충돌 조건 | 계정·권한 |
| --- | --- | --- | --- |
| `sqlite` | `reference_documents` 테이블의 key | 트랜잭션 안에서 revision 비교 | DB 파일 권한 |
| `http` | endpoint 아래 JSON 문서 경로 | 강한 ETag, If-Match / If-None-Match | 선택적 Bearer 환경변수와 서버 권한 |
| `github` | repository/branch/prefix 아래 파일 | Contents API 파일 SHA | 토큰의 Contents 권한과 저장소·브랜치 정책 |
| `supabase` | 지정한 테이블의 고유 id | id와 revision을 함께 조건으로 PATCH | API key, 사용자 토큰, RLS |
| `s3` | bucket/prefix 아래 객체 키 | 조건부 PutObject의 ETag | AWS 프로필·자격 증명 체계와 IAM |
| `confluence` | 지정한 기존 페이지의 content property key | property ID와 version.number | 페이지 조회·수정 권한 |
| `host` | 호스트 어댑터가 해석하는 키 | 어댑터가 보장하는 원자적 revision 비교 | 호스트가 연결한 실제 서비스 계정 |

HTTP는 조건부 PUT을 실제로 지원하는 서버가 필요합니다. 일반 JSON 웹페이지는 읽을 수 있지만 ETag 없는 문서를 안전하게 갱신한다고 주장하지 않습니다. 인증된 저장소 요청의 리다이렉트는 따라가지 않습니다. 새 endpoint가 필요한 경우 사용자가 확인한 주소로 설정을 바꿉니다.

GitHub는 특정 브랜치의 JSON 파일을 읽고 커밋합니다. 서비스의 파일 크기 제한·브랜치 보호 규칙을 유지합니다. 토큰을 URL에 넣지 않고 `token_env`가 지정한 환경변수로 전달합니다. [GitHub Contents API](https://docs.github.com/en/rest/repos/contents)

Supabase의 테이블 계약은 고유 `id`, JSONB `document`, 증가하는 `revision`입니다. [개인용 테이블 예제](../plugins/project-builder/examples/supabase.sql)는 새 테이블과 본인 소유 행만 접근하는 RLS를 구성합니다. 사용자는 publishable/anon API key와 로그인한 사용자의 액세스 토큰을 서로 다른 환경변수로 제공합니다. 개인·팀 권한을 유지하려는 클라이언트에 RLS를 우회하는 service-role key를 배포하지 않습니다. 팀 공유는 해당 프로젝트의 멤버십과 정책에 맞춰 원천 관리자가 구성해야 합니다. [Supabase Data API](https://supabase.com/docs/guides/api), [RLS](https://supabase.com/docs/guides/database/postgres/row-level-security)

같은 Supabase 테이블을 여러 개인이 쓴다면 문서키도 `users/<사용자 ID>/references`처럼 테이블 전체에서 구분되게 선택합니다. 키 이름 자체가 권한을 부여하지는 않으며 RLS가 실제 소유자를 확인합니다. 같은 팀 문서를 공유하는 사용자들은 의도적으로 같은 문서키를 사용합니다.

S3만 선택적으로 `boto3>=1.35.69`가 필요합니다. 해당 드라이버를 사용하는 Python 3.10 이상의 SDK 환경에 설치하며 다른 저장소에는 필요하지 않습니다. SDK의 일반 자격 증명 체계를 사용하고 코드·프로필 JSON에 액세스 키를 쓰지 않습니다. [S3 조건부 쓰기](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html)

Confluence는 Cloud REST v2의 **페이지 content property**를 사용합니다. 페이지 본문의 기존 글을 JSON으로 덮어쓰지 않습니다. endpoint는 사이트의 `/wiki`를 포함하며, `email_env`와 `token_env`를 함께 지정하면 API token의 Basic 인증, token만 지정하면 Bearer 인증을 사용합니다. property의 크기 제한과 페이지 접근 제한은 Confluence가 적용합니다. Data Center와 임의 본문 형식은 이 어댑터의 검증 범위가 아닙니다. [Confluence Content Properties API](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-content-properties/)

## 다른 서비스와 호스트 도구

`Stores(config, adapters={"custom": adapter})`로 호스트 어댑터를 주입할 수 있습니다. 선택한 프로필의 driver는 `host`로 둡니다. 어댑터의 계약은 다음과 같습니다.

```python
read(key) -> {"document": ..., "digest": "sha256...", "revision": "opaque-version"}
write(key, document, expected_revision=...) -> same_observation
```

`expected_revision=None`은 새 문서 생성입니다. 기존 문서가 있으면 실패해야 합니다. 나머지는 일치하는 리비전에만 원자적으로 쓰며 충돌·접근 거부를 그대로 보고합니다. 조회 후 무조건 쓰는 구현은 이 계약을 충족하지 않습니다. 호스트 도구가 원자적 변경을 제공하지 않으면 읽기 전용으로 연결합니다.

## 변경·검증과 한계

`references.py update/remove`는 조회한 `index_digest`를 요구하고, 저장소 어댑터는 실제 쓰기에 저장소 리비전 조건을 추가합니다. `remove`는 참조 항목을 제거할 뿐 원천 문서·DB 행·버킷 객체를 삭제하지 않습니다. `sources.py select`도 기존 선택을 바꿀 때 `show`의 digest를 요구합니다. 충돌 시 최신 문서를 다시 읽고 의도를 조정하며 무조건 덮어쓰기·숨은 로컬 대체 저장을 하지 않습니다.

원격 공유 상태가 로컬 원천을 가리키는 경우 `--source-root`로 호출자가 해당 로컬 범위를 명시해야 합니다. 세션의 `--scope`는 기록 분리용이며 인증이나 ACL을 대신하지 않습니다. 조회 영수증은 현재 로컬 파일 어댑터로 기록하며, 이 변경이 전체 실행 기록의 클라우드 동기화를 구현한 것은 아닙니다.

파일·SQLite는 실제 저장으로, HTTP 기반 서비스는 테스트 서버에서 인증 전달·정상 변경·접근 거부·충돌을, S3는 SDK 호출 계약을 검증합니다. 실제 Supabase/S3/Confluence 계정에 대한 쓰기와 공유 권한은 해당 계정에서 별도로 검증해야 합니다. 이 저장소가 임의의 서비스 계정에 가입하거나 권한을 변경하지는 않습니다.
