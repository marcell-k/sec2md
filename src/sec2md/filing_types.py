from enum import StrEnum
from typing import Literal

# Type alias for supported SEC filing types
FilingType = Literal["10-K", "10-Q", "20-F", "8-K", "SC 13D", "SC 13G"]


class Item10K(StrEnum):
    """Annual report disclosure items pursuant to Form 10-K."""

    # Part I
    BUSINESS = "1"
    RISK_FACTORS = "1A"
    UNRESOLVED_STAFF_COMMENTS = "1B"
    CYBERSECURITY = "1C"
    PROPERTIES = "2"
    LEGAL_PROCEEDINGS = "3"
    MINE_SAFETY = "4"

    # Part II
    MARKET_FOR_STOCK = "5"
    MD_AND_A = "7"
    MARKET_RISK = "7A"
    FINANCIAL_STATEMENTS = "8"
    CHANGES_IN_ACCOUNTING = "9"
    CONTROLS_AND_PROCEDURES = "9A"
    OTHER_INFORMATION = "9B"
    FOREIGN_JURISDICTIONS = "9C"

    # Part III
    DIRECTORS_AND_OFFICERS = "10"
    EXECUTIVE_COMPENSATION = "11"
    SECURITY_OWNERSHIP = "12"
    CERTAIN_RELATIONSHIPS = "13"
    PRINCIPAL_ACCOUNTANT = "14"

    # Part IV
    EXHIBITS = "15"
    FORM_10K_SUMMARY = "16"


class Item10Q(StrEnum):
    """Quarterly report disclosure items pursuant to Form 10-Q."""

    # Part I
    FINANCIAL_STATEMENTS_P1 = "1.P1"
    MD_AND_A_P1 = "2.P1"
    MARKET_RISK_P1 = "3.P1"
    CONTROLS_AND_PROCEDURES_P1 = "4.P1"

    # Part II
    LEGAL_PROCEEDINGS_P2 = "1.P2"
    RISK_FACTORS_P2 = "1A.P2"
    UNREGISTERED_SALES_P2 = "2.P2"
    DEFAULTS_P2 = "3.P2"
    MINE_SAFETY_P2 = "4.P2"
    OTHER_INFORMATION_P2 = "5.P2"
    EXHIBITS_P2 = "6.P2"


class Item8K(StrEnum):
    """Current report items pursuant to Form 8-K for event-driven disclosures."""

    # Section 1 - Registrant's Business and Operations
    MATERIAL_AGREEMENT = "1.01"
    TERMINATION_OF_AGREEMENT = "1.02"
    BANKRUPTCY = "1.03"
    MINE_SAFETY = "1.04"
    CYBERSECURITY_INCIDENT = "1.05"

    # Section 2 - Financial Information
    ACQUISITION_DISPOSITION = "2.01"
    RESULTS_OF_OPERATIONS = "2.02"
    DIRECT_FINANCIAL_OBLIGATION = "2.03"
    TRIGGERING_EVENTS = "2.04"
    EXIT_DISPOSAL_COSTS = "2.05"
    MATERIAL_IMPAIRMENTS = "2.06"

    # Section 3 - Securities and Trading Markets
    DELISTING_NOTICE = "3.01"
    UNREGISTERED_SALES = "3.02"
    SECURITY_RIGHTS_MODIFICATION = "3.03"

    # Section 4 - Matters Related to Accountants and Financial Statements
    ACCOUNTANT_CHANGE = "4.01"
    NON_RELIANCE = "4.02"

    # Section 5 - Corporate Governance and Management
    CONTROL_CHANGE = "5.01"
    DIRECTOR_OFFICER_CHANGE = "5.02"
    AMENDMENTS_TO_ARTICLES = "5.03"
    TRADING_SUSPENSION = "5.04"
    CODE_OF_ETHICS = "5.05"
    SHELL_COMPANY_STATUS = "5.06"
    SHAREHOLDER_VOTE = "5.07"
    SHAREHOLDER_NOMINATIONS = "5.08"

    # Section 6 - Asset-Backed Securities
    ABS_INFORMATIONAL = "6.01"
    SERVICER_TRUSTEE_CHANGE = "6.02"
    CREDIT_ENHANCEMENT_CHANGE = "6.03"
    DISTRIBUTION_FAILURE = "6.04"
    SECURITIES_ACT_UPDATING = "6.05"
    STATIC_POOL = "6.06"

    # Section 7 - Regulation FD
    REGULATION_FD = "7.01"

    # Section 8 - Other Events
    OTHER_EVENTS = "8.01"

    # Section 9 - Financial Statements and Exhibits
    FINANCIAL_STATEMENTS_EXHIBITS = "9.01"


