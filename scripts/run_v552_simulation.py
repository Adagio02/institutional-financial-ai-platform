import json
from finai.application.services.v552_simulation_service import V552SimulationService
if __name__ == "__main__": print(json.dumps(V552SimulationService().run(), indent=2, default=str))
