"""
StampFly System Identification Toolkit
StampFly システム同定ツールキット

Modules for identifying physical parameters from flight logs.
フライトログから物理パラメータを同定するモジュール群。

Submodules:
- defaults: Default StampFly physical parameters
- params: Parameter management (load, save, diff, export)
- noise: Sensor noise characterization (Allan variance)
- inertia: Moment of inertia estimation (step response)
- motor: Motor dynamics identification (Ct, Cq, τm)
- drag: Aerodynamic drag estimation (coastdown analysis)
- validation: Physical consistency validation
- visualizer: Plotting utilities
"""

from .defaults import DEFAULT_PARAMS, get_default_params, get_flat_defaults
from .params import (
    load_params,
    save_params,
    merge_params,
    diff_params,
    validate_params,
    flatten_params,
    create_result_params,
    export_to_c_header,
)
from .noise import (
    compute_allan_variance,
    extract_noise_params,
    estimate_sensor_noise,
    load_and_estimate,
    NoiseEstimate,
    AllanResult,
)
from .inertia import (
    estimate_inertia,
    load_step_response,
    reconstruct_torques,
    InertiaResult,
)
from .motor import (
    estimate_motor_params,
    MotorResult,
)
from .plant_fit import (
    fit_plant,
    compute_fit_timeseries,
    PlantFitResult,
    REFERENCE_PLANT_GAINS,
)
from .drag import (
    estimate_drag,
    DragResult,
)
from .validation import (
    validate_params_comprehensive,
    cross_validate_inertia_thrust,
    ValidationResult,
)

__all__ = [
    # Defaults
    "DEFAULT_PARAMS",
    "get_default_params",
    "get_flat_defaults",
    # Params
    "load_params",
    "save_params",
    "merge_params",
    "diff_params",
    "validate_params",
    "flatten_params",
    "create_result_params",
    "export_to_c_header",
    # Noise
    "compute_allan_variance",
    "extract_noise_params",
    "estimate_sensor_noise",
    "load_and_estimate",
    "NoiseEstimate",
    "AllanResult",
    # Inertia
    "estimate_inertia",
    "load_step_response",
    "reconstruct_torques",
    "InertiaResult",
    # Motor
    "estimate_motor_params",
    "MotorResult",
    # Plant fit
    "fit_plant",
    "compute_fit_timeseries",
    "PlantFitResult",
    "REFERENCE_PLANT_GAINS",
    # Drag
    "estimate_drag",
    "DragResult",
    # Validation
    "validate_params_comprehensive",
    "cross_validate_inertia_thrust",
    "ValidationResult",
]

__version__ = "0.1.0"