class Item13D(StrEnum):
    """Beneficial ownership disclosure items pursuant to Schedule 13D (active investors)."""

    SECURITY_AND_ISSUER = "1"
    IDENTITY_AND_BACKGROUND = "2"
    SOURCE_OF_FUNDS = "3"
    PURPOSE_OF_TRANSACTION = "4"
    INTEREST_IN_SECURITIES = "5"
    CONTRACTS_AND_ARRANGEMENTS = "6"
    EXHIBITS = "7"


class Item13G(StrEnum):
    """Beneficial ownership disclosure items pursuant to Schedule 13G (passive investors)."""

    SECURITY_AND_ISSUER = "1"
    IDENTITY_AND_BACKGROUND = "2"
    FILING_STATUS = "3"
    OWNERSHIP = "4"
    OWNERSHIP_FIVE_PERCENT_OR_LESS = "5"
    OWNERSHIP_ON_BEHALF_OF_ANOTHER = "6"
    SUBSIDIARY_CLASSIFICATION = "7"
    GROUP_MEMBERS = "8"
    NOTICE_OF_DISSOLUTION = "9"
    CERTIFICATION = "10"


# Internal mappings from enum to (part, item) tuples
ITEM_10K_MAPPING: dict[Item10K, tuple[str, str]] = {
    # Part I
    Item10K.BUSINESS: ("PART I", "ITEM 1"),
    Item10K.RISK_FACTORS: ("PART I", "ITEM 1A"),
    Item10K.UNRESOLVED_STAFF_COMMENTS: ("PART I", "ITEM 1B"),
    Item10K.CYBERSECURITY: ("PART I", "ITEM 1C"),
    Item10K.PROPERTIES: ("PART I", "ITEM 2"),
    Item10K.LEGAL_PROCEEDINGS: ("PART I", "ITEM 3"),
    Item10K.MINE_SAFETY: ("PART I", "ITEM 4"),
    # Part II
    Item10K.MARKET_FOR_STOCK: ("PART II", "ITEM 5"),
    Item10K.MD_AND_A: ("PART II", "ITEM 7"),
    Item10K.MARKET_RISK: ("PART II", "ITEM 7A"),
    Item10K.FINANCIAL_STATEMENTS: ("PART II", "ITEM 8"),
    Item10K.CHANGES_IN_ACCOUNTING: ("PART II", "ITEM 9"),
    Item10K.CONTROLS_AND_PROCEDURES: ("PART II", "ITEM 9A"),
    Item10K.OTHER_INFORMATION: ("PART II", "ITEM 9B"),
    Item10K.FOREIGN_JURISDICTIONS: ("PART II", "ITEM 9C"),
    # Part III
    Item10K.DIRECTORS_AND_OFFICERS: ("PART III", "ITEM 10"),
    Item10K.EXECUTIVE_COMPENSATION: ("PART III", "ITEM 11"),
    Item10K.SECURITY_OWNERSHIP: ("PART III", "ITEM 12"),
    Item10K.CERTAIN_RELATIONSHIPS: ("PART III", "ITEM 13"),
    Item10K.PRINCIPAL_ACCOUNTANT: ("PART III", "ITEM 14"),
    # Part IV
    Item10K.EXHIBITS: ("PART IV", "ITEM 15"),
    Item10K.FORM_10K_SUMMARY: ("PART IV", "ITEM 16"),
}


ITEM_10Q_MAPPING: dict[Item10Q, tuple[str, str]] = {
    # Part I
    Item10Q.FINANCIAL_STATEMENTS_P1: ("PART I", "ITEM 1"),
    Item10Q.MD_AND_A_P1: ("PART I", "ITEM 2"),
    Item10Q.MARKET_RISK_P1: ("PART I", "ITEM 3"),
    Item10Q.CONTROLS_AND_PROCEDURES_P1: ("PART I", "ITEM 4"),
    # Part II
    Item10Q.LEGAL_PROCEEDINGS_P2: ("PART II", "ITEM 1"),
    Item10Q.RISK_FACTORS_P2: ("PART II", "ITEM 1A"),
    Item10Q.UNREGISTERED_SALES_P2: ("PART II", "ITEM 2"),
    Item10Q.DEFAULTS_P2: ("PART II", "ITEM 3"),
    Item10Q.MINE_SAFETY_P2: ("PART II", "ITEM 4"),
    Item10Q.OTHER_INFORMATION_P2: ("PART II", "ITEM 5"),
    Item10Q.EXHIBITS_P2: ("PART II", "ITEM 6"),
}


