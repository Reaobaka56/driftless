from locust import HttpUser, between, task


class DriftlessUser(HttpUser):
    wait_time = between(1, 5)

    @task(10)
    def read_registry(self):
        self.client.get("/api/registry?vendor=stripe")

    @task(1)
    def enqueue_scan(self):
        self.client.post("/scan", json={"repo_url": "https://github.com/example/repo", "vendor": "stripe"})
