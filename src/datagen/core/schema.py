"""Pydantic models for Datagen DSL v1."""

from typing import Literal, Optional, Union, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from datetime import datetime


# ============================================================================
# Generator Specs
# ============================================================================

class SequenceGenerator(BaseModel):
    """Sequential integer generator."""
    sequence: dict = Field(default_factory=lambda: {"start": 1, "step": 1})

    @field_validator("sequence")
    @classmethod
    def validate_sequence(cls, v):
        start = v.get("start", 1)
        step = v.get("step", 1)
        if not isinstance(start, int):
            raise ValueError("start must be an integer")
        if not isinstance(step, int):
            raise ValueError("step must be an integer")
        if step == 0:
            raise ValueError("step cannot be 0")
        return {"start": start, "step": step}


class ChoiceGenerator(BaseModel):
    """Choice from list generator."""
    choice: dict

    @field_validator("choice")
    @classmethod
    def validate_choice(cls, v):
        has_choices = "choices" in v
        has_ref = "choices_ref" in v

        if not has_choices and not has_ref:
            raise ValueError("choice must have either 'choices' or 'choices_ref'")
        if has_choices and has_ref:
            raise ValueError("choice cannot have both 'choices' and 'choices_ref'")

        # Validate weights if provided
        if "weights" in v and not isinstance(v["weights"], list):
            raise ValueError("weights must be a list")

        # Validate weights_kind if provided
        if "weights_kind" in v:
            wk = v["weights_kind"]
            valid_kinds = ["uniform"]

            if wk in valid_kinds:
                pass  # Valid
            elif wk.startswith("zipf@"):
                # Validate zipf@alpha - alpha must be a float
                try:
                    alpha_str = wk.split("@", 1)[1]
                    alpha = float(alpha_str)
                    if alpha <= 0:
                        raise ValueError(f"zipf alpha must be positive, got: {alpha}")
                except (IndexError, ValueError) as e:
                    raise ValueError(f"Invalid zipf weights_kind format: {wk}. Expected 'zipf@<positive_float>', e.g., 'zipf@1.5'")
            elif wk.startswith("head_tail@"):
                # Validate head_tail@{head_share,tail_alpha} - both must be floats
                try:
                    params_str = wk.split("@", 1)[1]
                    if not (params_str.startswith("{") and params_str.endswith("}")):
                        raise ValueError(f"head_tail parameters must be in {{}} braces")

                    params_str = params_str[1:-1]  # Remove braces
                    parts = [p.strip() for p in params_str.split(",")]

                    if len(parts) != 2:
                        raise ValueError(f"head_tail requires exactly 2 parameters, got {len(parts)}")

                    head_share = float(parts[0])
                    tail_alpha = float(parts[1])

                    if not (0 < head_share < 1):
                        raise ValueError(f"head_share must be in (0, 1), got: {head_share}")
                    if tail_alpha <= 0:
                        raise ValueError(f"tail_alpha must be positive, got: {tail_alpha}")

                except (IndexError, ValueError) as e:
                    raise ValueError(
                        f"Invalid head_tail weights_kind format: {wk}. "
                        f"Expected 'head_tail@{{head_share,tail_alpha}}' with numeric values, "
                        f"e.g., 'head_tail@{{0.6,1.5}}'. Error: {e}"
                    )
            else:
                raise ValueError(f"Invalid weights_kind: {wk}")

        return v


class DistributionGenerator(BaseModel):
    """Statistical distribution generator."""
    distribution: dict

    @field_validator("distribution")
    @classmethod
    def validate_distribution(cls, v):
        dist_type = v.get("type")
        if dist_type not in ["normal", "lognormal", "uniform", "poisson"]:
            raise ValueError(f"Unknown distribution type: {dist_type}")

        if "params" not in v:
            raise ValueError("distribution must have 'params'")

        if "clamp" not in v:
            raise ValueError("distribution must have 'clamp' [min, max]")

        clamp = v["clamp"]
        if not isinstance(clamp, list) or len(clamp) != 2:
            raise ValueError("clamp must be [min, max]")

        return v


