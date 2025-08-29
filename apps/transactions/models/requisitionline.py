from dataclasses import dataclass

@dataclass
class BaseLineModel:
    # Basic placeholder fields/methods for the base line model
    id: int | None = None

class RequisitionLine(BaseLineModel):
    # Add any Requisition-specific fields or methods here
    pass