class Student:
    def __init__(self, name, grade, section):

        self.name = name
        self.grade = grade
        self.section = section
        self.scores = {}

    def add_score(self, subject, score):
        self.scores[subject] = score


student = Student("鈴木", 2, "B")
student.add_score("数学", "80点")
student.add_score("英語", "70点")
student.add_score("国語", "90点")

print(student.scores)
