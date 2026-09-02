$ErrorActionPreference = "Stop"

$ProjectRoot = (
    Resolve-Path "."
).Path

$OutputDirectory = Join-Path `
    $ProjectRoot `
    "artifacts\v45_interface_snapshot"

$OutputFile = Join-Path `
    $OutputDirectory `
    "v45_interfaces.txt"

New-Item `
    -ItemType Directory `
    -Path $OutputDirectory `
    -Force |
Out-Null

if (Test-Path $OutputFile) {
    Remove-Item `
        $OutputFile `
        -Force
}

function Add-Header {
    param(
        [string]$Title
    )

    Add-Content `
        -Path $OutputFile `
        -Value ""

    Add-Content `
        -Path $OutputFile `
        -Value (
        "=" * 80
    )

    Add-Content `
        -Path $OutputFile `
        -Value $Title

    Add-Content `
        -Path $OutputFile `
        -Value (
        "=" * 80
    )
}

function Add-File {
    param(
        [string]$RelativePath
    )

    $FullPath = Join-Path `
        $ProjectRoot `
        $RelativePath

    Add-Header `
        "FILE: $RelativePath"

    if (-not (Test-Path $FullPath)) {
        Add-Content `
            -Path $OutputFile `
            -Value "FILE NOT FOUND"

        return
    }

    Get-Content `
        $FullPath |
    Add-Content `
        -Path $OutputFile
}

function Add-Search {
    param(
        [string]$Title,
        [string]$Path,
        [string]$Pattern,
        [string]$Filter = "*.py"
    )

    Add-Header $Title

    $FullPath = Join-Path `
        $ProjectRoot `
        $Path

    if (-not (Test-Path $FullPath)) {
        Add-Content `
            -Path $OutputFile `
            -Value (
            "SEARCH PATH NOT FOUND: " +
            $Path
        )

        return
    }

    Get-ChildItem `
        -Path $FullPath `
        -Filter $Filter `
        -Recurse `
        -File |
    Select-String `
        -Pattern $Pattern |
    ForEach-Object {
        $Relative = (
            $_.Path.Substring(
                $ProjectRoot.Length
            ).TrimStart(
                "\"
            )
        )

        Add-Content `
            -Path $OutputFile `
            -Value (
            $Relative +
            ":" +
            $_.LineNumber +
            ": " +
            $_.Line.Trim()
        )
    }
}

Add-Header "V4.5 REAL INTERFACE SNAPSHOT"

Add-Content `
    -Path $OutputFile `
    -Value (
    "Generated: " +
    (Get-Date).ToString("o")
)

Add-Content `
    -Path $OutputFile `
    -Value (
    "Project: " +
    $ProjectRoot
)

Add-Content `
    -Path $OutputFile `
    -Value (
    "Branch: " +
    (
        git branch `
            --show-current
    )
)

Add-Content `
    -Path $OutputFile `
    -Value (
    "Commit: " +
    (
        git rev-parse HEAD
    )
)


# ============================================================
# FEATURE DEFINITIONS
# ============================================================

Add-File `
    "src\finai\domain\learning\v41_features.py"

Add-File `
    "src\finai\domain\learning\v421_features.py"

Add-Search `
    -Title "ALL FEATURE COLUMN DEFINITIONS" `
    -Path "src\finai" `
    -Pattern (
    "FEATURE_COLUMNS|" +
    "feature_columns|" +
    "trend_strength|" +
    "market_volatility"
)


# ============================================================
# CURRENT LEARNING SERVICES
# ============================================================

Add-File `
    "src\finai\application\services\v41_learning_service.py"

Add-File `
    "src\finai\application\services\v421_learning_service.py"

Add-File `
    "src\finai\application\services\v43_learning_service.py"

Add-File `
    "src\finai\application\services\v431_learning_service.py"

Add-File `
    "src\finai\application\services\v435_learning_service.py"

Add-File `
    "src\finai\application\services\v44_learning_service.py"

Add-File `
    "src\finai\application\services\v442_learning_service.py"

