import logging
from typing import List, Tuple, Dict
import json
import copy

class SchemaValidator:
    """Validates compliance constraints, bounds, and tag presence."""
    
    def __init__(self, schema_rules: dict):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.schema = schema_rules
        self.anchors = self.schema.get("extraction_meta", {}).get("anchors", [])
        
    def checkboundaries(self, raw_data: Dict)->List[str]:
        failures: List[str] = []
        metadata = raw_data.get("metadata", {})    
        for anchor in self.anchors:
            field_name = anchor.get("name")
            is_required = anchor.get("required", False)
            allowed_values = anchor.get("allowed_values")
            extracted_value = metadata.get(field_name)
            if is_required and extracted_value is None:
                failures.append(f"Missing mandatory field: '{field_name}'")
                continue  
            if extracted_value is not None and allowed_values is not None:
                items = extracted_value if isinstance(extracted_value, list) else [extracted_value]
                for item in items:
                    if str(item).strip() not in allowed_values:
                        failures.append(f"Value violation on '{field_name}': Element '{item}' is out of bounds.")
        return failures 

    def validate(self,raw_data:dict)->Tuple[bool,List[str],Dict]:
        boundary_failures = self.checkboundaries(raw_data=raw_data)
        #self.logger.info("*******Start******************")
        math_pass, trans_errs, clean_data = self.transform(raw_data=raw_data)

        if len(boundary_failures) == 0 and len(trans_errs) == 0:
            return True, [], clean_data
        else:
            errors = boundary_failures + trans_errs
            return False, errors, clean_data
        
    def transform(self, raw_data: dict) -> Tuple[bool, List[str], dict]:

        transformed = copy.deepcopy(raw_data)  # Better deep copy

        metadata = transformed.get("metadata", {})
        failures: List[str] = []

        # 1. Dynamic Matrix Array Padding 
        industry_fields = ["Industry risk", "Industry risk score", "Industry weight"]
        max_len = max(len(metadata.get(f, [])) if isinstance(metadata.get(f, []), list) else (1 if metadata.get(f) is not None else 0) for f in industry_fields)
        anchor_defaults = {a.get("name"): a.get("default") for a in self.anchors if "default" in a}

        for field in industry_fields:
            val = metadata.get(field, [])
            val_list = val if isinstance(val, list) else ([val] if val is not None else [])
            while len(val_list) < max_len:
                val_list.append(anchor_defaults.get(field))
            metadata[field] = val_list

        # 2. Parallel Vector Structural Object Mapping
        structured_industries = []
        for s, sc, w in zip(metadata.get("Industry risk", []), metadata.get("Industry risk score", []), metadata.get("Industry weight", [])):
            if isinstance(w, (int, float)):
                final_weight = f"{int(round(w*100))}%" if w <= 1.0 else f"{int(w)}%"
            else:
                final_weight = str(w or "0%")
            
            structured_industries.append({
                "sector": s, 
                "Industry risk score": "" if sc is None else str(sc), 
                "Industry weight": final_weight
            })
        
        metadata["Industry risk"] = structured_industries
        metadata.pop("Industry risk score", None)
        metadata.pop("Industry weight", None)

        # 3. Mathematical Sum Allocation Constraints Checking
        total_weight = 0.0
        #self.logger.info("*******1111111111******************")

        for item in structured_industries:
            try:
                total_weight += float(item.get("Industry weight", "0%").replace("%", "").strip())
                #self.logger.info("*******ind   Weight ****************** %s", total_weight )

            except ValueError:
                
                failures.append("Failed parsing allocation percentage.")
               
        #self.logger.info("*******Total    Weight ****************** %s", total_weight )
        if not failures and round(total_weight, 2) != 100.0:
            failures.append(f"Mathematical allocation error: Combined weights sum to {total_weight}% instead of 100%.")

        transformed["metadata"] = metadata
        return len(failures) == 0, failures, transformed