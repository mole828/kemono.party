
class Person:
    __name: str

    def __init__(self) -> None:
        self.__name = 'bob'

    @property
    def name(self):
        return self.__name


if __name__ == '__main__':
    p = Person()
    print(p.name)