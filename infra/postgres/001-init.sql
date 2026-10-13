CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE design_runs (
  id uuid PRIMARY KEY,
  parent_id uuid REFERENCES design_runs(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  validation_status text NOT NULL,
  manifest jsonb NOT NULL,
  manifest_sha256 char(64) NOT NULL
);
CREATE TABLE knowledge_chunks (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_uri text NOT NULL,
  source_sha256 char(64) NOT NULL,
  content text NOT NULL,
  embedding_model text,
  embedding vector
);
-- Add a dimension-specific index after selecting a local embedding model.
-- Run persistence is wired to the API; knowledge ingestion remains pending.
