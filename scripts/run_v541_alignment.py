import json
from finai.application.services.v541_alignment_service import V541AlignmentService

if __name__ == "__main__":
    print(json.dumps(V541AlignmentService().run(), indent=2, default=str))

