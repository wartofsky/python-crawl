from pydantic import BaseModel, Field
from typing import List, Optional


class StaffMember(BaseModel):
    """Modelo para representar un miembro del staff."""
    name: str = Field(description="Nombre completo del empleado")
    role: Optional[str] = Field(default=None, description="Cargo o posición en la organización")
    email: Optional[str] = Field(default=None, description="Email (de mailto:, texto visible, o inferido)")


class StaffDirectory(BaseModel):
    """Modelo para el directorio completo de staff."""
    staff_members: List[StaffMember] = Field(default_factory=list, description="Lista de miembros del staff")
