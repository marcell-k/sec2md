from typing import Literal

FilingType = Literal["10-K", "10-Q", "20-F", "8-K", "SC 13D", "SC 13G"]

_TITLES_10K: dict[str, str] = {
    "ITEM 1": "Business",
    "ITEM 1A": "Risk Factors",
    "ITEM 1B": "Unresolved Staff Comments",
    "ITEM 1C": "Cybersecurity",
    "ITEM 2": "Properties",
    "ITEM 3": "Legal Proceedings",
    "ITEM 4": "Mine Safety Disclosures",
    "ITEM 5": "Market for Registrant's Common Equity, Related Stockholder Matters and Issuer Purchases of Equity Securities",  # noqa: E501
    "ITEM 7": "Management's Discussion and Analysis of Financial Condition and Results of Operations",
    "ITEM 7A": "Quantitative and Qualitative Disclosures About Market Risk",
    "ITEM 8": "Financial Statements and Supplementary Data",
    "ITEM 9": "Changes in and Disagreements with Accountants on Accounting and Financial Disclosure",
    "ITEM 9A": "Controls and Procedures",
    "ITEM 9B": "Other Information",
    "ITEM 9C": "Disclosure Regarding Foreign Jurisdictions that Prevent Inspections",
    "ITEM 10": "Directors, Executive Officers and Corporate Governance",
    "ITEM 11": "Executive Compensation",
    "ITEM 12": "Security Ownership of Certain Beneficial Owners and Management and Related Stockholder Matters",
    "ITEM 13": "Certain Relationships and Related Transactions, and Director Independence",
    "ITEM 14": "Principal Accountant Fees and Services",
    "ITEM 15": "Exhibits and Financial Statement Schedules",
    "ITEM 16": "Form 10-K Summary",
}

# Part I wins for shared item numbers (ITEM 1-4 appear in both parts).
_TITLES_10Q: dict[str, str] = {
    "ITEM 1": "Financial Statements",
    "ITEM 2": "Management's Discussion and Analysis of Financial Condition and Results of Operations",
    "ITEM 3": "Quantitative and Qualitative Disclosures About Market Risk",
    "ITEM 4": "Controls and Procedures",
    "ITEM 1A": "Risk Factors",
    "ITEM 5": "Other Information",
    "ITEM 6": "Exhibits",
}

_TITLES_8K: dict[str, str] = {
    "ITEM 1.01": "Entry into a Material Definitive Agreement",
    "ITEM 1.02": "Termination of a Material Definitive Agreement",
    "ITEM 1.03": "Bankruptcy or Receivership",
    "ITEM 1.04": "Mine Safety - Reporting of Shutdowns and Patterns of Violations",
    "ITEM 1.05": "Material Cybersecurity Incidents",
    "ITEM 2.01": "Completion of Acquisition or Disposition of Assets",
    "ITEM 2.02": "Results of Operations and Financial Condition",
    "ITEM 2.03": "Creation of a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement of a Registrant",  # noqa: E501
    "ITEM 2.04": "Triggering Events That Accelerate or Increase a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement",  # noqa: E501
    "ITEM 2.05": "Costs Associated with Exit or Disposal Activities",
    "ITEM 2.06": "Material Impairments",
    "ITEM 3.01": "Notice of Delisting or Failure to Satisfy a Continued Listing Rule or Standard; Transfer of Listing",
    "ITEM 3.02": "Unregistered Sales of Equity Securities",
    "ITEM 3.03": "Material Modification to Rights of Security Holders",
    "ITEM 4.01": "Changes in Registrant's Certifying Accountant",
    "ITEM 4.02": "Non-Reliance on Previously Issued Financial Statements or a Related Audit Report or Completed Interim Review",  # noqa: E501
    "ITEM 5.01": "Changes in Control of Registrant",
    "ITEM 5.02": "Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers; Compensatory Arrangements of Certain Officers",  # noqa: E501
    "ITEM 5.03": "Amendments to Articles of Incorporation or Bylaws; Change in Fiscal Year",
    "ITEM 5.04": "Temporary Suspension of Trading Under Registrant's Employee Benefit Plans",
    "ITEM 5.05": "Amendments to the Registrant's Code of Ethics, or Waiver of a Provision of the Code of Ethics",
    "ITEM 5.06": "Change in Shell Company Status",
    "ITEM 5.07": "Submission of Matters to a Vote of Security Holders",
    "ITEM 5.08": "Shareholder Director Nominations",
    "ITEM 6.01": "ABS Informational and Computational Material",
    "ITEM 6.02": "Change of Servicer or Trustee",
    "ITEM 6.03": "Change in Credit Enhancement or Other External Support",
    "ITEM 6.04": "Failure to Make a Required Distribution",
    "ITEM 6.05": "Securities Act Updating Disclosure",
    "ITEM 6.06": "Static Pool",
    "ITEM 7.01": "Regulation FD Disclosure",
    "ITEM 8.01": "Other Events",
    "ITEM 9.01": "Financial Statements and Exhibits",
}

_TITLES_13D: dict[str, str] = {
    "ITEM 1": "Security and Issuer",
    "ITEM 2": "Identity and Background",
    "ITEM 3": "Source and Amount of Funds or Other Consideration",
    "ITEM 4": "Purpose of Transaction",
    "ITEM 5": "Interest in Securities of the Issuer",
    "ITEM 6": "Contracts, Arrangements, Understandings or Relationships with Respect to Securities of the Issuer",
    "ITEM 7": "Material to be Filed as Exhibits",
}

_TITLES_13G: dict[str, str] = {
    "ITEM 1": "Security and Issuer",
    "ITEM 2": "Identity and Background",
    "ITEM 3": "Filing Status / Type of Reporting Person",
    "ITEM 4": "Ownership",
    "ITEM 5": "Ownership of Five Percent or Less of a Class",
    "ITEM 6": "Ownership of More than Five Percent on Behalf of Another Person",
    "ITEM 7": "Identification and Classification of the Subsidiary Which Acquired the Security Being Reported on by the Parent Holding Company",  # noqa: E501
    "ITEM 8": "Identification and Classification of Members of the Group",
    "ITEM 9": "Notice of Dissolution of Group",
    "ITEM 10": "Certification",
}

_ALL: dict[str, str] = {}
for _d in (_TITLES_10K, _TITLES_10Q, _TITLES_8K, _TITLES_13D, _TITLES_13G):
    for k, v in _d.items():
        _ALL.setdefault(k, v)


def build_item_title_lookup() -> dict[str, str]:
    return dict(_ALL)


def build_item_title_lookup_for_type(filing_type: FilingType | None) -> dict[str, str]:
    match filing_type:
        case "10-K":
            return dict(_TITLES_10K)
        case "10-Q":
            return dict(_TITLES_10Q)
        case "8-K":
            return dict(_TITLES_8K)
        case "SC 13D":
            return dict(_TITLES_13D)
        case "SC 13G":
            return dict(_TITLES_13G)
        case _:
            return build_item_title_lookup()
