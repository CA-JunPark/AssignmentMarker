import uuid
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Student:
    name: str
    group_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class MarkingScheme:
    assignment_id: str
    name: str
    max_score: float = 100.0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class Assignment:
    name: str
    students: List[Student] = field(default_factory=list)
    marking_schemes: List[MarkingScheme] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class Classroom:
    name: str
    assignments: List[Assignment] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class Group:
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class Grade:
    student_id: str
    marking_scheme_id: str
    score: Optional[float] = None
    note: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
