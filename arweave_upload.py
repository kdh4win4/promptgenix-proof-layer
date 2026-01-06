"""
PromptGenix Proof Layer
-----------------------
This script demonstrates how to create an immutable proof record
for AI-generated outputs and store it permanently on Arweave.

Key concepts:
- Hashing AI outputs instead of storing raw content
- Creating reproducible metadata
- Uploading proof records to Arweave for long-term verification
"""

import json                    # JSON serialization for metadata
import os                      # Environment variable access
from datetime import datetime  # Standardized timestamp generation

from arweave import Wallet, Transaction   # Arweave SDK
from dotenv import load_dotenv             # Load .env file safely
import hashlib                              # Cryptographic hashing


# ---------------------------------------------------------
# 1️⃣ Load environment variables
# ---------------------------------------------------------

# Load variables from .env (NOT committed to GitHub)
load_dotenv()

# Path to Arweave wallet JSON file
# ⚠️ This file contains your private key and MUST NOT be committed
ARWEAVE_WALLET_PATH = os.getenv("ARWEAVE_WALLET_PATH")

if not ARWEAVE_WALLET_PATH:
    raise RuntimeError(
        "ARWEAVE_WALLET_PATH is not set. "
        "Please define it in your .env file."
    )


# ---------------------------------------------------------
# 2️⃣ Utility: SHA-256 hashing
# ---------------------------------------------------------

def sha256_from_text(text: str) -> str:
    """
    Convert a string (AI output, prompt, etc.)
    into a SHA-256 hash.

    Why hashing?
    - Prevents leaking sensitive content
    - Enables later verification
    - Guarantees immutability
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

    The raw prompt/output are NOT stored.
    Only their cryptographic fingerprints are preserved.
    """
    return {
        # Project identifier (important for audits / SBIR)
        "project": "PromptGenix Proof Layer",

        # Type of proof being created
        "proof_type": "AI_OUTPUT_PROVENANCE",

        # AI model used to generate the output
        "ai_model": ai_model,

        # Hash of the prompt text
        "prompt_hash": sha256_from_text(prompt),

        # Hash of the AI-generated output
        "output_hash": sha256_from_text(output),

        # ISO 8601 UTC timestamp (global standard)
        "created_at": datetime.utcnow().isoformat() + "Z",

        # Authorship information
        "author": author,
        "organization": organization,
    }


# ---------------------------------------------------------
# 4️⃣ Upload proof to Arweave
# ---------------------------------------------------------

def upload_to_arweave(metadata: dict) -> str:
    """
    Upload proof metadata to Arweave
    and return the immutable transaction ID (TX ID).
    """

    # Load Arweave wallet using local keyfile
    wallet = Wallet(ARWEAVE_WALLET_PATH)

    # Convert metadata dictionary to formatted JSON string
    data_str = json.dumps(metadata, indent=2)

    # Create Arweave transaction with JSON payload
    tx = Transaction(wallet, data=data_str)

    # Add tags for discoverability and indexing
    tx.add_tag("App-Name", "PromptGenix-Proof-Layer")
    tx.add_tag("Content-Type", "application/json")
    tx.add_tag("Proof-Type", metadata["proof_type"])

    # Cryptographically sign the transaction
    tx.sign()

    # Send transaction to Arweave network
    tx.send()

    # Return permanent transaction ID
    return tx.id


# ---------------------------------------------------------
# 5️⃣ Example usage (for testing)
# ---------------------------------------------------------

if __name__ == "__main__":
    # Example prompt and AI output
    prompt_text = "Summarize the risks of AI hallucination in research."
    ai_output = (
        "AI hallucinations may fabricate citations, "
        "misrepresent data, and undermine scientific trust."
    )

    # Build proof record
    proof = build_proof_metadata(
        ai_model="gpt-4.1",
        prompt=prompt_text,
        output=ai_output,
        author="Dohoon Kim",
        organization="PromptGenix LLC",
    )

    # Upload to Arweave and print TX ID
    tx_id = upload_to_arweave(proof)

    print("✅ Arweave transaction ID:", tx_id)

