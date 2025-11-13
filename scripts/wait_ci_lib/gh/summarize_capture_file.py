import json
from typing import Any
from rich.console import Console
from rich.tree import Tree

console = Console()

class CaptureFileSummarizer:
    RUN_FIELDS = [
        "id",
        "name",
        "status",
        "conclusion",
        "created_at",
        "updated_at",
    ]

    JOBS_FIELDS = [
        "status",
        "conclusion",
        "created_at",
        "started_at",
        "workflow_name",
    ]

    STEP_FIELDS = [
        "name",
        "status",
        "conclusion",
        "started_at",
        "completed_at",
        "number",
    ]

    def __init__(self, capture_path: str):
        self.capture_path = capture_path

    def summarize(self, as_rich_tree: bool = False) -> None:
        if as_rich_tree:
            self._summarize_to_rich_tree()
        else:
            self._summarize_to_text()

    def _summarize_to_text(self) -> None:
        """
        capture_path points to a JSON file like:

        [
            {
                "run": {...},
                "jobs": {
                    "total_count": N,
                    "jobs": [ {...job...}, ... ]
                },
                "epoch_offset": 0.6748
            },
            ...
        ]

        Only RUN_FIELDS, JOBS_FIELDS and STEP_FIELDS are used.
        """


        with open(self.capture_path, "r", encoding="utf-8") as f:
            capture_data: list[dict[str, Any]] = json.load(f)

        # Sort entries by epoch_offset
        entries = sorted(
            capture_data,
            key=lambda e: float(e.get("epoch_offset", 0.0)),
        )

        # 1) Print all epoch_offsets sorted
        print("=== epoch_offsets (sorted) ===")
        for e in entries:
            print(e.get("epoch_offset"))

        # 2) Print tree: run -> jobs -> steps
        print("\n=== capture summary ===")

        for i, entry in enumerate(entries, start=1):
            epoch_offset = entry.get("epoch_offset")
            run = entry.get("run", {}) or {}
            jobs_block = entry.get("jobs", {}) or {}

            jobs_list = jobs_block.get("jobs", []) or []
            total_count = jobs_block.get("total_count")

            # Top-level entry header (include epoch_offset here)
            print(f"\n@ epoch_offset = {epoch_offset}  (entry {i})")

            # Run info
            print("  run:")
            for field in self.RUN_FIELDS:
                print(f"    {field}: {run.get(field)}")

            # Jobs info
            print("  jobs:")
            print(f"    total_count: {total_count}")

            for j_idx, job in enumerate(jobs_list, start=1):
                job_id = job.get("id")
                job_name = job.get("name")

                print(f"    - job[{j_idx}] id={job_id}, name={job_name!r}")

                # Only JOBS_FIELDS
                for field in self.JOBS_FIELDS:
                    print(f"        {field}: {job.get(field)}")

                # Steps (sorted by 'number')
                steps = job.get("steps", []) or []
                steps_sorted = sorted(steps, key=lambda s: s.get("number", 0))

                print("        steps:")
                for step in steps_sorted:
                    step_num = step.get("number")
                    print(f"          - step #{step_num}:")
                    for sf in self.STEP_FIELDS:
                        print(f"              {sf}: {step.get(sf)}")

    def _summarize_to_rich_tree(self) -> None:
        """
        capture_path points to a JSON file like:

        [
            {
                "run": {...},
                "jobs": {
                    "total_count": N,
                    "jobs": [ {...job...}, ... ]
                },
                "epoch_offset": 0.6748
            },
            ...
        ]

        Only RUN_FIELDS, JOBS_FIELDS, STEP_FIELDS are used.
        """

        with open(self.capture_path, "r", encoding="utf-8") as f:
            capture_data: list[dict[str, Any]] = json.load(f)

        # Sort entries by epoch_offset
        entries = sorted(
            capture_data,
            key=lambda e: float(e.get("epoch_offset", 0.0)),
        )

        # 1) Print all epoch_offsets sorted
        console.print("[bold]=== epoch_offsets (sorted) ===[/bold]")
        for e in entries:
            console.print(e.get("epoch_offset"))

        # 2) Build a rich Tree: epoch_offset -> run/jobs -> jobs -> steps
        root = Tree("capture summary")

        for i, entry in enumerate(entries, start=1):
            epoch_offset = entry.get("epoch_offset")
            run = entry.get("run", {}) or {}
            jobs_block = entry.get("jobs", {}) or {}

            jobs_list = jobs_block.get("jobs", []) or []
            total_count = jobs_block.get("total_count")

            # Epoch node
            epoch_node = root.add(f"[bold]epoch_offset={epoch_offset}[/bold] (entry {i})")

            # Run node
            run_label_parts = []
            for field in self.RUN_FIELDS:
                run_label_parts.append(f"{field}={run.get(field)!r}")
            run_node = epoch_node.add(
                "[cyan]run[/cyan]: " + ", ".join(run_label_parts)
            )

            # Jobs node
            jobs_node = epoch_node.add(
                f"[magenta]jobs[/magenta] (total_count={total_count})"
            )

            # Each job
            for j_idx, job in enumerate(jobs_list, start=1):
                job_id = job.get("id")
                job_name = job.get("name")

                job_header = f"job[{j_idx}] id={job_id}, name={job_name!r}, epoch_offset={epoch_offset}"
                job_node = jobs_node.add(job_header)

                # Job fields (only JOBS_FIELDS)
                for field in self.JOBS_FIELDS:
                    job_node.add(f"{field}: {job.get(field)}")

                # Steps
                steps = job.get("steps", []) or []
                steps_sorted = sorted(steps, key=lambda s: s.get("number", 0))

                steps_node = job_node.add("steps")
                for step in steps_sorted:
                    step_num = step.get("number")
                    step_header = f"step #{step_num}"
                    step_node = steps_node.add(step_header)

                    for sf in self.STEP_FIELDS:
                        step_node.add(f"{sf}: {step.get(sf)}")

        console.print()
        console.print(root)