# 8-K items do not have PART divisions
ITEM_8K_TITLES: dict[Item8K, str] = {
    Item8K.MATERIAL_AGREEMENT: "Entry into a Material Definitive Agreement",
    Item8K.TERMINATION_OF_AGREEMENT: "Termination of a Material Definitive Agreement",
    Item8K.BANKRUPTCY: "Bankruptcy or Receivership",
    Item8K.MINE_SAFETY: "Mine Safety - Reporting of Shutdowns and Patterns of Violations",
    Item8K.CYBERSECURITY_INCIDENT: "Material Cybersecurity Incidents",
    Item8K.ACQUISITION_DISPOSITION: "Completion of Acquisition or Disposition of Assets",
    Item8K.RESULTS_OF_OPERATIONS: "Results of Operations and Financial Condition",
    Item8K.DIRECT_FINANCIAL_OBLIGATION: (
        "Creation of a Direct Financial Obligation or an Obligation under an Off-Balance Sheet "
        "Arrangement of a Registrant"
    ),
    Item8K.TRIGGERING_EVENTS: (
        "Triggering Events That Accelerate or Increase a Direct Financial Obligation or an "
        "Obligation under an Off-Balance Sheet Arrangement"
    ),
    Item8K.EXIT_DISPOSAL_COSTS: "Costs Associated with Exit or Disposal Activities",
    Item8K.MATERIAL_IMPAIRMENTS: "Material Impairments",
    Item8K.DELISTING_NOTICE: (
        "Notice of Delisting or Failure to Satisfy a Continued Listing Rule or Standard; Transfer of Listing"
    ),
    Item8K.UNREGISTERED_SALES: "Unregistered Sales of Equity Securities",
    Item8K.SECURITY_RIGHTS_MODIFICATION: "Material Modification to Rights of Security Holders",
    Item8K.ACCOUNTANT_CHANGE: "Changes in Registrant's Certifying Accountant",
    Item8K.NON_RELIANCE: (
        "Non-Reliance on Previously Issued Financial Statements or a Related Audit Report or Completed Interim Review"
    ),
    Item8K.CONTROL_CHANGE: "Changes in Control of Registrant",
    Item8K.DIRECTOR_OFFICER_CHANGE: (
        "Departure of Directors or Certain Officers; Election of Directors; Appointment of "
        "Certain Officers; Compensatory Arrangements of Certain Officers"
    ),
    Item8K.AMENDMENTS_TO_ARTICLES: "Amendments to Articles of Incorporation or Bylaws; Change in Fiscal Year",
    Item8K.TRADING_SUSPENSION: "Temporary Suspension of Trading Under Registrant's Employee Benefit Plans",
    Item8K.CODE_OF_ETHICS: "Amendments to the Registrant's Code of Ethics, or Waiver of a Provision of the Code of Ethics",  # noqa: E501
    Item8K.SHELL_COMPANY_STATUS: "Change in Shell Company Status",
    Item8K.SHAREHOLDER_VOTE: "Submission of Matters to a Vote of Security Holders",
    Item8K.SHAREHOLDER_NOMINATIONS: "Shareholder Director Nominations",
    Item8K.ABS_INFORMATIONAL: "ABS Informational and Computational Material",
    Item8K.SERVICER_TRUSTEE_CHANGE: "Change of Servicer or Trustee",
    Item8K.CREDIT_ENHANCEMENT_CHANGE: "Change in Credit Enhancement or Other External Support",
    Item8K.DISTRIBUTION_FAILURE: "Failure to Make a Required Distribution",
    Item8K.SECURITIES_ACT_UPDATING: "Securities Act Updating Disclosure",
    Item8K.STATIC_POOL: "Static Pool",
    Item8K.REGULATION_FD: "Regulation FD Disclosure",
    Item8K.OTHER_EVENTS: "Other Events",
    Item8K.FINANCIAL_STATEMENTS_EXHIBITS: "Financial Statements and Exhibits",
}


ITEM_13D_TITLES: dict[Item13D, str] = {
    Item13D.SECURITY_AND_ISSUER: "Security and Issuer",
    Item13D.IDENTITY_AND_BACKGROUND: "Identity and Background",
    Item13D.SOURCE_OF_FUNDS: "Source and Amount of Funds or Other Consideration",
    Item13D.PURPOSE_OF_TRANSACTION: "Purpose of Transaction",
    Item13D.INTEREST_IN_SECURITIES: "Interest in Securities of the Issuer",
    Item13D.CONTRACTS_AND_ARRANGEMENTS: (
        "Contracts, Arrangements, Understandings or Relationships with Respect to Securities of the Issuer"
    ),
    Item13D.EXHIBITS: "Material to be Filed as Exhibits",
}


