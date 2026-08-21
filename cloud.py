#!/usr/bin/env python3
"""R2/S3 cloud storage for zensync. No external dependencies, no encryption."""

import hashlib
import hmac
import json
import os
import sys
import tarfile
from datetime import datetime, timezone
from io import BytesIO
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def sign_aws_v4(method, url, headers, payload, region, service, access_key, secret_key):
    """AWS Signature V4 signing."""
    from urllib.parse import urlparse, quote

    parsed = urlparse(url)
    host = parsed.hostname
    path = quote(parsed.path or "/", safe="/")
    query = parsed.query or ""

    now = datetime.now(timezone.utc)
    datestamp = now.strftime("%Y%m%d")
    amzdate = now.strftime("%Y%m%dT%H%M%SZ")

    headers["host"] = host
    headers["x-amz-date"] = amzdate
    headers["x-amz-content-sha256"] = hashlib.sha256(payload).hexdigest()

    signed_headers = sorted(headers.keys())
    signed_headers_str = ";".join(signed_headers)

    canonical_headers = "".join(f"{k}:{headers[k]}\n" for k in signed_headers)
    canonical_request = "\n".join([
        method, path, query, canonical_headers,
        signed_headers_str, hashlib.sha256(payload).hexdigest()
    ])

    credential_scope = f"{datestamp}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256", amzdate, credential_scope,
        hashlib.sha256(canonical_request.encode()).hexdigest()
    ])

    def hmac_sha256(key, msg):
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()

    signing_key = hmac_sha256(
        hmac_sha256(
            hmac_sha256(
                hmac_sha256(f"AWS4{secret_key}".encode(), datestamp),
                region
            ),
            service
        ),
        "aws4_request"
    )

    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    headers["authorization"] = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers_str}, Signature={signature}"
    )

    return headers


def r2_request(method, key, data, config):
    """Make a signed request to R2. Transport is always TLS (https); this
    just skips the extra age-encryption-at-rest layer the upstream tool has."""
    account_id = config["account_id"]
    bucket = config["bucket"]
    access_key = config["access_key"]
    secret_key = config["secret_key"]

    url = f"https://{account_id}.r2.cloudflarestorage.com/{bucket}/{key}"
    headers = {"content-type": "application/octet-stream"} if data else {}

    signed = sign_aws_v4(
        method, url, headers, data or b"",
        "auto", "s3", access_key, secret_key
    )

    req = Request(url, data=data if method == "PUT" else None, method=method)
    for k, v in signed.items():
        req.add_header(k, v)

    try:
        resp = urlopen(req, timeout=60)
        return resp.read() if method == "GET" else True
    except HTTPError as e:
        if e.code == 404 and method == "GET":
            return None
        raise


def pack_files(profile_path, files):
    """Pack profile files into a tar.gz archive, preserving mtimes."""
    buf = BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for f in files:
            full = os.path.join(profile_path, f)
            if os.path.exists(full):
                tar.add(full, arcname=f)
    return buf.getvalue()


def unpack_files(data, dest_dir):
    """Unpack tar.gz archive into dest_dir."""
    buf = BytesIO(data)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        # Security: only extract expected relative paths
        for member in tar.getmembers():
            if member.name.startswith("/") or ".." in member.name:
                continue
            tar.extract(member, dest_dir)


def cmd_push(config, profile_path, files):
    """Pack and upload profile files to R2 (plaintext, TLS in transit only)."""
    archive = pack_files(profile_path, files)
    r2_request("PUT", "session.tar.gz", archive, config)

    meta = json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": os.uname().nodename,
        "files": files,
        "size": len(archive),
    }).encode()
    r2_request("PUT", "meta.json", meta, config)

    return len(archive)


def cmd_pull(config, dest_dir, files):
    """Download and unpack profile files from R2 into dest_dir."""
    archive = r2_request("GET", "session.tar.gz", None, config)
    if archive is None:
        return None
    unpack_files(archive, dest_dir)
    return len(archive)


def cmd_status(config):
    """Get metadata about the remote profile snapshot."""
    raw = r2_request("GET", "meta.json", None, config)
    if raw is None:
        return None
    return json.loads(raw)


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <push|pull|status|test> <config_json>")
        sys.exit(1)

    cmd = sys.argv[1]
    config = json.loads(sys.argv[2])

    files = config.get("files") or [
        "zen-sessions.jsonlz4",
        "zen-sessions-backup/clean.jsonlz4",
        "sessionstore-backups/recovery.jsonlz4",
        "sessionstore-backups/recovery.baklz4",
        "sessionstore-backups/previous.jsonlz4",
        "prefs.js",
        "xulstore.json",
        "containers.json",
        "places.sqlite",
        "favicons.sqlite",
        "permissions.sqlite",
        "cookies.sqlite",
        "logins.json",
        "key4.db",
    ]

    if cmd == "test":
        try:
            account_id = config["account_id"]
            bucket = config["bucket"]
            url = f"https://{account_id}.r2.cloudflarestorage.com/{bucket}?list-type=2&max-keys=1"
            headers = {"content-type": "application/xml"}
            signed = sign_aws_v4(
                "GET", url, headers, b"",
                "auto", "s3", config["access_key"], config["secret_key"]
            )
            req = Request(url, method="GET")
            for k, v in signed.items():
                req.add_header(k, v)
            urlopen(req, timeout=10)
            print("ok")
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
            sys.exit(1)
    elif cmd == "push":
        raw = cmd_push(config, config["profile"], files)
        print(json.dumps({"raw_size": raw}))
    elif cmd == "pull":
        size = cmd_pull(config, config["profile"], files)
        if size is None:
            print(json.dumps({"error": "no remote snapshot found"}))
        else:
            print(json.dumps({"size": size}))
    elif cmd == "status":
        meta = cmd_status(config)
        if meta is None:
            print(json.dumps({"error": "no remote snapshot found"}))
        else:
            print(json.dumps(meta))
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
