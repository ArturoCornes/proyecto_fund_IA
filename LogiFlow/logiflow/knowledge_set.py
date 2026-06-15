class KnowledgeSet:
    """
    A standardized Data Transfer Object (DTO) for symbolic engines.
    Stores facts as a dictionary mapping a predicate name to a list of atom tuples.
    """
    def __init__(self):
        self.facts: dict[str, list[tuple]] = {}

    def add_fact(self, predicate: str, *atoms):
        if predicate not in self.facts:
            self.facts[predicate] = []
        self.facts[predicate].append(atoms)

    def merge(self, other: 'KnowledgeSet'):
        """Merges facts from another KnowledgeSet into this one."""
        if not other:
            return
        for predicate, rows in other.facts.items():
            if predicate not in self.facts:
                self.facts[predicate] = []
            self.facts[predicate].extend(rows)

    def __str__(self):
        return str(self.facts)
