"""
verify.py
---------
Verify an AI proof stored on Arweave by TX ID.

What it does:
1) Download metadata JSON from Arweave (or AR.IO) using TX ID
2) Recompute hashes from your local prompt/output
3) Compare with stored hashes to confirm integrity
"""

import json                      # JSON parsing for downloaded metadata
import sys                       # Read CLI arguments (TX ID, etc.)
import urllib.request            # Simple HTTP GET (no extra dependency)
import urllib.error             # Handle HTTPError / URLError
import hashlib                   # SHA-256 hashing
from typing import List, Dict, Any


# ---------------------------------------------------------
# 1️⃣ Utility: SHA-256 hashing (must match upload script)
# ---------------------------------------------------------

def sha256_from_text(text: str) -> str:
    """Convert a string into a SHA-256 hex digest (same logic as upload)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------
# 2️⃣ Fetch proof JSON from Arweave / AR.IO gateways
# ---------------------------------------------------------

# We try several gateway + URL patterns so that both
# mainnet/testnet and different endpoint shapes are supported.
DEFAULT_GATEWAYS: List[str] = [
    "https://arweave.net",
    "https://arweave.net/tx",
    "https://ar-io.net",
]


def _try_fetch(url: str, timeout: int = 20) -> str:
    """Low-level helper: try a single URL and return the response body as text."""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data_bytes = resp.read()
    return data_bytes.decode("utf-8")


def fetch_proof_json(
    tx_id: str,
    gateways: List[str] | None = None,
) -> Dict[str, Any]:
    """
    Try multiple gateways and URL patterns to download the stored proof JSON.

    This function is intentionally defensive because in practice:
    - Some gateways serve raw data at  /<TX_ID>
    - Others serve raw data at      /tx/<TX_ID>/data
    - Some (testnets / AR.IO) may have slightly different routing

    Returns:
      dict parsed from JSON payload

    Raises:
      RuntimeError if all gateway attempts fail.
    """
    if gateways is None:
        gateways = DEFAULT_GATEWAYS

    # Candidate URL patterns (we will deduplicate later)
    url_patterns = [
        "{base}/{tx}",            # e.g. https://arweave.net/<TX_ID>
        "{base}/tx/{tx}/data",    # e.g. https://arweave.net/tx/<TX_ID>/data
        "{base}/{tx}/data",       # e.g. https://ar-io.net/<TX_ID>/data
    ]

    tried_urls: List[str] = []
    last_error: Exception | None = None

    for base in gateways:
        base_clean = base.rstrip("/")
        for pattern in url_patterns:
            url = pattern.format(base=base_clean, tx=tx_id).replace("//tx", "/tx")

            # Avoid hitting the exact same URL twice
            if url in tried_urls:
                continue
            tried_urls.append(url)

            try:
                body = _try_fetch(url)
                # If we reach here, HTTP status was 200 and we have a body.
                # Now try to parse as JSON.
                return json.loads(body)
            except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
                last_error = e
                # Just continue to the next candidate
                continue

    # If we are here, every attempt failed
    msg = "Failed to fetch proof JSON for TX ID {tx_id}. Tried URLs:\n  ".format(tx_id=tx_id)
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
    stored_prompt_hash = proof.get("prompt_hash")  # stored prompt fingerprint
    stored_output_hash = proof.get("output_hash")  # stored output fingerprint

    # Recompute hashes locally from the provided raw texts
    local_prompt_hash = sha256_from_text(prompt)
    local_output_hash = sha256_from_text(output)

    # Compare stored vs locally computed hashes
    prompt_ok = (stored_prompt_hash == local_prompt_hash)
    output_ok = (stored_output_hash == local_output_hash)

    # Overall verification passes only if both match
    verified = prompt_ok and output_ok

    # Return a complete report (useful for logs / UI)
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

    # Basic argument validation
    if len(sys.argv) < 4:
        print("Usage: python verify.py <TX_ID> \"<PROMPT_TEXT>\" \"<OUTPUT_TEXT>\"")
        sys.exit(1)

    # Read arguments from command line
    tx_id_arg = sys.argv[1]
    prompt_arg = sys.argv[2]
    output_arg = sys.argv[3]

    # Run verification
    result = verify_proof(tx_id_arg, prompt_arg, output_arg)

    # Print human-friendly summary
    print("TX ID:", result["tx_id"])
    print("Verified:", result["verified"])
    print("Prompt hash match:", result["prompt_ok"])
    print("Output hash match:", result["output_ok"])

    # If you want full details, print JSON
    print("\n--- Full report (JSON) ---")
    print(json.dumps(result, indent=2))
