# Blog queue

Pre-written posts waiting to publish, one per day, via the daily-blog workflow
(`scripts/blog/publish_from_queue.py`). The lowest-numbered file publishes next;
when the queue is empty the workflow goes back to generating posts.

- `NN-<slug>.json`: a `render_post` payload (`body_html`, `references`, product CTA fields).
  `date` is set at publish time.
- `images/blog-<slug>-*.jpg`: moved to `/optimized` when the post publishes.

To reorder, rename the number prefixes. To pull a post, delete its JSON and images.
This folder is excluded from deploys (`.vercelignore`).