ITEM_13D_MAPPING: dict[Item13D, tuple[str | None, str]] = {
    Item13D.SECURITY_AND_ISSUER: (None, "ITEM 1"),
    Item13D.IDENTITY_AND_BACKGROUND: (None, "ITEM 2"),
    Item13D.SOURCE_OF_FUNDS: (None, "ITEM 3"),
    Item13D.PURPOSE_OF_TRANSACTION: (None, "ITEM 4"),
    Item13D.INTEREST_IN_SECURITIES: (None, "ITEM 5"),
    Item13D.CONTRACTS_AND_ARRANGEMENTS: (None, "ITEM 6"),
    Item13D.EXHIBITS: (None, "ITEM 7"),
}


ITEM_13G_TITLES: dict[Item13G, str] = {
    Item13G.SECURITY_AND_ISSUER: "Security and Issuer",
    Item13G.IDENTITY_AND_BACKGROUND: "Identity and Background",
    Item13G.FILING_STATUS: "Filing Status / Type of Reporting Person",
    Item13G.OWNERSHIP: "Ownership",
    Item13G.OWNERSHIP_FIVE_PERCENT_OR_LESS: "Ownership of Five Percent or Less of a Class",
    Item13G.OWNERSHIP_ON_BEHALF_OF_ANOTHER: "Ownership of More than Five Percent on Behalf of Another Person",
    Item13G.SUBSIDIARY_CLASSIFICATION: (
        "Identification and Classification of the Subsidiary Which Acquired the Security Being "
        "Reported on by the Parent Holding Company"
    ),
    Item13G.GROUP_MEMBERS: "Identification and Classification of Members of the Group",
    Item13G.NOTICE_OF_DISSOLUTION: "Notice of Dissolution of Group",
    Item13G.CERTIFICATION: "Certification",
}


ITEM_13G_MAPPING: dict[Item13G, tuple[str | None, str]] = {
    Item13G.SECURITY_AND_ISSUER: (None, "ITEM 1"),
    Item13G.IDENTITY_AND_BACKGROUND: (None, "ITEM 2"),
    Item13G.FILING_STATUS: (None, "ITEM 3"),
    Item13G.OWNERSHIP: (None, "ITEM 4"),
    Item13G.OWNERSHIP_FIVE_PERCENT_OR_LESS: (None, "ITEM 5"),
    Item13G.OWNERSHIP_ON_BEHALF_OF_ANOTHER: (None, "ITEM 6"),
    Item13G.SUBSIDIARY_CLASSIFICATION: (None, "ITEM 7"),
    Item13G.GROUP_MEMBERS: (None, "ITEM 8"),
    Item13G.NOTICE_OF_DISSOLUTION: (None, "ITEM 9"),
    Item13G.CERTIFICATION: (None, "ITEM 10"),
}

ITEM_10K_TITLES: dict[Item10K, str] = {
    Item10K.BUSINESS: "Business",
    Item10K.RISK_FACTORS: "Risk Factors",
    Item10K.UNRESOLVED_STAFF_COMMENTS: "Unresolved Staff Comments",
    Item10K.CYBERSECURITY: "Cybersecurity",
    Item10K.PROPERTIES: "Properties",
    Item10K.LEGAL_PROCEEDINGS: "Legal Proceedings",
    Item10K.MINE_SAFETY: "Mine Safety Disclosures",
    Item10K.MARKET_FOR_STOCK: "Market for Registrant's Common Equity, Related Stockholder Matters and Issuer Purchases of Equity Securities",  # noqa: E501
    Item10K.MD_AND_A: "Management's Discussion and Analysis of Financial Condition and Results of Operations",
    Item10K.MARKET_RISK: "Quantitative and Qualitative Disclosures About Market Risk",
    Item10K.FINANCIAL_STATEMENTS: "Financial Statements and Supplementary Data",
    Item10K.CHANGES_IN_ACCOUNTING: "Changes in and Disagreements with Accountants on Accounting and Financial Disclosure",  # noqa: E501
    Item10K.CONTROLS_AND_PROCEDURES: "Controls and Procedures",
    Item10K.OTHER_INFORMATION: "Other Information",
    Item10K.FOREIGN_JURISDICTIONS: "Disclosure Regarding Foreign Jurisdictions that Prevent Inspections",
    Item10K.DIRECTORS_AND_OFFICERS: "Directors, Executive Officers and Corporate Governance",
    Item10K.EXECUTIVE_COMPENSATION: "Executive Compensation",
    Item10K.SECURITY_OWNERSHIP: "Security Ownership of Certain Beneficial Owners and Management and Related Stockholder Matters",  # noqa: E501
    Item10K.CERTAIN_RELATIONSHIPS: "Certain Relationships and Related Transactions, and Director Independence",
    Item10K.PRINCIPAL_ACCOUNTANT: "Principal Accountant Fees and Services",
    Item10K.EXHIBITS: "Exhibits and Financial Statement Schedules",
    Item10K.FORM_10K_SUMMARY: "Form 10-K Summary",
}

