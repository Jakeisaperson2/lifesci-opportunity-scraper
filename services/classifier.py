"""
Rule-based classifier for opportunity type and therapeutic area.

Applied after scraping, before persistence. Scrapers may already pre-classify
obvious cases (e.g., ClinicalTrials always sets type = "clinical_trial"). This
classifier fills in blanks and overrides when the scraper couldn't determine type.
"""

from scrapers.base import OpportunityData

# ---------------------------------------------------------------------------
# Opportunity type classification
# ---------------------------------------------------------------------------

_TYPE_RULES: list[tuple[str, list[str]]] = [
    ("clinical_trial", [
        "clinical trial", "phase i", "phase ii", "phase iii", "phase iv",
        "randomized controlled", "investigational drug", "investigational device",
        "nct", "first-in-human", "pivotal study", "dose escalation",
    ]),
    ("rfp", [
        "request for proposal", "request for application", "rfp", "rfa",
        "solicitation", "broad agency announcement", "baa", "other transaction",
        "ota", "contract opportunity",
    ]),
    ("grant", [
        "grant", "funding opportunity", "r01", "r21", "r44", "sbir", "sttr",
        "cooperative agreement", "u01", "u54", "p01", "program announcement",
        "par-", "rfa-",
    ]),
    ("sponsored_research", [
        "sponsored research", "sponsored research agreement", "sra",
        "industry sponsored", "corporate research", "industry collaboration",
    ]),
    ("collaboration", [
        "collaboration", "partnership", "co-development", "joint research",
        "consortium", "alliance", "joint venture", "innovation partnership",
        "public private partnership",
    ]),
    ("pilot_study", [
        "pilot study", "pilot program", "proof of concept", "feasibility study",
        "exploratory study", "innovation challenge",
    ]),
    ("data_partnership", [
        "data collaboration", "health data", "real world data", "real world evidence",
        "ai collaboration", "machine learning", "digital health",
        "data sharing", "data access",
    ]),
]

# ---------------------------------------------------------------------------
# Therapeutic area classification
# ---------------------------------------------------------------------------

_AREA_RULES: list[tuple[str, list[str]]] = [
    ("oncology", [
        "cancer", "oncology", "tumor", "tumour", "leukemia", "lymphoma",
        "carcinoma", "sarcoma", "melanoma", "glioma", "myeloma",
        "solid tumor", "hematologic", "immunotherapy", "chimeric antigen",
    ]),
    ("cardiology", [
        "cardiac", "cardiovascular", "heart failure", "coronary", "arrhythmia",
        "atrial fibrillation", "hypertension", "stroke", "atherosclerosis",
        "myocardial", "vascular",
    ]),
    ("neurology", [
        "neuro", "alzheimer", "parkinson", "multiple sclerosis", "epilepsy",
        "dementia", "stroke", "amyotrophic lateral", "als", "huntington",
        "psychiatric", "schizophrenia", "depression", "anxiety",
        "traumatic brain injury", "tbi", "spinal cord",
    ]),
    ("rare_disease", [
        "rare disease", "orphan drug", "rare pediatric", "ultra-rare",
        "genetic disorder", "lysosomal", "enzyme replacement",
        "duchenne", "cystic fibrosis", "sickle cell",
    ]),
    ("ai_digital_health", [
        "artificial intelligence", "machine learning", "deep learning",
        "digital health", "digital therapeutics", "telehealth", "telemedicine",
        "wearable", "remote monitoring", "health informatics",
        "electronic health record", "ehr", "clinical decision support",
        "natural language processing", "nlp", "precision medicine",
    ]),
    ("immunology", [
        "immune", "autoimmune", "inflammation", "rheumatoid arthritis",
        "lupus", "crohn", "ulcerative colitis", "immunodeficiency",
        "allergy", "asthma", "atopic dermatitis", "psoriasis",
    ]),
    ("infectious_disease", [
        "infectious disease", "antimicrobial", "antibiotic", "antiviral",
        "vaccine", "hiv", "aids", "tuberculosis", "malaria", "covid",
        "coronavirus", "pandemic", "sepsis", "fungal",
    ]),
    ("metabolic_endocrine", [
        "diabetes", "obesity", "metabolic syndrome", "fatty liver",
        "nash", "nafld", "thyroid", "adrenal", "endocrine",
        "insulin resistance",
    ]),
    ("respiratory", [
        "respiratory", "pulmonary", "lung", "copd", "asthma",
        "idiopathic pulmonary fibrosis", "ipf", "sleep apnea",
    ]),
    ("ophthalmology", [
        "ocular", "ophthalm", "retinal", "macular degeneration",
        "glaucoma", "dry eye",
    ]),
]


def _match_rules(text: str, rules: list[tuple[str, list[str]]]) -> str:
    lower = text.lower()
    for label, keywords in rules:
        for kw in keywords:
            if kw in lower:
                return label
    return ""


def classify(opp: OpportunityData) -> OpportunityData:
    """
    Fill in opportunity_type and therapeutic_area if not already set.
    Returns the same object (mutated in place) for chaining convenience.
    """
    search_text = f"{opp.title} {opp.description}"

    if not opp.opportunity_type:
        opp.opportunity_type = _match_rules(search_text, _TYPE_RULES) or "other"

    if not opp.therapeutic_area:
        opp.therapeutic_area = _match_rules(search_text, _AREA_RULES)

    return opp
