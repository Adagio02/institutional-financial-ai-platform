from __future__ import annotations
import httpx
from finai.core.config import get_settings


class SecConnector:
    base = "https://data.sec.gov"

    def _headers(self) -> dict[str, str]:
        user_agent = get_settings().sec_user_agent
        if "@" not in user_agent:
            raise RuntimeError("SEC_USER_AGENT must contain a contact email")
        return {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}

    def submissions(self, cik: str) -> dict:
        normalized = str(cik).zfill(10)
        response = httpx.get(
            f"{self.base}/submissions/CIK{normalized}.json",
            headers=self._headers(),
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    def company_facts(self, cik: str) -> dict:
        normalized = str(cik).zfill(10)
        response = httpx.get(
            f"{self.base}/api/xbrl/companyfacts/CIK{normalized}.json",
            headers=self._headers(),
            timeout=60,
        )
        response.raise_for_status()
        return response.json()