# 10-Q human-readable titles
ITEM_10Q_TITLES: dict[Item10Q, str] = {
    Item10Q.FINANCIAL_STATEMENTS_P1: "Financial Statements",
    Item10Q.MD_AND_A_P1: "Management's Discussion and Analysis of Financial Condition and Results of Operations",
    Item10Q.MARKET_RISK_P1: "Quantitative and Qualitative Disclosures About Market Risk",
    Item10Q.CONTROLS_AND_PROCEDURES_P1: "Controls and Procedures",
    Item10Q.LEGAL_PROCEEDINGS_P2: "Legal Proceedings",
    Item10Q.RISK_FACTORS_P2: "Risk Factors",
    Item10Q.UNREGISTERED_SALES_P2: "Unregistered Sales of Equity Securities",
    Item10Q.DEFAULTS_P2: "Defaults Upon Senior Securities",
    Item10Q.MINE_SAFETY_P2: "Mine Safety Disclosures",
    Item10Q.OTHER_INFORMATION_P2: "Other Information",
    Item10Q.EXHIBITS_P2: "Exhibits",
}


def build_item_title_lookup() -> dict[str, str]:
    """
    Return a flat dict mapping normalised item strings (e.g. ``"ITEM 1A"``) to
    their human-readable titles.

    When the same item number appears in multiple parts (e.g. 10-Q Part I Item 1
    vs Part II Item 1) the Part-I entry wins, which is the right default for the
    most common filings.  Call-sites that need part-aware resolution should use
    the typed mappings directly.
    """
    lookup: dict[str, str] = {}

    # 10-K
    for item, (_, item_str) in ITEM_10K_MAPPING.items():
        lookup.setdefault(item_str, ITEM_10K_TITLES[item])

    # 10-Q (may overwrite 10-K entries for shared item numbers - that's fine
    # because the lookup is only used as a best-effort enrichment)
    for item, (_, item_str) in ITEM_10Q_MAPPING.items():
        lookup.setdefault(item_str, ITEM_10Q_TITLES[item])

    # 8-K  (item strings look like "ITEM 1.01" - emit them as-is)
    for item, title in ITEM_8K_TITLES.items():
        lookup.setdefault(f"ITEM {item.value}", title)

    # 13-D
    for item, (_, item_str) in ITEM_13D_MAPPING.items():
        lookup.setdefault(item_str, ITEM_13D_TITLES[item])

    # 13-G
    for item, (_, item_str) in ITEM_13G_MAPPING.items():
        lookup.setdefault(item_str, ITEM_13G_TITLES[item])

    return lookup


def build_item_title_lookup_for_type(filing_type: FilingType | None) -> dict[str, str]:
    """Return a title lookup scoped to a single filing type.

    Unlike the merged ``build_item_title_lookup``, this avoids cross-type
    collisions (e.g. 10-Q "ITEM 6 → Exhibits" bleeding into a 10-K parse
    where ITEM 6 is "[Reserved]").  Falls back to the merged lookup when
    *filing_type* is ``None``.
    """
    if filing_type == "10-K":
        return {item_str: ITEM_10K_TITLES[item] for item, (_, item_str) in ITEM_10K_MAPPING.items()}
    if filing_type == "10-Q":
        # Part I and Part II share item numbers (both have "ITEM 1", "ITEM 4", …).
        # setdefault keeps the Part-I entry, which is the right default.
        lookup: dict[str, str] = {}
        for item, (_, item_str) in ITEM_10Q_MAPPING.items():
            lookup.setdefault(item_str, ITEM_10Q_TITLES[item])
        return lookup
    if filing_type == "8-K":
        return {f"ITEM {item.value}": title for item, title in ITEM_8K_TITLES.items()}
    if filing_type == "SC 13D":
        return {item_str: ITEM_13D_TITLES[item] for item, (_, item_str) in ITEM_13D_MAPPING.items()}
    if filing_type == "SC 13G":
        return {item_str: ITEM_13G_TITLES[item] for item, (_, item_str) in ITEM_13G_MAPPING.items()}
    return build_item_title_lookup()  # unknown type — best-effort merged fallback