Add-File `
    "src\finai\application\services\v445_learning_service.py"

Add-File `
    "src\finai\application\services\v446_learning_service.py"

Add-File `
    "src\finai\application\services\v447_learning_service.py"


# ============================================================
# FACTORIES
# ============================================================

Add-File `
    "src\finai\application\services\v442_learning_factory.py"

Add-File `
    "src\finai\application\services\v447_learning_factory.py"


# ============================================================
# DATASET / MARKET DATA INTERFACES
# ============================================================

Add-Search `
    -Title "BUILD_DATASET DEFINITIONS" `
    -Path "src\finai" `
    -Pattern "def build_dataset"

Add-Search `
    -Title "LOAD_MARKET_BARS DEFINITIONS AND CALLS" `
    -Path "src\finai" `
    -Pattern (
    "load_market_bars|" +
    "_load_bars|" +
    "MarketBarRepository"
)

Add-Search `
    -Title "MARKET BAR CLASSES" `
    -Path "src\finai" `
    -Pattern (
    "class MarketBar|" +
    "MarketBarRepository|" +
    "market_bars"
)

Add-Search `
    -Title "INSTRUMENT CLASSES AND REPOSITORIES" `
    -Path "src\finai" `
    -Pattern (
    "InstrumentRepository|" +
    "class Instrument|" +
    "instrument_id"
)


# ============================================================
# REPOSITORIES
# ============================================================

$RepositoryFiles = Get-ChildItem `
    -Path (
    Join-Path `
        $ProjectRoot `
        "src\finai"
) `
    -Filter "*.py" `
    -Recurse `
    -File |
Select-String `
    -Pattern (
    "class .*MarketBar.*Repository|" +
    "class .*Instrument.*Repository"
) |
Select-Object `
    -ExpandProperty Path `
    -Unique

foreach ($RepositoryFile in $RepositoryFiles) {
    $Relative = (
        $RepositoryFile.Substring(
            $ProjectRoot.Length
        ).TrimStart(
            "\"
        )
    )

    Add-File $Relative
}


# ============================================================
# MARKET BAR MODEL FILES
# ============================================================

$MarketBarFiles = Get-ChildItem `
    -Path (
    Join-Path `
        $ProjectRoot `
        "src\finai"
) `
    -Filter "*.py" `
    -Recurse `
    -File |
Select-String `
    -Pattern (
    "class MarketBar|" +
    "__tablename__.*market_bars"
) |
Select-Object `
    -ExpandProperty Path `
    -Unique

foreach ($MarketBarFile in $MarketBarFiles) {
    $Relative = (
        $MarketBarFile.Substring(
            $ProjectRoot.Length
        ).TrimStart(
            "\"
        )
    )

    Add-File $Relative
}


# ============================================================
# INSTRUMENT MODEL FILES
# ============================================================

$InstrumentFiles = Get-ChildItem `
    -Path (
    Join-Path `
        $ProjectRoot `
        "src\finai"
) `
    -Filter "*.py" `
    -Recurse `
    -File |
Select-String `
    -Pattern (
    "class Instrument|" +
    "__tablename__.*instruments"
) |
Select-Object `
    -ExpandProperty Path `
    -Unique

foreach ($InstrumentFile in $InstrumentFiles) {
    $Relative = (
        $InstrumentFile.Substring(
            $ProjectRoot.Length
        ).TrimStart(
            "\"
        )
    )

    Add-File $Relative
}


# ============================================================
# RESEARCH / BACKTEST INTERFACES
# ============================================================

Add-File `
    "src\finai\domain\learning\v44_research.py"

Add-File `
    "src\finai\domain\learning\v445_research.py"

Add-Search `
    -Title "MODEL TEMPLATE METHODS" `
    -Path "src\finai" `
    -Pattern (
    "def create_model_templates|" +
    "create_model_templates\("
)

Add-Search `
    -Title "MODEL EVALUATION METHODS" `
    -Path "src\finai" `
    -Pattern (
    "def evaluate_model|" +
    "def evaluate_holdout|" +
    "evaluate_model\(|" +
    "evaluate_holdout\("
)

