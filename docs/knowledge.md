# Knowledge Base

This phase introduces a vector store backed by Qdrant. Documents are chunked at 512 tokens with 20 token overlap and embedded using the Llama3 model via Ollama. The `docs` collection uses cosine distance with a 4096 dimensional vector size and HNSW parameters `m=16` and `ef_construct=64`. Each vector carries a `tenant_id` payload so queries always filter on the requesting tenant.

