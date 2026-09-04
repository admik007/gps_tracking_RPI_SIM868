MAX_POINTS = 100

class Buffer:

    def __init__(self):
        self.points = []

    def add(self, point):

        if len(self.points) >= MAX_POINTS:
            self.points.pop(0)

        self.points.append(point.copy())

    def get(self):
        return self.points.copy()

    def clear(self):
        self.points.clear()

    def count(self):
        return len(self.points)

    def empty(self):
        return len(self.points) == 0
