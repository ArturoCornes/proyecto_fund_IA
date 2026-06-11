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
        self.prolog_files.append(files)

    def add_dl_files(self, files):
        self.pydatalog_files.append(files)

    def remove_pl_files(self, files):
        self.prolog_files = [f for f in self.prolog_files if f not in files]

    def remove_dl_files(self, files):
        self.pydatalog_files = [f for f in self.pydatalog_files if f not in files]

    def run_pipeline(self,pipeline):
        """Execute all pipeline stages in dependency order, collecting outputs."""
        executed = set()
        results = []
        
        def execute_stage(stage: Stage):
            # Execute dependencies first
            for dep in stage.depends_on:
                if dep.name not in executed:
                    execute_stage(dep)
            
            # Execute this stage
            match stage.engine:
                case "prolog":
                    result = self.run_prolog_stage(stage)
                case "pydatalog":
                    result = self.run_pydatalog_stage(stage)
                case _:
                    raise ValueError(f"Unknown engine: {stage.engine}")
            
            executed.add(stage.name)
            results.append(result)
            return result
        
        # Execute all top-level stages (those not depended on by others)
        all_stages = pipeline.get_stages()
        depended_on = {s.name for s in all_stages for s in s.depends_on}
        top_level = [s for s in all_stages if s.name not in depended_on]
        
        # If all stages are depended on, just execute them all
        stages_to_run = top_level if top_level else all_stages
        for stage in stages_to_run:
            execute_stage(stage)
        
        return results
    
    def run_prolog_stage(self, stage: Stage):
        """Load Prolog rules and execute queries, returning results."""
        if stage.rule_file:
            self._prologw.load_pl(stage.rule_file)
        
        results = []
        for query in stage.queries:
            result = self._prologw.query(query)
            results.append(result)
        
        # Store outputs back into the knowledge base
        for fact in stage.outputs:
            self._prologw.add_fact(fact)
        print(f"stage: {stage.name} run")
        return results

    def run_pydatalog_stage(self, stage: Stage):
        """Load PyDatalog module and execute queries, returning results."""
        if stage.rule_file:
            self._pydatalogw.load_pydatalog_file(stage.rule_file)
        
        results = []
        for query in stage.queries:
            # Query can be a string (function name) or a Query object
            func_name = query.query_str if isinstance(query, Query) else query
            result = self._pydatalogw.query(func_name)
            results.append(result)
        print(f"stage: {stage.name} run")
        return results
