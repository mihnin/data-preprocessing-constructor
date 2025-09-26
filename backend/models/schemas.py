from pydantic import BaseModel, field_validator
from typing import List, Dict, Any, Optional
import re

class PreprocessingMethodConfig(BaseModel):
    """
    Configuration model for a single preprocessing method.
    """
    method_id: str
    parameters: Optional[Dict[str, Any]] = {}

class PreprocessingConfig(BaseModel):
    """
    Defines the full configuration for a preprocessing job, including the dataset
    to use and a list of methods to apply.
    """
    dataset_id: str
    methods: List[PreprocessingMethodConfig]

    @field_validator('dataset_id')
    def validate_dataset_id(cls, v: str) -> str:
        """
        Ensures that the dataset_id is a valid UUID string.
        """
        # A simple regex for UUID format. For strict validation, a library could be used.
        pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        if not re.match(pattern, v):
            raise ValueError('dataset_id must be a valid UUID')
        return v

    @field_validator('methods')
    def validate_methods(cls, v: List[PreprocessingMethodConfig]) -> List[PreprocessingMethodConfig]:
        """
        Ensures that at least one preprocessing method is specified.
        """
        if not v:
            raise ValueError('At least one preprocessing method must be specified.')
        return v