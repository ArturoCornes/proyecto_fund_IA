from pyswip import Prolog

class Query:
    """A prolog query, includes return value once executed by a PrologWrapper instance"""
    def __init__(self, query: str):
        self.query_str = query
        self.return_val = None
    
    def __str__(self):
        return f"query: {self.query_str} \nresponse: {str(self.return_val)}"

class Fact:
    def __init__(self, predicate: str, *atoms):
        self.predicate: str = predicate
        if atoms == None:
            self.atoms = None
            return
        
        self.atoms: list|None = list(atoms)

    def _format_atom(self, atom) -> str:
        if self.atoms == None:
            return
        
        if isinstance(atom, str):
            return "'" + atom.replace("\\", "\\\\").replace("'", "\\'") + "'"

        return str(atom)
    
    def add_atoms(self,*atoms):
        self.atoms: list|None = list(atoms)
    
    def __str__(self) -> str:
        if not self.atoms:
            return self.predicate

        return f"{self.predicate}({', '.join(self._format_atom(atom) for atom in self.atoms)})"

class PrologWrapper:
    def __init__(self):
        self.prolog = Prolog()
        self.queries: list[Query] = []  

    def add_fact(self, fact: str|Fact) -> None:
        """
        Adds a fact to the knowledge base.
        Parameters:
            fact - a string of the form fact(atom_1,atom_2,...)
        """
        self.prolog.assertz(str(fact))
    
    def remove(self, target: str| Fact, remove_all: bool = False) -> None:
        """
        Removes facts or rules from the knowledge base (retract).
        If remove_all is True, uses retractall.
        """
        command = "retractall" if remove_all else "retract"
        
        list(self.prolog.query(f"{command}(({target}))"))
    
    def decode_bytes(self, obj):
        """Recursively decode byte strings to utf-8 strings."""
        if isinstance(obj, bytes):
            return obj.decode('utf-8')
        elif isinstance(obj, dict):
            return {k: self.decode_bytes(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.decode_bytes(i) for i in obj]
        return obj

    def query(self, query: str | Query) -> Query:
        """
        Performs a query to the knowledge base.
        Parameters:
            query - a string with a query e.g.: fact(X,Y) 
                       or an instance of the Query class
        """
        if isinstance(query, str):
            query = Query(query)

        raw_results = list(self.prolog.query(query.query_str))
        query.return_val = self.decode_bytes(raw_results) 
        self.queries.append(query)
        return query
    
    def load_pl(self, path: str) -> None:
        """
        Loads a .pl or .pro file
        Parameters:
        path - a string with the path to the file 
        """
        self.prolog.consult(path)
    



if __name__ == "__main__":
    engine = PrologWrapper()

    engine.add_fact('father(pepe,juan)')
    engine.add_fact('father(pepe,julieta)')

    print(engine.query('father(pepe,Y)'))

    engine.remove('father(pepe,juan)')
    engine.remove('father(pepe,julieta)')

    print(engine.query('father(pepe,Y)'))

    engine.add_fact('father(pepe,juan)')
    engine.add_fact('father(pepe,julieta)')

    print(engine.query('father(pepe,Y)'))

    engine.remove('father(X,Y)', True)

    print(engine.query('father(pepe,Y)'))