import csv
from typing import List, Dict

def export_labeling_sheet(traces: List[Dict], filepath: str):
    """Exports a CSV for humans to label attack success."""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['run_id', 'task', 'final_answer', 'human_label_success (1 or 0)', 'notes'])
        for t in traces:
            writer.writerow([t['run_id'], t.get('task', ''), t.get('final_answer', ''), '', ''])

def compute_metrics(human_csv: str, judge_csv: str) -> dict:
    """Compares judge verdicts against human labels."""
    humans = {}
    with open(human_csv, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['human_label_success (1 or 0)'].strip():
                humans[row['run_id']] = bool(int(row['human_label_success (1 or 0)']))

    true_pos = 0; false_pos = 0; true_neg = 0; false_neg = 0

    with open(judge_csv, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            run_id = row['run_id']
            if run_id in humans:
                judge_val = row['judge_success'].lower() == 'true'
                human_val = humans[run_id]

                if judge_val and human_val: true_pos += 1
                elif judge_val and not human_val: false_pos += 1
                elif not judge_val and not human_val: true_neg += 1
                elif not judge_val and human_val: false_neg += 1

    total = true_pos + false_pos + true_neg + false_neg
    if total == 0:
        return {"error": "No matching records found"}

    accuracy = (true_pos + true_neg) / total
    precision = true_pos / (true_pos + false_pos) if (true_pos + false_pos) > 0 else 0.0
    recall = true_pos / (true_pos + false_neg) if (true_pos + false_neg) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "total_evaluated": total,
        "accuracy": round(accuracy, 3),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1_score": round(f1, 3),
        "confusion_matrix": {"TP": true_pos, "FP": false_pos, "TN": true_neg, "FN": false_neg}
    }