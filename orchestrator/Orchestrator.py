from Pipeline import Pipeline, Stage
from PrologWrapper import PrologWrapper, Query, Fact
from PyDatalogWrapper import PyDatalogWrapper


class Orchestrator:

    def __init__(self):
        self.prolog_files = []
        self.pydatalog_files = []
        self._prologw =  PrologWrapper()
        self._pydatalogw =  PyDatalogWrapper()

    def get_pl_files(self):
        return self.prolog_files

    def get_dl_files(self):
        return self.pydatalog_files

    def add_pl_files(self, files):
        if isinstance(files, list):
            self.prolog_files.extend(files)
        else:
            self.prolog_files.append(files)

    def add_dl_files(self, files):
        if isinstance(files, list):
            self.pydatalog_files.extend(files)
        else:
            self.pydatalog_files.append(files)

    def remove_pl_files(self, files):
        if not isinstance(files, list):
            files = [files]
        self.prolog_files = [f for f in self.prolog_files if f not in files]

    def remove_dl_files(self, files):
        if not isinstance(files, list):
            files = [files]
        self.pydatalog_files = [f for f in self.pydatalog_files if f not in files]

    def run_pipeline(self, pipeline):
        """Execute all pipeline stages in dependency order, collecting outputs."""
        all_stages = pipeline.get_stages()
        
        # 1. Circular dependency detection (Topological check)
        visited = set()
        path = set()
        
        def check_cycles(stage):
            if stage.name in path:
                raise RecursionError(f"Circular dependency detected involving stage: {stage.name}")
            if stage.name in visited:
                return
            path.add(stage.name)
            for dep in stage.depends_on:
                check_cycles(dep)
            path.remove(stage.name)
            visited.add(stage.name)
            
        for stage in all_stages:
            check_cycles(stage)
            
        # 2. Execution
        executed = set()
        stage_results = {}
        from KnowledgeSet import KnowledgeSet
        
        def execute_stage(stage: Stage) -> KnowledgeSet:
            # Execute dependencies first
            for dep in stage.depends_on:
                if dep.name not in executed:
                    execute_stage(dep)
            
            # Gather and merge inputs from dependencies
            merged_input = KnowledgeSet()
            for dep in stage.depends_on:
                merged_input.merge(stage_results[dep.name])
            
            # Execute this stage
            match stage.engine:
                case "prolog":
                    result_ks = self.run_prolog_stage(stage, merged_input)
                case "pydatalog":
                    result_ks = self.run_pydatalog_stage(stage, merged_input)
                case _:
                    raise ValueError(f"Unknown engine: {stage.engine}")
            
            executed.add(stage.name)
            stage_results[stage.name] = result_ks
            return result_ks
        
        depended_on = {s.name for s in all_stages for s in s.depends_on}
        top_level = [s for s in all_stages if s.name not in depended_on]
        
        stages_to_run = top_level if top_level else all_stages
        
        for stage in stages_to_run:
            execute_stage(stage)
        
        return [stage_results[stage.name] for stage in all_stages]
    
    def run_prolog_stage(self, stage: Stage, merged_input: 'KnowledgeSet' = None):
        """Load Prolog rules, inject facts, and execute queries, returning a KnowledgeSet."""
        if stage.rule_file:
            self._prologw.load_pl(stage.rule_file)
        
        # Store hardcoded outputs (facts)
        for fact in stage.outputs:
            self._prologw.add_fact(fact)
            
        # Ingest data from upstream KnowledgeSet
        if merged_input:
            from PrologWrapper import Fact
            for predicate, rows in merged_input.facts.items():
                for row in rows:
                    if isinstance(row, tuple):
                        self._prologw.add_fact(Fact(predicate, *row))
                    else:
                        self._prologw.add_fact(Fact(predicate, row))
            
        from KnowledgeSet import KnowledgeSet
        output_ks = KnowledgeSet()
        
        for query in stage.queries:
            query_obj = self._prologw.query(query)
            # query_obj.return_val is a list of dicts: [{'TxID': 'tx_001', ...}]
            # We convert this into the output KnowledgeSet using the query string as predicate
            predicate = query_obj.query_str.split('(')[0].strip()
            
            for match_dict in query_obj.return_val:
                # We need to extract the values in the order of the variables
                # For simplicity, we just add the dict values as a tuple
                if isinstance(match_dict, dict):
                    output_ks.add_fact(predicate, *match_dict.values())
        
        print(f"stage: {stage.name} run")
        return output_ks

    def run_pydatalog_stage(self, stage: Stage, merged_input: 'KnowledgeSet' = None):
        """Load PyDatalog rules and execute queries, returning a KnowledgeSet."""
        if stage.rule_file:
            self._pydatalogw.load_pydatalog_file(stage.rule_file)
        
        # We could also inject merged_input into PyDatalog here if required.
        
        from KnowledgeSet import KnowledgeSet
        output_ks = KnowledgeSet()
        
        for query in stage.queries:
            query_str = query.query_str if hasattr(query, 'query_str') else query
            ks = self._pydatalogw.query(query_str)
            output_ks.merge(ks)
            
        print(f"stage: {stage.name} run")
        return output_ks
