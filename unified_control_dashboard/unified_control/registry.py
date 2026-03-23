from pathlib import Path
from typing import Dict

from .models import ScraperJob


def build_jobs(repo_root: Path, python_executable: str) -> Dict[str, ScraperJob]:
    cwd = repo_root

    jobs = [
        ScraperJob(
            id="rankings_webometrics",
            name="Webometrics",
            category="rankings",
            description="Webometrics Turkey ranking scraper",
            command=[python_executable, "scrapers/rankings/scraper_webometrics.py"],
            cwd=cwd,
            expected_outputs=["data/raw/webometrics_*.csv", "data/raw/webometrics_*.xlsx"],
        ),
        ScraperJob(
            id="rankings_shanghai_urap",
            name="Shanghai + URAP",
            category="rankings",
            description="Shanghai ARWU and URAP combined scraper",
            command=[python_executable, "scrapers/rankings/shanghai_urap_scraper.py"],
            cwd=cwd,
            expected_outputs=["data/raw/Shanghai_ARWU_Turkey_*.xlsx", "data/raw/URAP_Turkey_*.xlsx"],
            dependencies=["rankings_webometrics"],
        ),
        ScraperJob(
            id="rankings_greenmetric",
            name="GreenMetric",
            category="rankings",
            description="UI GreenMetric Turkey scraper",
            command=[python_executable, "scrapers/rankings/scraper_greenmetric.py"],
            cwd=cwd,
            expected_outputs=["output/greenmetric_turkey_*.json"],
            dependencies=["rankings_shanghai_urap"],
        ),
        ScraperJob(
            id="rankings_leiden",
            name="Leiden",
            category="rankings",
            description="Leiden ranking scraper",
            command=[python_executable, "scrapers/rankings/scraper_leiden.py"],
            cwd=cwd,
            expected_outputs=["output/leiden_turkey_*.json"],
            dependencies=["rankings_greenmetric"],
        ),
        ScraperJob(
            id="rankings_engirank",
            name="EngiRank",
            category="rankings",
            description="EngiRank Turkey scraper",
            command=[python_executable, "scrapers/rankings/engirank_scraper.py"],
            cwd=cwd,
            expected_outputs=["data/raw/engirank_turkiye_*.json", "data/raw/engirank_turkiye_*.xlsx"],
            dependencies=["rankings_leiden"],
        ),
        ScraperJob(
            id="rankings_scholargps",
            name="ScholarGPS",
            category="rankings",
            description="ScholarGPS Turkey institutional ranking scraper",
            command=[python_executable, "scrapers/rankings/scholargps_scraper.py"],
            cwd=cwd,
            expected_outputs=["data/raw/scholargps_final_rapor_*.xlsx"],
            dependencies=["rankings_engirank"],
        ),
        ScraperJob(
            id="grants_all",
            name="Grants: all sources",
            category="grants",
            description="Run all grant sources and update grant dashboard database",
            command=[python_executable, "-m", "grant_dashboard.backend.run_scrapers"],
            cwd=cwd,
            expected_outputs=["grant_dashboard/backend/grants.db"],
        ),
        ScraperJob(
            id="grants_eu_funding",
            name="Grants: eu_funding",
            category="grants",
            description="Run only EU funding source",
            command=[python_executable, "-m", "grant_dashboard.backend.run_scrapers", "--source", "eu_funding"],
            cwd=cwd,
            expected_outputs=["grant_dashboard/backend/grants.db"],
        ),
        ScraperJob(
            id="grants_eu_affairs",
            name="Grants: eu_affairs",
            category="grants",
            description="Run only EU Affairs source",
            command=[python_executable, "-m", "grant_dashboard.backend.run_scrapers", "--source", "eu_affairs"],
            cwd=cwd,
            expected_outputs=["grant_dashboard/backend/grants.db"],
        ),
        ScraperJob(
            id="grants_yatirima_destek",
            name="Grants: yatirima",
            category="grants",
            description="Run only Yatirima Destek source",
            command=[python_executable, "-m", "grant_dashboard.backend.run_scrapers", "--source", "yatirima"],
            cwd=cwd,
            expected_outputs=["grant_dashboard/backend/grants.db"],
        ),
        ScraperJob(
            id="sustainability_itu_news",
            name="ITU Sustainability News",
            category="sustainability",
            description="Scrape ITU sustainability news",
            command=[python_executable, "Surdurulebilirlik_Projesi/itu_surdurulebilirlik.py"],
            cwd=cwd,
            expected_outputs=[
                "itu_haberler.json",
                "itu_haberler.xlsx",
                "data/raw/itu_haberler.json",
                "data/raw/itu_haberler.xlsx",
            ],
        ),
    ]

    return {job.id: job for job in jobs}
