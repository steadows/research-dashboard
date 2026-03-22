# Research: Obsidian Graph & Network Analysis Tools

**Date:** 2026-03-18
**Sources:**
- https://github.com/SkepticMystic/graph-analysis
- https://github.com/mfarragher/obsidiantools
- https://github.com/luolanaatud/obsidian-graph-analysis
- https://github.com/azuma520/obsidian-graph-query
- https://github.com/ElsaTam/obsidian-extended-graph
- https://github.com/noduslabs/infranodus-obsidian-plugin
- https://infranodus.com/obsidian-plugin
- https://github.com/coddingtonbear/obsidian-local-rest-api
- https://github.com/ghanithan/obsidian-graph-memory
- https://github.com/cyanheads/obsidian-mcp-server
- https://data-wise.github.io/obsidian-cli-ops/
- https://pypi.org/project/obsidiantools/
- https://pypi.org/project/obsidianmd-parser/
- https://github.com/drewburchfield/obsidian-graph-mcp
- https://blog.kaliser.com/Graph+Metrics+Hub+Analysis
- https://publish.obsidian.md/hub/02+-+Community+Expansions/02.01+Plugins+by+Category/Graph+plugins

## Overview

The Obsidian ecosystem has a surprisingly rich set of graph analysis tools spanning community plugins (in-app), Python libraries (offline analysis), MCP servers (AI agent integration), and CLI tools. Most operate on the same underlying data: wiki-link directed graphs extracted from markdown files. The key question for our use case is: which tools expose a **Python-accessible API** that we can integrate into the Research Intelligence Dashboard?

## Key Concepts

1. **Wiki-link graph** -- The directed graph formed by `[[wikilinks]]` between notes. Every tool in this space ultimately parses this structure. Edges can be weighted (by co-citation proximity, link count, etc.).

2. **Centrality metrics** -- PageRank, betweenness, closeness, eigenvector, and degree centrality are the standard metrics for identifying important/hub notes. Several tools compute these.

3. **Community detection** -- Clustering notes into topical groups. Approaches range from label propagation (Graph Analysis plugin) to Louvain clustering (various Python implementations) to folder/tag grouping (simpler MCP tools).

4. **Link prediction** -- Algorithms (Adamic-Adar, Jaccard, Common Neighbors) that suggest notes that *should* be linked but aren't. This is directly relevant to our "recommendation" use case.

5. **Co-citation analysis** -- Notes frequently referenced together in the same document. A "2nd-order backlinks" concept that surfaces implicit relationships.

---

## 1. Obsidian Community Plugins

### Graph Analysis (SkepticMystic)
| Field | Value |
|-------|-------|
| **Repo** | https://github.com/SkepticMystic/graph-analysis |
| **Stars** | 497 |
| **Last release** | v0.15.4 (Jan 2022) |
| **Status** | **Unmaintained** -- no releases in 4+ years |
| **License** | GPL-3.0 |

**Algorithms implemented:**
- **Similarity**: Jaccard Similarity (graph structure, not content)
- **Link Prediction**: Adamic-Adar, Common Neighbours
- **Co-Citations**: Proximity-weighted co-occurrence counting
- **Community Detection**: Label Propagation, Clustering Coefficient

**Assessment:** The most algorithmically complete plugin, but effectively abandoned. The algorithms are well-documented and the codebase is a good reference for what metrics matter, but it cannot be relied upon for ongoing use. UI-only, no API exposure.

---

### Knowledge Graph Analysis (luolanaaTUD)
| Field | Value |
|-------|-------|
| **Repo** | https://github.com/luolanaatud/obsidian-graph-analysis |
| **Stars** | 1 |
| **Last release** | v0.6.0 (Mar 2026) |
| **Status** | Active development, early stage |
| **License** | MIT |
| **AI backend** | Google Gemini 3.1 Flash Lite (free tier) |