Add-Search `
    -Title "BACKTEST METHODS" `
    -Path "src\finai" `
    -Pattern (
    "simulate\(|" +
    "def simulate|" +
    "non_overlapping|" +
    "round_trip_cost"
)


# ============================================================
# TARGET / GOVERNANCE ATTRIBUTES
# ============================================================

Add-Search `
    -Title "TARGET CONFIGURATION ATTRIBUTES" `
    -Path "src\finai" `
    -Pattern (
    "_forward_horizon_bars|" +
    "_target_minimum_edge_bps|" +
    "_minimum_edge_bps"
)

Add-Search `
    -Title "GOVERNANCE ATTRIBUTES" `
    -Path "src\finai" `
    -Pattern (
    "_minimum_trades|" +
    "_minimum_positive_fold_fraction|" +
    "_minimum_balanced_accuracy|" +
    "_minimum_macro_f1|" +
    "_maximum_holdout_drawdown"
)


# ============================================================
# V4.4.7 ARTIFACT STRUCTURE
# ============================================================

$V447Artifact = Join-Path `
    $ProjectRoot `
    "artifacts\v447\v447_requalification.json"

Add-Header "V4.4.7 ARTIFACT"

if (Test-Path $V447Artifact) {
    Get-Content `
        $V447Artifact |
    Add-Content `
        -Path $OutputFile
}
else {
    Add-Content `
        -Path $OutputFile `
        -Value "V4.4.7 ARTIFACT NOT FOUND"
}


# ============================================================
# V4.4.6 ARTIFACT STRUCTURE
# ============================================================

$V446Artifact = Join-Path `
    $ProjectRoot `
    "artifacts\v446\v446_focused_discovery.json"

Add-Header "V4.4.6 ARTIFACT"

if (Test-Path $V446Artifact) {
    Get-Content `
        $V446Artifact |
    Add-Content `
        -Path $OutputFile
}
else {
    Add-Content `
        -Path $OutputFile `
        -Value "V4.4.6 ARTIFACT NOT FOUND"
}


# ============================================================
# DATABASE SCHEMA FROM POSTGRES
# Best-effort only. Database inspection must never prevent
# collection of the Python interfaces required for V4.5.
# ============================================================

Add-Header "POSTGRES DATABASE DISCOVERY"

$PostgresService = "postgres"
$PostgresUser = $null
$PostgresDatabase = $null

try {
    $ContainerEnvironment = @(
        docker compose exec `
            -T `
            $PostgresService `
            env `
            2>$null
    )

    foreach ($Line in $ContainerEnvironment) {
        if (
            $Line -match "^POSTGRES_USER=(.+)$"
        ) {
            $PostgresUser = $Matches[1]
        }

        if (
            $Line -match "^POSTGRES_DB=(.+)$"
        ) {
            $PostgresDatabase = $Matches[1]
        }
    }

    Add-Content `
        -Path $OutputFile `
        -Value (
        "Postgres service: " +
        $PostgresService
    )

    Add-Content `
        -Path $OutputFile `
        -Value (
        "Postgres user discovered: " +
        $PostgresUser
    )

    Add-Content `
        -Path $OutputFile `
        -Value (
        "Postgres database discovered: " +
        $PostgresDatabase
    )
}
catch {
    Add-Content `
        -Path $OutputFile `
        -Value (
        "Database environment discovery failed: " +
        $_.Exception.Message
    )
}


# ============================================================
# DATABASE SCHEMA
# ============================================================

Add-Header "POSTGRES MARKET TABLE SCHEMA"

if (
    -not [string]::IsNullOrWhiteSpace(
        $PostgresUser
    ) -and
    -not [string]::IsNullOrWhiteSpace(
        $PostgresDatabase
    )
) {
    $SchemaQuery = @"
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN (
      'market_bars',
      'instruments'
  )
ORDER BY
    table_name,
    ordinal_position;
"@

    try {
        $SchemaOutput = @(
            $SchemaQuery |
            docker compose exec `
                -T `
                $PostgresService `
                psql `
                -U $PostgresUser `
                -d $PostgresDatabase `
                2>&1
        )

        $SchemaOutput |
        Add-Content `
            -Path $OutputFile
    }
    catch {
        Add-Content `
            -Path $OutputFile `
            -Value (
            "OPTIONAL DATABASE SCHEMA QUERY FAILED: " +
            $_.Exception.Message
        )
    }
}
else {
    Add-Content `
        -Path $OutputFile `
        -Value (
        "Database schema query skipped because " +
        "POSTGRES_USER/POSTGRES_DB could not be discovered."
    )
}


