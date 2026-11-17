"""Bounded unauthenticated GETs for documented ATS endpoints and hosted job pages."""

from dataclasses import dataclass
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from .models import canonical_url

AGENT = "CareerDiscoveryPrototype/0.1"
ATS_HOSTS = {
    "boards-api.greenhouse.io", "boards.greenhouse.io", "job-boards.greenhouse.io", "job-boards.eu.greenhouse.io",
    "api.ashbyhq.com", "jobs.ashbyhq.com",
}
API_HOSTS = {"boards-api.greenhouse.io", "api.ashbyhq.com"}
REDIRECT = {301, 302, 303, 307, 308}
MAX_BODY = 8 * 1024 * 1024


@dataclass(frozen=True)
class Response:
    status: int
    url: str
    body: bytes
    location: str = ""


class NetworkUnavailable(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PublicHTTP:
    def __init__(self, *, budget=45, timeout=8):
        self.budget = budget
        self.timeout = timeout
        self.calls = 0
        self.opener = build_opener(ProxyHandler({}), NoRedirect())
        self.policies = {}
        self.delays = {}
        self.last_request = {}
        self.blocked = {}

    def _once(self, url, max_bytes):
        host = urlsplit(url).hostname
        if host in self.blocked:
            raise NetworkUnavailable(self.blocked[host])
        if self.calls >= self.budget:
            raise NetworkUnavailable("Public request budget reached for this command.")
        delay = self.delays.get(host, 1.0)
        if delay > 15:
            raise NetworkUnavailable("The source asks for a longer delay than this run supports.")
        pending = delay - (time.monotonic() - self.last_request.get(host, 0))
        if pending > 0:
            time.sleep(pending)
        self.calls += 1
        self.last_request[host] = time.monotonic()
        request = Request(url, headers={"User-Agent": AGENT, "Accept": "*/*"})
        try:
            with self.opener.open(request, timeout=self.timeout) as stream:
                body = stream.read(max_bytes + 1)
                if len(body) > max_bytes:
                    raise NetworkUnavailable("Public response exceeded the size limit.")
                return Response(stream.status, url, body)
        except HTTPError as exc:
            try:
                if exc.code == 429:
                    self.blocked[host] = "The source returned HTTP 429. No further requests were made to this host."
                return Response(exc.code, url, b"", exc.headers.get("Location", ""))
            finally:
                exc.close()
        except (TimeoutError, URLError, OSError) as exc:
            raise NetworkUnavailable(f"Public request failed for {host}: {exc}") from exc

    def _policy(self, host):
        if host in self.policies:
            return self.policies[host]
        try:
            response = self._follow(f"https://{host}/robots.txt", consult_policy=False, max_bytes=512 * 1024)
        except NetworkUnavailable:
            self.policies[host] = "unreachable"
            raise
        if response.status in {404, 410}:
            policy = "absent"
        elif host == "api.ashbyhq.com" and response.status == 401:
            # RFC 9309 permits reads when robots.txt is unavailable. Limit this
            # exception to Ashby's documented unauthenticated job-board route.
            policy = "ashby_public_api_only"
        elif response.status == 200:
            policy = RobotFileParser()
            policy.parse(response.body.decode("utf-8", errors="replace").splitlines())
            delay = policy.crawl_delay(AGENT) or 1
            rate = policy.request_rate(AGENT)
            if rate and rate.requests:
                delay = max(delay, rate.seconds / rate.requests)
            self.delays[host] = max(1, delay)
        else:
            policy = "unreachable"
        self.policies[host] = policy
        return policy

    def _follow(self, url, *, consult_policy, max_bytes):
        for _ in range(6):
            url = canonical_url(url)
            parts = urlsplit(url)
            host = parts.hostname
            if host not in ATS_HOSTS:
                raise NetworkUnavailable("Destination is outside the supported ATS hosts.")
            if consult_policy:
                policy = self._policy(host)
                if isinstance(policy, RobotFileParser):
                    allowed = policy.can_fetch(AGENT, url)
                else:
                    allowed = policy == "absent" or (
                        policy == "ashby_public_api_only" and parts.path.startswith("/posting-api/job-board/")
                    )
                if not allowed:
                    raise NetworkUnavailable(f"Robots policy did not allow this request to {host}.")
            response = self._once(url, max_bytes)
            if response.status not in REDIRECT or not response.location:
                return response
            url = urljoin(url, response.location)
        raise NetworkUnavailable("Public request exceeded the redirect limit.")

    def get(self, url, max_bytes=MAX_BODY):
        return self._follow(url, consult_policy=True, max_bytes=max_bytes)
