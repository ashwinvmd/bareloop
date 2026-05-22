#!/usr/bin/env bash
# Serve nvidia/Llama-3.3-70B-Instruct-FP8 on a single RTX PRO 6000 Blackwell Max-Q (TP=1, GPU 0)
# Uses vLLM's llama3_json tool-call parser to fix the Ollama-side tool-call format mismatch
# observed with llama3.3:70b-instruct-q8_0 + OpenCode (Llama emits {"parameters": ...},
# OpenCode expects {"arguments": ...}).
# vLLM listens on port 8000.

set -euo pipefail

MODEL="${MODEL:-/data/local_llm/models/Llama-3.3-70B-Instruct-FP8}"
PORT="${PORT:-8000}"
MAX_CTX="${MAX_CTX:-65536}"     # 64K to leave KV headroom on single 96 GB card for 70B
GPU="${GPU:-0}"

VENV="/data/local_llm/.venv"

export HF_HOME="/data/local_llm/models"
export TOKENIZERS_PARALLELISM=false
export CUDA_VISIBLE_DEVICES="${GPU}"

source "${VENV}/bin/activate"

exec vllm serve "${MODEL}" \
  --served-model-name meta-llama/Llama-3.3-70B-Instruct \
  --tensor-parallel-size 1 \
  --max-model-len "${MAX_CTX}" \
  --max-num-seqs 128 \
  --trust-remote-code \
  --gpu-memory-utilization 0.9 \
  --enable-chunked-prefill \
  --enable-auto-tool-choice \
  --tool-call-parser llama3_json \
  --port "${PORT}" \
  --host 0.0.0.0