class DatetimeSeriesGenerator(BaseModel):
    """Datetime series generator with optional patterns."""
    datetime_series: dict

    @field_validator("datetime_series")
    @classmethod
    def validate_datetime_series(cls, v):
        if "within" not in v:
            raise ValueError("datetime_series must have 'within'")

        if "freq" not in v:
            raise ValueError("datetime_series must have 'freq'")

        # Validate pattern if provided
        if "pattern" in v:
            pattern = v["pattern"]
            if "dimension" not in pattern:
                raise ValueError("pattern must have 'dimension'")
            if pattern["dimension"] not in ["hour", "dow", "month"]:
                raise ValueError("dimension must be one of: hour, dow, month")
            if "weights" not in pattern:
                raise ValueError("pattern must have 'weights'")

            # Validate weights length
            weights = pattern["weights"]
            expected_len = {"hour": 24, "dow": 7, "month": 12}[pattern["dimension"]]
            if len(weights) != expected_len:
                raise ValueError(f"weights for {pattern['dimension']} must have {expected_len} values")

        return v


class FakerGenerator(BaseModel):
    """Faker semantic data generator."""
    faker: dict

    @field_validator("faker")
    @classmethod
    def validate_faker(cls, v):
        if "method" not in v:
            raise ValueError("faker must have 'method'")
        return v


class LookupGenerator(BaseModel):
    """Lookup/foreign key generator."""
    lookup: dict

    @field_validator("lookup")
    @classmethod
    def validate_lookup(cls, v):
        if "from" not in v:
            raise ValueError("lookup must have 'from' (table.column)")

        from_ref = v["from"]
        if not isinstance(from_ref, str) or "." not in from_ref:
            raise ValueError("lookup 'from' must be in format 'table.column'")

        return v


class ExpressionGenerator(BaseModel):
    """Expression-based generator."""
    expression: dict

    @field_validator("expression")
    @classmethod
    def validate_expression(cls, v):
        if "code" not in v:
            raise ValueError("expression must have 'code'")
        return v


class EnumListGenerator(BaseModel):
    """Enum list generator (for vocab nodes)."""
    enum_list: dict

    @field_validator("enum_list")
    @classmethod
    def validate_enum_list(cls, v):
        if "values" not in v:
            raise ValueError("enum_list must have 'values'")
        if not isinstance(v["values"], list):
            raise ValueError("enum_list 'values' must be a list")
        return v


# Union of all generator types
GeneratorSpec = Union[
    SequenceGenerator,
    ChoiceGenerator,
    DistributionGenerator,
    DatetimeSeriesGenerator,
    FakerGenerator,
    LookupGenerator,
    ExpressionGenerator,
    EnumListGenerator,
]


# ============================================================================
# Modifier Specs
# ============================================================================

class ModifierSpec(BaseModel):
    """Generic modifier specification."""
    transform: Literal[
        "multiply", "add", "clamp", "jitter", "map_values",
        "seasonality", "time_jitter", "effect", "outliers", "trend"
    ]
    args: dict


# ============================================================================
# Column & Node
# ============================================================================

class Fanout(BaseModel):
    """Fanout specification for fact tables."""
    model_config = ConfigDict(populate_by_name=True)

    distribution: Literal["poisson", "uniform"]
    lambda_: Optional[float] = Field(None, alias="lambda")
    min: Optional[int] = None
    max: Optional[int] = None
    clamp: Optional[list[int]] = None


