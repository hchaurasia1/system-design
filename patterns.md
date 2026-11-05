# Pattern Index

The same ideas keep showing up in different systems. This page is organized by pattern, not by system, so you can see where each one gets used and where it stops working.

Each entry links to the article section that explains it in detail. Systems without a link haven't been written up yet.

## Contents

- [Fan-out-on-write](#fan-out-on-write)
- [Single serialization point](#single-serialization-point)
- [Durability before delivery](#durability-before-delivery)
- [TTL as absence detection](#ttl-as-absence-detection)
- [Atomic countdown barrier](#atomic-countdown-barrier)
- [Idempotent conditional writes](#idempotent-conditional-writes)
- [Exponential backoff with full jitter](#exponential-backoff-with-full-jitter)
- [Versioned membership](#versioned-membership)
- [Event loop over thread-per-connection](#event-loop-over-thread-per-connection)
- [Targeted routing vs load-sharing](#targeted-routing-vs-load-sharing)
- [Hybrid fan-out by author and reader](#hybrid-fan-out-by-author-and-reader)
- [Sorted-source merge](#sorted-source-merge)
- [Cursor boundaries versus snapshots](#cursor-boundaries-versus-snapshots)
- [Derived caches versus product state](#derived-caches-versus-product-state)
- [Coordinated bounded rebuilds](#coordinated-bounded-rebuilds)

---

## Fan-out-on-write

When a message is sent, write a copy for each recipient right away, so each recipient's read is a single cheap partition scan.

- **Used in:** [WhatsApp: per-user inbox](designs/whatsapp/README.md#data-model-and-database-selection), [WhatsApp: group fan-out](designs/whatsapp/README.md#group-messaging-and-the-fan-out-question), [News feed: preparing reader references](designs/fb-news-feed/README.md#why-push-ordinary-posts-and-pull-celebrity-posts)
- **Also appears in:** Twitter home timelines, Instagram feeds
- **Breaks when:** there are a huge number of recipients (celebrity tweets, broadcast channels with millions of followers)
- **What replaces it:** fan-out-on-read for the big senders, or a hybrid of both
- **Interview line:** "Fan-out-on-write trades write amplification for O(1) reads. It works when fan-out is bounded."

## Single serialization point

Send every operation for one key through a single writer so the operations get one definite order.

- **Used in:** [WhatsApp: per-chat message ordering](designs/whatsapp/README.md#ordering-why-clocks-cant-be-trusted), [WhatsApp: closing the join race](designs/whatsapp/README.md#race-conditions-when-someone-joins-mid-message)
- **Also appears in:** partition leaders in replicated databases, per-driver dispatch locks in ride-hailing designs
- **Breaks when:** that single writer becomes the throughput ceiling. One writer per chat is fine; one writer for the whole system isn't.
- **Interview line:** "One sequencer per conversation means there's no second clock to disagree with."

## Durability before delivery

Write to durable storage first, then do the real-time push. A lossy push is safe as long as a durable record sits behind it.

- **Used in:** [WhatsApp: inbox write before Redis publish](designs/whatsapp/README.md#the-core-hard-problem-routing-a-message-to-an-online-recipient), [News feed: committed changes drive delivery](designs/fb-news-feed/README.md#making-the-event-pipeline-recoverable)
- **Also appears in:** any system that promises at-least-once delivery
- **Breaks when:** the durable store is down. When that happens, fail the send visibly instead of quietly dropping the message.
- **Interview line:** "The real-time hop can be lossy because the DB is the source of truth."

## TTL as absence detection

Give ephemeral state an expiry and refresh it with heartbeats. When the heartbeats stop, the key expires on its own, and that expiry is the state change.

- **Used in:** [WhatsApp: presence](designs/whatsapp/README.md#presence-and-last-seen-at-scale), [WhatsApp: registry cleanup after a server dies](designs/whatsapp/README.md#what-happens-when-a-connection-server-dies)
- **Also appears in:** distributed lock leases, session expiry, leader election
- **Breaks when:** the TTL is too long (stale state hangs around) or too short (flaky clients flap between online and offline)
- **Interview line:** "Absence is the signal. No explicit 'went offline' event needed."

## Atomic countdown barrier

To answer "has everyone finished?", keep a counter that drops to zero instead of scanning N rows.

- **Used in:** [WhatsApp: group delivery and read ticks](designs/whatsapp/README.md#group-read-receipts-the-tick-problem)
- **Also appears in:** job-completion tracking in batch pipelines
- **Breaks when:** decrements aren't idempotent (see the next pattern) or a participant leaves and their count is never decremented
- **Interview line:** "Don't scan N states on the hot path. Keep a counter and trip when the last one crosses."

## Idempotent conditional writes

Only change a row if it's still in the expected state (for example, `deliveredAt IS NULL`). Do any side effects only when that write succeeds.

- **Used in:** [WhatsApp: deduplicating retried acks](designs/whatsapp/README.md#group-read-receipts-the-tick-problem), [News feed: stable references and version-aware updates](designs/fb-news-feed/README.md#making-the-event-pipeline-recoverable)
- **Also appears in:** payment processing, exactly-once event consumers
- **Interview line:** "The row flips exactly once, so the counter decrements exactly once."

## Exponential backoff with full jitter

Double the wait after each failed retry, and pick a random point inside that wait so clients don't retry in lockstep.

- **Used in:** [WhatsApp: reconnecting after a server dies](designs/whatsapp/README.md#the-thundering-herd-and-how-jitter-fixes-it)
- **Also appears in:** nearly every retrying client in a distributed system
- **Interview line:** "Backoff protects the server. Jitter breaks the synchronization."

## Versioned membership

Don't overwrite membership. Record the version range each member belonged to, and have every message store the version it was sent under.

- **Used in:** [WhatsApp: who receives a message sent during a join](designs/whatsapp/README.md#race-conditions-when-someone-joins-mid-message)
- **Also appears in:** event sourcing, audit trails, slowly changing dimensions in data warehouses
- **Interview line:** "Every message captures its membership snapshot, so fan-out and the tick counter can't disagree."

## Event loop over thread-per-connection

Use one thread and an `epoll`/`kqueue` loop to watch many sockets. Idle connections cost memory, but they don't cost CPU.

- **Used in:** [WhatsApp: 2M sockets on one machine](designs/whatsapp/README.md#how-2-million-sockets-fit-on-one-machine)
- **Also appears in:** Nginx, Redis, Node.js
- **Interview line:** "Connections are a memory problem, not a CPU problem, once you stop using a thread per socket."

## Targeted routing vs load-sharing

To pick a messaging tool, ask whether the message has to reach one specific stateful node (use pub/sub plus a registry) or whether any worker can handle it (use Kafka consumer groups).

- **Used in:** [WhatsApp: Redis Pub/Sub vs Kafka](designs/whatsapp/README.md#redis-pubsub-vs-kafka-making-the-call)
- **Interview line:** "In Kafka, 'per-user' is a partition key, not a topic, and Kafka chooses which consumer gets it."

## Hybrid fan-out by author and reader

Prepare ordinary-author references on write, pull celebrity timelines for ordinary readers, and selectively prepare combined feeds for active readers following very many celebrities.

- **Used in:** [News feed: heavy readers](designs/fb-news-feed/README.md#what-if-i-follow-thousands-of-celebrities)
- **Breaks when:** source activity makes recipient updates too expensive, or cold rebuilds have unbounded work
- **Interview line:** "Delivery mode depends on both the author's audience and the reader's retrieval workload."

## Sorted-source merge

Keep the next item from each sorted source in a heap. Emit the largest and advance only its source, refilling buffered batches as needed.

- **Used in:** [News feed: celebrity timeline merge](designs/fb-news-feed/README.md#how-many-celebrity-posts-do-i-fetch)
- **Also appears in:** merged event streams and distributed ordered queries
- **Breaks when:** sources are incomplete or fail; a heap cannot prove the missing source has no newer item
- **Interview line:** "Each source's head bounds the items behind it, so I can select the next global item without reading every item."

## Cursor boundaries versus snapshots

A cursor continues after an immutable ordering key. A snapshot separately fixes which items belong to the session; completeness additionally needs adequate source coverage.

- **Used in:** [News feed: pagination](designs/fb-news-feed/README.md#ordering-and-cursor-pagination), [News feed: late arrivals](designs/fb-news-feed/README.md#what-happens-when-a-post-arrives-late), [Search pagination comparison](designs/fb-news-feed/README.md#google-has-page-numbers-so-why-use-cursors)
- **Breaks when:** a delayed item arrives above a boundary already traversed; continuation does not revisit it
- **Interview line:** "A stable position does not freeze membership or prove that all earlier delivery work has finished."

## Derived caches versus product state

Keep rebuildable candidate lists separate from persistent viewing history and per-session browsing position. Cache loss must not erase authoritative product behavior.

- **Used in:** [News feed: deleting read IDs](designs/fb-news-feed/README.md#why-deleting-read-ids-is-not-enough)
- **Also appears in:** unread queues, notifications, and recommendation impressions
- **Breaks when:** eviction or a replay silently changes what the product considers consumed
- **Interview line:** "Candidates, scrolling position, and seen history have different lifetimes and guarantees."

## Coordinated bounded rebuilds

Share recovery work for one missing cache entry, cap rebuild concurrency across entries, and merge with writes that arrive during recovery.

- **Used in:** [News feed: cache loss and rebuild races](designs/fb-news-feed/README.md#race-conditions-and-failure-modes)
- **Breaks when:** a broad cache outage starts unlimited authoritative reads, or a replacement cache overwrites concurrent updates
- **Interview line:** "I coordinate rebuilds per key and bound total recovery work so cache loss does not take down the source of truth."
