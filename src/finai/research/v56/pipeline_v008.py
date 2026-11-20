from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from .core import Config, config_dict, normalize, numeric_features, read_frame, sha256, write_frame, write_json
from .models import fit_predict_residual_ranked
from .portfolio import metrics
from .portfolio_v007 import simulate_v007
from .validation import audit, folds


def _residualize_target(section: pd.DataFrame) -> pd.Series:
    result = pd.Series(np.nan, index=section.index, dtype=float)
    valid = section.forward_return.notna() & section.beta.notna() & section.sector.notna()
    sample = section.loc[valid]
    if len(sample) < 10: return result
    dummies = pd.get_dummies(sample.sector, drop_first=False, dtype=float)
    design = np.column_stack([dummies.to_numpy(), sample.beta.to_numpy(float)])
    y = sample.forward_return.to_numpy(float)
    coefficient = np.linalg.lstsq(design, y, rcond=None)[0]
    result.loc[sample.index] = y - design @ coefficient
    return result


def _rank_ic(section: pd.DataFrame, target: str) -> float:
    pair = section[["ensemble", target]].dropna()
    if len(pair)<4 or pair.ensemble.nunique()<2 or pair[target].nunique()<2:return np.nan
    return float(pair.ensemble.corr(pair[target], method="spearman"))


def run_v008(input_path: str, output_dir: str, cfg: Config) -> dict:
    output=Path(output_dir);output.mkdir(parents=True,exist_ok=True)
    frame=normalize(read_frame(input_path),cfg)
    frame["forward_residual_return"] = frame.groupby("timestamp",group_keys=False,observed=True).apply(
        _residualize_target, include_groups=False
    ).reset_index(level=0,drop=True).reindex(frame.index)
    candidates=numeric_features(frame);fold_list=list(folds(frame,cfg))
    if len(fold_list)<2:raise RuntimeError("Fewer than two purged walk-forward folds")
    first=fold_list[0][1]
    features=[c for c in candidates if first[c].notna().mean()>=.60 and first[c].nunique(dropna=True)>=10]
    excluded=sorted(set(candidates)-set(features))
    audit_report=audit(frame,features,cfg);audit_report["excluded_low_coverage_features"]=excluded
    audit_report["target"]="cross-sectional residual of forward return on sector indicators and lagged beta"
    write_json(output/"audit.json",audit_report)
    pieces=[]
    for fold_id,train,test in fold_list:
        part=fit_predict_residual_ranked(train,test,features,cfg.seed+fold_id);part["fold"]=fold_id;pieces.append(part)
    pred=pd.concat(pieces,ignore_index=True)
    def combine(section):
        result=section.copy();ic=np.array([result.elastic_calibration_ic.iloc[0],result.tree_calibration_ic.iloc[0]],float)
        weight=np.maximum(ic-cfg.ic_floor,0.)
        result["ensemble"]=0. if weight.sum()==0 else result[["elastic","tree"]].to_numpy()@(weight/weight.sum())
        return result
    pred=pred.groupby("fold",group_keys=False,observed=True).apply(combine).reset_index(drop=True)
    pred_path=write_frame(pred,output/"oos_predictions.parquet")
    ledger,positions=simulate_v007(pred,cfg)
    ledger_path=write_frame(ledger,output/"ledger.parquet");positions_path=write_frame(positions,output/"positions.parquet")
    result_metrics=metrics(ledger, cfg.rebalance_every)
    rebalance=pred[pred.timestamp.isin(ledger.timestamp)]
    residual_ic=rebalance.groupby("timestamp",observed=True).apply(
        lambda section:_rank_ic(section,"forward_residual_return"),include_groups=False
    ).dropna()
    raw_ic=rebalance.groupby("timestamp",observed=True).apply(
        lambda section:_rank_ic(section,"forward_return"),include_groups=False
    ).dropna()
    active=float((ledger.construction_status=="active").mean())
    gross=float((1+ledger.gross_return).prod()-1)
    checks={
        "minimum_periods":len(ledger)>=52,"active_fraction":active>=.80,
        "positive_residual_rank_ic":float(residual_ic.mean())>0,
        "positive_gross_return":gross>0,"positive_net_return":result_metrics["cumulative_net_return"]>0,
        "minimum_sharpe":result_metrics["annualized_sharpe"]>=.25,
        "maximum_drawdown":result_metrics["maximum_drawdown"]>=-.30,
        "maximum_turnover":float(ledger.turnover.max())<=cfg.rebalance_turnover_limit+.005,
        "beta_band":float(ledger.beta_exposure.abs().max())<=cfg.beta_exposure_limit+1e-8,
    }
    passed=all(checks.values())
    report={
        "version":"5.6-research-008","research_only":True,"development_window_previously_observed":True,
        "eligible_to_freeze_candidate":passed,"not_eligible_for_v57_without_new_lock":True,
        "target_definition":"forward return residualized cross-sectionally by sector and lagged beta",
        "config":config_dict(cfg),"features":features,"excluded_features":excluded,
        "mean_rebalance_residual_rank_ic":float(residual_ic.mean()),"mean_rebalance_raw_rank_ic":float(raw_ic.mean()),
        "active_fraction":active,"gross_compounded_return":gross,
        "construction_status_counts":ledger.construction_status.value_counts().to_dict(),
        "metrics":result_metrics,"checks":checks,
        "artifacts":{"predictions":str(pred_path),"ledger":str(ledger_path),"positions":str(positions_path)},
        "hashes":{p.name:sha256(p) for p in (pred_path,ledger_path,positions_path)},
        "blocking_reasons":[k for k,v in checks.items() if not v],
        "required_next_step":"If all gates pass, freeze V008 and run once on genuinely unseen locked V5.6 data before V5.7.",
    }
    write_json(output/"research_report.json",report);return report
