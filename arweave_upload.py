"""
arweave_upload.py
-----------------
Upload AI output provenance metadata to Arweave.

This script:
1) Builds a small JSON proof object (project, hashes, metadata)
2) Signs it with your Arweave wallet
3) Sends it to the Arweave *mainnet* via https://arweave.net
4) Prints the transaction ID (TX ID)
"""

import json
import os
from datetime import datetime, timezone

from arweave import Wallet, Transaction  # arweave-python-client


# ---------------------------------------------------------
# 1️⃣ Load Arweave wallet (mainnet)
# ---------------------------------------------------------

# 환경변수에서 지갑 경로 읽기 (없으면 에러)
ARWEAVE_WALLET_PATH = os.getenv("ARWEAVE_WALLET_PATH")
if not ARWEAVE_WALLET_PATH:
    raise RuntimeError(
        "ARWEAVE_WALLET_PATH is not set. Please define it in your .env file."
    )

if not os.path.exists(ARWEAVE_WALLET_PATH):
    raise FileNotFoundError(
        f"Arweave keyfile not found at: {ARWEAVE_WALLET_PATH}"
    )

# 지갑 로드
wallet = Wallet(ARWEAVE_WALLET_PATH)

# ✅ 여기가 중요: 무조건 메인넷 게이트웨이 사용
wallet.api_url = "https://arweave.net"


# ---------------------------------------------------------
# 2️⃣ Utility: SHA-256 hashing
# ---------------------------------------------------------

import hashlib


def sha256_from_text(text: str) -> str:
    """
    Convert a string (AI output, prompt, etc.)
    into a SHA-256 hash.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------
# 3️⃣ Build proof metadata
# ---------------------------------------------------------

def build_proof_metadata(
    ai_model: str,
    prompt: str,
    output: str,
    author: str,
    organization: str,
) -> dict:
    """
    Construct a minimal but verifiable proof record.
    Raw prompt/output are NOT stored. Only hashes.
    """
    return {
        "project": "PromptGenix Proof Layer",
        "proof_type": "AI_OUTPUT_PROVENANCE",
        "ai_model": ai_model,
        "prompt_hash": sha256_from_text(prompt),
        "output_hash": sha256_from_text(output),
        # timezone-aware UTC timestamp
        "created_at": datetime.now(timezone.utc).isoformat(),
        "author": author,
        "organization": organization,
    }


# ---------------------------------------------------------
# 4️⃣ Upload proof to Arweave mainnet
# ---------------------------------------------------------

def upload_to_arweave(metadata: dict) -> str:
    """
    Upload proof metadata to Arweave mainnet
    and return the immutable transaction ID (TX ID).
    """

    # JSON 직렬화 후 bytes 로 인코딩
    data_bytes = json.dumps(metadata, ensure_ascii=False).encode("utf-8")

    # 트랜잭션 생성 (data = our JSON)
    tx = Transaction(wallet, data=data_bytes)

    # 메타데이터 태그
    tx.add_tag("Content-Type", "application/json")
    tx.add_tag("Project", "PromptGenix Proof Layer")
    tx.add_tag("Proof-Type", metadata["proof_type"])
    tx.add_tag("AI-Model", metadata["ai_model"])

    # 서명 및 전송
    tx.sign()
    tx.send()

    # 여기서 바로 검증 시도는 하지 않고,
    # TX ID만 출력하게 두는 것이 더 안전함.
    return tx.id


# ---------------------------------------------------------
# 5️⃣ Example usage (for testing)
# ---------------------------------------------------------

if __name__ == "__main__":
    # 예시 prompt / output
    prompt_text = "Summarize the risks of AI hallucination in research."
    ai_output = (
        "AI hallucinations may fabricate citations, "
        "misrepresent data, and undermine scientific trust."
    )

    # proof JSON 생성
    proof = build_proof_metadata(
        ai_model="gpt-4.1",
        prompt=prompt_text,
        output=ai_output,
        author="Dohoon Kim",
        organization="PromptGenix LLC",
    )

    # 업로드 & TX ID 출력
    tx_id = upload_to_arweave(proof)
    print("✅ Arweave transaction ID:", tx_id)
    print("➡ You can later check:",
          f"https://arweave.net/tx/{tx_id}/data")
