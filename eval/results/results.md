# Issue #44 evaluation results

- provider: silicon / model: deepseek-ai/DeepSeek-V3
- RAG baseline: embeddings BAAI/bge-m3, top-k=8
- repeats per document: 2; segment size: 1600
- stub run: no

## Per document

| doc | group | term hit | occurrence hit | prompt tokens (est) | embedding tokens | total extra vs A | provider tokens | seconds | errors |
|---|---|---|---|---|---|---|---|---|---|
| novel | A | 66.7% | 38.4% | 11421.0 | 0.0 | 0.0 | 15893.5 | 277.17 | 0 |
| novel | B | 81.7% | 53.7% | 12584.0 | 2889.0 | 4052.0 | 14967.5 | 236.915 | 0 |
| novel | C | 100.0% | 97.0% | 12929.0 | 0.0 | 1508.0 | 17114.0 | 185.835 | 0 |
| rulebook | A | 75.0% | 47.2% | 11464.0 | 0.0 | 0.0 | 15550.0 | 239.9 | 0 |
| rulebook | B | 80.0% | 55.9% | 12756.0 | 3025.0 | 4317.0 | 16556.0 | 370.85 | 0 |
| rulebook | C | 100.0% | 99.1% | 12883.0 | 0.0 | 1419.0 | 13074.5 | 117.68 | 0 |
| technical_doc | A | 63.7% | 46.1% | 11479.0 | 0.0 | 0.0 | 13920.5 | 191.875 | 0 |
| technical_doc | B | 77.5% | 52.7% | 12797.0 | 3085.0 | 4403.0 | 14191.5 | 203.295 | 0 |
| technical_doc | C | 98.8% | 89.7% | 12783.0 | 0.0 | 1304.0 | 18543.0 | 210.555 | 0 |

## Overall

| group | term hit | occurrence hit | prompt tokens (est) | embedding tokens | provider tokens | seconds | errors |
|---|---|---|---|---|---|---|---|
| A | 68.5% | 43.9% | 11454.6667 | 0.0 | 15121.3333 | 236.315 | 0 |
| B | 79.7% | 54.1% | 12712.3333 | 2999.6667 | 15238.3333 | 270.3533 | 0 |
| C | 99.6% | 95.3% | 12865.0 | 0.0 | 16243.8333 | 171.3567 | 0 |

RAG index build tokens (one-time, reported separately): {"technical_doc": 16222, "rulebook": 14358, "novel": 15825}