class Column(BaseModel):
    """Column definition."""
    name: str
    type: Literal["int", "float", "string", "bool", "datetime", "date"]
    nullable: bool = False
    generator: dict  # Will be validated as one of the GeneratorSpec types
    modifiers: Optional[list[ModifierSpec]] = None
    constraints: Optional[dict] = None

    @field_validator("generator")
    @classmethod
    def validate_generator(cls, v):
        # Check that exactly one generator key exists
        valid_keys = {
            "sequence", "choice", "distribution", "datetime_series",
            "faker", "lookup", "expression", "enum_list"
        }
        gen_keys = set(v.keys()) & valid_keys

        if len(gen_keys) == 0:
            raise ValueError(f"Column must have one of: {valid_keys}")
        if len(gen_keys) > 1:
            raise ValueError(f"Column can only have one generator, found: {gen_keys}")

        # Run type-specific validation
        gen_type = list(gen_keys)[0]

        if gen_type == "sequence":
            SequenceGenerator.model_validate(v)
        elif gen_type == "choice":
            ChoiceGenerator.model_validate(v)
        elif gen_type == "distribution":
            DistributionGenerator.model_validate(v)
        elif gen_type == "datetime_series":
            DatetimeSeriesGenerator.model_validate(v)
        elif gen_type == "faker":
            FakerGenerator.model_validate(v)
        elif gen_type == "lookup":
            LookupGenerator.model_validate(v)
        elif gen_type == "expression":
            ExpressionGenerator.model_validate(v)
        elif gen_type == "enum_list":
            EnumListGenerator.model_validate(v)

        return v


class Node(BaseModel):
    """Entity, fact, or vocab table definition."""
    id: str
    kind: Literal["entity", "fact", "vocab"]
    pk: str
    parents: Optional[list[str]] = None
    fanout: Optional[Fanout] = None
    columns: list[Column]
    modifiers: Optional[list[ModifierSpec]] = None  # Table-level modifiers (e.g., effects)
    rows: Optional[int] = None  # For entities: override default row count
    segment_behavior: Optional[dict] = None  # Behavioral segmentation config

    @model_validator(mode="after")
    def validate_node(self):
        # Vocab nodes are like entities but use enum_list generator
        if self.kind == "vocab":
            # Vocab should not have parents or fanout
            if self.parents:
                raise ValueError("vocab nodes cannot have parents")
            if self.fanout:
                raise ValueError("vocab nodes cannot have fanout")

        # Facts can have parents and fanout
        if self.kind == "fact":
            if self.parents and len(self.parents) > 1:
                # MVP: warn about multiple parents (complex)
                pass
        else:
            # Entities cannot have parents or fanout
            if self.parents:
                raise ValueError("entity nodes cannot have 'parents'")
            if self.fanout:
                raise ValueError("entity nodes cannot have 'fanout'")

        # Ensure PK column exists
        pk_exists = any(col.name == self.pk for col in self.columns)
        if not pk_exists:
            raise ValueError(f"pk '{self.pk}' not found in columns")

        return self


# ============================================================================
# Constraints
# ============================================================================

class ForeignKey(BaseModel):
    """Foreign key constraint."""
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(..., alias="from")
    to: str

    @field_validator("from_", "to")
    @classmethod
    def validate_ref(cls, v):
        if not isinstance(v, str) or "." not in v:
            raise ValueError("Reference must be in format 'table.column'")
        return v


class RangeConstraint(BaseModel):
    """Range constraint for numeric columns."""
    attr: str
    min: Optional[float] = None
    max: Optional[float] = None

    @field_validator("attr")
    @classmethod
    def validate_attr(cls, v):
        if "." not in v:
            raise ValueError("attr must be in format 'table.column'")
        return v


class InequalityConstraint(BaseModel):
    """Inequality constraint between columns."""
    left: str
    op: Literal["<", "<=", ">", ">=", "=="]
    right: str


class PatternConstraint(BaseModel):
    """Regex pattern constraint."""
    attr: str
    regex: str


class EnumConstraint(BaseModel):
    """Enum membership constraint."""
    attr: str
    values: Optional[list[Any]] = None
    enum_ref: Optional[str] = None


