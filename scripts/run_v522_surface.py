import json

from finai.application.services.v522_surface_service import V522SurfaceService


if __name__ == "__main__":
    print(json.dumps(V522SurfaceService().run(), indent=2, default=str))

