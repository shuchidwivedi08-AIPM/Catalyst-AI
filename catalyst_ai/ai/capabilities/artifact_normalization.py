"""Deterministic, non-AI cleanup for generated delivery artifacts."""
from pydantic import BaseModel
from catalyst_ai.ai.schemas import GeneratedArtifact

_PREFIXES = {"business_objectives":"BO", "in_scope":"SCOPE", "out_of_scope":"SCOPE", "functional_requirements":"FR", "non_functional_requirements":"NFR", "dependencies":"DEP", "risks":"RISK", "technical_risks":"RISK", "assumptions":"ASM", "success_metrics":"METRIC", "open_questions":"OQ", "stories":"US", "acceptance_criteria":"AC", "architecture_components":"COMP", "integrations":"INT", "api_requirements":"API", "data_requirements":"DATA", "security_requirements":"SEC", "deployment_considerations":"DEPLOY", "observability_requirements":"OBS", "open_decisions":"DEC"}
_CASE={"high":"High","medium":"Medium","low":"Low","critical":"Critical"}
def _clean(value):
    if isinstance(value,str): return value.strip()
    if isinstance(value,list): return [_clean(x) for x in value]
    if isinstance(value,BaseModel):
        for name in value.__class__.model_fields: setattr(value,name,_clean(getattr(value,name)))
    return value
def _ids(items,prefix):
    seen=set()
    for index,item in enumerate(items,1):
        current=item.id.strip() if hasattr(item,"id") else ""
        if not current or current in seen:
            candidate=f"{prefix}-{index:03d}"; n=index
            while candidate in seen: n+=1; candidate=f"{prefix}-{n:03d}"
            item.id=candidate
        seen.add(item.id)
def _normalize_model(model):
    _clean(model)
    for field,prefix in _PREFIXES.items():
        items=getattr(model,field,None)
        if isinstance(items,list):
            _ids(items,prefix)
            for item in items:
                if isinstance(item,BaseModel): _normalize_model(item)
    for attr in ("priority","likelihood","severity"):
        value=getattr(model,attr,None)
        if isinstance(value,str): setattr(model,attr,_CASE.get(value.lower(),value))
    return model
def normalize_generated_artifact(artifact: GeneratedArtifact) -> GeneratedArtifact:
    """Normalize IDs, whitespace and display casing without adding business facts."""
    _normalize_model(artifact.content)
    return artifact
