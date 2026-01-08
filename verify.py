"""
verify.py
---------
Verify an AI proof stored on Arweave by TX ID.

What it does:
1) Download metadata JSON from Arweave (or AR.IO) using TX ID
2) Decode raw or Base64-encoded payload into JSON
3) Recompute hashes from your local prompt/output
4) Compare with stored hashes to confirm integrity
"""

import json
import sys
import urllib.request
import urllib.error
import hashlib
import base64
from typing import List, Dict, Any


# ---------------------------------------------------------
# 1️⃣ Utility: SHA-256 hashing (must match upload script)
# ---------------------------------------------------------

def sha256_from_text(text: str) -> str:
    """Convert a string into a SHA-256 hex digest (same logic as upload)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------
# 2️⃣ Fetch & decode proof JSON from Arweave / AR.IO gateways
# ---------------------------------------------------------

# 기본 게이트웨이 후보들
DEFAULT_GATEWAYS: List[str] = [
    "https://arweave.net",
    "https://ar-io.net",
]


def _try_fetch(url: str, timeout: int = 20) -> str:
    """Low-level helper: try a single URL and return response body as text."""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data_bytes = resp.read()
    # 바이트를 그대로 텍스트로 디코딩 (Base64일 수도 있음)
    return data_bytes.decode("utf-8")


def _decode_json(body: str) -> Dict[str, Any]:
    """
    1차: body 자체를 JSON 으로 파싱 시도
    2차: 실패하면 Base64 로 보고 디코드 후 JSON 파싱
    """
    # 1) 그냥 JSON 이라면 바로 파싱
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        pass

    # 2) Base64 로 인코딩된 JSON 일 수 있음
    try:
        decoded_bytes = base64.b64decode(body)
        decoded_str = decoded_bytes.decode("utf-8")
        return json.loads(decoded_str)
    except (base64.binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as e:
        # 최종 실패
        raise json.JSONDecodeError(
            f"Failed to decode response as JSON or Base64 JSON: {e}",
            body,
            0,
        )


def fetch_proof_json(
    tx_id: str,
    gateways: List[str] | None = None,
) -> Dict[str, Any]:
    """
    Try multiple gateways and URL patterns to download the stored proof JSON.

    URL 패턴:
      - https://arweave.net/<TX_ID>?raw=1         (raw data)
      - https://arweave.net/<TX_ID>              (보통 raw 데이터)
      - https://arweave.net/tx/<TX_ID>/data      (종종 Base64 인코딩된 데이터)
      - https://arweave.net/<TX_ID>/data         (예비 패턴)

    Returns:
      dict parsed from JSON payload

    Raises:
      RuntimeError if all gateway attempts fail.
    """
    if gateways is None:
        gateways = DEFAULT_GATEWAYS

    url_patterns = [
        "{base}/{tx}?raw=1",
        "{base}/{tx}",
        "{base}/tx/{tx}/data",
        "{base}/{tx}/data",
    ]

    tried_urls: List[str] = []
    last_error: Exception | None = None

    for base in gateways:
        base_clean = base.rstrip("/")
        for pattern in url_patterns:
            url = pattern.format(base=base_clean, tx=tx_id).replace("//tx", "/tx")

            if url in tried_urls:
                continue
            tried_urls.append(url)

            try:
                body = _try_fetch(url)
                # body 가 JSON 이거나, Base64-encoded JSON 인지 디코딩
                return _decode_json(body)
            except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
                last_error = e
                continue

    msg = f"Failed to fetch proof JSON for TX ID {tx_id}. Tried URLs:\n  "
    msg += "\n  ".join(tried_urls)
    if last_error is not None:
        msg += f"\nLast error: {repr(last_error)}"
    raise RuntimeError(msg)


# ---------------------------------------------------------
# 3️⃣ Verify hashes against local prompt/output
# ---------------------------------------------------------

def verify_proof(tx_id: str, prompt: str, output: str) -> Dict[str, Any]:
    """
    Verify:
    - prompt_hash matches hash(prompt)
    - output_hash matches hash(output)

    Returns a structured verification result dictionary.
    """
    # Fetch stored proof record from Arweave / AR.IO
    proof = fetch_proof_json(tx_id)

    # Extract stored hashes from proof JSON
    stored_prompt_hash = proof.get("prompt_hash")
    stored_output_hash = proof.get("output_hash")

    # Recompute hashes locally from the provided raw texts
    local_prompt_hash = sha256_from_text(prompt)
    local_output_hash = sha256_from_text(output)

    # Compare stored vs locally computed hashes
    prompt_ok = (stored_prompt_hash == local_prompt_hash)
    output_ok = (stored_output_hash == local_output_hash)

    verified = prompt_ok and output_ok

    return {
        "tx_id": tx_id,
        "verified": verified,
        "prompt_ok": prompt_ok,
        "output_ok": output_ok,
        "stored_prompt_hash": stored_prompt_hash,
        "local_prompt_hash": local_prompt_hash,
        "stored_output_hash": stored_output_hash,
        "local_output_hash": local_output_hash,
        "proof_metadata": {
            "project": proof.get("project"),
            "proof_type": proof.get("proof_type"),
            "ai_model": proof.get("ai_model"),
            "created_at": proof.get("created_at"),
            "author": proof.get("author"),
            "organization": proof.get("organization"),
        },
    }


# ---------------------------------------------------------
# 4️⃣ CLI entry point (easy testing)
# ---------------------------------------------------------

if __name__ == "__main__":
    """
    Usage:
      python verify.py <TX_ID> "<PROMPT_TEXT>" "<OUTPUT_TEXT>"

    Example:
      python verify.py abc123 "my prompt" "my output"
    """

    if len(sys.argv) < 4:
        print("Usage: python verify.py <TX_ID> \"<PROMPT_TEXT>\" \"<OUTPUT_TEXT>\"")
        sys.exit(1)

    tx_id_arg = sys.argv[1]
    prompt_arg = sys.argv[2]
    output_arg = sys.argv[3]

    result = verify_proof(tx_id_arg, prompt_arg, output_arg)

    print("TX ID:", result["tx_id"])
    print("Verified:", result["verified"])
    print("Prompt hash match:", result["prompt_ok"])
    print("Output hash match:", result["output_ok"])

    print("\n--- Full report (JSON) ---")
    print(json.dumps(result, indent=2))
