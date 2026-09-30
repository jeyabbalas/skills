Running open-weight LLMs on FRCE's GPUs and calling them from code or agents: the routes FRCE offers, the Ollama + Jupyter OnDemand app, a corrected Ollama endpoint job, the shared model store, sizing a model to a GPU, client recipes, and the security and etiquette of an endpoint without authentication. You write and check the scripts; every command here that submits or cancels a job, or starts or deletes an OnDemand session, is the user's to run (ground rules in SKILL.md). GPU choice for training and framework installs: DEEP-LEARNING.md. The `--gres` syntax: JOBS.md (GPUs). OnDemand in general: ONDEMAND.md. VS Code on a GPU node: INTERACTIVE.md (VS Code on a compute node).

Table of contents

- [Options on FRCE](#options-on-frce)
- [Ollama and Jupyter in OnDemand](#ollama-and-jupyter-in-ondemand)
- [An Ollama endpoint job](#an-ollama-endpoint-job)
- [Models and the shared store](#models-and-the-shared-store)
- [Sizing a model to a GPU](#sizing-a-model-to-a-gpu)
- [Calling the endpoint](#calling-the-endpoint)
- [Security, privacy, and etiquette](#security-privacy-and-etiquette)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Options on FRCE

FRCE documents three routes, all running Ollama with open-weight models ([Inference Capabilities](https://ncifrederick.cancer.gov/staff/FRCE/InferenceCapabilities)). This file adds a fourth pattern and vLLM. An ABCS talk by EIT staff sets the scope: "Slurm is not designed as a dedicated or production-scale inference platform", but these routes suit "model exploration, coding, testing, and small-scale experimentation" ([Local AI Inference on FRCE](https://bioinfo-abcc.ncifcrf.gov/training/event/local-ai-inference-on-frce), Aug 2026).

| Route | Use it for | The user starts it with | Reachable from |
|---|---|---|---|
| Ollama + Jupyter app in OnDemand | trying models from Python or R notebooks; the Jupyter AI chat | the OnDemand form | that session, per the page |
| Ollama endpoint job | an application elsewhere on FRCE that needs an API: Biomni, LangChain, LiteLLM, an agent, your scripts | `sbatch` | anywhere inside FRCE while the job runs |
| Server and client in one batch job | bulk extraction, classification, summarization | `sbatch` | its node only (loopback) |
| VS Code `frce-gpu` session | developing inference code with small models (its fixed size: INTERACTIVE.md (VS Code on a compute node)); running `ollama serve` yourself | VS Code Remote-SSH | that session |
| vLLM (AppDB development env) | high-throughput serving of Hugging Face weights | a GPU session or job | wherever it's bound |

- Commercial models (OpenAI, Anthropic, Azure OpenAI): the Documentation index promises "AI inference with commercial or open-weight models", but no FRCE page covers commercial APIs, their keys, or what data may go to them. That is the user's decision under NIH policy: never send FRCE data to an outside API on your own.
- vLLM: AppDB lists 0.26.0 (Sept 2026) as a development install (MODULES.md (Finding software)) to use "On a GPU node": `source /bioinfoA/apps/python/miniconda3/26.1.1/bin/activate vllm_0.26`, then `module load gcc/15.2.0`, with no `python` module loaded (PYTHON-R.md (Python on FRCE)). The login node sees envs `vllm_0.19` and `vllm_0.26` there (Sept 2026); whether GPU nodes mount `/bioinfoA` is unchecked, so `ls /bioinfoA/apps/python/miniconda3/26.1.1/envs` in your session first. No FRCE page mentions vLLM. Current vLLM needs compute capability 7.5 or newer ([vLLM GPU requirements](https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html)): A100, L40s, or H200. It loads Hugging Face weights (cache: DEEP-LEARNING.md (Data staging and I/O); gated models need the user's token). `vllm serve MODEL --host 127.0.0.1 --port PORT` serves an OpenAI-compatible `/v1` to its own job; for clients elsewhere, bind the node's name and set `--api-key`, which vLLM, unlike Ollama, enforces on `/v1`.

## Ollama and Jupyter in OnDemand

The "Ollama + Jupyter" interactive app runs JupyterLab and an Ollama server together in one GPU job ([page](https://ncifrederick.cancer.gov/staff/FRCE/OOD-Jupyter-Ollama)). The user fills in the form (Aug 2026 screenshot):

| Field | Notes |
|---|---|
| Project Root Directory | JupyterLab's starting directory |
| Ollama model to pre-pull (optional) | a name `ollama pull` accepts, e.g. `qwen3-coder:30b`; without it, an uncached model downloads at the first Jupyter AI chat, which "may hang while it pulls" |
| Number of cores | CPUs for the job |
| Allocated wall time (hours) | "Jupyter and Ollama stop when this allocation expires" |
| GPU card | L40s, V100, or A100 (no H200 or P100); size the model first ([Sizing a model to a GPU](#sizing-a-model-to-a-gpu)) |

The form has no partition or memory field, and the app's memory, `OLLAMA_HOST` format, and model store are undocumented and unchecked (Sept 2026). To see them, in the session's terminal: `scontrol show job "$SLURM_JOB_ID" | grep -i mem; echo "$OLLAMA_HOST $OLLAMA_MODELS"`.

- "Running" doesn't mean ready: allow up to five minutes ([Stale advice](#stale-advice-on-the-official-pages)), then use Connect to Jupyter; if it fails, retry after a minute.
- Inside, `$OLLAMA_HOST` points at the session's own server, so no `.info` file is needed. The launcher's kernels are Python 3, Python 3.12, R, and MATLAB. The page's Python example calls `ollama.Client(host=os.environ.get("OLLAMA_HOST", ...))` and `client.chat(..., format="json")` to turn free text into structured records; R code uses the HTTP API ([Calling the endpoint](#calling-the-endpoint)). An agent can work in the session's Terminal (ONDEMAND.md (Working inside a session)) and reach the model through `$OLLAMA_HOST`.
- Finished early: the user deletes the session (ONDEMAND.md (Sessions)), which "releases the allocated GPU".

## An Ollama endpoint job

FRCE's [endpoint page](https://ncifrederick.cancer.gov/staff/FRCE/OllamaEndpoint) serves one model as an HTTP API from a Slurm GPU job. Its script has five faults, so hand the user this copy instead: the page's script with each fix marked `FIX n` (explained below), `OLLAMA_NO_CLOUD` added, the module pinned, and its comments trimmed. Save it as `ollama-endpoint.sbatch` in the directory the user will submit from (cluster scratch or home), where the `.info` and `.log` files land.

```bash
#!/bin/bash
#SBATCH --job-name=ollama-endpoint
#SBATCH --partition=gpu
#SBATCH --gres=gpu:l40s:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=08:00:00
#SBATCH --output=ollama-endpoint-%j.log
# ollama-endpoint.sbatch — the user submits it. Overrides via sbatch --export=ALL,VAR=value: MODEL (must be
# in the store), PORT (default from the job ID), CONTEXT (tokens, default 65536), OLLAMA_MODELS (the store)
set -euo pipefail
STORE="${OLLAMA_MODELS:-/mnt/nasapps/production/ollama/models}"   # FIX 1: read before module load
source /etc/profile.d/modules.sh 2>/dev/null || true
module load ollama/0.32.0
export OLLAMA_MODELS="$STORE"
MODEL="${MODEL:-qwen3-coder:30b}"
PORT="${PORT:-$(( 20000 + ${SLURM_JOB_ID:-0} % 10000 ))}"         # FIX 2: not the shared 11434
CONTEXT="${CONTEXT:-65536}"
export OLLAMA_HOST="0.0.0.0:${PORT}"
export OLLAMA_CONTEXT_LENGTH="${CONTEXT}"
export OLLAMA_KEEP_ALIVE=-1     # keep the model resident for the whole job
export OLLAMA_FLASH_ATTENTION=1
export OLLAMA_NUM_PARALLEL=1    # one client, full context, no KV cache split
export OLLAMA_NO_CLOUD=1        # added: no cloud models, which send prompts to ollama.com (honored since 0.16.2)
NODE=$(hostname -f)
INFO="${SLURM_SUBMIT_DIR:-$PWD}/ollama-endpoint-${SLURM_JOB_ID}.info"
echo "node=${NODE} port=${PORT} gpus=${CUDA_VISIBLE_DEVICES:-none}"
echo "OLLAMA_MODELS=${OLLAMA_MODELS}"
(: <"/dev/tcp/127.0.0.1/${PORT}") 2>/dev/null \
  && { echo "ERROR: port ${PORT} is in use on ${NODE}; resubmit with --export=ALL,PORT=<another>" >&2; exit 1; }   # FIX 2
ollama serve &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT
for _ in $(seq 1 60); do
  kill -0 "$SERVER_PID" 2>/dev/null || { echo "ERROR: ollama serve exited (see above)" >&2; exit 1; }   # FIX 3
  curl -sf "http://127.0.0.1:${PORT}/api/tags" >/dev/null && break
  sleep 2
done
curl -sf "http://127.0.0.1:${PORT}/api/tags" >/dev/null \
  || { echo "ERROR: ollama serve did not answer within 2 minutes" >&2; exit 1; }                      # FIX 3
curl -sf "http://127.0.0.1:${PORT}/api/show" -d "{\"model\":\"${MODEL}\"}" >/dev/null \
  || { echo "ERROR: ${MODEL} is not in ${OLLAMA_MODELS}" >&2; exit 1; }                               # FIX 4
# Written before warm-up so it exists even if the model load is slow.
cat > "$INFO" <<EOF
JOB=${SLURM_JOB_ID}
NODE=${NODE}
PORT=${PORT}
MODEL=${MODEL}
CONTEXT=${CONTEXT}

# OpenAI-compatible API - most clients, LiteLLM, LangChain, openai SDK
OPENAI_BASE_URL=http://${NODE}:${PORT}/v1
OPENAI_API_KEY=not-needed

# Native Ollama API - the ollama python package, langchain_ollama
# (langchain_ollama ignores its base_url argument; set OLLAMA_HOST instead)
OLLAMA_HOST=http://${NODE}:${PORT}
EOF
echo "warming ${MODEL}, first load off NFS can take several minutes..."
curl -sf --max-time 900 "http://127.0.0.1:${PORT}/api/generate" \
  -d "{\"model\":\"${MODEL}\",\"prompt\":\"ready\",\"stream\":false}" >/dev/null \
  && echo "warm-up ok" \
  || echo "WARNING: warm-up did not complete; first request will be slow"                               # FIX 5: -f
echo "=============================================================="
cat "$INFO"
echo "=============================================================="
echo "connection details written to: ${INFO}"
wait $SERVER_PID
```

1. The module sets `OLLAMA_MODELS=$HOME/.ollama/models` and `OLLAMA_HOME=$HOME/.ollama` (live, Sept 2026: `module show ollama`), so the page's `${OLLAMA_MODELS:-…}` line after `module load` always keeps the module's value, ignoring both the shared store and `--export=ALL,OLLAMA_MODELS=…`. Reading the variable before the module loads fixes both; the user submits from a shell without the module loaded, whose value the job would inherit.
2. The page's default port, 11434, is the same in every job, and GPU nodes run several jobs: a second server can't bind, and the page's readiness loop then gets answers from someone else's server and writes a `.info` pointing at it. The port now comes from the job ID, and the job stops if it's taken.
3. The page writes the `.info` even if the server never answered; now the job stops, freeing the GPU.
4. A model missing from the store held the GPU for the whole walltime, serving nothing; now the job stops and logs the store path.
5. The warm-up's `curl -s` reported `warm-up ok` on HTTP errors; `-f` sends them to the WARNING branch.

```bash
# on the FRCE login node, in the directory holding the script — the user runs:
freen                                                   # free GPUs per type; pick one the model fits
sbatch ollama-endpoint.sbatch                           # prints: Submitted batch job JOBID
sbatch --export=ALL,MODEL=llama3.1:70b,CONTEXT=32768 --gres=gpu:h200:1 ollama-endpoint.sbatch   # another model and GPU: h200:1, a100:1, or l40s:2, whichever freen shows free
squeue --me                                             # R = running; then read ollama-endpoint-JOBID.log
scancel JOBID                                           # when finished; until then the endpoint holds its GPU
```

- The `.info` file (`ollama-endpoint-JOBID.info`) is "how to connect": the here-document's `KEY=VALUE` lines and comments (`NODE` is `fsitgl-hpcNNNp.ncifcrf.gov`), so `set -a; . FILE; set +a` exports every value. It is written before warm-up, so a large model may still be loading when it appears. The `.log` is "what the server is doing": `warm-up ok`, `WARNING` and `ERROR` lines, model loading. When the job ends, the endpoint is gone but both files stay; the next job gets a new node and port.

## Models and the shared store

FRCE keeps a curated store, read-only to users (hence the script never pulls), at `/mnt/nasapps/production/ollama/models`. As of Sept 2026 it holds the ten models in [Sizing a model to a GPU](#sizing-a-model-to-a-gpu) (live listing); contents change. Listing it needs no server:

```bash
# on the compute node (inside your session) — a read-only listing of the shared store
cd /mnt/nasapps/production/ollama/models/manifests/registry.ollama.ai/library && for m in */*; do echo "${m%/*}:${m##*/}"; done
```

- `ollama list` asks a running server, so the page's `ollama list` "from a login node" finds none ("could not connect to a running Ollama instance", live, Sept 2026). Never start `ollama serve` on a login host. Against a running endpoint, `curl -s "$OLLAMA_HOST/api/tags"` lists what that server sees.
- A model the store lacks goes into your own store on cluster scratch, not home (STORAGE.md (Home)). Pulling needs a running server and internet access, which compute nodes have directly (TRANSFER.md (Downloads on the cluster)), so run a private server in your session just for the pull:

```bash
# on the compute node (inside your session): a loopback server that lives only for the pull
module load ollama
export OLLAMA_MODELS=/scratch/cluster_scratch/$USER/ollama/models OLLAMA_HOST=127.0.0.1:$(( 20000 + RANDOM % 10000 ))
mkdir -p "$OLLAMA_MODELS"; ollama serve > /dev/null 2>&1 & pid=$!
for _ in $(seq 30); do ollama list > /dev/null 2>&1 && break; sleep 1; done
ollama pull gemma3:12b && ollama list; kill "$pid"      # gemma3:12b is a placeholder model name
```

Then the user serves it with `sbatch --export=ALL,OLLAMA_MODELS=/scratch/cluster_scratch/$USER/ollama/models,MODEL=gemma3:12b ollama-endpoint.sbatch`. Use the shared copy whenever it has the model. Each model's license (Llama, Gemma, …) binds the user.

## Sizing a model to a GPU

`ollama list` shows the stored weights, about parameters × 0.6 bytes at Ollama's default 4-bit tags (× 2 bytes at fp16), "not ... the complete amount of GPU memory required at runtime" (page). Add the KV cache, which grows with context: VRAM ≈ stored size + 2 × layers × KV heads × head size × 2 bytes × `CONTEXT` × `OLLAMA_NUM_PARALLEL` + 1–2 GB. Estimates for the store's models (also the page's example list) at the script's defaults (context 65536 or the model's own maximum, whichever is smaller; f16 cache; one slot). Card memory: HARDWARE.md (GPUs).

| Model (stored size) | Context | Estimated VRAM | Fits on one |
|---|---|---|---|
| `llama3.2:1b` (1.3 GB), `llama3.2:3b` (2.0 GB), `phi4-mini:latest` (2.5 GB) | 65536 | ~4, ~10, ~12 GB | any GPU |
| `gemma3:4b` (3.3 GB), `mistral:7b` (4.4 GB) | 65536, 32768 | ~6, ~10 GB | any GPU |
| `qwen3:8b` (5.2 GB) | 40960 | ~12 GB | any GPU (P100 tight) |
| `llama3.1:8b` (4.9 GB) | 65536 | ~14 GB | any GPU (P100 tight) |
| `phi4-reasoning:14b` (11 GB) | 32768 | ~19 GB | V100 and up |
| `qwen3-coder:30b` (18 GB) | 65536 | ~25 GB | V100, L40s, A100, H200 |
| `llama3.1:70b` (42 GB) | 65536 / 32768 / 8192 | ~64 / ~54 / ~46 GB | A100 or H200; one L40s only near 8K context, else `gpu:l40s:2` |

- Too big for one card, Ollama spreads the model over all the job's GPUs; too big for all of them, it runs layers on the CPU, slowly (raise `--mem` then), and `curl -s "$OLLAMA_HOST/api/ps"` shows `size_vram` below `size`.
- Levers ([FAQ](https://docs.ollama.com/faq)): a smaller `CONTEXT`; `OLLAMA_KV_CACHE_TYPE=q8_0`, about half the cache (it needs flash attention, which the script enables); a smaller quantization tag; and `OLLAMA_NUM_PARALLEL`, which multiplies the cache.
- OpenAI-compatible clients can't set the context ("The OpenAI API does not have a way of setting the context size"), so the server's `CONTEXT` rules; native clients can pass `options.num_ctx`. Agents and coding tools want at least 64000 tokens ([context length](https://docs.ollama.com/context-length)).

## Calling the endpoint

Clients run inside FRCE, in an allocation: your session, a batch job, OnDemand, or VS Code. The page: "The Ollama endpoint therefore cannot be called directly from a desktop, laptop, or other external system". Not from the login node either.

```bash
# on the compute node (inside your session); JOBID from the user's sbatch output
cd /scratch/cluster_scratch/$USER/llm                    # placeholder: the directory the user submitted from
grep -E 'warm-up ok|WARNING|ERROR' ollama-endpoint-JOBID.log
set -a; . ./ollama-endpoint-JOBID.info; set +a           # exports OPENAI_BASE_URL, OPENAI_API_KEY, OLLAMA_HOST, MODEL, ...
curl -s "$OPENAI_BASE_URL/chat/completions" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}"
curl -s "$OLLAMA_HOST/api/ps"                            # the loaded model and its GPU share
```

| Base URL | Routes (Ollama docs, Sept 2026) |
|---|---|
| `$OPENAI_BASE_URL` (ends `/v1`) | `POST /chat/completions`, `/completions`, `/embeddings`, `/responses` (stateless; Ollama ≥ 0.13.3); `GET /models`, `/models/{model}` |
| `$OLLAMA_HOST`, native | `POST /api/chat`, `/api/generate`, `/api/embed`, `/api/show`; `GET /api/tags`, `/api/ps`, `/api/version`; `/api/pull`, `/api/create`, `/api/copy`, and `DELETE /api/delete` change the store |
| `$OLLAMA_HOST`, Anthropic-compatible | `POST /v1/messages`: Anthropic SDKs and Claude Code take `$OLLAMA_HOST` as base URL with any key (Ollama ≥ 0.14; the module is 0.32.0) |

- Clients, after the `set -a` step: the openai SDK's `OpenAI()` reads `OPENAI_BASE_URL` and `OPENAI_API_KEY` by itself (pass `model=os.environ["MODEL"]`); the `ollama` package takes `ollama.Client(host=os.environ["OLLAMA_HOST"])`; LiteLLM with `model=f"openai/{MODEL}"` and `api_base=OPENAI_BASE_URL`; LangChain's `ChatOpenAI(model=..., base_url=..., api_key="not-needed")`, or `ChatOllama` with `OLLAMA_HOST` exported (it ignores `base_url`). R: any HTTP client, e.g. httr2 posting JSON to `$OLLAMA_HOST/api/chat` (prefix `http://` if the variable lacks a scheme). Biomni has a module (`biomni/0.0.8`, live Sept 2026); per the page, "use the model name reported by `MODEL`, and point its custom OpenAI-compatible base URL at `OPENAI_BASE_URL`".
- Agents and pipelines: tool calling depends on the model (the page's store labels `qwen3-coder:30b` for "Coding and tool-oriented workloads"). With `OLLAMA_NUM_PARALLEL=1`, concurrent requests queue (up to 512, then HTTP 503), so raise it only together with a smaller `CONTEXT`. Use the exact name in `MODEL`, re-read the `.info` on each run, and handle refused connections, because the endpoint dies with its job.

### Server and client in one batch job

For bulk work, start the server on loopback inside the job that runs the client. Only processes on that node (other jobs there included) can reach it, and the GPU is released as soon as the client finishes.

```bash
#!/bin/bash
#SBATCH --partition=gpu
#SBATCH --gres=gpu:l40s:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=llm-batch-%j.log
# llm-batch.sh — the user submits it; classify.py and its flags are placeholders for the client
set -euo pipefail
source /etc/profile.d/modules.sh 2>/dev/null || true
module load ollama/0.32.0
export OLLAMA_MODELS=/mnt/nasapps/production/ollama/models OLLAMA_NO_CLOUD=1 OLLAMA_CONTEXT_LENGTH=16384 \
       OLLAMA_HOST="127.0.0.1:$(( 20000 + SLURM_JOB_ID % 10000 ))"
ollama serve > "ollama-serve-$SLURM_JOB_ID.log" 2>&1 &
SERVER_PID=$!; trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT
for _ in $(seq 60); do curl -sf "http://$OLLAMA_HOST/api/tags" > /dev/null && break; sleep 2; done
module load python/3.12; unset PYTHONPATH                        # the venv's interpreter (PYTHON-R.md)
source /scratch/cluster_scratch/$USER/envs/llm/bin/activate      # the ollama package reads OLLAMA_HOST; openai needs base_url http://$OLLAMA_HOST/v1
python classify.py --model qwen3:8b --in records.jsonl --out labels.jsonl
```

## Security, privacy, and etiquette

- No authentication: "`OPENAI_API_KEY=not-needed` is provided only for client libraries that require an API-key value. It is not an authentication mechanism" (page). The endpoint listens on the node's network interface, so any process inside FRCE that finds it can send prompts and occupy the GPU, and, if the server can write its store (your own), pull or delete models. Other users can't read your prompts or answers through the API. When the only client is in the same job, bind to loopback, as in the one-job pattern. The endpoint is unreachable from outside FRCE, and no page documents or sanctions tunneling it to the user's computer; the user asks the admins if they want that.
- The inference itself stays on FRCE, but "the application calling the model may have other network connections or services of its own" (page): check the client for telemetry, web-search tools, and hosted fallbacks. Ollama's cloud models (`cloud` tags such as `gemma4:cloud`, usable after `ollama signin`) run on ollama.com, which compute nodes can reach; `OLLAMA_NO_CLOUD=1`, set in both scripts, turns them off ([FAQ](https://docs.ollama.com/faq)).
- To have an LLM work on sensitive text without reading it yourself (ground rule 4 in SKILL.md), write a script that sends it to an FRCE endpoint and look only at aggregate results, if the data's terms allow processing on FRCE at all; the user decides. NIH's AI-tool guidance is on the NIH AI Hub (NIH-only; linked from Biowulf's [Ollama page](https://hpc.nih.gov/apps/ollama.html)).
- An endpoint holds its GPU for its whole `--time`, idle or not, and `OLLAMA_KEEP_ALIVE=-1` keeps the model loaded. Set `--time` to the need, and have the user cancel the job or delete the OnDemand session when done: FRCE's idle-session rule weighs most on GPUs (INTERACTIVE.md (Interactive shells with srun)).

## Stale advice on the official pages

- [OllamaEndpoint](https://ncifrederick.cancer.gov/staff/FRCE/OllamaEndpoint)'s script has five faults, from port collisions to an `OLLAMA_MODELS` the module overrides → the corrected script in [An Ollama endpoint job](#an-ollama-endpoint-job).
- The same page offers `l4` as a GPU type → none is in service (HARDWARE.md (GPUs)); use `l40s`, `a100`, `h200`, or `v100`.
- The same page: "use `ollama list` from a login node", and "Using your own Ollama models" pulls into `$HOME/.ollama/models`, both with no server running → list the store's files, and pull in your session into cluster scratch ([Models and the shared store](#models-and-the-shared-store)).
- The same page's override `MODEL=llama3.1:70b,CONTEXT=32768` keeps the default `gpu:l40s:1`, too small for its ~54 GB, so part of the model runs on the CPU → add `--gres=gpu:a100:1`, `gpu:h200:1`, or `gpu:l40s:2`.
- [OOD-Jupyter-Ollama](https://ncifrederick.cancer.gov/staff/FRCE/OOD-Jupyter-Ollama): "two to three minutes" to start, while the session card says "up to five minutes" → allow five.
- AppDB's [Ollama](https://appdb.ncifcrf.gov/software/Ollama) entry lists only development 0.11.4, run from `PATH` with `ollama serve&` → the module, as the FRCE pages use: `ollama/0.32.0` (live, Sept 2026).
- The Documentation index's "commercial or open-weight models" → only open-weight models are documented ([Options on FRCE](#options-on-frce)).

## Going further

- FRCE: [Inference Capabilities](https://ncifrederick.cancer.gov/staff/FRCE/InferenceCapabilities) · [Ollama + Jupyter](https://ncifrederick.cancer.gov/staff/FRCE/OOD-Jupyter-Ollama) · [Ollama endpoint](https://ncifrederick.cancer.gov/staff/FRCE/OllamaEndpoint) · [VS Code on a compute node](https://ncifrederick.cancer.gov/staff/FRCE/VSCodeSlurm) · AppDB [vLLM](https://appdb.ncifcrf.gov/software/vLLM) (NIH network) · the ABCS talk [Local AI Inference on FRCE](https://bioinfo-abcc.ncifcrf.gov/training/event/local-ai-inference-on-frce) (slides and recording need NIH Login).
- Ollama: [API](https://docs.ollama.com/api) · [OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility) · [Anthropic compatibility](https://docs.ollama.com/api/anthropic-compatibility) · [FAQ](https://docs.ollama.com/faq) (server variables) · [context length](https://docs.ollama.com/context-length). vLLM: [GPU install](https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html) · [OpenAI-compatible server](https://docs.vllm.ai/en/latest/serving/online_serving/#openai-compatible-server) · [`vllm serve` options](https://docs.vllm.ai/en/latest/cli/serve/).
- Biowulf's [Ollama page](https://hpc.nih.gov/apps/ollama.html) (its VRAM advice carries over; its `ollama_start`, lscratch, and `/data` don't: FROM-BIOWULF.md).
- Live: `module avail ollama`, `module show ollama`, `freen`, `squeue --me`, `curl -s "$OLLAMA_HOST/api/ps"`.