# ============================================================
# SYMBOL COUNTS / DATE RANGES
# ============================================================

Add-Header "AVAILABLE MARKET DATA"

if (
    -not [string]::IsNullOrWhiteSpace(
        $PostgresUser
    ) -and
    -not [string]::IsNullOrWhiteSpace(
        $PostgresDatabase
    )
) {
    $DataQuery = @"
SELECT
    i.symbol,
    mb.interval,
    COUNT(*) AS bar_count,
    MIN(mb.timestamp) AS first_bar,
    MAX(mb.timestamp) AS last_bar
FROM market_bars mb
JOIN instruments i
    ON i.id = mb.instrument_id
WHERE i.symbol IN (
    'AAPL',
    'SPY',
    'QQQ'
)
GROUP BY
    i.symbol,
    mb.interval
ORDER BY
    i.symbol,
    mb.interval;
"@

    try {
        $DataOutput = @(
            $DataQuery |
            docker compose exec `
                -T `
                $PostgresService `
                psql `
                -U $PostgresUser `
                -d $PostgresDatabase `
                2>&1
        )

        $DataOutput |
        Add-Content `
            -Path $OutputFile
    }
    catch {
        Add-Content `
            -Path $OutputFile `
            -Value (
            "OPTIONAL MARKET DATA QUERY FAILED: " +
            $_.Exception.Message
        )
    }
}
else {
    Add-Content `
        -Path $OutputFile `
        -Value (
        "Market-data SQL query skipped because " +
        "POSTGRES_USER/POSTGRES_DB could not be discovered."
    )
}


# ============================================================
# PYTHON RUNTIME INTROSPECTION
# ============================================================

Add-Header "PYTHON SERVICE INTROSPECTION"

$PythonCode = @'
import inspect

from finai.core.config import get_settings
from finai.application.services.v447_learning_factory import (
    build_v447_learning_service,
)

settings = get_settings()

service = build_v447_learning_service(
    settings=settings,
)

print(
    "SERVICE_CLASS:",
    type(service).__name__,
)

print(
    "MRO:"
)

for cls in type(service).__mro__:
    print(
        "  ",
        cls.__module__,
        cls.__name__,
    )

attributes = [
    "_forward_horizon_bars",
    "_target_minimum_edge_bps",
    "_minimum_edge_bps",
    "_minimum_trades",
    "_minimum_positive_fold_fraction",
    "_minimum_balanced_accuracy",
    "_minimum_macro_f1",
    "_maximum_holdout_drawdown",
    "_v41_round_trip_cost_bps",
]

print(
    "\nATTRIBUTES:"
)

for name in attributes:
    print(
        name,
        "=",
        getattr(
            service,
            name,
            "MISSING",
        ),
    )

methods = [
    "build_dataset",
    "load_market_bars",
    "create_model_templates",
    "evaluate_model",
    "evaluate_holdout",
    "positions_from_probabilities",
]

print(
    "\nMETHOD SIGNATURES:"
)

for name in methods:
    method = getattr(
        service,
        name,
        None,
    )

    if method is None:
        print(
            name,
            "= MISSING",
        )
        continue

    try:
        signature = inspect.signature(
            method
        )
    except Exception as exc:
        signature = (
            f"<signature error: {exc}>"
        )

    print(
        name,
        signature,
    )

    try:
        print(
            "defined_in =",
            inspect.getfile(
                method
            ),
        )
    except Exception as exc:
        print(
            "defined_in =",
            f"<unknown: {exc}>",
        )

print(
    "\nMODEL TEMPLATES:"
)

models = service.create_model_templates()

for name, model in models.items():
    print(
        name,
        "=>",
        type(model).__module__,
        type(model).__name__,
    )
'@

$PythonCode |
python - 2>&1 |
Add-Content `
    -Path $OutputFile


# ============================================================
# DATASET INTROSPECTION
# ============================================================

Add-Header "AAPL DATASET INTROSPECTION"

$DatasetCode = @'
from finai.core.config import get_settings
from finai.application.services.v447_learning_factory import (
    build_v447_learning_service,
)

service = build_v447_learning_service(
    settings=get_settings(),
)

dataset, rows_loaded = service.build_dataset(
    symbol="AAPL",
    interval="1m",
    include_target=True,
)

print(
    "rows_loaded =",
    rows_loaded,
)

print(
    "dataset_rows =",
    len(dataset),
)

print(
    "columns:"
)

for column in dataset.columns:
    print(
        "  ",
        column,
        "=>",
        dataset[column].dtype,
    )

print(
    "\nfirst_timestamp =",
    dataset.index.min(),
)

print(
    "last_timestamp =",
    dataset.index.max(),
)

if "target" in dataset.columns:
    print(
        "\ntarget_counts:"
    )

    print(
        dataset["target"]
        .value_counts(
            dropna=False
        )
        .sort_index()
    )
'@

$DatasetCode |
python - 2>&1 |
Add-Content `
    -Path $OutputFile


# ============================================================
# RAW MARKET BAR INTROSPECTION
# ============================================================

Add-Header "RAW AAPL MARKET BAR INTROSPECTION"

$BarCode = @'
import inspect

from finai.core.config import get_settings
from finai.application.services.v447_learning_factory import (
    build_v447_learning_service,
)

service = build_v447_learning_service(
    settings=get_settings(),
)

loader = getattr(
    service,
    "load_market_bars",
    None,
)

if loader is None:
    print(
        "load_market_bars = MISSING"
    )
else:
    print(
        "signature =",
        inspect.signature(
            loader
        ),
    )

    try:
        bars = loader(
            symbol="AAPL",
            interval="1m",
        )

        print(
            "type =",
            type(bars),
        )

        try:
            print(
                "length =",
                len(bars),
            )
        except Exception:
            pass

        if hasattr(
            bars,
            "columns",
        ):
            print(
                "columns =",
                list(
                    bars.columns
                ),
            )

            print(
                "dtypes:"
            )

            print(
                bars.dtypes
            )

            print(
                "head:"
            )

            print(
                bars.head(3)
            )
        else:
            print(
                "sample =",
                repr(
                    bars[:3]
                    if hasattr(
                        bars,
                        "__getitem__",
                    )
                    else bars
                ),
            )

    except TypeError as exc:
        print(
            "CALL_REQUIRES_DIFFERENT_ARGUMENTS:",
            exc,
        )
'@

$BarCode |
python - 2>&1 |
Add-Content `
    -Path $OutputFile


# ============================================================
# GIT STATUS
# ============================================================

Add-Header "GIT STATUS"

git status `
    --short |
Add-Content `
    -Path $OutputFile


# ============================================================
# FINISH
# ============================================================

Add-Header "SNAPSHOT COMPLETE"

Add-Content `
    -Path $OutputFile `
    -Value (
    "Output file: " +
    $OutputFile
)

Write-Host ""
Write-Host "V4.5 interface snapshot created:"
Write-Host $OutputFile
Write-Host ""
Write-Host "Size:"
Get-Item $OutputFile |
Select-Object `
    FullName, `
    Length