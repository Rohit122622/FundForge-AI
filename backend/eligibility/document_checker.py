

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("fundforge.eligibility.document_checker")






@dataclass
class DocumentRequirement:
    
    doc_id:      str
    name:        str
    description: str   = ""
    mandatory:   bool  = True
    hint:        str   = ""   


@dataclass
class DocumentStatus:
    
    requirement: DocumentRequirement
    is_present:  bool
    match_type:  str = ""   

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id":      self.requirement.doc_id,
            "name":        self.requirement.name,
            "mandatory":   self.requirement.mandatory,
            "is_present":  self.is_present,
            "match_type":  self.match_type,
            "hint":        self.requirement.hint,
        }


@dataclass
class DocumentCheckResult:
    
    grant_id:       str
    total_required: int
    total_present:  int
    missing:        List[DocumentStatus]  = field(default_factory=list)
    present:        List[DocumentStatus]  = field(default_factory=list)
    suggestions:    List[str]             = field(default_factory=list)

    @property
    def completeness_pct(self) -> float:
        if self.total_required == 0:
            return 100.0
        return round(100.0 * self.total_present / self.total_required, 1)

    @property
    def mandatory_missing(self) -> List[DocumentStatus]:
        return [s for s in self.missing if s.requirement.mandatory]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grant_id":        self.grant_id,
            "total_required":  self.total_required,
            "total_present":   self.total_present,
            "completeness_pct":self.completeness_pct,
            "missing":         [s.to_dict() for s in self.missing],
            "present":         [s.to_dict() for s in self.present],
            "suggestions":     self.suggestions,
        }






_COMMON_DOCS: List[DocumentRequirement] = [
    DocumentRequirement("incorporation_cert",  "Certificate of Incorporation",
        "Proof of company registration with MCA/RoC.", True,
        "Download from MCA21 portal (mca.gov.in)."),
    DocumentRequirement("pan_card",            "PAN Card (Company)",
        "Company PAN card issued by Income Tax Dept.", True,
        "Apply via NSDL or UTIITSL portal."),
    DocumentRequirement("gst_registration",    "GST Registration Certificate",
        "Valid GST registration (if applicable).", False,
        "Register at gst.gov.in if turnover exceeds threshold."),
    DocumentRequirement("bank_statement",      "Bank Account Statement (6 months)",
        "Last 6 months company bank statement.", True,
        "Download from your company's bank internet banking portal."),
    DocumentRequirement("startup_pitch_deck",  "Startup Pitch Deck",
        "Product/service overview presentation.", True,
        "Prepare a 10–15 slide deck covering product, team, and market."),
    DocumentRequirement("team_bio",            "Founding Team Bios",
        "CVs/resumes of all co-founders.", True,
        "Prepare individual CVs highlighting relevant domain experience."),
]

_DPIIT_DOCS: List[DocumentRequirement] = [
    DocumentRequirement("dpiit_certificate",   "DPIIT Recognition Certificate",
        "DPIIT recognition from Startup India portal.", True,
        "Register at startupindia.gov.in and complete recognition process."),
]

_BIOTECH_DOCS: List[DocumentRequirement] = [
    DocumentRequirement("research_proposal",   "Research Proposal / Concept Note",
        "Detailed scientific research plan.", True,
        "Prepare a 5–10 page research proposal with objectives, methodology, and expected outcomes."),
    DocumentRequirement("ethics_clearance",    "Ethics Committee Clearance (if applicable)",
        "IRB / ethics clearance for human or animal studies.", False,
        "Obtain from institutional ethics committee."),
    DocumentRequirement("patent_filing",       "Patent Filing Receipt (if applicable)",
        "Evidence of IP protection for the innovation.", False,
        "File provisional patent with Indian Patent Office (ipindia.gov.in)."),
]

_AGRI_DOCS: List[DocumentRequirement] = [
    DocumentRequirement("farmer_mou",          "Farmer / FPO Partnership MoU",
        "Letter of intent or MoU with farmer group or FPO.", False,
        "Execute MoU with a registered FPO or farmer society."),
    DocumentRequirement("field_trial_report",  "Field Trial Report (if available)",
        "Evidence of on-farm or pilot testing.", False,
        "Conduct and document a small-scale field pilot."),
]

_GRANT_DOC_MAP: Dict[str, List[DocumentRequirement]] = {
    "sisfs":       _COMMON_DOCS + _DPIIT_DOCS,
    "birac_big":   _COMMON_DOCS + _BIOTECH_DOCS,
    "birac_seed":  _COMMON_DOCS + _DPIIT_DOCS + _BIOTECH_DOCS,
    "tide_2":      _COMMON_DOCS,
    "samridh":     _COMMON_DOCS + _DPIIT_DOCS,
    "rkvy_raftaar":_COMMON_DOCS + _AGRI_DOCS,
    "agrisure":    _COMMON_DOCS + _DPIIT_DOCS + _AGRI_DOCS,
    "nidhi_prayas":_COMMON_DOCS,
    "nidhi_eir":   _COMMON_DOCS,
    "ffs_sidbi":   _COMMON_DOCS + _DPIIT_DOCS,
    "cgss":        _COMMON_DOCS + _DPIIT_DOCS,
    "default":     _COMMON_DOCS,
}






class DocumentChecker:
    

    def __init__(self, doc_map: Optional[Dict[str, List[DocumentRequirement]]] = None) -> None:
        self._map = doc_map or _GRANT_DOC_MAP

    def check(
        self,
        grant_id:         str,
        uploaded_doc_names: List[str],
    ) -> DocumentCheckResult:
        
        requirements = self._map.get(grant_id, self._map["default"])
        uploaded_lower = {d.lower() for d in uploaded_doc_names}

        present_statuses: List[DocumentStatus] = []
        missing_statuses: List[DocumentStatus] = []

        for req in requirements:
            found = self._is_present(req, uploaded_lower)
            status = DocumentStatus(
                requirement = req,
                is_present  = found,
                match_type  = "inferred" if found else "missing",
            )
            if found:
                present_statuses.append(status)
            else:
                missing_statuses.append(status)

        suggestions = [
            f"Upload '{s.requirement.name}': {s.requirement.hint}"
            for s in missing_statuses if s.requirement.mandatory
        ]

        return DocumentCheckResult(
            grant_id       = grant_id,
            total_required = len([r for r in requirements if r.mandatory]),
            total_present  = len([s for s in present_statuses if s.requirement.mandatory]),
            missing        = missing_statuses,
            present        = present_statuses,
            suggestions    = suggestions[:8],
        )

    @staticmethod
    def _is_present(req: DocumentRequirement, uploaded_lower: set) -> bool:
        
        key_words = req.doc_id.lower().replace("_", " ").split()
        for doc in uploaded_lower:
            if any(kw in doc for kw in key_words):
                return True
        return False

    def get_requirements(self, grant_id: str) -> List[DocumentRequirement]:
        
        return self._map.get(grant_id, self._map["default"])
