from __future__ import annotations
from io import BytesIO
from zipfile import ZipFile
import httpx
import pandas as pd

class FrenchFactorConnector:
    daily_5_factor_url = (
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip"
    )

    def fetch_daily_five_factor(self) -> pd.DataFrame:
        response = httpx.get(self.daily_5_factor_url, timeout=60, follow_redirects=True)
        response.raise_for_status()
        with ZipFile(BytesIO(response.content)) as archive:
            name = archive.namelist()[0]
            raw = archive.read(name).decode("utf-8", errors="replace")
        lines = raw.splitlines()
        start = next(i for i, line in enumerate(lines) if line.strip().startswith(",Mkt-RF"))
        end = next(i for i in range(start + 1, len(lines)) if not lines[i].strip())
        from io import StringIO
        frame = pd.read_csv(StringIO("\n".join(lines[start:end])))
        frame = frame.rename(columns={frame.columns[0]: "date"})
        frame["date"] = pd.to_datetime(frame["date"].astype(str), format="%Y%m%d")
        numeric = [c for c in frame.columns if c != "date"]
        frame[numeric] = frame[numeric] / 100.0
        return frame
