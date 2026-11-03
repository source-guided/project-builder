-- 선택한 Supabase 프로젝트에 새 개인용 저장소를 만들 때만 실행한다.
-- 기존 테이블·정책을 대체하거나 팀 공유 권한을 자동 생성하지 않는다.
create table public.reference_documents (
  -- 테이블 전체에서 고유한 키를 사용한다. 예: users/<사용자 ID>/references.
  id text primary key,
  owner_id uuid not null default auth.uid(),
  document jsonb not null,
  revision bigint not null check (revision > 0)
);

alter table public.reference_documents enable row level security;
revoke all on public.reference_documents from anon, authenticated;
grant select, insert, update on public.reference_documents to authenticated;

create policy "Read own reference documents"
  on public.reference_documents for select to authenticated
  using (owner_id = (select auth.uid()));

create policy "Create own reference documents"
  on public.reference_documents for insert to authenticated
  with check (owner_id = (select auth.uid()) and revision = 1);

create policy "Update own reference documents"
  on public.reference_documents for update to authenticated
  using (owner_id = (select auth.uid()))
  with check (owner_id = (select auth.uid()));

-- 다른 클라이언트도 리비전을 감소·재사용하지 못하게 한다.
create function public.check_reference_document_revision()
returns trigger language plpgsql set search_path = '' as $$
begin
  if new.revision <> old.revision + 1 then
    raise exception 'Reference document revision must increase by one';
  end if;
  return new;
end;
$$;

create trigger reference_document_revision
before update on public.reference_documents
for each row execute function public.check_reference_document_revision();
