class Student:
    def __init__(self, name, grade, section, scores):

        self.name = name
        self.grade = grade
        self.section = section
        self.scores = scores

    def add_score(self, subject, score):
        self.scores[subject] = score

    def total_score(self):
        return sum(self.scores.values())


student_1 = Student("鈴木", 2, "B", {"数学": 80, "英語": 70, "国語": 90})
student_2 = Student("田中", 2, "B", {"数学": 70, "英語": 80, "国語": 75})
student_3 = Student("斎藤", 2, "B", {"数学": 90, "英語": 85, "国語": 80})


for student in [student_1, student_2, student_3]:
    print(f"{student.name}さんの合計点数は{student.total_score()}点です")
