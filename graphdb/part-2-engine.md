# Graph Database Internals: How Storage Engines Decide Your Performance Ceiling

*Part 2 of 5 — Series: Graph Databases: From Zero to Production*
*Last verified: May 2026*

---

In Part 1, we covered the landscape — why graph databases exist, how to evaluate them, and which one fits which workload. That was the buyer's map.

This is the builder's map.

And here's the thing that made me want to write this post: most production failures in graph systems get blamed on "bad queries." But when I dig in, many of them are actually storage-model failures that were baked in on day one. The engine you picked already decided your latency profile and your failure mode. The queries just exposed it.

If you only remember one idea from this post, make it this: **the engine model determines both your latency profile and your failure mode**. Not the query. Not the schema. The engine.

In this post, we're going one level deeper. We'll look at what actually happens in bytes when you write a node, what actually happens when you read one, and why two databases that both call themselves "native graph" can behave nothing alike under load.

Don't worry — we'll make the internals feel intuitive. By the end, storage engines will feel less like black-box magic and more like "oh, it's just pointers and linked lists." Ready? Let's go 🚀

---

## Blog Series

Part 1: So You Need a Graph Database — The Landscape
📌 **Part 2: Graph Database Internals: How Storage Engines Decide Your Performance Ceiling** *(this post!)*
Part 3: Graph Query Languages Compared: Cypher vs Gremlin vs GSQL vs DQL *(coming next!)*
Part 4: Graph Databases in Production: What Breaks, Why It Breaks, and How to Contain It *(coming soon!)*
Part 5: Running Graph Databases in Production: Optimization, Pitfalls, and the Go-Live Playbook *(coming soon!)*

---

## What We'll Cover

- How different graph databases store adjacency (and why it matters more than any benchmark)
- The write path: what actually happens when you INSERT a node and an edge
- The read path: what actually happens when you MATCH
- Property Graph vs RDF: a decision you make before you even pick a database
- Graph data modeling fundamentals — when something should be a node, a property, or an intermediate node
- The #1 modeling mistake that causes production failures

---

## TL;DR (for the impatient)

- Native pointer-based adjacency and non-native wide-row storage behave *very* differently under high degree.
- The write path (WAL, pointer updates, MVCC, replication) explains most real-world contention issues.
- Data modeling decisions (node vs property vs reification) become expensive to reverse later.

> **The key takeaway:** "Graph database" is a category label. It is NOT a guarantee of equivalent storage behavior. Two "native graph" databases can be night and day under load.

---

## The Rolodex vs. the Phonebook — Going Deeper

In Part 1, I introduced index-free adjacency as a concept. Let me now take that analogy one level deeper — because this is where the performance story really lives.

Here's the setup. A relational database is a phonebook. Looking up "Alice" takes O(log n) time — logarithmic in the total number of people. When you find Alice and want to know who she knows, you close the phonebook, open the junction table phonebook, and look up "Alice" there. Then you open the users phonebook *again* for each result. Every hop is a new index lookup. The cost grows with the size of the index, which grows with your data.

A native graph database is a rolodex. Alice's card has Bob's card physically clipped to the back of it. Bob's card has Carol's. To traverse Alice's network, you flip cards — O(1) per hop. You don't search the whole deck. You follow a wire.

Now let's see what that actually looks like in bytes. This is where it gets interesting.

### Neo4j (Native — Record and Block formats)

