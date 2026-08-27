# FinAI V4.2 Interview Guide

## Project

FinAI is a quantitative machine-learning research and
paper-execution platform built around strict model governance.

The system is designed to avoid declaring a model successful
based only on an in-sample or single backtest result.

## Architecture

Market data is ingested for the target instrument together
with SPY and QQQ market context.

The learning system performs:

- multi-market feature engineering
- cost-aware target construction
- regime-aware modeling
- purged walk-forward evaluation
- probability-threshold calibration
- transaction-cost-aware simulation
- untouched holdout evaluation
- candidate/champion governance
- prospective shadow validation

## V4.1

V4.1 improves signal quality with:

- momentum over multiple horizons
- volatility-normalized momentum
- ATR and range-state features
- abnormal-volume features
- VWAP displacement
- trend persistence
- SPY/QQQ relative strength
- rolling beta and correlation
- market regime context
- time-of-day features
- cost-aware target labels

## V4.2

V4.2 adds the operational and presentation layer.

It includes:

- an R/Shiny dashboard
- ggplot2 research visualization
- model comparison
- walk-forward fold visualization
- holdout metrics
- model-governance status
- Docker packaging
- automatic Windows startup
- automatic Visual Studio Code launch
- autonomous supervisor startup

## Model governance

The model lifecycle is:

candidate
→ historical validation
→ shadow candidate
→ prospective validation
→ champion
→ paper execution

A failed candidate is retained as research evidence rather
than forcibly promoted.

## Safety

Live-money execution is intentionally outside the V4.2
portfolio release.

The interview/demo system operates in research, shadow,
and paper modes.