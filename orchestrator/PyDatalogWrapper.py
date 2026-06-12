from pyDatalog import pyDatalog
from pathlib import Path
import re
from KnowledgeSet import KnowledgeSet

class PyDatalogWrapper:
    def __init__(self):
        # We will keep track of queries
        pass

    def load_pydatalog_file(self, file_path):
        path = Path(file_path)
        content = path.read_text(encoding='utf-8')
        
        # PyDatalog requires terms to be created globally before they are used.
        # We extract all words to conservatively create terms for everything.
        words = re.findall(r'\b[A-Za-z_]\w*\b', content)
        terms = list(set(words))
        if terms:
            pyDatalog.create_terms(", ".join(terms))
            
        pyDatalog.load(content)

    def query(self, query_str: str) -> KnowledgeSet:
        """
        Executes a query and returns a KnowledgeSet containing the results.
        """
        # Ensure query terms are also created
        words = re.findall(r'\b[A-Za-z_]\w*\b', query_str)
        terms = list(set(words))
        if terms:
            pyDatalog.create_terms(", ".join(terms))
            
        answer = pyDatalog.ask(query_str)
        
        # Parse predicate name from query_str (e.g. "transaccion(X, Y, Z)" -> "transaccion")
        predicate = query_str.split('(')[0].strip()
        
        ks = KnowledgeSet()
        if answer and answer.answers:
            for row in answer.answers:
                # Answer rows are tuples
                if isinstance(row, tuple):
                    ks.add_fact(predicate, *row)
                else:
                    ks.add_fact(predicate, row)
        return ks