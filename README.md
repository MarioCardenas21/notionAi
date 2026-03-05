<<<<<<< HEAD
# notionAi
=======
# AI Tech Research System v1 (MCP-ready)

Sistema local para investigación técnica automatizada:
- Crawler/Extractor (HTML → texto)
- Motor LLM (prompt "anti-alucinación" + output estructurado)
- Evidencia trazable (Claim → Evidence → Source)
- Storage (JSONL + SQLite)
- Export: Notion payload (JSON) + opcional Neo4j (Cypher)
- MCP Server (JSON-RPC stdio) para exponer `research.url`

> **Requisitos**: Python 3.10+ (recomendado 3.11/3.12)

---

## 1) Setup rápido

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate  # Windows

pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` con tus claves (OpenAI y/o Notion).

---

## 2) Ejecutar (CLI)

### Analizar 1 URL
```bash
python -m research.cli url https://modelcontextprotocol.io/docs/learn/architecture --out out/
```

### Analizar varias URLs (archivo)
```bash
python -m research.cli batch urls.txt --out out/
```

Genera:
- `out/results.jsonl` (una entrada por URL)
- `out/results.sqlite` (tabla `research_runs`)
- `out/notion_payloads/` (JSON sugerido)
- `out/neo4j/` (opcional: cypher)

---

## 3) Exportar a Notion (opcional)

1) Crea una integración en Notion y copia el token.
2) Crea una base de datos en Notion y comparte la DB con tu integración.
3) Obtén el `DATABASE_ID` y configúralo en `.env`.

Luego:

```bash
python -m research.cli notion-sync out/results.jsonl
```

---

## 4) Ejecutar como MCP Server (JSON-RPC por stdio)

Esto permite que un *MCP client* invoque el tool `research.url`.

```bash
python -m research.mcp_server
```

El server expone:
- `tools/list`
- `tools/call` con name=`research.url`

---

## 5) Estructura

- `research/`
  - `cli.py` (CLI)
  - `config.py` (config/env)
  - `fetch.py` (descarga + limpieza HTML)
  - `llm.py` (OpenAI Responses API / Chat Completions)
  - `pipeline.py` (orquestación: fetch → LLM → persist)
  - `store.py` (JSONL + SQLite)
  - `notion.py` (crear página en DB)
  - `neo4j.py` (export cypher)
  - `mcp_server.py` (MCP JSON-RPC stdio)
- `prompts/`
  - `prompt_mcp_definitivo.txt` (tu prompt)

---

## 6) Licencia
MIT. Ver `LICENSE`.

---

## 8) Modo “One-click”: Investigar IA + Noticias y subir a Notion

Este modo hace en una sola ejecución:
1) Descubre fuentes (RSS + Hacker News)
2) Descarga y extrae texto técnico
3) Genera brief estructurado (LLM local vía Ollama recomendado)
4) Genera un paquete listo para Notion (JSONL + payloads)
5) (Opcional) Sube automáticamente a Notion

### One-click (local)
```bash
python -m research.cli oneclick --topic "AI agents" --days 7 --limit 10 --out out/
```

### One-click + Notion sync
```bash
python -m research.cli oneclick --topic "AI agents" --days 7 --limit 10 --out out/
python -m research.cli notion-sync out/oneclick_results.jsonl
```

### LLM gratis (Ollama)
Si no quieres APIs de paga, usa Ollama (local). Configura:
- OPENAI_MODEL=llama3.1:8b (o qwen2.5:7b)
y cambia `research/llm.py` para usar Ollama (ver `research/llm_ollama.py`).



---

## 9) Modo 100% local (excepto búsqueda de noticias)

Configura en `.env`:
- `LLM_PROVIDER=ollama`
- `OPENAI_MODEL=llama3.1:8b` (o el modelo local que tengas)

Luego ejecuta el modo one-click. Esto solo usa internet para:
- descubrir links (RSS + HN)
- descargar el HTML
El análisis es local (Ollama) y el resultado final se empaqueta en:
- `out/notion_upload_pack_<topic>.zip`
>>>>>>> d829c5d (Initial commit: AI Tech Research System with Ollama + MCP pipeline)