class Constraints(BaseModel):
    """All constraint definitions."""
    unique: Optional[list[str]] = None
    foreign_keys: Optional[list[ForeignKey]] = None
    ranges: Optional[list[RangeConstraint]] = None
    inequalities: Optional[list[InequalityConstraint]] = None
    pattern: Optional[list[PatternConstraint]] = None
    enum: Optional[list[EnumConstraint]] = None


# ============================================================================
# Targets
# ============================================================================

class WeekendShareTarget(BaseModel):
    """Weekend share target validation."""
    table: str
    timestamp: str
    min: float
    max: float


class MeanInRangeTarget(BaseModel):
    """Mean value range target."""
    table: str
    column: str
    min: float
    max: float


class CompositeEffectInfluence(BaseModel):
    """Single influence in composite effect."""
    kind: Literal["seasonality", "effect", "outliers"]
    # Fields depend on kind, keep flexible for now
    dimension: Optional[str] = None
    weights: Optional[list[float]] = None
    table: Optional[str] = None
    on: Optional[dict] = None
    field: Optional[str] = None
    default: Optional[float] = None
    rate: Optional[float] = None
    mode: Optional[str] = None


class CompositeEffectTarget(BaseModel):
    """Composite effect validation."""
    table: str
    metric: str
    influences: list[CompositeEffectInfluence]
    tolerance: dict  # {mae: float, mape: float}


class Targets(BaseModel):
    """Quality targets for validation."""
    weekend_share: Optional[WeekendShareTarget] = None
    mean_in_range: Optional[MeanInRangeTarget] = None
    composite_effect: Optional[CompositeEffectTarget] = None


# ============================================================================
# Timeframe
# ============================================================================

class Timeframe(BaseModel):
    """Timeframe definition."""
    start: str  # ISO8601
    end: str    # ISO8601
    freq: str   # pandas offset alias

    @field_validator("start", "end")
    @classmethod
    def validate_datetime(cls, v):
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"Invalid ISO8601 datetime: {v}")
        return v


# ============================================================================
# Top-Level Schema
# ============================================================================

class Metadata(BaseModel):
    """Schema metadata."""
    name: str


class Dataset(BaseModel):
    """Top-level Datagen schema."""
    model_config = ConfigDict(extra="forbid")  # Reject unknown fields

    version: str
    metadata: Metadata
    timeframe: Timeframe
    nodes: list[Node]
    constraints: Constraints
    targets: Optional[Targets] = None
    dag: Optional[list[list[str]]] = None

    @field_validator("version")
    @classmethod
    def validate_version(cls, v):
        if v != "1.0":
            raise ValueError(f"Unsupported version: {v}. Expected '1.0'")
        return v

    @model_validator(mode="after")
    def validate_dataset(self):
        # Validate that all node ids are unique
        node_ids = [n.id for n in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Duplicate node ids found")

        # If DAG provided, validate all ids exist
        if self.dag:
            dag_ids = {nid for level in self.dag for nid in level}
            node_id_set = set(node_ids)
            if dag_ids != node_id_set:
                missing = dag_ids - node_id_set
                extra = node_id_set - dag_ids
                msg = []
                if missing:
                    msg.append(f"DAG references unknown nodes: {missing}")
                if extra:
                    msg.append(f"DAG missing nodes: {extra}")
                raise ValueError("; ".join(msg))

        return self


# ============================================================================
# Validation Helper
# ============================================================================

def validate_schema(schema_dict: dict) -> Dataset:
    """
    Validate a schema dictionary against the Datagen DSL.

    This includes both structural validation (Pydantic) and
    comprehensive preflight validation to catch runtime errors.

    Args:
        schema_dict: Raw schema dictionary

    Returns:
        Validated Dataset model

    Raises:
        ValidationError: If schema is invalid
        ValueError: If preflight validation fails
    """
    # Step 1: Structural validation with Pydantic
    dataset = Dataset.model_validate(schema_dict)

    # Step 2: Preflight validation to catch runtime errors
    from .preflight import preflight_validate
    preflight_validate(dataset)

    return dataset
