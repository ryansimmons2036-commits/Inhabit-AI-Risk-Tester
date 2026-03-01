import csv
import os
from collections import Counter, defaultdict
from datetime import datetime

LOG_PATH = os.path.join("reports", "manual_run_log.csv")
OUT_PATH = os.path.join("reports", "executive_summary.md")

def norm(s: str) -> str:
    return (s or "").strip()

def split_flags(flag_str: str) -> list[str]:
    # pattern_flag examples:
    # "A | B | C" or "A|B|C" or ""
    s = norm(flag_str)
    if not s:
        return []
    parts = [p.strip() for p in s.split("|")]
    return [p for p in parts if p]

def rollup_cluster(cluster: str) -> str:
    """
    Roll up 'Privacy & Data Leakage / Tenant PII Disclosure' -> 'Privacy & Data Leakage'
    If there's no '/', returns the full string.
    """
    c = norm(cluster)
    if "/" in c:
        return c.split("/", 1)[0].strip()
    return c

def subcluster_name(cluster: str) -> str:
    """
    Extract subcluster detail 'Tenant PII Disclosure' from
    'Privacy & Data Leakage / Tenant PII Disclosure'
    If there's no '/', returns '(unspecified)'.
    """
    c = norm(cluster)
    if "/" in c:
        return c.split("/", 1)[1].strip()
    return "(unspecified)"

def main():
    if not os.path.exists(LOG_PATH):
        raise FileNotFoundError(f"Missing log file: {LOG_PATH}")

    rows = []
    with open(LOG_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # Skip empty lines
            if not any((v or "").strip() for v in r.values()):
                continue
            rows.append(r)

    total = len(rows)
    unique_test_ids = len(set(norm(r.get("test_id")) for r in rows if norm(r.get("test_id"))))
    if total == 0:
        raise ValueError("manual_run_log.csv has no data rows.")

    # Aggregate risk levels
    risk_counts = Counter(norm(r.get("risk_level")) for r in rows)

    # Aggregate clusters: rollup + subcluster
    rollup_counts = Counter()
    subcluster_counts = defaultdict(Counter)
    rollup_risk_counts = defaultdict(Counter)
    for r in rows:
        cluster_full = norm(r.get("cluster"))
        risk = norm(r.get("risk_level"))
        if not cluster_full:
            continue

        top = rollup_cluster(cluster_full)
        sub = subcluster_name(cluster_full)

        rollup_counts[top] += 1
        subcluster_counts[top][sub] += 1
        if risk:
            rollup_risk_counts[top][risk] += 1

    # Aggregate pattern flags
    flag_counts = Counter()
    for r in rows:
        for flag in split_flags(r.get("pattern_flag", "")):
            flag_counts[flag] += 1

    top_flags = flag_counts.most_common(10)

    # Highest risk items (for quick callout)
    high_risk = [r for r in rows if norm(r.get("risk_level")) == "High"]
    medium_risk = [r for r in rows if norm(r.get("risk_level")) == "Medium"]

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Write executive summary markdown
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    def fmt_count(label: str) -> str:
        return str(risk_counts.get(label, 0))
        
    def pluralize(count: int, word: str) -> str:
        return f"{count} {word}" if count == 1 else f"{count} {word}s"

    with open(OUT_PATH, "w", encoding="utf-8") as out:
        out.write("# Inhabit AI Risk Tester\n")
        out.write("## Executive Summary (Auto-Generated)\n\n")
        out.write(f"**Generated:** {now}\n\n")

        out.write("### Scope\n")
        out.write(f"- **Total executions:** {total}\n")
        out.write(f"- **Unique scenarios (test_id):** {unique_test_ids}\n")
        out.write("- **Source of truth:** `reports/manual_run_log.csv`\n")
        out.write("- **Artifacts:** JSON outputs in `outputs/`\n\n")

        out.write("### Risk Distribution\n")
        out.write(f"- **High:** {fmt_count('High')}\n")
        out.write(f"- **Medium:** {fmt_count('Medium')}\n")
        out.write(f"- **Low:** {fmt_count('Low')}\n\n")

        out.write("### Cluster Coverage (Rollup + Detail)\n")
        for top, total_top in rollup_counts.most_common():
            # Risk distribution per rollup (if present)
            h = rollup_risk_counts[top].get("High", 0)
            m = rollup_risk_counts[top].get("Medium", 0)
            l = rollup_risk_counts[top].get("Low", 0)

            out.write(f"- **{top}**: {pluralize(total_top, 'test')}  _(High: {h}, Medium: {m}, Low: {l})_\n")

            # Subcluster breakdown
            for sub, sub_count in subcluster_counts[top].most_common():
                out.write(f"  - {sub}: {pluralize(sub_count, 'test')}\n")

        out.write("\n")

        if top_flags:
            out.write("### Top Recurring Pattern Flags\n")
            for flag, c in top_flags:
                out.write(f"- `{flag}`: {c}\n")
            out.write("\n")

        # Callouts
        out.write("### High-Risk Callouts\n")
        if not high_risk:
            out.write("- No High-risk results logged.\n\n")
        else:
            # Show up to 5 high-risk items
            for r in high_risk[:5]:
                out.write(
                    f"- **{norm(r.get('test_id'))}** ({norm(r.get('cluster'))}): "
                    f"{norm(r.get('question'))}\n"
                )
            out.write("\n")

        out.write("### Medium-Risk Callouts\n")
        if not medium_risk:
            out.write("- No Medium-risk results logged.\n\n")
        else:
            for r in medium_risk[:5]:
                out.write(
                    f"- **{norm(r.get('test_id'))}** ({norm(r.get('cluster'))}): "
                    f"{norm(r.get('question'))}\n"
                )
            out.write("\n")

        out.write("### Recommended Next Steps\n")
        out.write("- Add hard-stop guardrails for protected-class steering (Fair Housing) and cross-tenant data requests (Privacy).\n")
        out.write("- Add response templates that include brief legal/privacy context + an authorized next step (e.g., secure portal / verified channel).\n")
        out.write("- Expand coverage to additional clusters (Fraud, Prompt Injection, Governance & Escalation) once baseline guardrails are confirmed.\n")

    print(f"✅ Wrote {OUT_PATH} from {total} logged tests.")

if __name__ == "__main__":
    main()