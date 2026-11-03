"""참조 위치의 주소 해석. 발견·관리·접근 어댑터가 같은 규칙을 사용한다."""

from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse


def address(base, locator=None):
    value = str(base)
    if urlparse(value).username or urlparse(value).password:
        raise ValueError("Reference addresses must not contain credentials")
    if locator is None:
        return value if urlparse(value).scheme and len(urlparse(value).scheme) != 1 else str(Path(value).resolve())
    parsed = urlparse(str(locator))
    if parsed.scheme and len(parsed.scheme) != 1:
        return str(locator)
    if urlparse(value).scheme in {"http", "https", "file"}:
        return urljoin(value, str(locator))
    return str((Path(value).parent / locator).resolve())


def index_access(index):
    scheme = urlparse(str(index)).scheme
    return "web" if scheme in {"http", "https"} else "file" if scheme in {"", "file"} or len(scheme) == 1 else "connector"


def index_address(index, access):
    if urlparse(str(index)).username or urlparse(str(index)).password:
        raise ValueError("Reference addresses must not contain credentials")
    if access == "connector":
        return str(index)
    if access == "web" and index_access(index) != "web":
        raise ValueError("Web index needs an HTTP(S) address")
    if access == "file" and index_access(index) != "file":
        raise ValueError("File index cannot be read through a different access method")
    if access == "file" and urlparse(str(index)).scheme == "file":
        parsed=urlparse(str(index))
        if parsed.netloc not in {"","localhost"}:
            raise ValueError("Remote file authorities require their own adapter")
        return str(Path(unquote(parsed.path)).resolve())
    return address(index)


def source_address(index, locator, access):
    if access == "connector":
        return str(locator)
    if access == "web":
        return index_address(locator, "web")
    if index_access(index) != "file" and not Path(locator).is_absolute() and urlparse(locator).scheme != "file":
        raise ValueError("Relative file locations require a file index")
    if index_access(index) != "file":
        return address(locator)
    return address(index, locator)


def local_path(address):
    parsed = urlparse(str(address))
    if parsed.scheme == "file":
        if parsed.netloc not in ("", "localhost"):
            raise ValueError("Remote file authorities require their own adapter")
        return Path(unquote(parsed.path)).resolve()
    if parsed.scheme and len(parsed.scheme) != 1:
        raise ValueError(f"No index adapter configured for {parsed.scheme}")
    return Path(address).resolve()
