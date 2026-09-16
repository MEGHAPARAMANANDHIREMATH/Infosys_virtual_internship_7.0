from agents.constants import NOT_SPECIFIED


class BaseAgent:
    name = "base"
    prompt_schema = ""

    def analyze(self, document_text: str, metadata: dict | None = None) -> dict:
        raise NotImplementedError

    def build_prompt(self, document_text: str, metadata: dict | None = None) -> str:
        clipped = document_text if len(document_text) <= 14000 else document_text[:14000]
        return (
            f"{self.prompt_schema}\n\n"
            f"Document file name: {metadata_name(metadata)}\n"
            f"DOCUMENT TEXT:\n{clipped}\n"
        )


def missing_overview():
    return {
        "project_name": NOT_SPECIFIED,
        "objective": NOT_SPECIFIED,
        "scope": NOT_SPECIFIED,
        "start_date": NOT_SPECIFIED,
        "end_date": NOT_SPECIFIED,
        "responsibilities": [],
        "tasks": [],
        "deliverables": [],
        "milestones": [],
        "dependencies": [],
    }


def metadata_name(metadata: dict | None) -> str:
    if not metadata:
        return ""
    return metadata.get("file_name") or ""
