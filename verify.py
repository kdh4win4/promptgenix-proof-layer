"""
verify.py
---------
Verify an AI proof stored on Arweave by TX ID.

What it does:
1) Download metadata JSON from Arweave using TX ID
2) Recompute hashes from your local prompt/output
3) Compare with stored hashes to confirm integrity
"""

import json                      # JSON parsing for downloaded metadata
import sys                       # Read CLI arguments (TX ID, etc.)
import urllib.request            # Simple HTTP GET (no extra dependency)
import hashlib                   # SHA-256 hashing


# ---------------------------------------------------------
# 1️⃣ Utility: SHA-256 hashing (must match upload script)
# ---------------------------------------------------------

def sha256_from_text(text: str) -> str:
    """Convert a string into a SHA-256 hex digest (same as upload)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------
# 2️⃣ Fetch proof JSON from Arweave gateway
# ---------------------------------------------------------

def fetch_proof_json(tx_id: str, gateway_base: str = "https://arweave.net") -> dict:
    """
    Download the proof JSON stored at:
      https://arweave.net/<TX_ID>

    Returns:
      dict parsed from JSON payload
    """
    # Build full URL for the transaction payload
    url = f"{gateway_base.rstrip('/')}/{tx_id}"  # rstrip to avoid double slashes

    # Make a GET request to download the stored data
    with urllib.request.urlopen(url) as resp:
        # Read bytes -> decode to string
        data_str = resp.read().decode("utf-8")

    # Parse JSON string into Python dict
    return json.loads(data_str)


# ---------------------------------------------------------
# 3️⃣ Verify hashes against local prompt/output
# ---------------------------------------------------------

def verify_proof(tx_id: str, prompt: str, output: str) -> dict:
    """
    Verify:
    - prompt_hash matches hash(prompt)
    - output_hash matches hash(output)

    Returns a structured verification result dictionary.
    """
    # Fetch stored proof record from Arweave
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
    # (This is helpful for debugging or building a UI later)
    print("\n--- Full report (JSON) ---")
    print(json.dumps(result, indent=2))
