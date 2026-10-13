# ADR-0002: Append-only run registry
Status: accepted.

Persist completed run manifests and their byte hashes in PostgreSQL before API success. Use parameterized transactions, a SELECT/INSERT application role, and mutation-blocking triggers. Retain filesystem artifacts on registration failure; recover via explicit idempotent registration. Verification compares files to the independent database record. PostgreSQL administration and local file ownership remain trusted; future signing/offline backups strengthen tamper evidence.
