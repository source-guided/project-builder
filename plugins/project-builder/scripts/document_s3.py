"""선택한 S3 저장소에서만 AWS SDK를 로드하며 IAM과 ETag 조건을 유지한다."""

import json

from document_store import ConflictError, MissingDocument, StoreError, encode, observation


class S3Store:
    def __init__(self, *, bucket, prefix="", region=None, profile=None, client=None, max_bytes=1024 * 1024):
        if client is None:
            try:
                import boto3
            except ImportError:
                raise StoreError("S3 requires optional boto3>=1.35.69; other stores do not require it") from None
            client = boto3.Session(profile_name=profile, region_name=region).client("s3")
        self.client, self.bucket, self.prefix, self.max_bytes = client, bucket, prefix.strip("/"), max_bytes

    def _key(self, key):
        return "/".join(filter(None, (self.prefix, key)))

    def _call(self, method, **kwargs):
        try:
            return getattr(self.client, method)(**kwargs)
        except Exception as error:
            code = str(getattr(error, "response", {}).get("Error", {}).get("Code", ""))
            if code in {"NoSuchKey", "404"}:
                raise MissingDocument("S3 document does not exist") from None
            if code in {"PreconditionFailed", "ConditionalRequestConflict", "412", "409"}:
                raise ConflictError("S3 object changed; read it again") from None
            raise StoreError("S3 request failed; inspect AWS credentials, IAM, endpoint and SDK version") from None

    def read(self, key):
        result = self._call("get_object", Bucket=self.bucket, Key=self._key(key))
        try:
            raw = result["Body"].read(self.max_bytes + 1)
        finally:
            result["Body"].close()
        if len(raw) > self.max_bytes:
            raise StoreError("S3 document exceeds the configured size limit")
        return observation(json.loads(raw), result["ETag"], raw=raw)

    def write(self, key, document, *, expected_revision):
        condition = {"IfNoneMatch": "*"} if expected_revision is None else {"IfMatch": expected_revision}
        result = self._call("put_object", Bucket=self.bucket, Key=self._key(key), Body=encode(document),
                            ContentType="application/json", **condition)
        return observation(document, result["ETag"])