**Metrics computed:**
- Degree centrality
- Betweenness centrality
- Closeness centrality
- Eigenvector centrality

**AI features:**
- Per-note summaries, keywords, knowledge domain extraction
- Vault-level analysis: Semantic Analysis, Knowledge Structure, Knowledge Evolution, Recommended Actions
- AI-suggested connections with one-click link insertion
- Priority cards identifying hub notes, bridges, and authorities

**Assessment:** Very new (1 star), but the most feature-rich graph+AI plugin. Feeds graph metrics directly to an LLM for interpretation. Not yet in the community plugin directory (manual install). UI-only, no API. The concept of feeding centrality metrics to AI for interpretation is directly relevant to what we'd build.

---

### InfraNodus AI Graph View
| Field | Value |
|-------|-------|
| **Repo** | https://github.com/noduslabs/infranodus-obsidian-plugin |
| **Stars** | 125 |
| **Last release** | Active (last push Jan 2026) |
| **Status** | Maintained |
| **License** | AGPL-3.0 |
| **Pricing** | Free plugin, but InfraNodus SaaS required for full features |

**Features:**
- Text-to-graph transformation (not just wiki-links -- analyzes note *content*)
- Topic modeling and clustering
- Betweenness centrality visualization (node size = centrality)
- Structural gap identification (where topics aren't connected)
- GPT-powered research question generation from gap analysis
- 3D force-directed graph visualization

**Assessment:** The most polished graph visualization plugin. However, it requires the InfraNodus SaaS backend (paid), making it unsuitable for pipeline integration. The *concept* of structural gap analysis (finding disconnected topic clusters) is valuable for our recommendations engine.

---

### Extended Graph (ElsaTam)
| Field | Value |
|-------|-------|
| **Repo** | https://github.com/ElsaTam/obsidian-extended-graph |
| **Stars** | 171 |
| **Last release** | v2.7.7 (Oct 2025) |
| **Status** | Maintained |
| **License** | Custom |

**Features:**
- Enhanced built-in graph: custom node shapes, images, sizing by metadata
- Node/link scaling based on statistics
- Advanced filtering by tags and properties
- Link type visualization

**Assessment:** Visualization-focused enhancement of the built-in graph. No analysis algorithms. Not relevant for our programmatic use case.

---

### Hub Analysis (Path Analysis extension)
| Field | Value |
|-------|-------|
| **Source** | https://blog.kaliser.com/Graph+Metrics+Hub+Analysis |
| **Status** | Blog post / feature in an Obsidian plugin |

**Features:**
- PageRank implementation for vault notes
- Eigenvector centrality
- Hub identification -- "conceptual anchors" of your knowledge network
- Complements path analysis (specific note-to-note relationships)

**Assessment:** Good conceptual reference. Demonstrates PageRank applied to Obsidian vaults with clear explanations of why it matters for PKM.

---

## 2. Python Libraries

### obsidiantools (mfarragher) -- PRIMARY RECOMMENDATION
| Field | Value |
|-------|-------|
| **PyPI** | https://pypi.org/project/obsidiantools/ |
| **Repo** | https://github.com/mfarragher/obsidiantools |
| **Stars** | 535 |
| **Version** | 0.11.0 (Jul 2025) |
| **Python** | 3.9+ |
| **Status** | Maintained, mature |
| **License** | BSD-style |

**Core API:**
```python
import obsidiantools.api as otools

vault = otools.Vault("/path/to/vault").connect().gather()

# Access the NetworkX DiGraph directly
G = vault.graph

# Pandas DataFrames
df = vault.get_note_metadata()  # backlinks, wikilinks count, etc.

# Individual note data
vault.get_backlinks("Note Name")
vault.get_wikilinks("Note Name")
vault.get_front_matter("Note Name")

# Subgraph filtering
nodes = [n for n in vault.graph.nodes() if n not in vault.isolated_notes]
subgraph = vault.graph.subgraph(nodes).copy()
```

**What you get from `vault.graph`:**
- Full NetworkX DiGraph of the vault
- Directed edges from wikilinks (including multiple edges for repeated links)
- Self-loops for internal header links
- Can filter to subdirectories at instantiation

**What you get from metadata DataFrames:**
- Note name, file path, frontmatter
- Wikilink count, backlink count
- Embedded file references
- Markdown link references

**Dependencies:** `networkx`, `pandas`, `numpy`, `markdown`, `python-frontmatter`, `beautifulsoup4`

**Integration potential:** EXCELLENT. This is the primary tool for our use case. It gives us a NetworkX graph we can run any algorithm on:
```python
import networkx as nx

# PageRank
pr = nx.pagerank(vault.graph)

# Betweenness centrality
bc = nx.betweenness_centrality(vault.graph)

# Community detection (requires networkx or python-louvain)
from networkx.algorithms.community import louvain_communities
communities = louvain_communities(vault.graph.to_undirected())

# Shortest paths
path = nx.shortest_path(vault.graph, "Note A", "Note B")

# Link prediction
from networkx.algorithms.link_prediction import adamic_adar_index
predictions = list(adamic_adar_index(vault.graph.to_undirected(), [("Note A", "Note B")]))
```

**Known quirks (from wiki):**
- Graph includes self-loops (Obsidian app doesn't show these)
- Multiple wikilinks from A to B create multiple edges (Obsidian shows one)
- Relative path wikilinks (`[[./foo]]`) are not supported
- Graph shows non-existent notes as nodes (linked but not yet created)
- Does not include tags or attachments as graph nodes (notes-only philosophy)

---

### obsidianmd-parser (paddyd)
| Field | Value |
|-------|-------|
| **PyPI** | https://pypi.org/project/obsidianmd-parser/ |
| **Version** | 0.4.0 (Jan 2026) |
| **Python** | 3.12+ |
| **Status** | Active, early stage |
| **License** | MIT |

**Features:**
```python
from obsidian_parser import Vault

vault = Vault("path/to/vault")
note = vault.get_note("My Note")

# Access properties
note.title, note.tags, note.wikilinks, note.tasks, note.frontmatter

# Relationships
note.get_backlinks(vault=vault)
note.get_forward_links(vault=vault)

# Graph
graph = vault.get_note_graph()  # Returns graph tuple object

# Dataview query support
note.get_evaluated_view(vault)

# Broken links
vault.find_broken_links()
```

**Assessment:** Newer alternative to obsidiantools. Key differentiator is **Dataview query support**. However, it requires Python 3.12+ (our project uses 3.9+ compatible code), and the graph output format is unclear (may not be NetworkX). Less mature, fewer users.

---

### py-obsidianmd (selimrbd)
| Field | Value |
|-------|-------|
| **Repo** | https://github.com/selimrbd/py-obsidianmd |
| **Status** | Last push Aug 2023 -- likely unmaintained |
| **License** | BSD-3 |

**Focus:** Batch metadata modification (moving frontmatter to inline, adding/removing tags). Not graph-focused. Not recommended for our use case.

---

### prototype-05-obsidian-networkx (cristianvasquez)
| Field | Value |
|-------|-------|
| **Repo** | https://github.com/cristianvasquez/prototype_05 |
| **Status** | Last push Apr 2021 -- abandoned |

**Features:** PageRank + Louvain clustering for Obsidian vaults. Proof-of-concept quality. Interesting as a reference for the exact algorithms we'd want, but not usable as a library.

---

## 3. CLI & External Tools

### Obsidian CLI Ops (data-wise)
| Field | Value |
|-------|-------|
| **Docs** | https://data-wise.github.io/obsidian-cli-ops/ |
| **Version** | 3.2.0 |
| **Language** | Python 3.9+ with ZSH CLI wrapper |
| **Tests** | 265 passing |
| **Status** | Active, reasonably mature |

**Features:**
- `obs discover` -- scan and catalog vaults
- `obs health` -- analyze vault structure (PageRank, centrality, clustering, orphans, hubs)
- AI-powered duplicate detection and reorganization suggestions
- SQLite persistence layer

**Assessment:** Well-engineered but focused on vault *maintenance* rather than analysis export. The health command computes exactly the metrics we want. Worth examining the source code for algorithm implementation patterns. Python-based so potentially importable.

---

### obsidian-graph-query (azuma520) -- Claude Code Skill
| Field | Value |
|-------|-------|
| **Repo** | https://github.com/azuma520/obsidian-graph-query |
| **Stars** | 24 |
| **Version** | v1.1.0 (Mar 2026) |
| **Type** | Claude Code skill (not a library or plugin) |
| **Status** | New, active |

**Architecture:** Executes JavaScript in Obsidian's Electron process via Obsidian CLI `eval` command. Accesses `app.metadataCache.resolvedLinks` directly for live graph data.

**Supported queries:**
- Hub detection (high-degree nodes)
- Shortest path analysis
- N-hop neighborhood exploration
- Bridge/articulation point detection (Tarjan's algorithm)
- Orphan discovery
- Vault-wide statistics

**Assessment:** Interesting architecture that taps into Obsidian's live metadata cache. However, it's a Claude Code skill, not a library. The approach of using `obsidian cli eval` to query live graph data is novel but requires Obsidian to be running. Not suitable for batch/pipeline integration.

---

## 4. MCP Servers & API Access

### Obsidian Local REST API (coddingtonbear)
| Field | Value |
|-------|-------|
| **Repo** | https://github.com/coddingtonbear/obsidian-local-rest-api |
| **Type** | Obsidian community plugin |
| **Status** | Mature, well-established |

**Endpoints:**
- CRUD operations on notes (GET, PUT, POST, PATCH, DELETE)
- Directory listing / vault browsing
- Periodic notes access (daily, weekly, etc.)
- Command execution
- Search (text, Dataview DQL, JsonLogic)

**Graph-related capabilities:** NONE. This is a content CRUD API only. No graph structure, no link data, no relationship querying. However, it's the foundation that several MCP servers build upon.

---

### obsidian-graph-memory (ghanithan)
| Field | Value |
|-------|-------|
| **Repo** | https://github.com/ghanithan/obsidian-graph-memory |
| **Language** | TypeScript |
| **Status** | Very early (3 commits, 0 stars) |

**MCP Tools:**
- `graph_query_related` -- N-hop wikilink traversal
- `graph_find_path` -- shortest path between notes
- `graph_get_hubs` -- most-connected notes
- `graph_get_orphans` -- disconnected notes
- `graph_get_clusters` -- group by folder/tag
- `graph_get_stats` -- vault-wide statistics
- `graph_refresh` -- rebuild graph

**How it works:** Fetches markdown via Local REST API, parses wikilinks, builds in-memory directed graph, runs BFS traversals. Auto-refreshes every 5 minutes.

**Assessment:** Exactly the right idea for AI agent integration, but too immature (3 commits). The tool list is a good reference for what graph queries are useful for AI agents.

---

### obsidian-graph-mcp (drewburchfield)
| Field | Value |
|-------|-------|
| **Repo** | https://github.com/drewburchfield/obsidian-graph-mcp |
| **Approach** | Vector embeddings + PostgreSQL/pgvector |

**Features:** Semantic similarity between notes using vector embeddings. Multi-hop knowledge graph traversal. Goes beyond wiki-links to find *conceptual* relationships.

**Assessment:** Different approach -- semantic rather than structural. Requires PostgreSQL + pgvector infrastructure. Overkill for our current needs but interesting for future semantic search integration.

---

### Obsidian MCP Server (cyanheads)
| Field | Value |
|-------|-------|
| **Repo** | https://github.com/cyanheads/obsidian-mcp-server |
| **Version** | 2.0.7 |
| **Status** | Production-grade |

**Tools:** 8 tools for note CRUD, search/replace, frontmatter management, tag management. **No graph analysis capabilities.** Content-focused only.

---

## Integration Pattern

### Recommended approach for Research Intelligence Dashboard

**Use `obsidiantools` as the foundation.** It gives us a NetworkX graph with zero custom parsing needed. Then layer on NetworkX algorithms for the specific metrics we want.

```python
import obsidiantools.api as otools
import networkx as nx
from networkx.algorithms.community import louvain_communities

def build_vault_graph(vault_path: str) -> tuple[otools.Vault, nx.DiGraph]:
    """Parse vault and return connected graph."""
    vault = otools.Vault(vault_path).connect()
    return vault, vault.graph

def compute_graph_metrics(G: nx.DiGraph) -> dict:
    """Compute centrality metrics on the vault graph."""
    G_undirected = G.to_undirected()
    return {
        "pagerank": nx.pagerank(G),
        "betweenness": nx.betweenness_centrality(G),
        "degree": dict(G.degree()),
        "in_degree": dict(G.in_degree()),
        "out_degree": dict(G.out_degree()),
        "communities": louvain_communities(G_undirected),
    }

def suggest_links(G: nx.DiGraph, note: str, top_n: int = 10) -> list[tuple]:
    """Predict missing links using Adamic-Adar index."""
    G_undirected = G.to_undirected()
    non_neighbors = [
        n for n in G_undirected.nodes()
        if n != note and n not in G_undirected.neighbors(note)
    ]
    pairs = [(note, n) for n in non_neighbors]
    predictions = nx.adamic_adar_index(G_undirected, pairs)
    scored = [(v, score) for u, v, score in predictions]
    return sorted(scored, key=lambda x: x[1], reverse=True)[:top_n]
```

**Why not the alternatives:**
- Obsidian plugins are UI-only -- cannot be called from Python
- MCP servers add infrastructure complexity for no gain (we can parse markdown directly)
- `obsidianmd-parser` requires Python 3.12+ and has an unclear graph format
- CLI tools are shells around the same parsing we can do directly

**Dependencies to add:** `obsidiantools`, `python-louvain` (for Louvain community detection if not using networkx built-in)

---

## Gotchas & Pitfalls

1. **obsidiantools graph vs Obsidian app graph:** The library creates multi-edges for repeated wikilinks and includes self-loops for header links (`[[note#section]]`). The Obsidian app shows neither. For centrality metrics, convert to a simple graph first: `nx.DiGraph(vault.graph)` to collapse multi-edges.

2. **Non-existent notes as nodes:** If you link to `[[Future Note]]` but haven't created it yet, obsidiantools includes it as a node. Filter with `vault.isolated_notes` or check against `vault.file_index`.

3. **Relative path wikilinks:** `[[./subdir/note]]` and `[[../note]]` syntax is not supported by obsidiantools. Our vault doesn't use these (we use shortest-path resolution), so this is fine.

4. **Performance on large vaults:** `connect()` is fast (graph construction). `gather()` is slow (reads all note content). For graph-only analysis, skip `gather()` entirely -- we only need `connect()`.

5. **Caching strategy:** The vault graph is relatively stable (changes only when notes are edited). Cache the graph object and recompute metrics on a TTL basis, not on every page load.

6. **Undirected vs directed:** Wikilinks are inherently directed (A links to B doesn't mean B links to A). Some algorithms (Louvain, Jaccard, Adamic-Adar) require undirected graphs. Use `G.to_undirected()` explicitly and be aware this loses directionality information. For PageRank, use the directed graph.

7. **InfraNodus requires SaaS:** Despite being an Obsidian plugin, InfraNodus routes analysis through their cloud service. Not suitable for local/pipeline integration.

---

## API Reference

### obsidiantools key API surface

```python
# Initialization
vault = otools.Vault(dirpath, include_subdirs=None, exclude_subdirs=None)
vault.connect()   # Build graph from wikilinks (fast)
vault.gather()    # Read note content (slow, optional for graph-only work)

# Graph access
vault.graph                    # networkx.MultiDiGraph
vault.backlinks_index          # dict: note_name -> list of notes linking to it
vault.wikilinks_index          # dict: note_name -> list of notes it links to
vault.nonexistent_notes        # list of linked-but-uncreated notes
vault.isolated_notes           # list of orphan notes (no links in or out)
vault.front_matter_index       # dict: note_name -> frontmatter dict

# Metadata DataFrames
vault.get_note_metadata()      # pd.DataFrame with all note stats
vault.get_media_file_metadata()

# Individual note queries
vault.get_backlinks(note_name)
vault.get_wikilinks(note_name)
vault.get_front_matter(note_name)
```

### NetworkX algorithms most relevant to our use case

```python
# Centrality (use directed graph)
nx.pagerank(G)
nx.betweenness_centrality(G)
nx.closeness_centrality(G)
nx.eigenvector_centrality(G, max_iter=1000)
dict(G.in_degree())   # backlink count
dict(G.out_degree())  # wikilink count

# Community detection (use undirected)
from networkx.algorithms.community import louvain_communities
louvain_communities(G.to_undirected())

# Link prediction (use undirected)
nx.adamic_adar_index(G.to_undirected(), pairs)
nx.jaccard_coefficient(G.to_undirected(), pairs)
nx.common_neighbor_centrality(G.to_undirected(), pairs)

# Path analysis
nx.shortest_path(G, source, target)
nx.has_path(G, source, target)

# Structural analysis
nx.is_connected(G.to_undirected())
list(nx.connected_components(G.to_undirected()))
list(nx.bridges(G.to_undirected()))  # critical edges
```

---

## Decision Notes

### Why obsidiantools + NetworkX over alternatives

| Option | Verdict | Reason |
|--------|---------|--------|
| **obsidiantools + NetworkX** | CHOSEN | Mature (535 stars), Python-native, gives raw NetworkX graph, we already use vault_parser.py for wikilink extraction so this is complementary |
| Obsidian Graph Analysis plugin | Reject | UI-only, unmaintained since 2022, cannot call from Python |
| InfraNodus | Reject | Requires paid SaaS backend, AGPL license |
| obsidianmd-parser | Watch | Interesting Dataview support but requires Python 3.12+, less mature |
| Obsidian CLI Ops | Reference | Good algorithm reference, but adds CLI wrapper complexity |
| MCP graph servers | Reject | Too immature (0-3 commits), add infrastructure for minimal gain |
| obsidian-graph-query | Reject | Requires Obsidian running, Claude Code skill not a library |
| Knowledge Graph Analysis plugin | Watch | Interesting AI+metrics concept, but UI-only and very new |

### Integration with existing vault_parser.py

Our `src/utils/vault_parser.py` already parses Obsidian vault projects and extracts wiki-links for the project index. Rather than replacing it, `obsidiantools` would complement it:

- **vault_parser.py** continues to handle project-specific parsing (frontmatter, GSD plans, overview extraction)
- **obsidiantools** handles vault-wide graph construction and NetworkX integration
- Graph metrics from obsidiantools feed into the Dashboard as a new data source
- Link predictions from NetworkX could power a "Suggested Connections" feature in the Cockpit

### What we'd build (not in scope for this research doc)

1. A `src/utils/graph_analyzer.py` module wrapping obsidiantools + NetworkX
2. Cached graph metrics (PageRank, communities, hubs) refreshed on vault changes
3. A Dashboard tab or Cockpit section showing graph insights per project
4. Link recommendation engine using Adamic-Adar or Jaccard for "notes you should connect"
