# NexoMercado AI

Plataforma de inteligencia de mercado que transforma noticias y datos verificables en señales explicables y briefings sujetos a revisión humana.

## Documentación

- [Plan de implementación por fases](docs/PLAN_IMPLEMENTACION_POR_FASES.md)
- [Matriz de aceptación de la Fase 0](docs/FASE_0_MATRIZ_ACEPTACION.md)
- [Estado técnico y prioridades](docs/ESTADO_TECNICO_Y_PRIORIDADES.md)
- [Contrato OpenAPI](contracts/openapi.json)
- [Fixtures reproducibles](data/fixtures/v1/phase0_bundle.json)
- [Arquitectura general](docs/referencias/ARQUITECTURA_GENERAL_NexoMercado_AI.md)
- [Guía del Track 5](docs/referencias/Hackathon_Guide_Financial_Agents_IA_-_Track_5.md)

La Fase S0 fue aceptada y la Fase 0 está lista para revisión. Ninguna fase se acepta o avanza automáticamente.

## Configuracion de OpenAI

La integracion del backend usa la API oficial de OpenAI a traves de variables de entorno. No guardes claves reales en el repositorio.

Variables esperadas:

- `OPENAI_API_KEY`
- `OPENAI_MODEL` con valor sugerido `gpt-5.4`
- `OPENAI_REASONING_EFFORT` con uno de `minimal`, `low`, `medium` o `high`
- `LLM_PROVIDER` con `fixture` o `openai`
- `REPOSITORY_BACKEND` con `fixture` o `supabase`
- `FIXTURE_BUNDLE_PATH` para seleccionar el bundle offline
- `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY` solo para persistencia real

Ejemplo rapido:

```bash
cp .env.example .env
export OPENAI_API_KEY="tu_api_key_nueva"
export OPENAI_MODEL="gpt-5.4"
export OPENAI_REASONING_EFFORT="medium"
export LLM_PROVIDER="fixture"
export REPOSITORY_BACKEND="fixture"
export FIXTURE_BUNDLE_PATH="data/fixtures/v1/phase0_bundle.json"
```

Base de integracion agregada:

- Configuracion: `backend/app/config.py`
- Cliente OpenAI: `backend/app/openai_client.py`

## Modos de runtime del backend

### Modo fixture

Es el baseline estable del proyecto y no requiere credenciales externas.

```bash
cd backend
../backend/.venv314/bin/python -m pytest tests -q
```

### Modo supabase

Mantiene lecturas deterministicas desde fixtures y persiste solo el estado mutable del flujo:

- reviews
- briefings
- runs
- run steps
- idempotencia

Antes de usarlo:

1. aplica [`supabase/schema.sql`](supabase/schema.sql) en tu proyecto Supabase;
2. configura `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` y `REPOSITORY_BACKEND=supabase`.

Comandos utiles:

```bash
backend/.venv314/bin/python backend/scripts/check_supabase_connection.py --env-file .env
backend/.venv314/bin/python backend/scripts/bootstrap_supabase.py --env-file .env --apply
backend/.venv314/bin/python backend/scripts/check_supabase_persistence.py --env-file .env
```
