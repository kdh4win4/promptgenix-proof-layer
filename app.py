"""
Streamlit Web UI for PromptGenix Proof Layer

This app allows non-technical users to:
- Enter an Arweave TX ID
- Paste the original prompt and AI output
- Verify whether the content matches the immutable proof on Arweave
"""

import streamlit as st
import json
import urllib.request
import hashlib


# ---------------------------------------------------------
# Utility: SHA-256 hashing (must match upload/verify logic)
# ---------------------------------------------------------

def sha256_from_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------
# Fetch proof metadata from Arweave
# ---------------------------------------------------------

def fetch_proof(tx_id: str) -> dict:
    url = f"https://arweave.net/{tx_id}"
    with urllib.request.urlopen(url) as response:
        data = response.read().decode("utf-8")
    return json.loads(data)


# ---------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------

st.set_page_config(
    page_title="PromptGenix Proof Verifier",
    page_icon="🔐",
    layout="centered"
)

st.title("🔐 PromptGenix Proof Verifier")
st.markdown(
    "Verify AI-generated outputs using immutable proof records stored on Arweave."
)

st.divider()

# User inputs
tx_id = st.text_input("Arweave Transaction ID (TX ID)")
prompt_text = st.text_area("Original Prompt", height=150)
output_text = st.text_area("AI Output", height=150)

verify_button = st.button("Verify Proof")

if verify_button:
    if not tx_id or not prompt_text or not output_text:
        st.error("Please fill in all fields before verification.")
    else:
        try:
            proof = fetch_proof(tx_id)

            stored_prompt_hash = proof.get("prompt_hash")
            stored_output_hash = proof.get("output_hash")

            local_prompt_hash = sha256_from_text(prompt_text)
            local_output_hash = sha256_from_text(output_text)

            prompt_ok = stored_prompt_hash == local_prompt_hash
            output_ok = stored_output_hash == local_output_hash

            verified = prompt_ok and output_ok

            if verified:
                st.success("✅ Verification successful. The content is authentic.")
            else:
                st.error("❌ Verification failed. The content does NOT match the proof.")

            st.subheader("Verification Details")
            st.json({
                "prompt_hash_match": prompt_ok,
                "output_hash_match": output_ok,
                "ai_model": proof.get("ai_model"),
                "created_at": proof.get("created_at"),
                "author": proof.get("author"),
                "organization": proof.get("organization"),
            })

        except Exception as e:
            st.error(f"Error during verification: {e}")
