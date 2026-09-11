"""输入和分层验证契约。几何、尺寸、惯量容差互不替代。"""
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

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

class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    compile: Literal["passed","failed","not_run"] = "not_run"
    physics: Literal["passed","failed","not_run","not_applicable"] = "not_run"
    render: Literal["passed","failed","not_run","unavailable"] = "not_run"
    appearance_review: Literal["pending","approved","rejected"] = "pending"
    asset_physics_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    evidence_issues: list[str] = Field(default_factory=list)

    def aggregate(self):
        if "failed" in (self.compile,self.physics,self.render):
            return "FAILED"
        if self.compile!="passed":
            return "CONVERTED"
        if self.physics=="not_applicable":
            return "VISUAL_ONLY"
        if self.physics=="passed":
            if not self.asset_physics_sha256:
                return "INVALID_EVIDENCE"
            if self.render=="passed" and self.appearance_review=="approved":
                return "FULLY_VALIDATED"
            return "PHYSICS_VALIDATED"
        return "COMPILE_VALIDATED"
