from typing import Dict, List

from .models import ScraperJob


PIPELINES: Dict[str, List[str]] = {
    "rankings_full": [
        "rankings_webometrics",
        "rankings_shanghai_urap",
        "rankings_greenmetric",
        "rankings_leiden",
        "rankings_engirank",
        "rankings_scholargps",
    ],
    "grants_full": ["grants_all"],
    "sustainability_full": ["sustainability_itu_news"],
    "all_full": [
        "rankings_webometrics",
        "rankings_shanghai_urap",
        "rankings_greenmetric",
        "rankings_leiden",
        "rankings_engirank",
        "rankings_scholargps",
        "grants_all",
        "sustainability_itu_news",
    ],
}


def ordered_jobs_with_dependencies(jobs: Dict[str, ScraperJob], requested_ids: List[str]) -> List[ScraperJob]:
    ordered: List[ScraperJob] = []
    visited = set()
    visiting = set()

    def visit(job_id: str) -> None:
        if job_id in visited:
            return
        if job_id in visiting:
            raise ValueError(f"Circular dependency detected at: {job_id}")
        job = jobs.get(job_id)
        if job is None:
            raise ValueError(f"Unknown job id: {job_id}")

        visiting.add(job_id)
        for dep in job.dependencies:
            visit(dep)
        visiting.remove(job_id)

        visited.add(job_id)
        ordered.append(job)

    for requested in requested_ids:
        visit(requested)

    return ordered
