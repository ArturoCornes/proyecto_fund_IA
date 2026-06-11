from pyDatalog import pyDatalog
from pathlib import Path

class PyDatalogWrapper:
    def load_pydatalog_file(self, file_path):
        path =  Path(file_path)
        self.module = dynamic_import(path)

    def query(self, func_name: str, *args, **kwargs):
        if not self.module:
            raise RuntimeError("No module loaded.")
            
        try:
            # 1. Safely retrieve the actual function object from the module
            func_obj = getattr(self.module, func_name)
        except AttributeError:
            raise ValueError(f"Function '{func_name}' not found in the loaded module.")
        
        # 2. Call it directly and return its output
        return func_obj(*args, **kwargs)


# written by AI:
import importlib.util
import sys
from pathlib import Path

def dynamic_import(file_path: str, module_name: str = "dynamic_mod"):
    path = Path(file_path)
    
    # 1. Create a module spec from the file path
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None:
        raise ImportError(f"Could not load spec for {file_path}")
        
    # 2. Create a new module based on the spec
    module = importlib.util.module_from_spec(spec)
    
    # 3. Optional: Add it to sys.modules so imports inside the file work correctly
    sys.modules[module_name] = module
    
    # 4. Execute the module to populate its attributes/functions
    spec.loader.exec_module(module)
    
    return module

if __name__ == "__main__":
    wpr = PyDatalogWrapper()
    wpr.load_pydatalog_file("datos_datalog.py")
    wpr.query("extraer_datos_para_prolog")