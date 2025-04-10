# modules/PatternRecognition.py
import logging
from typing import Dict, Any, List, Optional
import time
import uuid
import numpy as np
from scipy.stats import pearsonr # Import for correlation calculation

logger = logging.getLogger(__name__)

class PatternRecognition:
    """
    Recognizes patterns within the system's data flow for a given cycle.
    Includes examples for anomaly detection and correlation.
    """
    def __init__(self):
        logger.info("PatternRecognition initialized.")
        # Could initialize more complex state or models here
        self.cycle_history = {} # Store limited history for trend analysis?
        self.history_limit = 100

    def recognize_patterns(self, combined_data: Dict[str, Any]) -> List[Dict]:
        """
        Analyzes the combined data from a cycle to find patterns.

        Args:
            combined_data (Dict[str, Any]): Dictionary containing input data,
                                             node outputs, perspective outputs, etc.
        """
        patterns = []
        cycle = combined_data.get("cycle", "unknown")
        node_outputs = combined_data.get("node_outputs", {})
        input_data = combined_data.get("input_data", {})
        input_id = input_data.get("id") if input_data else None

        # --- Pattern 1: High Energy Consumption Anomaly (from previous example) ---
        # (Keep the previous anomaly detection example or refine it)
        energy_levels = [res.get("energy_remaining") for res in node_outputs.values()
                          if res and "energy_remaining" in res]
        if energy_levels: # Avoid division by zero or errors on empty list
             avg_energy = np.mean(energy_levels)
             nodes_with_high_consumption = [
                 node_id for node_id, result in node_outputs.items()
                 if result and "energy_remaining" in result and result["energy_remaining"] < avg_energy * 0.5 # Threshold
             ]
             if nodes_with_high_consumption:
                  pattern_id = f"p_high_energy_{cycle}_{str(uuid.uuid4())[:4]}"
                  patterns.append({
                      "id": pattern_id, "type": "anomaly",
                      "description": "Unusually high energy consumption detected.",
                      "confidence": 0.6, "involved_nodes": nodes_with_high_consumption,
                      "related_data_ids": [input_id] if input_id else [],
                      "timestamp": time.time(),
                      "details": {"average_energy_after_processing": avg_energy}
                  })


        # --- Pattern 2: Concept Co-occurrence (from previous example) ---
        # (Keep the previous co-occurrence example)
        entity_counts = {}
        nodes_reporting_entities = []
        for node_id, result in node_outputs.items():
            if result and result.get("status") == "success" and "entities" in result and result["entities"]:
                nodes_reporting_entities.append(node_id)
                for entity, label in result["entities"]:
                    key = (entity, label)
                    entity_counts[key] = entity_counts.get(key, 0) + 1
        cooccurring_entities = [entity for entity, count in entity_counts.items() if count > 1]
        if cooccurring_entities:
             pattern_id = f"p_cooccur_{cycle}_{str(uuid.uuid4())[:4]}"
             patterns.append({
                 "id": pattern_id, "type": "correlation",
                 "description": "Multiple nodes concurrently identified common entities.",
                 "confidence": min(0.95, 0.7 + len(cooccurring_entities) * 0.05),
                 "involved_nodes": list(set(nodes_reporting_entities)), # Unique nodes
                 "related_data_ids": [input_id] if input_id else [],
                 "timestamp": time.time(),
                 "details": {"cooccurring_entities": [f"{e[0]} ({e[1]})" for e in cooccurring_entities]}
             })


        # --- Pattern 3: Numerical Data Correlation (More Concrete Example) ---
        # Check if the input data contained numerical values processed by multiple nodes
        if input_data and 'values' in input_data and isinstance(input_data['values'], list):
            original_values = np.array(input_data['values'])
            # Collect numerical results from nodes (e.g., if a capability node returned a list)
            numerical_outputs = {}
            for node_id, result in node_outputs.items():
                 # Check if the result indicates processing of numerical data
                 # (This depends on how your CapabilityNodes report their results)
                 # Example: Assume result['result'] contains a list of numbers if successful
                 if result and result.get('status') == 'success' and 'result' in result and isinstance(result['result'], list) and len(result['result']) == len(original_values):
                      numerical_outputs[node_id] = np.array(result['result'])
                 # Example 2: Check for a specific action reported by generic node
                 elif result and result.get('action') == 'processed_numerical' and 'value_count' in result:
                      # We don't have the *processed* values here, maybe just check *if* it processed numbers
                      pass # Cannot correlate without output values

            # If we have at least one numerical output matching input length, check correlation
            correlated_nodes = []
            correlation_details = {}
            if len(numerical_outputs) >= 1 and len(original_values) > 1:
                for node_id, output_values in numerical_outputs.items():
                    try:
                        # Calculate Pearson correlation between input and output
                        correlation_coefficient, p_value = pearsonr(original_values, output_values)

                        # Define thresholds for strong correlation
                        correlation_threshold = 0.8
                        p_value_threshold = 0.05

                        if abs(correlation_coefficient) >= correlation_threshold and p_value < p_value_threshold:
                            correlated_nodes.append(node_id)
                            correlation_details[node_id] = {"correlation": round(correlation_coefficient, 3), "p_value": round(p_value, 4)}
                            logger.info(f"Strong correlation found for Node {node_id}: r={correlation_coefficient:.3f}, p={p_value:.4f}")

                    except ValueError as ve:
                        logger.warning(f"Could not calculate correlation for Node {node_id}: {ve}") # e.g., if arrays have zero variance
                    except Exception as e:
                        logger.error(f"Error calculating correlation for Node {node_id}: {e}", exc_info=True)


            if correlated_nodes:
                 pattern_id = f"p_num_corr_{cycle}_{str(uuid.uuid4())[:4]}"
                 patterns.append({
                     "id": pattern_id,
                     "type": "correlation",
                     "description": "Strong correlation detected between input numerical data and node output(s).",
                     "confidence": 0.8, # Confidence could vary based on p-value or coefficient strength
                     "involved_nodes": correlated_nodes,
                     "related_data_ids": [input_id] if input_id else [],
                     "timestamp": time.time(),
                     "details": {"correlations": correlation_details}
                 })

        # Update history (Example - store number of patterns found per cycle)
        self.cycle_history[cycle] = len(patterns)
        if len(self.cycle_history) > self.history_limit:
            # Remove oldest entry
            oldest_cycle = min(self.cycle_history.keys())
            del self.cycle_history[oldest_cycle]

        return patterns

