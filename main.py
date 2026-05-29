import yaml
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path("config/sources.yaml")


def load_sources() -> list[dict]:
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    return [s for s in config.get("sources", []) if s.get("enabled")]


def main():
    logger.info("Starting LifeSci Opportunity Scraper")
    sources = load_sources()

    if not sources:
        logger.warning("No enabled sources found in config/sources.yaml")
        return

    for source in sources:
        logger.info(f"Scraping: {source['name']} ({source['type']})")
        # Dispatcher will be wired up as parsers are implemented

    logger.info("Run complete.")


if __name__ == "__main__":
    main()
