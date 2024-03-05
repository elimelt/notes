import argparse
import re


class Section:
    def __init__(self, title, content, level, subsections=None):
        self.subsections = subsections or []
        self.title = title
        self.content = content
        self.level = level

    def __str__(self):
        return f"{'#' * self.level} {self.title}\n{self.content}\n" + "\n".join(str(sub) for sub in self.subsections)

    def __repr__(self):
        return self.__str__()

    def append_subsection(self, subsection):
        self.subsections.append(subsection)

    def remove_subsection(self, subsection):
        self.subsections.remove(subsection)

    def remove_subsection_by_title(self, title):
        for sub in self.subsections:
            if sub.title == title:
                self.subsections.remove(sub)
                break

    def get_subsection(self, title):
        for sub in self.subsections:
            if sub.title == title:
                return sub
        return None

    def debug(self):
        print(f"Title: {self.title}")
        print(f"Content: {self.content}")
        print(f"Level: {self.level}")



class MarkdownTree:
    def __init__(self, md):
        self.md = md
        self.root = Section("Root", "", 0)
        self.sections = self.parse_sections(md, self.root)

    def __str__(self):
        return "\n".join(str(section) for section in self.sections)

    def __repr__(self):
        return self.__str__()

    def debug(self, section):
        section.debug()
        for sub in section.subsections:
            self.debug(sub)


    def parse_sections(self, md: str = None, parent: Section = None):
        pass

def main(args):
    for path in args.input_paths:
        with open(path) as f:
            md = f.read()
            tree = MarkdownTree(md)
            print(tree)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Markdown Tree Utility")
    parser.add_argument('input_paths', nargs='+', help='List of input files/paths')
    parser.add_argument('-r', '--recursive', action='store_true', help='Traverse directories recursively')
     
    args = parser.parse_args()

    main(args)

    # path = 'simple.md'
    # with open (path) as f:
    #     md = f.read()
    #     tree = MarkdownTree(md)
    #     print(tree)
        # tree.debug(tree.root)

