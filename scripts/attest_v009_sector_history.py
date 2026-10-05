import argparse,hashlib,json
from pathlib import Path
import pandas as pd
p=argparse.ArgumentParser();p.add_argument("--universe",required=True);p.add_argument("--source",required=True);p.add_argument("--verified-by",required=True);p.add_argument("--output",required=True);a=p.parse_args()
path=Path(a.universe);frame=pd.read_csv(path);required={"symbol","sector","effective_from","effective_to","classification_provenance"}
missing=required.difference(frame.columns)
if missing:raise ValueError(f"Universe missing {sorted(missing)}")
bad=frame.classification_provenance.astype(str).str.contains("unverified|seed",case=False,regex=True)
if bad.any():raise RuntimeError(f"{int(bad.sum())} rows remain seed/unverified; replace provenance only after checking the cited dated source")
if not a.source.strip():raise ValueError("A dated authoritative source reference is required")
result={"verified":True,"verified_by":a.verified_by,"source":a.source,"verified_utc":pd.Timestamp.now(tz="UTC").isoformat(),
 "universe_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"rows":len(frame),"symbols":frame.symbol.nunique(),"sectors":frame.sector.nunique()}
out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2),encoding="utf-8");print(json.dumps(result,indent=2))
