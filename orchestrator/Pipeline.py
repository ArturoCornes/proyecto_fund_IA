from __future__ import annotations
from PrologWrapper import Query, Fact

class Pipeline:
    def __init__(self):
        self.stages:list[Stage] = []

    def get_stages(self)->list[Stage]:
        return self.stages

    def add_stage(self, stage):
        self.stages.append(stage)

class Stage:
    def __init__(self, name, engine, rule_file, queries, outputs, depends_on):
        self.name:str = name
        self.engine:str = engine
        self.rule_file:str = rule_file
        self.queries:list[Query] = queries
        self.outputs:list[Fact] = outputs
        self.depends_on:list[Stage] = depends_on
