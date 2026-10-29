
import json
from pathlib import Path

from src.schemas.research_plan import ResearchPlan
from src.schemas.evidence import EvidenceRecord
from src.schemas.final_report import FinalResearchReport


OUTPUT_DIR = Path("schemas")
OUTPUT_DIR.mkdir(exist_ok=True)

models = {
    "research_plan.schema.json": ResearchPlan,
    "evidence_record.schema.json": EvidenceRecord,
    "final_report.schema.json": FinalResearchReport,
}

for filename, model in models.items():
    schema = model.model_json_schema()
    output_path = OUTPUT_DIR / filename
    output_path.write_text(
        json.dumps(schema, indent=2),
        encoding="utf-8",
    )
    print(f"Exported {output_path}")
