import os

import redis
from rq import Queue, Retry

from worker.ids import repo_hash

redis_conn = redis.from_url(os.environ["REDIS_URL"])
HOT_VENDORS = ("stripe", "twilio")
queues = {v: Queue(v, connection=redis_conn) for v in HOT_VENDORS}
queues["default"] = Queue("default", connection=redis_conn)


def enqueue_scan(repo_url: str, vendor: str) -> str:
    q = queues.get(vendor, queues["default"])
    job_id = f"scan-{repo_hash(repo_url)}-{vendor}"
    q.enqueue("worker.tasks.run_scan", repo_url, vendor, job_id=job_id,
              job_timeout=600, retry=Retry(max=3, interval=[10, 60, 300]))
    return job_id
