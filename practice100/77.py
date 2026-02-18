class Student:
    def __init__(self, name, grade, section):

        self.name = name
        self.grade = grade
        self.section = section
        self.scores = {}

    def add_score(self, subject, score):
        self.scores[subject] = score

    def total_score(self):
        return sum(self.scores.values())


student = Student("鈴木", 2, "B")

student.grade = 3
student.section = "C"

print(student.grade)
print(student.section)
