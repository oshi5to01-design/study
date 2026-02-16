class Student:
    def __init__(self, name, grade, section):

        self.name = name
        self.grade = grade
        self.section = section
        self.scores = {}


student = Student("鈴木", 2, "B")
print(student.name)
