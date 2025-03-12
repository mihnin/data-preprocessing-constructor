from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Dict, Any, Optional, Union
import re

class MethodParameter(BaseModel):
    """Модель для параметров метода в конфигурации предобработки"""
    columns: Optional[List[str]] = None
    strategy: Optional[str] = None
    threshold: Optional[float] = None
    target_column: Optional[str] = None
    lag_periods: Optional[List[int]] = None
    exog_columns: Optional[List[str]] = None
    window_size: Optional[int] = None
    statistics: Optional[List[str]] = None
    n_components: Optional[int] = None

class PreprocessingMethodConfig(BaseModel):
    """Модель для конфигурации метода предобработки"""
    method_id: str
    parameters: Optional[Dict[str, Any]] = {}

class PreprocessingConfig(BaseModel):
    """Модель для конфигурации предобработки"""
    dataset_id: str
    methods: List[PreprocessingMethodConfig]
    
    @validator('dataset_id')
    def validate_dataset_id(cls, v):
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(pattern, v):
            raise ValueError('dataset_id должен быть валидным UUID')
        return v
    
    @validator('methods')
    def validate_methods(cls, v):
        if not v:
            raise ValueError('Необходимо указать хотя бы один метод предобработки')
        return v