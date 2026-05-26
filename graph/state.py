from typing import TypedDict, List, Dict, Optional, Any, Annotated
import operator


class Module(TypedDict):
    name: str
    description: str
    code: str
    dependencies: List[str]
    layer: str


class AuditIssue(TypedDict):
    severity: str       # "critical" | "major" | "minor"
    module: str
    issue: str
    suggestion: str


class AuditReport(TypedDict):
    score: float
    passed: bool
    threshold: float
    issues: List[AuditIssue]
    summary: str
    timestamp: str
    recommendations: List[str]
    metrics: Dict[str, Any]


class ConvertedModule(TypedDict):
    name: str
    package: str
    java_code: str
    microservice_type: str  # "service" | "controller" | "repository" | "model" | "dto" | "config" | "exception"
    dependencies: List[str]
    file_path: str


class TestSuite(TypedDict):
    module_name: str
    test_class_name: str
    test_code: str
    test_count: int
    file_path: str


class WorkflowState(TypedDict):
    # Input
    source_code: str
    source_file_path: str

    # Code Splitter output
    modules: List[Module]

    # Documenter output
    documentation: Optional[Dict[str, Any]]

    # Auditor output
    audit_report: Optional[AuditReport]
    audit_feedback: str
    audit_retries: int

    # Converter output
    converted_modules: List[ConvertedModule]

    # Tester output
    test_suites: List[TestSuite]

    # Reassembly output (joiner node)
    assembly_result: Optional[Dict[str, Any]]

    # Human-in-the-Loop (Review Gate)
    hitl_decision:   str    # "approve" | "reject" | ""
    awaiting_review: bool   # True while paused at the review gate

    # Build verification output
    build_report:   Optional[Dict[str, Any]]
    build_feedback: str    # per-class error detail fed back to Converter
    build_retries:  int    # incremented each time BuildVerifier runs

    # Agent-level evaluation results
    converter_eval: Optional[Dict[str, Any]]
    tester_eval:    Optional[Dict[str, Any]]
    joiner_eval:    Optional[Dict[str, Any]]

    # Observability — accumulated by instrument_node wrapper
    metrics_summary: Optional[Dict[str, Any]]
    trace_data:      Optional[Dict[str, Any]]

    # Metadata — uses reducer so nodes can append without replacing
    errors: Annotated[List[str], operator.add]
    current_step: str
    processing_complete: bool