# Example Usage (if run directly)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pattern_recognizer = PatternRecognition()

    # Simulate combined data with numerical correlation potential
    simulated_data = {
        "cycle": 102,
        "input_data": {"id": "data_102_xyz", "type": "numerical", "values": [1.1, 2.3, 2.9, 4.1, 5.0]},
        "node_outputs": {
            "node_A": {"status": "success", "action": "processed_numerical", "result": [1.0, 2.1, 3.0, 4.0, 5.1]}, # High correlation
            "node_B": {"status": "success", "action": "processed_numerical", "result": [5.0, 1.0, 3.5, 2.0, 4.2]}, # Low correlation
            "node_C": {"status": "success", "action": "processed_numerical", "result": [-1.2, -2.1, -3.1, -3.9, -5.2]}, # High negative correlation
            "node_D": {"status": "success", "message": "Processed text data"}, # Irrelevant node
            "node_E": {"status": "success", "action": "processed_numerical", "result": [1, 1, 1, 1, 1]} # Constant output (ValueError for pearsonr)
        },
        "perspective_outputs": {}
    }

    print("Running pattern recognition on simulated numerical data...")
    found_patterns = pattern_recognizer.recognize_patterns(simulated_data)

    print(f"\nFound {len(found_patterns)} patterns:")
    for i, pattern in enumerate(found_patterns):
        print(f"--- Pattern {i+1} ({pattern.get('type')}) ---")
        print(f"  Description: {pattern.get('description')}")
        print(f"  Involved Nodes: {pattern.get('involved_nodes')}")
        print(f"  Details: {pattern.get('details')}")
        print("-" * 20)
