import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("--protocol",required=True);p.add_argument("--locked-report",required=True);p.add_argument("--sector-attestation",required=True);a=p.parse_args()
protocol=json.loads(Path(a.protocol).read_text());report=json.loads(Path(a.locked_report).read_text());attestation=json.loads(Path(a.sector_attestation).read_text())
decision=report.get("decision",report);metrics=report.get("metrics",{})
checks={
 "real_data":bool(decision.get("verified_real_data") or report.get("verified_real_data")),
 "sector_provenance_verified":bool(attestation.get("verified")) and attestation.get("universe_sha256")==protocol.get("universe_sha256"),
 "validation_passed":bool(decision.get("validation_passed") or report.get("validation_passed")),
 "eligible_for_v57":bool(decision.get("eligible_for_v57_untouched_final_test") or report.get("eligible_for_v57_untouched_final_test")),
 "single_execution":int(report.get("execution_count",1))==1,
 "minimum_periods":int(metrics.get("period_count",0))>=int(protocol["locked_rules"]["minimum_periods"]),
 "positive_return":float(metrics.get("cumulative_net_return",-1))>0,
 "minimum_sharpe":float(metrics.get("annualized_sharpe",-999))>=float(protocol["locked_rules"]["minimum_sharpe"]),
 "drawdown":float(metrics.get("maximum_drawdown",-999))>=float(protocol["locked_rules"]["maximum_drawdown"]),
}
print(json.dumps({"v57_unlocked":all(checks.values()),"checks":checks},indent=2));sys.exit(0 if all(checks.values()) else 2)
