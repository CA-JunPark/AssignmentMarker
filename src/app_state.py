import json
import os
from typing import List, Optional
from src.models import Classroom, Assignment, Student, MarkingScheme, Group, Grade

class AppState:
    def __init__(self, filepath="data.txt"):
        self.filepath = filepath
        self.classrooms: List[Classroom] = []
        self.selected_classroom: Optional[Classroom] = None
        self.selected_assignment: Optional[Assignment] = None
        self.groups: List[Group] = []
        self.grades: List[Grade] = []
        self.load_from_file()

    def to_dict(self):
        return {
            "classrooms": [
                {
                    "name": c.name,
                    "id": c.id,
                    "assignments": [
                        {
                            "name": a.name,
                            "id": a.id,
                            "students": [{"name": s.name, "group_id": s.group_id, "id": s.id} for s in a.students],
                            "marking_schemes": [{"assignment_id": m.assignment_id, "name": m.name, "max_score": m.max_score, "id": m.id} for m in a.marking_schemes]
                        } for a in c.assignments
                    ]
                } for c in self.classrooms
            ],
            "groups": [{"name": g.name, "id": g.id} for g in self.groups],
            "grades": [{"student_id": g.student_id, "marking_scheme_id": g.marking_scheme_id, "score": g.score, "note": g.note, "id": g.id} for g in self.grades]
        }

    def load_from_file(self):
        if not os.path.exists(self.filepath):
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for g in data.get("groups", []):
                self.groups.append(Group(name=g["name"], id=g["id"]))
                
            for g in data.get("grades", []):
                self.grades.append(Grade(student_id=g["student_id"], marking_scheme_id=g["marking_scheme_id"], score=g["score"], note=g["note"], id=g["id"]))
                
            for c in data.get("classrooms", []):
                cls = Classroom(name=c["name"], id=c["id"])
                for a in c.get("assignments", []):
                    ast = Assignment(name=a["name"], id=a["id"])
                    for s in a.get("students", []):
                        ast.students.append(Student(name=s["name"], group_id=s.get("group_id"), id=s["id"]))
                    for m in a.get("marking_schemes", []):
                        ast.marking_schemes.append(MarkingScheme(assignment_id=m["assignment_id"], name=m["name"], max_score=m.get("max_score", 100.0), id=m["id"]))
                    cls.assignments.append(ast)
                self.classrooms.append(cls)
                
            if self.classrooms:
                self.select_classroom(self.classrooms[0])
        except Exception as e:
            print(f"Error loading data: {e}")

    def save_to_file(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4)

    def add_classroom(self, name: str):
        if any(c.name.lower() == name.lower() for c in self.classrooms):
            raise ValueError(f"Class '{name}' already exists.")
        new_class = Classroom(name=name)
        self.classrooms.append(new_class)
        if not self.selected_classroom:
            self.select_classroom(new_class)
        self.save_to_file()

    def select_classroom(self, classroom: Optional[Classroom]):
        self.selected_classroom = classroom
        if classroom and classroom.assignments:
            self.select_assignment(classroom.assignments[0])
        else:
            self.select_assignment(None)

    def add_assignment(self, classroom_id: str, name: str):
        for cls in self.classrooms:
            if cls.id == classroom_id:
                if any(a.name.lower() == name.lower() for a in cls.assignments):
                    raise ValueError(f"Assignment '{name}' already exists in this class.")
                new_assignment = Assignment(name=name)
                
                if cls.assignments:
                    prev = cls.assignments[-1]
                    for s in prev.students:
                        new_assignment.students.append(Student(name=s.name, group_id=s.group_id))
                        
                cls.assignments.append(new_assignment)
                if self.selected_classroom and self.selected_classroom.id == classroom_id:
                    if not self.selected_assignment:
                        self.select_assignment(new_assignment)
                self.save_to_file()
                break

    def select_assignment(self, assignment: Optional[Assignment]):
        self.selected_assignment = assignment

    def add_students(self, assignment_id: str, comma_separated_names: str):
        names = [n.strip() for n in comma_separated_names.split(",") if n.strip()]
        if not names: return
        for cls in self.classrooms:
            for ast in cls.assignments:
                if ast.id == assignment_id:
                    existing_names = set(s.name.lower() for s in ast.students)
                    for name in names:
                        if name.lower() in existing_names:
                            raise ValueError(f"Student '{name}' already exists in this assignment.")
                        existing_names.add(name.lower())
                        
                    for name in names:
                        ast.students.append(Student(name=name))
                    self.save_to_file()
                    return

    def add_marking_scheme(self, assignment_id: str, name: str, max_score: float = 100.0):
        for cls in self.classrooms:
            for ast in cls.assignments:
                if ast.id == assignment_id:
                    if any(m.name.lower() == name.lower() for m in ast.marking_schemes):
                        raise ValueError(f"Marking Scheme '{name}' already exists in this assignment.")
                    ast.marking_schemes.append(MarkingScheme(assignment_id=assignment_id, name=name, max_score=max_score))
                    self.save_to_file()
                    return

    def create_group(self, name: str, student_ids: List[str]):
        if any(g.name.lower() == name.lower() for g in self.groups):
            raise ValueError(f"Group '{name}' already exists.")
        group = Group(name=name)
        self.groups.append(group)
        for cls in self.classrooms:
            for ast in cls.assignments:
                for student in ast.students:
                    if student.id in student_ids:
                        student.group_id = group.id
        self.save_to_file()

    def add_student_to_group(self, student_id: str, group_id: str):
        for cls in self.classrooms:
            for ast in cls.assignments:
                for student in ast.students:
                    if student.id == student_id:
                        student.group_id = group_id
                        self.save_to_file()
                        return

    def remove_student_from_group(self, student_id: str):
        for cls in self.classrooms:
            for ast in cls.assignments:
                for student in ast.students:
                    if student.id == student_id:
                        student.group_id = None
                        self.save_to_file()
                        return

    def delete_group(self, group_id: str):
        self.groups = [g for g in self.groups if g.id != group_id]
        for cls in self.classrooms:
            for ast in cls.assignments:
                for student in ast.students:
                    if student.group_id == group_id:
                        student.group_id = None
        self.save_to_file()

    def update_grade(self, student_id: str, marking_scheme_id: str, score: Optional[float], note: str = ""):
        existing_grade = next((g for g in self.grades if g.student_id == student_id and g.marking_scheme_id == marking_scheme_id), None)
        if existing_grade:
            existing_grade.score = score
            existing_grade.note = note
        else:
            self.grades.append(Grade(student_id=student_id, marking_scheme_id=marking_scheme_id, score=score, note=note))
            
        student_group_id = None
        for cls in self.classrooms:
            for ast in cls.assignments:
                student = next((s for s in ast.students if s.id == student_id), None)
                if student and student.group_id:
                    student_group_id = student.group_id
                    break
            if student_group_id:
                break
                
        if student_group_id:
            all_grouped_students = [s for cls in self.classrooms for ast in cls.assignments for s in ast.students if s.group_id == student_group_id and s.id != student_id]
            seen = set()
            for gs in all_grouped_students:
                if gs.id in seen: continue
                seen.add(gs.id)
                g_grade = next((g for g in self.grades if g.student_id == gs.id and g.marking_scheme_id == marking_scheme_id), None)
                if g_grade:
                    g_grade.score = score
                    g_grade.note = note
                else:
                    self.grades.append(Grade(student_id=gs.id, marking_scheme_id=marking_scheme_id, score=score, note=note))
        self.save_to_file()

    def get_grade(self, student_id: str, marking_scheme_id: str) -> Optional[Grade]:
        return next((g for g in self.grades if g.student_id == student_id and g.marking_scheme_id == marking_scheme_id), None)

    def get_total_grade(self, student_id: str, assignment_id: str) -> float:
        assignment = None
        for cls in self.classrooms:
            assignment = next((a for a in cls.assignments if a.id == assignment_id), None)
            if assignment: break
        
        if not assignment: return 0.0
            
        total = 0.0
        for scheme in assignment.marking_schemes:
            grade = self.get_grade(student_id, scheme.id)
            if grade and grade.score is not None:
                total += grade.score
        return total

    def delete_classroom(self, classroom_id: str):
        self.classrooms = [c for c in self.classrooms if c.id != classroom_id]
        if self.selected_classroom and self.selected_classroom.id == classroom_id:
            self.select_classroom(self.classrooms[0] if self.classrooms else None)
        self.save_to_file()

    def delete_assignment(self, classroom_id: str, assignment_id: str):
        cls = next((c for c in self.classrooms if c.id == classroom_id), None)
        if cls:
            cls.assignments = [a for a in cls.assignments if a.id != assignment_id]
            if self.selected_assignment and self.selected_assignment.id == assignment_id:
                self.select_assignment(cls.assignments[0] if cls.assignments else None)
            self.save_to_file()

    def delete_student(self, assignment_id: str, student_id: str):
        for cls in self.classrooms:
            ast = next((a for a in cls.assignments if a.id == assignment_id), None)
            if ast:
                ast.students = [s for s in ast.students if s.id != student_id]
                self.save_to_file()
                return

    def delete_marking_scheme(self, assignment_id: str, scheme_id: str):
        for cls in self.classrooms:
            ast = next((a for a in cls.assignments if a.id == assignment_id), None)
            if ast:
                ast.marking_schemes = [s for s in ast.marking_schemes if s.id != scheme_id]
                self.save_to_file()
                return
