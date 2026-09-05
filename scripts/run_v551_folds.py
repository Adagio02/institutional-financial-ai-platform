import json
from finai.application.services.v551_fold_service import V551FoldService
if __name__ == "__main__": print(json.dumps(V551FoldService().run(), indent=2, default=str))
