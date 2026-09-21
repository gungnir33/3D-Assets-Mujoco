"""输入和分层验证契约。几何、尺寸、惯量容差互不替代。"""
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field

TARGET_RTOL, TARGET_ATOL = 0.02, 1e-7
GEOMETRY_RTOL, GEOMETRY_ATOL = 1e-6, 1e-7
INERTIA_RTOL, INERTIA_ATOL = 1e-8, 1e-12

class SuppliedInertia(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    frame: Literal["normalized_body"]
    reference: Literal["com"]
    com_unit: Literal["m"]
    inertia_unit: Literal["kg*m^2"]
    com: tuple[float, float, float]
    tensor: tuple[tuple[float,float,float],tuple[float,float,float],tuple[float,float,float]]
    mass_kg: float = Field(gt=0)
    final_size_m: tuple[float,float,float]

class ConversionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    input: Path
    output: Path
    name: str = Field(default="asset", pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    source_up: Literal["x","y","z"] | None = None
    scale: float | None = Field(default=None, gt=0)
    target_size_m: tuple[float,float,float] | None = None
    yaw_deg: float = 0
    scale_mode: Literal["uniform","fit_axes"] = "uniform"
    body_mode: Literal["static","free"] = "static"
    collision_mode: Literal["hull","none","supplied","decompose"] = "hull"
    validation_level: Literal["compile","physics","full"] = "full"
    contact_profile: Literal['preserve','engineering_static_v1'] = 'preserve'
    mass: float | None = Field(default=None, gt=0)
    inertia_mode: Literal["supplied","box_approx","watertight"] | None = None
    supplied_inertia: SuppliedInertia | None = None
    seed: int = 12345

    @model_validator(mode="after")
    def constraints(self):
        if self.contact_profile!='preserve' and (self.body_mode!='static' or self.collision_mode!='hull'):
            raise ValueError('engineering_static_v1 only supports static+hull')
        if self.scale is not None and self.target_size_m is not None:
            raise ValueError("scale 与 target_size_m 互斥")
        if self.target_size_m is not None and (min(self.target_size_m)<0 or max(self.target_size_m)<=0):
            raise ValueError("目标尺寸必须非负且至少一轴为正")
        if self.input.suffix.lower() not in (".glb", ".obj"):
            raise ValueError("仅支持 GLB/OBJ")
        if self.input.suffix.lower()==".obj" and (self.source_up is None or (self.scale is None and self.target_size_m is None)):
            raise ValueError("OBJ 必须声明 up-axis 和物理尺度")
        if self.body_mode=="free" and (self.mass is None or self.inertia_mode is None):
            raise ValueError("free 必须指定质量和惯量策略")
        if self.inertia_mode=="supplied" and self.supplied_inertia is None:
            raise ValueError("缺少 supplied 惯量")
        if self.collision_mode=="none" and (self.body_mode!="static" or self.validation_level!="compile"):
            raise ValueError("VISUAL_ONLY 仅 static/compile")
        return self

class ValidationScope(BaseModel):
    model_config = ConfigDict(extra='forbid')
    case_id: str | None = None
    required_pairs: list[list[str]] = Field(default_factory=list)
    evidence_status: Literal['unknown','declared','verified','missing','stale','contradictory'] = 'unknown'
    evidence_refs: dict[str,str] = Field(default_factory=dict)
    conditions: dict = Field(default_factory=dict)

class GroundObservation(BaseModel):
    model_config = ConfigDict(extra='forbid',allow_inf_nan=False)
    status: Literal['passed','failed','not_tested','unknown'] = 'unknown'
    mandatory_for_physics: Literal[False] = False
    comparison_threshold_m: float | None = Field(default=None,gt=0)
    evidence_refs: dict[str,str] = Field(default_factory=dict)
    last_recorded_status: str | None = None

class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    compile: Literal["passed","failed","not_run"] = "not_run"
    physics: Literal["passed","failed","not_run","not_applicable"] = "not_run"
    render: Literal["passed","failed","not_run","unavailable"] = "not_run"
    appearance_review: Literal["pending","approved","rejected"] = "pending"
    asset_physics_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    evidence_issues: list[str] = Field(default_factory=list)
    scope_report_version: Literal[1] | None = None
    contact_profile: str | None = None
    validation_scope: ValidationScope = Field(default_factory=ValidationScope)
    followup_ground: GroundObservation = Field(default_factory=GroundObservation)
    application_force_limit: Literal['not_specified'] = 'not_specified'
    host_integration: Literal['pending'] = 'pending'
    robot_contact_safety: Literal['not_validated'] = 'not_validated'
    physics_error: str | None = None
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def ignore_cached_aggregate(cls,values):
        # status始终由当前事实聚合；持久化的展示缓存不是输入授权。
        if isinstance(values,dict) and 'status' in values:
            values=dict(values)
            values.pop('status')
        return values

    @computed_field
    @property
    def status(self) -> str:
        return self.aggregate()

    def aggregate(self):
        if "failed" in (self.compile,self.physics,self.render):
            return "FAILED"
        if self.compile!="passed":
            return "CONVERTED"
        if self.physics=="not_applicable":
            return "VISUAL_ONLY"
        if self.physics=="passed":
            scope=self.validation_scope
            if not self.asset_physics_sha256 or scope.evidence_status!='verified' or not scope.case_id or not scope.required_pairs or not scope.evidence_refs:
                return "INVALID_EVIDENCE"
            if self.render=="passed" and self.appearance_review=="approved":
                return "SCOPED_FULLY_VALIDATED"
            return "SCOPED_PHYSICS_VALIDATED"
        return "COMPILE_VALIDATED"