Every node is a **15-byte record** on disk. Every relationship is a **34-byte record** ([Neo4j docs: Store formats](https://neo4j.com/docs/operations-manual/current/database-internals/store-formats/)). These are fixed-size — which means the database can calculate the file offset of any record from its ID in O(1) time. No index needed.

> **A note on Neo4j 5+ Block format.** Neo4j 5 introduced a new on-disk format called **Block** (8 KB blocks packing node, relationship, and property data together) alongside the legacy fixed-size Record format. Block is now the default for new Enterprise databases. The doubly-linked-list traversal model we're about to discuss is unchanged — Block changes *layout and locality* (fewer page faults, better compression), not the algorithm. Think of the 15-byte/34-byte figures as the canonical mental model; Block as the format you'll likely actually run.

Inside each relationship record are four pointers:
- `prev_rel_start`: the previous relationship in the start node's chain
- `next_rel_start`: the next relationship in the start node's chain
- `prev_rel_end`: the previous relationship in the end node's chain
- `next_rel_end`: the next relationship in the end node's chain

These four pointers form **doubly-linked lists** — one list per node, threading all relationships that connect to that node. When Neo4j traverses from Alice to her friends, it follows Alice's relationship linked list. It doesn't scan a table. It follows pointers.

Here's the critical implication: Neo4j follows only the pointers it needs. A `MATCH (alice)-[:KNOWS]->(friend)` follows Alice's relationship list, skips non-KNOWS relationships, and loads the endpoint node for each match. A 500-million-edge node has a 17GB storage footprint (500M × 34 bytes) — but Neo4j doesn't load all 17GB. It walks the linked list and filters at each step.

> 📸 **Image placeholder:** Diagram showing a 15-byte Neo4j node record with a pointer to the first relationship, and a 34-byte relationship record with its four pointers. *Caption: "Neo4j 5.x: every relationship record is a doubly-linked list node."*

### JanusGraph on Cassandra (Non-Native)

JanusGraph doesn't have its own storage engine. It delegates to a backend — typically Apache Cassandra. And here's the consequence that caught me off guard when I first learned it:

Each node's entire adjacency list is stored as a single **Cassandra wide row**. Every edge from that node is one column. Every property is another column.

So to read *one* edge from a high-degree node, Cassandra has to deserialize the entire row. A node with 100,000 edges? You're deserializing all 100,000 before you can filter the one you want.

This is the predictable performance cliff that JanusGraph users hit when nodes become popular. It's not a bug — it's the structural consequence of non-native graph storage. And once you understand this, you'll never wonder again why "the same query" performs so differently across databases.

### TigerGraph (MPP, Columnar)

TigerGraph uses a proprietary columnar binary encoding with vendor-reported 2–10× compression (independently confirmed at 2.57× on the Twitter dataset). All outbound edges from a node are co-located on the same machine — so single-hop traversals are local. Cross-partition traversal only happens when the endpoint lives on a different machine.

The MPP architecture means TigerGraph can execute multi-hop traversals across machines simultaneously, using Bulk Synchronous Parallel execution. This is why it handles billion-edge analytics that would exhaust other databases.

### Memgraph (In-Memory)

All data lives in RAM. Every pointer hop is a direct memory dereference — no I/O, no cache lookup, no disk seek. This is why Memgraph achieves sub-millisecond traversal latency.

Each write creates a **56-byte Delta object** ([Memgraph storage docs](https://memgraph.com/docs/fundamentals/storage-memory-usage)) — a record of what changed. Deltas enable MVCC without locking: readers see a consistent snapshot, writers create new deltas, and the database reconciles at commit time. The base edge object is 32 bytes; with a Delta, 88 bytes minimum. (Vertex is 80 bytes base, 136 bytes with Delta.)

Memgraph has two modes:
- `IN_MEMORY_TRANSACTIONAL` (default): Deltas enabled, MVCC active, full ACID.
- `IN_MEMORY_ANALYTICAL`: Deltas disabled. No MVCC overhead. 5–10× faster bulk load. Use this for initial data ingestion, then switch back.

> 📸 **Image placeholder:** Side-by-side — JanusGraph wide row (must deserialize all to read one) vs. Neo4j linked-list (follow only what you need). *Caption: "Cassandra wide-row vs. linked-list: the storage model determines your performance ceiling."*

---

## The Write Path — What Actually Happens on INSERT

Let's make this super concrete. You run: "Create a Person node Alice and a KNOWS relationship to Bob."

Here's what each database *actually* does under the hood. (This is the part most tutorials skip, and it's the part that explains 80% of production contention issues.)

### Neo4j Write Path

1. Begin transaction → acquire write lock on the write-ahead log
2. Allocate a new node record (15 bytes) in the node store file
3. Allocate a new relationship record (34 bytes) in the relationship store file
4. Update the relationship record's four pointers: thread Alice's linked list (prev/next) and Bob's linked list (prev/next)
5. Update the property store if Alice or the relationship has properties
6. Write the WAL (Write-Ahead Log) entry — written *before* flushing to the page cache. Crash = replay from WAL.
7. Commit → WAL entry marked committed. Page cache updated asynchronously.

The pointer threading in step 4 is the expensive part. Creating an edge doesn't just write one record — it mutates two nodes' relationship lists. Under high write concurrency to the same node, those pointer updates serialize. This is the structural reason Neo4j struggles with high-degree write hot spots. It's physics, not tuning.

### Memgraph Write Path

1. Begin transaction → create an MVCC snapshot timestamp
2. Create an in-memory node object with an empty Delta chain pointer
3. Create an in-memory edge object (32-byte base + 56-byte Delta)
4. Append the Delta to the WAL buffer
5. Commit → Delta marked committed in the MVCC version chain

Memgraph's MVCC avoids write-write locking: if two transactions write to the same node simultaneously, one gets an optimistic conflict failure and must retry. No deadlock — just retry. Clean.

### TigerGraph Write Path

1. Hash the vertex ID → determine which partition (machine) owns this vertex
2. Write the vertex/edge to that partition's adjacency column structure
3. Synchronous replication to configured replicas before acknowledging commit

The synchronous replication in step 3 means TigerGraph's write latency is bounded by the network RTT between partition replicas. High throughput at scale, but not sub-millisecond for individual writes.

> 📸 **Image placeholder:** Write path flowchart — Application → Begin Transaction → WAL Write → Page Cache → Pointer Update → Commit. *Caption: "Write path in a native graph DB: WAL before page cache, pointer update last."*

---

## The Read Path — What Actually Happens on MATCH

The write path creates the structure. The read path is where that structure pays off.

You run: `MATCH (p:Person {name: 'Alice'})-[:KNOWS]->(friend) RETURN friend.name`

### Neo4j Read Path

1. Cost-based optimizer parses the query → estimates cardinality of each clause
2. If an index exists on `Person.name`, use it → file offset to Alice's node record (O(log n) index lookup, then O(1) for the record itself)
3. Load Alice's node record (15 bytes) from page cache (or disk if cache miss)
4. Follow the first relationship pointer in Alice's node record
5. Traverse the doubly-linked relationship list: at each record, check type (`[:KNOWS]`) and direction. Skip if it doesn't match.
6. For each passing relationship: load the endpoint node record, evaluate property filters
7. Stream results to the client — lazy evaluation, rows returned as found

The key insight: Neo4j never reads the full graph. It follows pointers surgically. The same traversal in JanusGraph reads the entire wide row — all edges, all columns — even if you only want KNOWS relationships. At 10 friends, the difference is irrelevant. At 100,000 relationships per node, it's the difference between a fast query and a timeout.

---

## Property Graph vs. RDF — The Data Model Decision

Before you write your first query, you make a foundational decision. And I'll be honest — I didn't appreciate how much this matters until I saw teams try to switch later. (Spoiler: they couldn't.)

A **property graph** has first-class edges. An edge can have properties. `(Alice)-[KNOWS {since: 2020}]->(Bob)` is one relationship record with a `since` property. Three hops = three pointer follows.

An **RDF triple store** has no edge objects. Everything is a `(subject, predicate, object)` triple. The relationship `Alice KNOWS Bob` is one triple. The property `since: 2020` requires a separate triple (or reification). Three hops = three SPARQL triple pattern joins.

**When to choose property graph:** You're building application-driven traversals, your relationships have meaningful properties, and your team writes code in a mainstream language. This is 90% of use cases.

**When to choose RDF:** You need SPARQL federation across external datasets, you're integrating with W3C Linked Data standards, or your domain has established ontologies (healthcare HL7 FHIR, scientific publishing). Neptune supports both — if this flexibility matters, Neptune is the practical choice.

> 📸 **Image placeholder:** Same relationship shown two ways — property graph with edge property vs. three RDF triples. *Caption: "Property graph vs. RDF: same relationship, different storage costs."*

---

## Graph Data Modeling — The Decisions That Break Production

This is the section I wish someone had shown me before I built my first graph system. Seriously. These three decisions, made at design time, will either reward or punish you for the lifetime of your system.

### Decision 1: Is This a Node or a Property?

Use a **property** when the value is intrinsic to the entity and you'll never traverse *through* it. `Person {name: 'Alice', age: 30, country: 'US'}` — age and country can be properties if your queries only filter by them.

Use a **node** when the concept is something you'd traverse *to* or *from*. `Country` should be a node if you ever want to run `MATCH (p:Person)-[:LIVES_IN]->(c:Country {name: 'France'})`. If you need "find all people in the same country as Alice," the country *must* be a node.

**The rule, sharpened:**
- **Properties** = fields you'll only ever *filter on* or *return* (`WHERE p.age > 30`, `RETURN p.email`)
- **Nodes** = entities you'll ever *traverse through* (`-[:LIVES_IN]->(c:Country)<-[:LIVES_IN]-(other)`)

If you'd ever write `->(it)->` or `<-(it)<-` in a Cypher pattern, `it` is a node — not a property. Get this wrong and you'll either be doing string-equality joins in application code, or paying for pointless extra hops on filter-only fields.

### Decision 2: Relationship Properties or Intermediate Node?

`(Alice)-[PURCHASED {date: '2024-01-15', amount: 99.99}]->(Product)` works great when you only query from Alice's or the product's perspective.

The problem arrives when the relationship itself needs relationships. "This Purchase was fulfilled by this Warehouse." "This Purchase contains multiple line items." Relationships can't have relationships. So you need **reification** — turning the relationship into a node:

```
(Alice)-[MADE]->(Purchase {date: '2024-01-15', amount: 99.99})-[CONTAINS]->(Product)
(Purchase)-[FULFILLED_BY]->(Warehouse)
```

The cost: every "Alice bought Product" query now traverses two hops instead of one. But you gain first-class entity modeling — auditable, extendable, connectable.

### Decision 3: Too Many Relationship Types vs. Too Few

Too many: `PURCHASED_IN_JANUARY`, `PURCHASED_IN_FEBRUARY`, `PURCHASED_IN_Q1_2024`. Now you can't write a generic "find all purchases" query without enumerating dozens of types. Your traversal patterns fragment.

Too few: `HAS` for everything. `(Alice)-[HAS]->(Friend)`, `(Alice)-[HAS]->(Purchase)`, `(Alice)-[HAS]->(Subscription)`. No storage-level filtering — the database loads all HAS edges and filters in memory. This is how supernodes form.

The rule: name relationship types for what they *semantically mean*, not when or how something happened. `PURCHASED`. `KNOWS`. `LIVES_IN`. Filter by date, status, or amount in the WHERE clause.

### The #1 Production Failure

Projecting a relational schema directly into a graph. Tables become nodes. Foreign keys become relationships. The result? A graph with the same join structure as the relational model — but with graph engine overhead on top of it, and without the query optimizer optimizations built for relational data. You get worse performance than the database you replaced. Ouch.

The correct approach: **query-driven design**. Start with the traversal questions your application needs to answer. Design the schema that makes those traversals fast. Let access patterns drive the model — not the existing table structure.

---

## Closing

You now have the engine-level view: what gets written, what gets read, and where the bottlenecks come from. The internals are not magic — they're pointers, linked lists, and WAL files. Once you see them that way, a lot of production behavior stops being surprising.

Next up, we're looking at the other half of the performance equation: query language behavior. Same graph, different language choices, radically different execution paths.

Don't worry — we'll compare the same query in all four languages side by side, so you can see exactly what each optimizer does differently. 🚀

*Next: Graph Query Languages Compared: Cypher vs Gremlin vs GSQL vs DQL →*
