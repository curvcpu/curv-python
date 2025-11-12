from enum import Enum, auto
import subprocess
import sys
from time import sleep
from dataclasses import field, dataclass
from typing import Any, Callable
from collections.abc import Generator

# default poll intervals in seconds to avoid hitting API too often
DEFAULT_INTERVALS = {
    'RUN_POLL':  2,
    'JOBS_POLL': 2,
}
# how long to wait before timing out
TIMEOUT_ATTEMPTS = {
    # timeout if we make 2 minutes worth of attempts
    'RUN_POLL':  (60*2) // DEFAULT_INTERVALS['RUN_POLL'],
    # timeout if we make 10 minutes worth of attempts
    'JOBS_POLL': (60*10) // DEFAULT_INTERVALS['JOBS_POLL'],
}

def get_gh_run_json(run_id: str|int) -> str:
    cmd = ["gh", "api", "repos/{owner}/{repo}/actions/runs/" + str(run_id), "--paginate"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get GitHub Actions run for run ID {run_id}: {result.stderr.decode('utf-8')}")
    return str(result.stdout)

def get_gh_jobs_json(run_id: str|int) -> str:
    cmd = ["gh", "api", "repos/{owner}/{repo}/actions/runs/" + str(run_id) + "/jobs", "--paginate"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get GitHub Actions jobs by run ID {run_id}: {result.stderr.decode('utf-8')}")
    return str(result.stdout)

class GhStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    QUEUED = "queued"
    OTHER = "(other)"

LONGEST_STATUS_NAME_LEN = max(len(status.value) for status in GhStatus)

class GhConclusion(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    NULL = None

LONGEST_CONCLUSION_NAME_LEN = max(len(conclusion.value) if conclusion.value else 0 for conclusion in GhConclusion)

class GhJobStep:
    def __init__(self, name: str, status: GhStatus, conclusion: GhConclusion = GhConclusion.NULL):
        self.name = name
        self.status = status
        self.conclusion = conclusion

@dataclass
class ProgressStats:
    cnt_complete: int = field(init=True, default=0)
    cnt_in_progress: int = field(init=True, default=0)
    cnt_total: int = field(init=True, default=0)
    @property
    def completed(self) -> int:
        # scoring function is: cnt_complete + (cnt_in_progress * 0.5)
        return self.cnt_complete + (self.cnt_in_progress * 0.5)
    @property
    def total(self) -> int:
        return self.cnt_total
    @property
    def percent_complete(self) -> float:
        return self.completed / self.total * 100.0 if self.total > 0 else 0.0

class GhJob(list[GhJobStep]):
    def __init__(self, job_id: int, name: str, status: GhStatus, conclusion: GhConclusion | None):
        self.job_id = job_id
        self.name = name
        self.status = status
        self.conclusion = conclusion
        super().__init__()

    @classmethod
    def construct_from_job_json_element(cls, latest_jobs_json_str: str) -> Generator["GhJob", None, None]:
        """
        Given the jobs status json for a given github action run id, constructs GhJob and yields GhJob objects
        for insertion/replacement into a parent GhRun object.

            {
                "total_count": 7,
                "jobs": [
                    {
                    "id": 54831551871,
                    "run_id": 19179223310,
                    "workflow_name": "Release curvtools-v0.0.9",
                    "head_branch": "curvtools-v0.0.9",
                    "status": "completed",
                    "conclusion": "success",
                    ...
                    "steps": [
                        {
                        "name": "Set up job",
                        "status": "completed",
                        "conclusion": "success",
                        },
                        {
                        "name": "Set up job",
                        "status": "in-progress",
                        "conclusion": null,
                        },
                        ...
                    ]
                    }
                    ...
                ]
            }
        """
        import json
        jobs_json_data = json.loads(latest_jobs_json_str)
        for job in jobs_json_data["jobs"]:
            # Construct a new GhJob object
            job_id = job['id']
            job_name = job['name']
            job_status = GhStatus(job.get("status", GhStatus.PENDING.value))
            job_conclusion = GhConclusion(job.get("conclusion", GhConclusion.NULL.value))
            ghjob = cls(job_id, job_name, job_status, job_conclusion)
            for step_json_element in job["steps"]:
                ghjob.append(GhJobStep(step_json_element["name"], 
                            GhStatus(step_json_element.get("status", GhStatus.PENDING.value)), 
                            GhConclusion(step_json_element.get("conclusion", GhConclusion.NULL.value))))
            yield ghjob

    def _get_steps_count_by_status(self) -> dict[GhStatus, int]:
        steps_by_status: dict[GhStatus, int] = {}
        for status in GhStatus:
            steps_by_status[status] = 0
        for step in self:
            steps_by_status[step.status] += 1
        assert steps_by_status[GhStatus.COMPLETED] + steps_by_status[GhStatus.IN_PROGRESS] + steps_by_status[GhStatus.PENDING] + steps_by_status[GhStatus.QUEUED] == len(self), \
            f"This assertion probably failed because more statuses were added to GhStatus enum: {steps_by_status[GhStatus.COMPLETED]} + {steps_by_status[GhStatus.IN_PROGRESS]} + {steps_by_status[GhStatus.PENDING] + steps_by_status[GhStatus.QUEUED]} != {len(self)}"
        return steps_by_status
    
    def get_progress(self) -> ProgressStats:
        steps_by_status = self._get_steps_count_by_status()
        return ProgressStats(cnt_complete=steps_by_status[GhStatus.COMPLETED], 
                             cnt_in_progress=steps_by_status[GhStatus.IN_PROGRESS], 
                             cnt_total=sum(steps_by_status.values()))
    
    def get_status_summary(self, indent: int = 0) -> str:
        print_str = ""
        steps_by_status = self._get_steps_count_by_status()
        for status, count in steps_by_status.items():
            print_str += f"\n{' ' * indent}{status.value.ljust(LONGEST_STATUS_NAME_LEN)}: {count}"
        
        progress = self.get_progress()
        print_str += f"\n{' ' * indent}Job percent complete: {progress.percent_complete:.2f}% ({progress.completed:.2f}/{progress.total:.2f})"
        return print_str

class GhRun(list[GhJob]):
    def __init__(self, run_id: int, name: str, status: GhStatus = GhStatus.PENDING, conclusion: GhConclusion = GhConclusion.NULL):
        self.run_id = run_id
        self.name = name
        self.status = status
        self.conclusion = conclusion
        self.run_progress: ProgressStats = ProgressStats()
        super().__init__()
    
    @classmethod
    def construct_from_run_json_query(cls, run_id: int, poll_interval_sec: int = DEFAULT_INTERVALS['RUN_POLL']) -> "GhRun":
        import json
        run = None
        attempts = 0
        while True:
            sleep(poll_interval_sec)
            attempts += 1
            if attempts > TIMEOUT_ATTEMPTS['RUN_POLL']:
                raise TimeoutError(f"Failed to get metadata for Run ID {run_id} after {TIMEOUT_ATTEMPTS['RUN_POLL'] * poll_interval_sec} seconds")
            try:
                run_json_str = get_gh_run_json(run_id)
            except RuntimeError as e:
                print(f"GitHub Actions run for run ID {run_id} not yet available...")
                continue
            run_json_data = json.loads(run_json_str)
            run = cls(run_id, name=run_json_data.get("name", ""), status=GhStatus(run_json_data.get("status", GhStatus.PENDING.value)), conclusion=GhConclusion(run_json_data.get("conclusion", GhConclusion.NULL.value)))
            break
        assert run is not None, "Object should have been constructed if we exited the loop without raising"
        return run

    def _get_jobs_count_by_status(self) -> dict[GhStatus, int]:
        jobs_by_status: dict[GhStatus, int] = {}
        for status in GhStatus:
            jobs_by_status[status] = 0
        for job in self:
            jobs_by_status[job.status] += 1
        return jobs_by_status

    def get_progress(self) -> ProgressStats:
        cnt_complete=sum(job.get_progress().cnt_complete for job in self)
        cnt_in_progress=sum(job.get_progress().cnt_in_progress for job in self)
        cnt_total=sum(job.get_progress().cnt_total for job in self)
        if self.status != GhStatus.COMPLETED:
            self.run_progress = ProgressStats(cnt_complete=cnt_complete, 
                                              cnt_in_progress=cnt_in_progress, 
                                              cnt_total=cnt_total)
        else:
            # once selt.status is marked completed, we force progress to 100%
            self.run_progress = ProgressStats(cnt_complete=cnt_total, 
                                              cnt_in_progress=0, 
                                              cnt_total=cnt_total)
        return self.run_progress

    def update_run_status(self, latest_run_json_str: str) -> None:
        import json
        run_json_data = json.loads(latest_run_json_str)
        self.status = GhStatus(run_json_data.get("status", GhStatus.PENDING.value))
        self.conclusion = GhConclusion(run_json_data.get("conclusion", GhConclusion.NULL.value))

    def upsert_job(self, ghjob: GhJob) -> None:
        existing_index = next((i for i, existing in enumerate(self) if getattr(existing, "job_id", None) == ghjob.job_id), None)
        if existing_index is not None:
            existing_ghjob_object = self[existing_index]
            if getattr(existing_ghjob_object, "status", None) == GhStatus.COMPLETED:
                # already completed, no need to update except for final conclusion
                existing_ghjob_object.conclusion = ghjob.conclusion
            else:
                # otherwise, replace the existing GhJob object with the new one
                self[existing_index] = ghjob
        else:
            # if no existing job object matched by id, append this job
            self.append(ghjob)

    def get_child_job(self, job_id: int) -> GhJob:
        return next((job for job in self if job.job_id == job_id), None)

    def get_status_summary(self, indent: int = 0) -> str:
        jobs_by_status = self._get_jobs_count_by_status()
        print_str = f"GhRun(id={self.run_id}, status={self.status.value}, jobs={sum(jobs_by_status.values())})"
        for key, cnt in jobs_by_status.items():
            print_str += f"\n{' ' * indent}{key.value.ljust(LONGEST_STATUS_NAME_LEN)}: {cnt}"

        print_str += "\n\nJobs:"
        longest_job_name_len = max(len(job.name) for job in self)
        for job in self:
            print_str += f"\n{' ' * indent}{(job.name + ':').ljust(longest_job_name_len)} {job.get_status_summary(indent=indent + 2)}"

        progress = self.get_progress()
        print_str += f"\n\nRun percent complete: {progress.percent_complete:.2f}% ({progress.completed:.2f}/{progress.total:.2f})"
        return print_str


test_run_json1 = """
{
  "id": 19217851608,
  "name": "experimenting with badges",
  "node_id": "WFR_kwLOQDTFVs8AAAAEeXkk2A",
  "head_branch": "main",
  "head_sha": "90d6bc9cd0a659c96f871a7a00989ed4f4b5cfff",
  "path": ".github/workflows/ci.yaml",
  "display_title": "experimenting with badges",
  "run_number": 170,
  "event": "push",
  "status": "in_progress",
  "conclusion": null,
  "workflow_id": 202821626,
  "check_suite_id": 49505467147,
  "check_suite_node_id": "CS_kwDOQDTFVs8AAAALhsF7Cw",
  "url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608",
  "html_url": "https://github.com/curvcpu/curv-python/actions/runs/19217851608",
  "pull_requests": [],
  "created_at": "2025-11-10T01:32:36Z",
  "updated_at": "2025-11-10T01:34:32Z",
  "actor": {
    "login": "mikegoelzer",
    "id": 142158875,
    "node_id": "U_kgDOCHksGw",
    "avatar_url": "https://avatars.githubusercontent.com/u/142158875?v=4",
    "gravatar_id": "",
    "url": "https://api.github.com/users/mikegoelzer",
    "html_url": "https://github.com/mikegoelzer",
    "followers_url": "https://api.github.com/users/mikegoelzer/followers",
    "following_url": "https://api.github.com/users/mikegoelzer/following{/other_user}",
    "gists_url": "https://api.github.com/users/mikegoelzer/gists{/gist_id}",
    "starred_url": "https://api.github.com/users/mikegoelzer/starred{/owner}{/repo}",
    "subscriptions_url": "https://api.github.com/users/mikegoelzer/subscriptions",
    "organizations_url": "https://api.github.com/users/mikegoelzer/orgs",
    "repos_url": "https://api.github.com/users/mikegoelzer/repos",
    "events_url": "https://api.github.com/users/mikegoelzer/events{/privacy}",
    "received_events_url": "https://api.github.com/users/mikegoelzer/received_events",
    "type": "User",
    "user_view_type": "public",
    "site_admin": false
  },
  "run_attempt": 1,
  "referenced_workflows": [],
  "run_started_at": "2025-11-10T01:32:36Z",
  "triggering_actor": {
    "login": "mikegoelzer",
    "id": 142158875,
    "node_id": "U_kgDOCHksGw",
    "avatar_url": "https://avatars.githubusercontent.com/u/142158875?v=4",
    "gravatar_id": "",
    "url": "https://api.github.com/users/mikegoelzer",
    "html_url": "https://github.com/mikegoelzer",
    "followers_url": "https://api.github.com/users/mikegoelzer/followers",
    "following_url": "https://api.github.com/users/mikegoelzer/following{/other_user}",
    "gists_url": "https://api.github.com/users/mikegoelzer/gists{/gist_id}",
    "starred_url": "https://api.github.com/users/mikegoelzer/starred{/owner}{/repo}",
    "subscriptions_url": "https://api.github.com/users/mikegoelzer/subscriptions",
    "organizations_url": "https://api.github.com/users/mikegoelzer/orgs",
    "repos_url": "https://api.github.com/users/mikegoelzer/repos",
    "events_url": "https://api.github.com/users/mikegoelzer/events{/privacy}",
    "received_events_url": "https://api.github.com/users/mikegoelzer/received_events",
    "type": "User",
    "user_view_type": "public",
    "site_admin": false
  },
  "jobs_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608/jobs",
  "logs_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608/logs",
  "check_suite_url": "https://api.github.com/repos/curvcpu/curv-python/check-suites/49505467147",
  "artifacts_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608/artifacts",
  "cancel_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608/cancel",
  "rerun_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608/rerun",
  "previous_attempt_url": null,
  "workflow_url": "https://api.github.com/repos/curvcpu/curv-python/actions/workflows/202821626",
  "head_commit": {
    "id": "90d6bc9cd0a659c96f871a7a00989ed4f4b5cfff",
    "tree_id": "ae064b6a985b59547b19a50f280abe8352d654e7",
    "message": "experimenting with badges",
    "timestamp": "2025-11-10T01:30:23Z",
    "author": {
      "name": "Mike Goelzer",
      "email": "mikegoelzer@goelzer.org"
    },
    "committer": {
      "name": "Mike Goelzer",
      "email": "mikegoelzer@goelzer.org"
    }
  },
  "repository": {
    "id": 1077200214,
    "node_id": "R_kgDOQDTFVg",
    "name": "curv-python",
    "full_name": "curvcpu/curv-python",
    "private": false,
    "owner": {
      "login": "curvcpu",
      "id": 234678378,
      "node_id": "O_kgDODfzoag",
      "avatar_url": "https://avatars.githubusercontent.com/u/234678378?v=4",
      "gravatar_id": "",
      "url": "https://api.github.com/users/curvcpu",
      "html_url": "https://github.com/curvcpu",
      "followers_url": "https://api.github.com/users/curvcpu/followers",
      "following_url": "https://api.github.com/users/curvcpu/following{/other_user}",
      "gists_url": "https://api.github.com/users/curvcpu/gists{/gist_id}",
      "starred_url": "https://api.github.com/users/curvcpu/starred{/owner}{/repo}",
      "subscriptions_url": "https://api.github.com/users/curvcpu/subscriptions",
      "organizations_url": "https://api.github.com/users/curvcpu/orgs",
      "repos_url": "https://api.github.com/users/curvcpu/repos",
      "events_url": "https://api.github.com/users/curvcpu/events{/privacy}",
      "received_events_url": "https://api.github.com/users/curvcpu/received_events",
      "type": "Organization",
      "user_view_type": "public",
      "site_admin": false
    },
    "html_url": "https://github.com/curvcpu/curv-python",
    "description": "Python package mono-repo for SystemVerilog-related tooling for Curv CPU",
    "fork": false,
    "url": "https://api.github.com/repos/curvcpu/curv-python",
    "forks_url": "https://api.github.com/repos/curvcpu/curv-python/forks",
    "keys_url": "https://api.github.com/repos/curvcpu/curv-python/keys{/key_id}",
    "collaborators_url": "https://api.github.com/repos/curvcpu/curv-python/collaborators{/collaborator}",
    "teams_url": "https://api.github.com/repos/curvcpu/curv-python/teams",
    "hooks_url": "https://api.github.com/repos/curvcpu/curv-python/hooks",
    "issue_events_url": "https://api.github.com/repos/curvcpu/curv-python/issues/events{/number}",
    "events_url": "https://api.github.com/repos/curvcpu/curv-python/events",
    "assignees_url": "https://api.github.com/repos/curvcpu/curv-python/assignees{/user}",
    "branches_url": "https://api.github.com/repos/curvcpu/curv-python/branches{/branch}",
    "tags_url": "https://api.github.com/repos/curvcpu/curv-python/tags",
    "blobs_url": "https://api.github.com/repos/curvcpu/curv-python/git/blobs{/sha}",
    "git_tags_url": "https://api.github.com/repos/curvcpu/curv-python/git/tags{/sha}",
    "git_refs_url": "https://api.github.com/repos/curvcpu/curv-python/git/refs{/sha}",
    "trees_url": "https://api.github.com/repos/curvcpu/curv-python/git/trees{/sha}",
    "statuses_url": "https://api.github.com/repos/curvcpu/curv-python/statuses/{sha}",
    "languages_url": "https://api.github.com/repos/curvcpu/curv-python/languages",
    "stargazers_url": "https://api.github.com/repos/curvcpu/curv-python/stargazers",
    "contributors_url": "https://api.github.com/repos/curvcpu/curv-python/contributors",
    "subscribers_url": "https://api.github.com/repos/curvcpu/curv-python/subscribers",
    "subscription_url": "https://api.github.com/repos/curvcpu/curv-python/subscription",
    "commits_url": "https://api.github.com/repos/curvcpu/curv-python/commits{/sha}",
    "git_commits_url": "https://api.github.com/repos/curvcpu/curv-python/git/commits{/sha}",
    "comments_url": "https://api.github.com/repos/curvcpu/curv-python/comments{/number}",
    "issue_comment_url": "https://api.github.com/repos/curvcpu/curv-python/issues/comments{/number}",
    "contents_url": "https://api.github.com/repos/curvcpu/curv-python/contents/{+path}",
    "compare_url": "https://api.github.com/repos/curvcpu/curv-python/compare/{base}...{head}",
    "merges_url": "https://api.github.com/repos/curvcpu/curv-python/merges",
    "archive_url": "https://api.github.com/repos/curvcpu/curv-python/{archive_format}{/ref}",
    "downloads_url": "https://api.github.com/repos/curvcpu/curv-python/downloads",
    "issues_url": "https://api.github.com/repos/curvcpu/curv-python/issues{/number}",
    "pulls_url": "https://api.github.com/repos/curvcpu/curv-python/pulls{/number}",
    "milestones_url": "https://api.github.com/repos/curvcpu/curv-python/milestones{/number}",
    "notifications_url": "https://api.github.com/repos/curvcpu/curv-python/notifications{?since,all,participating}",
    "labels_url": "https://api.github.com/repos/curvcpu/curv-python/labels{/name}",
    "releases_url": "https://api.github.com/repos/curvcpu/curv-python/releases{/id}",
    "deployments_url": "https://api.github.com/repos/curvcpu/curv-python/deployments"
  },
  "head_repository": {
    "id": 1077200214,
    "node_id": "R_kgDOQDTFVg",
    "name": "curv-python",
    "full_name": "curvcpu/curv-python",
    "private": false,
    "owner": {
      "login": "curvcpu",
      "id": 234678378,
      "node_id": "O_kgDODfzoag",
      "avatar_url": "https://avatars.githubusercontent.com/u/234678378?v=4",
      "gravatar_id": "",
      "url": "https://api.github.com/users/curvcpu",
      "html_url": "https://github.com/curvcpu",
      "followers_url": "https://api.github.com/users/curvcpu/followers",
      "following_url": "https://api.github.com/users/curvcpu/following{/other_user}",
      "gists_url": "https://api.github.com/users/curvcpu/gists{/gist_id}",
      "starred_url": "https://api.github.com/users/curvcpu/starred{/owner}{/repo}",
      "subscriptions_url": "https://api.github.com/users/curvcpu/subscriptions",
      "organizations_url": "https://api.github.com/users/curvcpu/orgs",
      "repos_url": "https://api.github.com/users/curvcpu/repos",
      "events_url": "https://api.github.com/users/curvcpu/events{/privacy}",
      "received_events_url": "https://api.github.com/users/curvcpu/received_events",
      "type": "Organization",
      "user_view_type": "public",
      "site_admin": false
    },
    "html_url": "https://github.com/curvcpu/curv-python",
    "description": "Python package mono-repo for SystemVerilog-related tooling for Curv CPU",
    "fork": false,
    "url": "https://api.github.com/repos/curvcpu/curv-python",
    "forks_url": "https://api.github.com/repos/curvcpu/curv-python/forks",
    "keys_url": "https://api.github.com/repos/curvcpu/curv-python/keys{/key_id}",
    "collaborators_url": "https://api.github.com/repos/curvcpu/curv-python/collaborators{/collaborator}",
    "teams_url": "https://api.github.com/repos/curvcpu/curv-python/teams",
    "hooks_url": "https://api.github.com/repos/curvcpu/curv-python/hooks",
    "issue_events_url": "https://api.github.com/repos/curvcpu/curv-python/issues/events{/number}",
    "events_url": "https://api.github.com/repos/curvcpu/curv-python/events",
    "assignees_url": "https://api.github.com/repos/curvcpu/curv-python/assignees{/user}",
    "branches_url": "https://api.github.com/repos/curvcpu/curv-python/branches{/branch}",
    "tags_url": "https://api.github.com/repos/curvcpu/curv-python/tags",
    "blobs_url": "https://api.github.com/repos/curvcpu/curv-python/git/blobs{/sha}",
    "git_tags_url": "https://api.github.com/repos/curvcpu/curv-python/git/tags{/sha}",
    "git_refs_url": "https://api.github.com/repos/curvcpu/curv-python/git/refs{/sha}",
    "trees_url": "https://api.github.com/repos/curvcpu/curv-python/git/trees{/sha}",
    "statuses_url": "https://api.github.com/repos/curvcpu/curv-python/statuses/{sha}",
    "languages_url": "https://api.github.com/repos/curvcpu/curv-python/languages",
    "stargazers_url": "https://api.github.com/repos/curvcpu/curv-python/stargazers",
    "contributors_url": "https://api.github.com/repos/curvcpu/curv-python/contributors",
    "subscribers_url": "https://api.github.com/repos/curvcpu/curv-python/subscribers",
    "subscription_url": "https://api.github.com/repos/curvcpu/curv-python/subscription",
    "commits_url": "https://api.github.com/repos/curvcpu/curv-python/commits{/sha}",
    "git_commits_url": "https://api.github.com/repos/curvcpu/curv-python/git/commits{/sha}",
    "comments_url": "https://api.github.com/repos/curvcpu/curv-python/comments{/number}",
    "issue_comment_url": "https://api.github.com/repos/curvcpu/curv-python/issues/comments{/number}",
    "contents_url": "https://api.github.com/repos/curvcpu/curv-python/contents/{+path}",
    "compare_url": "https://api.github.com/repos/curvcpu/curv-python/compare/{base}...{head}",
    "merges_url": "https://api.github.com/repos/curvcpu/curv-python/merges",
    "archive_url": "https://api.github.com/repos/curvcpu/curv-python/{archive_format}{/ref}",
    "downloads_url": "https://api.github.com/repos/curvcpu/curv-python/downloads",
    "issues_url": "https://api.github.com/repos/curvcpu/curv-python/issues{/number}",
    "pulls_url": "https://api.github.com/repos/curvcpu/curv-python/pulls{/number}",
    "milestones_url": "https://api.github.com/repos/curvcpu/curv-python/milestones{/number}",
    "notifications_url": "https://api.github.com/repos/curvcpu/curv-python/notifications{?since,all,participating}",
    "labels_url": "https://api.github.com/repos/curvcpu/curv-python/labels{/name}",
    "releases_url": "https://api.github.com/repos/curvcpu/curv-python/releases{/id}",
    "deployments_url": "https://api.github.com/repos/curvcpu/curv-python/deployments"
  }
}
"""

test_jobs_json1 = """
{
  "total_count": 6,
  "jobs": [
    {
      "id": 54930140729,
      "run_id": 19217851608,
      "workflow_name": "experimenting with badges",
      "head_branch": "main",
      "run_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608",
      "run_attempt": 1,
      "node_id": "CR_kwDOQDTFVs8AAAAMyhduOQ",
      "head_sha": "90d6bc9cd0a659c96f871a7a00989ed4f4b5cfff",
      "url": "https://api.github.com/repos/curvcpu/curv-python/actions/jobs/54930140729",
      "html_url": "https://github.com/curvcpu/curv-python/actions/runs/19217851608/job/54930140729",
      "status": "in_progress",
      "conclusion": null,
      "created_at": "2025-11-10T01:32:37Z",
      "started_at": "2025-11-10T01:32:41Z",
      "completed_at": null,
      "name": "Test (py3.10 • macos-latest)",
      "steps": [
        {
          "name": "Set up job",
          "status": "completed",
          "conclusion": "success",
          "number": 1,
          "started_at": "2025-11-10T01:32:41Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Run actions/checkout@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 2,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:46Z"
        },
        {
          "name": "Run actions/setup-python@v5",
          "status": "in_progress",
          "conclusion": null,
          "number": 3,
          "started_at": "2025-11-10T01:32:46Z",
          "completed_at": null
        },
        {
          "name": "Run astral-sh/setup-uv@v4",
          "status": "pending",
          "conclusion": null,
          "number": 4,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Cache uv",
          "status": "pending",
          "conclusion": null,
          "number": 5,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Sync deps",
          "status": "pending",
          "conclusion": null,
          "number": 6,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install verilator (Linux)",
          "status": "pending",
          "conclusion": null,
          "number": 7,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Attempt install delta (Linux)",
          "status": "pending",
          "conclusion": null,
          "number": 8,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install verilator (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 9,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Attempt install delta (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 10,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install packages (editable)",
          "status": "pending",
          "conclusion": null,
          "number": 11,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Unit tests",
          "status": "pending",
          "conclusion": null,
          "number": 12,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "E2E tests",
          "status": "pending",
          "conclusion": null,
          "number": 13,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/setup-python@v5",
          "status": "pending",
          "conclusion": null,
          "number": 25,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/checkout@v4",
          "status": "pending",
          "conclusion": null,
          "number": 26,
          "started_at": null,
          "completed_at": null
        }
      ],
      "check_run_url": "https://api.github.com/repos/curvcpu/curv-python/check-runs/54930140729",
      "labels": [
        "macos-latest"
      ],
      "runner_id": 1000001081,
      "runner_name": "GitHub Actions 1000001081",
      "runner_group_id": 0,
      "runner_group_name": "GitHub Actions"
    },
    {
      "id": 54930140730,
      "run_id": 19217851608,
      "workflow_name": "experimenting with badges",
      "head_branch": "main",
      "run_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608",
      "run_attempt": 1,
      "node_id": "CR_kwDOQDTFVs8AAAAMyhduOg",
      "head_sha": "90d6bc9cd0a659c96f871a7a00989ed4f4b5cfff",
      "url": "https://api.github.com/repos/curvcpu/curv-python/actions/jobs/54930140730",
      "html_url": "https://github.com/curvcpu/curv-python/actions/runs/19217851608/job/54930140730",
      "status": "in_progress",
      "conclusion": null,
      "created_at": "2025-11-10T01:32:37Z",
      "started_at": "2025-11-10T01:32:40Z",
      "completed_at": null,
      "name": "Test (py3.11 • macos-latest)",
      "steps": [
        {
          "name": "Set up job",
          "status": "completed",
          "conclusion": "success",
          "number": 1,
          "started_at": "2025-11-10T01:32:40Z",
          "completed_at": "2025-11-10T01:32:42Z"
        },
        {
          "name": "Run actions/checkout@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 2,
          "started_at": "2025-11-10T01:32:42Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Run actions/setup-python@v5",
          "status": "completed",
          "conclusion": "success",
          "number": 3,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Run astral-sh/setup-uv@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 4,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:45Z"
        },
        {
          "name": "Cache uv",
          "status": "completed",
          "conclusion": "success",
          "number": 5,
          "started_at": "2025-11-10T01:32:45Z",
          "completed_at": "2025-11-10T01:32:46Z"
        },
        {
          "name": "Sync deps",
          "status": "completed",
          "conclusion": "success",
          "number": 6,
          "started_at": "2025-11-10T01:32:46Z",
          "completed_at": "2025-11-10T01:32:48Z"
        },
        {
          "name": "Install verilator (Linux)",
          "status": "completed",
          "conclusion": "skipped",
          "number": 7,
          "started_at": "2025-11-10T01:32:48Z",
          "completed_at": "2025-11-10T01:32:48Z"
        },
        {
          "name": "Attempt install delta (Linux)",
          "status": "completed",
          "conclusion": "skipped",
          "number": 8,
          "started_at": "2025-11-10T01:32:48Z",
          "completed_at": "2025-11-10T01:32:48Z"
        },
        {
          "name": "Install verilator (macOS)",
          "status": "in_progress",
          "conclusion": null,
          "number": 9,
          "started_at": "2025-11-10T01:32:48Z",
          "completed_at": null
        },
        {
          "name": "Attempt install delta (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 10,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install packages (editable)",
          "status": "pending",
          "conclusion": null,
          "number": 11,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Unit tests",
          "status": "pending",
          "conclusion": null,
          "number": 12,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "E2E tests",
          "status": "pending",
          "conclusion": null,
          "number": 13,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Cache uv",
          "status": "pending",
          "conclusion": null,
          "number": 23,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run astral-sh/setup-uv@v4",
          "status": "pending",
          "conclusion": null,
          "number": 24,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/setup-python@v5",
          "status": "pending",
          "conclusion": null,
          "number": 25,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/checkout@v4",
          "status": "pending",
          "conclusion": null,
          "number": 26,
          "started_at": null,
          "completed_at": null
        }
      ],
      "check_run_url": "https://api.github.com/repos/curvcpu/curv-python/check-runs/54930140730",
      "labels": [
        "macos-latest"
      ],
      "runner_id": 1000001082,
      "runner_name": "GitHub Actions 1000001082",
      "runner_group_id": 0,
      "runner_group_name": "GitHub Actions"
    },
    {
      "id": 54930140731,
      "run_id": 19217851608,
      "workflow_name": "experimenting with badges",
      "head_branch": "main",
      "run_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608",
      "run_attempt": 1,
      "node_id": "CR_kwDOQDTFVs8AAAAMyhduOw",
      "head_sha": "90d6bc9cd0a659c96f871a7a00989ed4f4b5cfff",
      "url": "https://api.github.com/repos/curvcpu/curv-python/actions/jobs/54930140731",
      "html_url": "https://github.com/curvcpu/curv-python/actions/runs/19217851608/job/54930140731",
      "status": "in_progress",
      "conclusion": null,
      "created_at": "2025-11-10T01:32:37Z",
      "started_at": "2025-11-10T01:32:40Z",
      "completed_at": null,
      "name": "Test (py3.12 • macos-latest)",
      "steps": [
        {
          "name": "Set up job",
          "status": "completed",
          "conclusion": "success",
          "number": 1,
          "started_at": "2025-11-10T01:32:41Z",
          "completed_at": "2025-11-10T01:32:43Z"
        },
        {
          "name": "Run actions/checkout@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 2,
          "started_at": "2025-11-10T01:32:43Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Run actions/setup-python@v5",
          "status": "completed",
          "conclusion": "success",
          "number": 3,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Run astral-sh/setup-uv@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 4,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:45Z"
        },
        {
          "name": "Cache uv",
          "status": "completed",
          "conclusion": "success",
          "number": 5,
          "started_at": "2025-11-10T01:32:45Z",
          "completed_at": "2025-11-10T01:32:46Z"
        },
        {
          "name": "Sync deps",
          "status": "completed",
          "conclusion": "success",
          "number": 6,
          "started_at": "2025-11-10T01:32:46Z",
          "completed_at": "2025-11-10T01:32:48Z"
        },
        {
          "name": "Install verilator (Linux)",
          "status": "completed",
          "conclusion": "skipped",
          "number": 7,
          "started_at": "2025-11-10T01:32:48Z",
          "completed_at": "2025-11-10T01:32:48Z"
        },
        {
          "name": "Attempt install delta (Linux)",
          "status": "completed",
          "conclusion": "skipped",
          "number": 8,
          "started_at": "2025-11-10T01:32:48Z",
          "completed_at": "2025-11-10T01:32:48Z"
        },
        {
          "name": "Install verilator (macOS)",
          "status": "in_progress",
          "conclusion": null,
          "number": 9,
          "started_at": "2025-11-10T01:32:48Z",
          "completed_at": null
        },
        {
          "name": "Attempt install delta (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 10,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install packages (editable)",
          "status": "pending",
          "conclusion": null,
          "number": 11,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Unit tests",
          "status": "pending",
          "conclusion": null,
          "number": 12,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "E2E tests",
          "status": "pending",
          "conclusion": null,
          "number": 13,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Cache uv",
          "status": "pending",
          "conclusion": null,
          "number": 23,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run astral-sh/setup-uv@v4",
          "status": "pending",
          "conclusion": null,
          "number": 24,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/setup-python@v5",
          "status": "pending",
          "conclusion": null,
          "number": 25,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/checkout@v4",
          "status": "pending",
          "conclusion": null,
          "number": 26,
          "started_at": null,
          "completed_at": null
        }
      ],
      "check_run_url": "https://api.github.com/repos/curvcpu/curv-python/check-runs/54930140731",
      "labels": [
        "macos-latest"
      ],
      "runner_id": 1000001080,
      "runner_name": "GitHub Actions 1000001080",
      "runner_group_id": 0,
      "runner_group_name": "GitHub Actions"
    },
    {
      "id": 54930140737,
      "run_id": 19217851608,
      "workflow_name": "experimenting with badges",
      "head_branch": "main",
      "run_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608",
      "run_attempt": 1,
      "node_id": "CR_kwDOQDTFVs8AAAAMyhduQQ",
      "head_sha": "90d6bc9cd0a659c96f871a7a00989ed4f4b5cfff",
      "url": "https://api.github.com/repos/curvcpu/curv-python/actions/jobs/54930140737",
      "html_url": "https://github.com/curvcpu/curv-python/actions/runs/19217851608/job/54930140737",
      "status": "in_progress",
      "conclusion": null,
      "created_at": "2025-11-10T01:32:37Z",
      "started_at": "2025-11-10T01:32:41Z",
      "completed_at": null,
      "name": "Test (py3.11 • ubuntu-latest)",
      "steps": [
        {
          "name": "Set up job",
          "status": "completed",
          "conclusion": "success",
          "number": 1,
          "started_at": "2025-11-10T01:32:42Z",
          "completed_at": "2025-11-10T01:32:43Z"
        },
        {
          "name": "Run actions/checkout@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 2,
          "started_at": "2025-11-10T01:32:43Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Run actions/setup-python@v5",
          "status": "completed",
          "conclusion": "success",
          "number": 3,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:45Z"
        },
        {
          "name": "Run astral-sh/setup-uv@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 4,
          "started_at": "2025-11-10T01:32:45Z",
          "completed_at": "2025-11-10T01:32:46Z"
        },
        {
          "name": "Cache uv",
          "status": "completed",
          "conclusion": "success",
          "number": 5,
          "started_at": "2025-11-10T01:32:46Z",
          "completed_at": "2025-11-10T01:32:46Z"
        },
        {
          "name": "Sync deps",
          "status": "completed",
          "conclusion": "success",
          "number": 6,
          "started_at": "2025-11-10T01:32:46Z",
          "completed_at": "2025-11-10T01:32:48Z"
        },
        {
          "name": "Install verilator (Linux)",
          "status": "in_progress",
          "conclusion": null,
          "number": 7,
          "started_at": "2025-11-10T01:32:48Z",
          "completed_at": null
        },
        {
          "name": "Attempt install delta (Linux)",
          "status": "pending",
          "conclusion": null,
          "number": 8,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install verilator (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 9,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Attempt install delta (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 10,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install packages (editable)",
          "status": "pending",
          "conclusion": null,
          "number": 11,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Unit tests",
          "status": "pending",
          "conclusion": null,
          "number": 12,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "E2E tests",
          "status": "pending",
          "conclusion": null,
          "number": 13,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Cache uv",
          "status": "pending",
          "conclusion": null,
          "number": 23,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run astral-sh/setup-uv@v4",
          "status": "pending",
          "conclusion": null,
          "number": 24,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/setup-python@v5",
          "status": "pending",
          "conclusion": null,
          "number": 25,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/checkout@v4",
          "status": "pending",
          "conclusion": null,
          "number": 26,
          "started_at": null,
          "completed_at": null
        }
      ],
      "check_run_url": "https://api.github.com/repos/curvcpu/curv-python/check-runs/54930140737",
      "labels": [
        "ubuntu-latest"
      ],
      "runner_id": 1000001083,
      "runner_name": "GitHub Actions 1000001083",
      "runner_group_id": 0,
      "runner_group_name": "GitHub Actions"
    },
    {
      "id": 54930140743,
      "run_id": 19217851608,
      "workflow_name": "experimenting with badges",
      "head_branch": "main",
      "run_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608",
      "run_attempt": 1,
      "node_id": "CR_kwDOQDTFVs8AAAAMyhduRw",
      "head_sha": "90d6bc9cd0a659c96f871a7a00989ed4f4b5cfff",
      "url": "https://api.github.com/repos/curvcpu/curv-python/actions/jobs/54930140743",
      "html_url": "https://github.com/curvcpu/curv-python/actions/runs/19217851608/job/54930140743",
      "status": "in_progress",
      "conclusion": null,
      "created_at": "2025-11-10T01:32:37Z",
      "started_at": "2025-11-10T01:32:40Z",
      "completed_at": null,
      "name": "Test (py3.12 • ubuntu-latest)",
      "steps": [
        {
          "name": "Set up job",
          "status": "completed",
          "conclusion": "success",
          "number": 1,
          "started_at": "2025-11-10T01:32:41Z",
          "completed_at": "2025-11-10T01:32:43Z"
        },
        {
          "name": "Run actions/checkout@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 2,
          "started_at": "2025-11-10T01:32:43Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Run actions/setup-python@v5",
          "status": "completed",
          "conclusion": "success",
          "number": 3,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Run astral-sh/setup-uv@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 4,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:46Z"
        },
        {
          "name": "Cache uv",
          "status": "completed",
          "conclusion": "success",
          "number": 5,
          "started_at": "2025-11-10T01:32:46Z",
          "completed_at": "2025-11-10T01:32:46Z"
        },
        {
          "name": "Sync deps",
          "status": "completed",
          "conclusion": "success",
          "number": 6,
          "started_at": "2025-11-10T01:32:46Z",
          "completed_at": "2025-11-10T01:32:49Z"
        },
        {
          "name": "Install verilator (Linux)",
          "status": "in_progress",
          "conclusion": null,
          "number": 7,
          "started_at": "2025-11-10T01:32:49Z",
          "completed_at": null
        },
        {
          "name": "Attempt install delta (Linux)",
          "status": "pending",
          "conclusion": null,
          "number": 8,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install verilator (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 9,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Attempt install delta (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 10,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install packages (editable)",
          "status": "pending",
          "conclusion": null,
          "number": 11,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Unit tests",
          "status": "pending",
          "conclusion": null,
          "number": 12,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "E2E tests",
          "status": "pending",
          "conclusion": null,
          "number": 13,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Cache uv",
          "status": "pending",
          "conclusion": null,
          "number": 23,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run astral-sh/setup-uv@v4",
          "status": "pending",
          "conclusion": null,
          "number": 24,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/setup-python@v5",
          "status": "pending",
          "conclusion": null,
          "number": 25,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/checkout@v4",
          "status": "pending",
          "conclusion": null,
          "number": 26,
          "started_at": null,
          "completed_at": null
        }
      ],
      "check_run_url": "https://api.github.com/repos/curvcpu/curv-python/check-runs/54930140743",
      "labels": [
        "ubuntu-latest"
      ],
      "runner_id": 1000001085,
      "runner_name": "GitHub Actions 1000001085",
      "runner_group_id": 0,
      "runner_group_name": "GitHub Actions"
    },
    {
      "id": 54930140745,
      "run_id": 19217851608,
      "workflow_name": "experimenting with badges",
      "head_branch": "main",
      "run_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608",
      "run_attempt": 1,
      "node_id": "CR_kwDOQDTFVs8AAAAMyhduSQ",
      "head_sha": "90d6bc9cd0a659c96f871a7a00989ed4f4b5cfff",
      "url": "https://api.github.com/repos/curvcpu/curv-python/actions/jobs/54930140745",
      "html_url": "https://github.com/curvcpu/curv-python/actions/runs/19217851608/job/54930140745",
      "status": "in_progress",
      "conclusion": null,
      "created_at": "2025-11-10T01:32:37Z",
      "started_at": "2025-11-10T01:32:40Z",
      "completed_at": null,
      "name": "Test (py3.10 • ubuntu-latest)",
      "steps": [
        {
          "name": "Set up job",
          "status": "completed",
          "conclusion": "success",
          "number": 1,
          "started_at": "2025-11-10T01:32:41Z",
          "completed_at": "2025-11-10T01:32:42Z"
        },
        {
          "name": "Run actions/checkout@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 2,
          "started_at": "2025-11-10T01:32:42Z",
          "completed_at": "2025-11-10T01:32:43Z"
        },
        {
          "name": "Run actions/setup-python@v5",
          "status": "completed",
          "conclusion": "success",
          "number": 3,
          "started_at": "2025-11-10T01:32:43Z",
          "completed_at": "2025-11-10T01:32:43Z"
        },
        {
          "name": "Run astral-sh/setup-uv@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 4,
          "started_at": "2025-11-10T01:32:43Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Cache uv",
          "status": "completed",
          "conclusion": "success",
          "number": 5,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Sync deps",
          "status": "completed",
          "conclusion": "success",
          "number": 6,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:47Z"
        },
        {
          "name": "Install verilator (Linux)",
          "status": "in_progress",
          "conclusion": null,
          "number": 7,
          "started_at": "2025-11-10T01:32:47Z",
          "completed_at": null
        },
        {
          "name": "Attempt install delta (Linux)",
          "status": "pending",
          "conclusion": null,
          "number": 8,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install verilator (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 9,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Attempt install delta (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 10,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install packages (editable)",
          "status": "pending",
          "conclusion": null,
          "number": 11,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Unit tests",
          "status": "pending",
          "conclusion": null,
          "number": 12,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "E2E tests",
          "status": "pending",
          "conclusion": null,
          "number": 13,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Cache uv",
          "status": "pending",
          "conclusion": null,
          "number": 23,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run astral-sh/setup-uv@v4",
          "status": "pending",
          "conclusion": null,
          "number": 24,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/setup-python@v5",
          "status": "pending",
          "conclusion": null,
          "number": 25,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/checkout@v4",
          "status": "pending",
          "conclusion": null,
          "number": 26,
          "started_at": null,
          "completed_at": null
        }
      ],
      "check_run_url": "https://api.github.com/repos/curvcpu/curv-python/check-runs/54930140745",
      "labels": [
        "ubuntu-latest"
      ],
      "runner_id": 1000001084,
      "runner_name": "GitHub Actions 1000001084",
      "runner_group_id": 0,
      "runner_group_name": "GitHub Actions"
    }
  ]
}
"""

test_run_json2 = """
{
  "id": 19217851608,
  "name": "experimenting with badges",
  "node_id": "WFR_kwLOQDTFVs8AAAAEeXkk2A",
  "head_branch": "main",
  "head_sha": "90d6bc9cd0a659c96f871a7a00989ed4f4b5cfff",
  "path": ".github/workflows/ci.yaml",
  "display_title": "experimenting with badges",
  "run_number": 170,
  "event": "push",
  "status": "in_progress",
  "conclusion": "success",
  "workflow_id": 202821626,
  "check_suite_id": 49505467147,
  "check_suite_node_id": "CS_kwDOQDTFVs8AAAALhsF7Cw",
  "url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608",
  "html_url": "https://github.com/curvcpu/curv-python/actions/runs/19217851608",
  "pull_requests": [],
  "created_at": "2025-11-10T01:32:36Z",
  "updated_at": "2025-11-10T01:34:32Z",
  "actor": {
    "login": "mikegoelzer",
    "id": 142158875,
    "node_id": "U_kgDOCHksGw",
    "avatar_url": "https://avatars.githubusercontent.com/u/142158875?v=4",
    "gravatar_id": "",
    "url": "https://api.github.com/users/mikegoelzer",
    "html_url": "https://github.com/mikegoelzer",
    "followers_url": "https://api.github.com/users/mikegoelzer/followers",
    "following_url": "https://api.github.com/users/mikegoelzer/following{/other_user}",
    "gists_url": "https://api.github.com/users/mikegoelzer/gists{/gist_id}",
    "starred_url": "https://api.github.com/users/mikegoelzer/starred{/owner}{/repo}",
    "subscriptions_url": "https://api.github.com/users/mikegoelzer/subscriptions",
    "organizations_url": "https://api.github.com/users/mikegoelzer/orgs",
    "repos_url": "https://api.github.com/users/mikegoelzer/repos",
    "events_url": "https://api.github.com/users/mikegoelzer/events{/privacy}",
    "received_events_url": "https://api.github.com/users/mikegoelzer/received_events",
    "type": "User",
    "user_view_type": "public",
    "site_admin": false
  },
  "run_attempt": 1,
  "referenced_workflows": [],
  "run_started_at": "2025-11-10T01:32:36Z",
  "triggering_actor": {
    "login": "mikegoelzer",
    "id": 142158875,
    "node_id": "U_kgDOCHksGw",
    "avatar_url": "https://avatars.githubusercontent.com/u/142158875?v=4",
    "gravatar_id": "",
    "url": "https://api.github.com/users/mikegoelzer",
    "html_url": "https://github.com/mikegoelzer",
    "followers_url": "https://api.github.com/users/mikegoelzer/followers",
    "following_url": "https://api.github.com/users/mikegoelzer/following{/other_user}",
    "gists_url": "https://api.github.com/users/mikegoelzer/gists{/gist_id}",
    "starred_url": "https://api.github.com/users/mikegoelzer/starred{/owner}{/repo}",
    "subscriptions_url": "https://api.github.com/users/mikegoelzer/subscriptions",
    "organizations_url": "https://api.github.com/users/mikegoelzer/orgs",
    "repos_url": "https://api.github.com/users/mikegoelzer/repos",
    "events_url": "https://api.github.com/users/mikegoelzer/events{/privacy}",
    "received_events_url": "https://api.github.com/users/mikegoelzer/received_events",
    "type": "User",
    "user_view_type": "public",
    "site_admin": false
  },
  "jobs_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608/jobs",
  "logs_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608/logs",
  "check_suite_url": "https://api.github.com/repos/curvcpu/curv-python/check-suites/49505467147",
  "artifacts_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608/artifacts",
  "cancel_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608/cancel",
  "rerun_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608/rerun",
  "previous_attempt_url": null,
  "workflow_url": "https://api.github.com/repos/curvcpu/curv-python/actions/workflows/202821626",
  "head_commit": {
    "id": "90d6bc9cd0a659c96f871a7a00989ed4f4b5cfff",
    "tree_id": "ae064b6a985b59547b19a50f280abe8352d654e7",
    "message": "experimenting with badges",
    "timestamp": "2025-11-10T01:30:23Z",
    "author": {
      "name": "Mike Goelzer",
      "email": "mikegoelzer@goelzer.org"
    },
    "committer": {
      "name": "Mike Goelzer",
      "email": "mikegoelzer@goelzer.org"
    }
  },
  "repository": {
    "id": 1077200214,
    "node_id": "R_kgDOQDTFVg",
    "name": "curv-python",
    "full_name": "curvcpu/curv-python",
    "private": false,
    "owner": {
      "login": "curvcpu",
      "id": 234678378,
      "node_id": "O_kgDODfzoag",
      "avatar_url": "https://avatars.githubusercontent.com/u/234678378?v=4",
      "gravatar_id": "",
      "url": "https://api.github.com/users/curvcpu",
      "html_url": "https://github.com/curvcpu",
      "followers_url": "https://api.github.com/users/curvcpu/followers",
      "following_url": "https://api.github.com/users/curvcpu/following{/other_user}",
      "gists_url": "https://api.github.com/users/curvcpu/gists{/gist_id}",
      "starred_url": "https://api.github.com/users/curvcpu/starred{/owner}{/repo}",
      "subscriptions_url": "https://api.github.com/users/curvcpu/subscriptions",
      "organizations_url": "https://api.github.com/users/curvcpu/orgs",
      "repos_url": "https://api.github.com/users/curvcpu/repos",
      "events_url": "https://api.github.com/users/curvcpu/events{/privacy}",
      "received_events_url": "https://api.github.com/users/curvcpu/received_events",
      "type": "Organization",
      "user_view_type": "public",
      "site_admin": false
    },
    "html_url": "https://github.com/curvcpu/curv-python",
    "description": "Python package mono-repo for SystemVerilog-related tooling for Curv CPU",
    "fork": false,
    "url": "https://api.github.com/repos/curvcpu/curv-python",
    "forks_url": "https://api.github.com/repos/curvcpu/curv-python/forks",
    "keys_url": "https://api.github.com/repos/curvcpu/curv-python/keys{/key_id}",
    "collaborators_url": "https://api.github.com/repos/curvcpu/curv-python/collaborators{/collaborator}",
    "teams_url": "https://api.github.com/repos/curvcpu/curv-python/teams",
    "hooks_url": "https://api.github.com/repos/curvcpu/curv-python/hooks",
    "issue_events_url": "https://api.github.com/repos/curvcpu/curv-python/issues/events{/number}",
    "events_url": "https://api.github.com/repos/curvcpu/curv-python/events",
    "assignees_url": "https://api.github.com/repos/curvcpu/curv-python/assignees{/user}",
    "branches_url": "https://api.github.com/repos/curvcpu/curv-python/branches{/branch}",
    "tags_url": "https://api.github.com/repos/curvcpu/curv-python/tags",
    "blobs_url": "https://api.github.com/repos/curvcpu/curv-python/git/blobs{/sha}",
    "git_tags_url": "https://api.github.com/repos/curvcpu/curv-python/git/tags{/sha}",
    "git_refs_url": "https://api.github.com/repos/curvcpu/curv-python/git/refs{/sha}",
    "trees_url": "https://api.github.com/repos/curvcpu/curv-python/git/trees{/sha}",
    "statuses_url": "https://api.github.com/repos/curvcpu/curv-python/statuses/{sha}",
    "languages_url": "https://api.github.com/repos/curvcpu/curv-python/languages",
    "stargazers_url": "https://api.github.com/repos/curvcpu/curv-python/stargazers",
    "contributors_url": "https://api.github.com/repos/curvcpu/curv-python/contributors",
    "subscribers_url": "https://api.github.com/repos/curvcpu/curv-python/subscribers",
    "subscription_url": "https://api.github.com/repos/curvcpu/curv-python/subscription",
    "commits_url": "https://api.github.com/repos/curvcpu/curv-python/commits{/sha}",
    "git_commits_url": "https://api.github.com/repos/curvcpu/curv-python/git/commits{/sha}",
    "comments_url": "https://api.github.com/repos/curvcpu/curv-python/comments{/number}",
    "issue_comment_url": "https://api.github.com/repos/curvcpu/curv-python/issues/comments{/number}",
    "contents_url": "https://api.github.com/repos/curvcpu/curv-python/contents/{+path}",
    "compare_url": "https://api.github.com/repos/curvcpu/curv-python/compare/{base}...{head}",
    "merges_url": "https://api.github.com/repos/curvcpu/curv-python/merges",
    "archive_url": "https://api.github.com/repos/curvcpu/curv-python/{archive_format}{/ref}",
    "downloads_url": "https://api.github.com/repos/curvcpu/curv-python/downloads",
    "issues_url": "https://api.github.com/repos/curvcpu/curv-python/issues{/number}",
    "pulls_url": "https://api.github.com/repos/curvcpu/curv-python/pulls{/number}",
    "milestones_url": "https://api.github.com/repos/curvcpu/curv-python/milestones{/number}",
    "notifications_url": "https://api.github.com/repos/curvcpu/curv-python/notifications{?since,all,participating}",
    "labels_url": "https://api.github.com/repos/curvcpu/curv-python/labels{/name}",
    "releases_url": "https://api.github.com/repos/curvcpu/curv-python/releases{/id}",
    "deployments_url": "https://api.github.com/repos/curvcpu/curv-python/deployments"
  },
  "head_repository": {
    "id": 1077200214,
    "node_id": "R_kgDOQDTFVg",
    "name": "curv-python",
    "full_name": "curvcpu/curv-python",
    "private": false,
    "owner": {
      "login": "curvcpu",
      "id": 234678378,
      "node_id": "O_kgDODfzoag",
      "avatar_url": "https://avatars.githubusercontent.com/u/234678378?v=4",
      "gravatar_id": "",
      "url": "https://api.github.com/users/curvcpu",
      "html_url": "https://github.com/curvcpu",
      "followers_url": "https://api.github.com/users/curvcpu/followers",
      "following_url": "https://api.github.com/users/curvcpu/following{/other_user}",
      "gists_url": "https://api.github.com/users/curvcpu/gists{/gist_id}",
      "starred_url": "https://api.github.com/users/curvcpu/starred{/owner}{/repo}",
      "subscriptions_url": "https://api.github.com/users/curvcpu/subscriptions",
      "organizations_url": "https://api.github.com/users/curvcpu/orgs",
      "repos_url": "https://api.github.com/users/curvcpu/repos",
      "events_url": "https://api.github.com/users/curvcpu/events{/privacy}",
      "received_events_url": "https://api.github.com/users/curvcpu/received_events",
      "type": "Organization",
      "user_view_type": "public",
      "site_admin": false
    },
    "html_url": "https://github.com/curvcpu/curv-python",
    "description": "Python package mono-repo for SystemVerilog-related tooling for Curv CPU",
    "fork": false,
    "url": "https://api.github.com/repos/curvcpu/curv-python",
    "forks_url": "https://api.github.com/repos/curvcpu/curv-python/forks",
    "keys_url": "https://api.github.com/repos/curvcpu/curv-python/keys{/key_id}",
    "collaborators_url": "https://api.github.com/repos/curvcpu/curv-python/collaborators{/collaborator}",
    "teams_url": "https://api.github.com/repos/curvcpu/curv-python/teams",
    "hooks_url": "https://api.github.com/repos/curvcpu/curv-python/hooks",
    "issue_events_url": "https://api.github.com/repos/curvcpu/curv-python/issues/events{/number}",
    "events_url": "https://api.github.com/repos/curvcpu/curv-python/events",
    "assignees_url": "https://api.github.com/repos/curvcpu/curv-python/assignees{/user}",
    "branches_url": "https://api.github.com/repos/curvcpu/curv-python/branches{/branch}",
    "tags_url": "https://api.github.com/repos/curvcpu/curv-python/tags",
    "blobs_url": "https://api.github.com/repos/curvcpu/curv-python/git/blobs{/sha}",
    "git_tags_url": "https://api.github.com/repos/curvcpu/curv-python/git/tags{/sha}",
    "git_refs_url": "https://api.github.com/repos/curvcpu/curv-python/git/refs{/sha}",
    "trees_url": "https://api.github.com/repos/curvcpu/curv-python/git/trees{/sha}",
    "statuses_url": "https://api.github.com/repos/curvcpu/curv-python/statuses/{sha}",
    "languages_url": "https://api.github.com/repos/curvcpu/curv-python/languages",
    "stargazers_url": "https://api.github.com/repos/curvcpu/curv-python/stargazers",
    "contributors_url": "https://api.github.com/repos/curvcpu/curv-python/contributors",
    "subscribers_url": "https://api.github.com/repos/curvcpu/curv-python/subscribers",
    "subscription_url": "https://api.github.com/repos/curvcpu/curv-python/subscription",
    "commits_url": "https://api.github.com/repos/curvcpu/curv-python/commits{/sha}",
    "git_commits_url": "https://api.github.com/repos/curvcpu/curv-python/git/commits{/sha}",
    "comments_url": "https://api.github.com/repos/curvcpu/curv-python/comments{/number}",
    "issue_comment_url": "https://api.github.com/repos/curvcpu/curv-python/issues/comments{/number}",
    "contents_url": "https://api.github.com/repos/curvcpu/curv-python/contents/{+path}",
    "compare_url": "https://api.github.com/repos/curvcpu/curv-python/compare/{base}...{head}",
    "merges_url": "https://api.github.com/repos/curvcpu/curv-python/merges",
    "archive_url": "https://api.github.com/repos/curvcpu/curv-python/{archive_format}{/ref}",
    "downloads_url": "https://api.github.com/repos/curvcpu/curv-python/downloads",
    "issues_url": "https://api.github.com/repos/curvcpu/curv-python/issues{/number}",
    "pulls_url": "https://api.github.com/repos/curvcpu/curv-python/pulls{/number}",
    "milestones_url": "https://api.github.com/repos/curvcpu/curv-python/milestones{/number}",
    "notifications_url": "https://api.github.com/repos/curvcpu/curv-python/notifications{?since,all,participating}",
    "labels_url": "https://api.github.com/repos/curvcpu/curv-python/labels{/name}",
    "releases_url": "https://api.github.com/repos/curvcpu/curv-python/releases{/id}",
    "deployments_url": "https://api.github.com/repos/curvcpu/curv-python/deployments"
  }
}
"""

test_jobs_json2 = """
{
  "total_count": 6,
  "jobs": [
    {
      "id": 54930140729,
      "run_id": 19217851608,
      "workflow_name": "experimenting with badges",
      "head_branch": "main",
      "run_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608",
      "run_attempt": 1,
      "node_id": "CR_kwDOQDTFVs8AAAAMyhduOQ",
      "head_sha": "90d6bc9cd0a659c96f871a7a00989ed4f4b5cfff",
      "url": "https://api.github.com/repos/curvcpu/curv-python/actions/jobs/54930140729",
      "html_url": "https://github.com/curvcpu/curv-python/actions/runs/19217851608/job/54930140729",
      "status": "in_progress",
      "conclusion": null,
      "created_at": "2025-11-10T01:32:37Z",
      "started_at": "2025-11-10T01:32:41Z",
      "completed_at": null,
      "name": "Test (py3.10 • macos-latest)",
      "steps": [
        {
          "name": "Set up job",
          "status": "completed",
          "conclusion": "success",
          "number": 1,
          "started_at": "2025-11-10T01:32:41Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Run actions/checkout@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 2,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:46Z"
        },
        {
          "name": "Run actions/setup-python@v5",
          "status": "in_progress",
          "conclusion": null,
          "number": 3,
          "started_at": "2025-11-10T01:32:46Z",
          "completed_at": null
        },
        {
          "name": "Run astral-sh/setup-uv@v4",
          "status": "pending",
          "conclusion": null,
          "number": 4,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Cache uv",
          "status": "pending",
          "conclusion": null,
          "number": 5,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Sync deps",
          "status": "pending",
          "conclusion": null,
          "number": 6,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install verilator (Linux)",
          "status": "pending",
          "conclusion": null,
          "number": 7,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Attempt install delta (Linux)",
          "status": "pending",
          "conclusion": null,
          "number": 8,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install verilator (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 9,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Attempt install delta (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 10,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install packages (editable)",
          "status": "pending",
          "conclusion": null,
          "number": 11,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Unit tests",
          "status": "pending",
          "conclusion": null,
          "number": 12,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "E2E tests",
          "status": "pending",
          "conclusion": null,
          "number": 13,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/setup-python@v5",
          "status": "pending",
          "conclusion": null,
          "number": 25,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/checkout@v4",
          "status": "pending",
          "conclusion": null,
          "number": 26,
          "started_at": null,
          "completed_at": null
        }
      ],
      "check_run_url": "https://api.github.com/repos/curvcpu/curv-python/check-runs/54930140729",
      "labels": [
        "macos-latest"
      ],
      "runner_id": 1000001081,
      "runner_name": "GitHub Actions 1000001081",
      "runner_group_id": 0,
      "runner_group_name": "GitHub Actions"
    },
    {
      "id": 54930140730,
      "run_id": 19217851608,
      "workflow_name": "experimenting with badges",
      "head_branch": "main",
      "run_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608",
      "run_attempt": 1,
      "node_id": "CR_kwDOQDTFVs8AAAAMyhduOg",
      "head_sha": "90d6bc9cd0a659c96f871a7a00989ed4f4b5cfff",
      "url": "https://api.github.com/repos/curvcpu/curv-python/actions/jobs/54930140730",
      "html_url": "https://github.com/curvcpu/curv-python/actions/runs/19217851608/job/54930140730",
      "status": "in_progress",
      "conclusion": null,
      "created_at": "2025-11-10T01:32:37Z",
      "started_at": "2025-11-10T01:32:40Z",
      "completed_at": null,
      "name": "Test (py3.11 • macos-latest)",
      "steps": [
        {
          "name": "Set up job",
          "status": "completed",
          "conclusion": "success",
          "number": 1,
          "started_at": "2025-11-10T01:32:40Z",
          "completed_at": "2025-11-10T01:32:42Z"
        },
        {
          "name": "Run actions/checkout@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 2,
          "started_at": "2025-11-10T01:32:42Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Run actions/setup-python@v5",
          "status": "completed",
          "conclusion": "success",
          "number": 3,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Run astral-sh/setup-uv@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 4,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:45Z"
        },
        {
          "name": "Cache uv",
          "status": "completed",
          "conclusion": "success",
          "number": 5,
          "started_at": "2025-11-10T01:32:45Z",
          "completed_at": "2025-11-10T01:32:46Z"
        },
        {
          "name": "Sync deps",
          "status": "completed",
          "conclusion": "success",
          "number": 6,
          "started_at": "2025-11-10T01:32:46Z",
          "completed_at": "2025-11-10T01:32:48Z"
        },
        {
          "name": "Install verilator (Linux)",
          "status": "completed",
          "conclusion": "skipped",
          "number": 7,
          "started_at": "2025-11-10T01:32:48Z",
          "completed_at": "2025-11-10T01:32:48Z"
        },
        {
          "name": "Attempt install delta (Linux)",
          "status": "completed",
          "conclusion": "skipped",
          "number": 8,
          "started_at": "2025-11-10T01:32:48Z",
          "completed_at": "2025-11-10T01:32:48Z"
        },
        {
          "name": "Install verilator (macOS)",
          "status": "in_progress",
          "conclusion": null,
          "number": 9,
          "started_at": "2025-11-10T01:32:48Z",
          "completed_at": null
        },
        {
          "name": "Attempt install delta (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 10,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install packages (editable)",
          "status": "pending",
          "conclusion": null,
          "number": 11,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Unit tests",
          "status": "pending",
          "conclusion": null,
          "number": 12,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "E2E tests",
          "status": "pending",
          "conclusion": null,
          "number": 13,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Cache uv",
          "status": "pending",
          "conclusion": null,
          "number": 23,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run astral-sh/setup-uv@v4",
          "status": "pending",
          "conclusion": null,
          "number": 24,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/setup-python@v5",
          "status": "pending",
          "conclusion": null,
          "number": 25,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/checkout@v4",
          "status": "pending",
          "conclusion": null,
          "number": 26,
          "started_at": null,
          "completed_at": null
        }
      ],
      "check_run_url": "https://api.github.com/repos/curvcpu/curv-python/check-runs/54930140730",
      "labels": [
        "macos-latest"
      ],
      "runner_id": 1000001082,
      "runner_name": "GitHub Actions 1000001082",
      "runner_group_id": 0,
      "runner_group_name": "GitHub Actions"
    },
    {
      "id": 54930140731,
      "run_id": 19217851608,
      "workflow_name": "experimenting with badges",
      "head_branch": "main",
      "run_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608",
      "run_attempt": 1,
      "node_id": "CR_kwDOQDTFVs8AAAAMyhduOw",
      "head_sha": "90d6bc9cd0a659c96f871a7a00989ed4f4b5cfff",
      "url": "https://api.github.com/repos/curvcpu/curv-python/actions/jobs/54930140731",
      "html_url": "https://github.com/curvcpu/curv-python/actions/runs/19217851608/job/54930140731",
      "status": "in_progress",
      "conclusion": null,
      "created_at": "2025-11-10T01:32:37Z",
      "started_at": "2025-11-10T01:32:40Z",
      "completed_at": null,
      "name": "Test (py3.12 • macos-latest)",
      "steps": [
        {
          "name": "Set up job",
          "status": "completed",
          "conclusion": "success",
          "number": 1,
          "started_at": "2025-11-10T01:32:41Z",
          "completed_at": "2025-11-10T01:32:43Z"
        },
        {
          "name": "Run actions/checkout@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 2,
          "started_at": "2025-11-10T01:32:43Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Run actions/setup-python@v5",
          "status": "completed",
          "conclusion": "success",
          "number": 3,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Run astral-sh/setup-uv@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 4,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:45Z"
        },
        {
          "name": "Cache uv",
          "status": "completed",
          "conclusion": "success",
          "number": 5,
          "started_at": "2025-11-10T01:32:45Z",
          "completed_at": "2025-11-10T01:32:46Z"
        },
        {
          "name": "Sync deps",
          "status": "completed",
          "conclusion": "success",
          "number": 6,
          "started_at": "2025-11-10T01:32:46Z",
          "completed_at": "2025-11-10T01:32:48Z"
        },
        {
          "name": "Install verilator (Linux)",
          "status": "completed",
          "conclusion": "skipped",
          "number": 7,
          "started_at": "2025-11-10T01:32:48Z",
          "completed_at": "2025-11-10T01:32:48Z"
        },
        {
          "name": "Attempt install delta (Linux)",
          "status": "completed",
          "conclusion": "skipped",
          "number": 8,
          "started_at": "2025-11-10T01:32:48Z",
          "completed_at": "2025-11-10T01:32:48Z"
        },
        {
          "name": "Install verilator (macOS)",
          "status": "in_progress",
          "conclusion": null,
          "number": 9,
          "started_at": "2025-11-10T01:32:48Z",
          "completed_at": null
        },
        {
          "name": "Attempt install delta (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 10,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install packages (editable)",
          "status": "pending",
          "conclusion": null,
          "number": 11,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Unit tests",
          "status": "pending",
          "conclusion": null,
          "number": 12,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "E2E tests",
          "status": "pending",
          "conclusion": null,
          "number": 13,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Cache uv",
          "status": "pending",
          "conclusion": null,
          "number": 23,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run astral-sh/setup-uv@v4",
          "status": "pending",
          "conclusion": null,
          "number": 24,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/setup-python@v5",
          "status": "pending",
          "conclusion": null,
          "number": 25,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/checkout@v4",
          "status": "pending",
          "conclusion": null,
          "number": 26,
          "started_at": null,
          "completed_at": null
        }
      ],
      "check_run_url": "https://api.github.com/repos/curvcpu/curv-python/check-runs/54930140731",
      "labels": [
        "macos-latest"
      ],
      "runner_id": 1000001080,
      "runner_name": "GitHub Actions 1000001080",
      "runner_group_id": 0,
      "runner_group_name": "GitHub Actions"
    },
    {
      "id": 54930140737,
      "run_id": 19217851608,
      "workflow_name": "experimenting with badges",
      "head_branch": "main",
      "run_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608",
      "run_attempt": 1,
      "node_id": "CR_kwDOQDTFVs8AAAAMyhduQQ",
      "head_sha": "90d6bc9cd0a659c96f871a7a00989ed4f4b5cfff",
      "url": "https://api.github.com/repos/curvcpu/curv-python/actions/jobs/54930140737",
      "html_url": "https://github.com/curvcpu/curv-python/actions/runs/19217851608/job/54930140737",
      "status": "in_progress",
      "conclusion": null,
      "created_at": "2025-11-10T01:32:37Z",
      "started_at": "2025-11-10T01:32:41Z",
      "completed_at": null,
      "name": "Test (py3.11 • ubuntu-latest)",
      "steps": [
        {
          "name": "Set up job",
          "status": "completed",
          "conclusion": "success",
          "number": 1,
          "started_at": "2025-11-10T01:32:42Z",
          "completed_at": "2025-11-10T01:32:43Z"
        },
        {
          "name": "Run actions/checkout@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 2,
          "started_at": "2025-11-10T01:32:43Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Run actions/setup-python@v5",
          "status": "completed",
          "conclusion": "success",
          "number": 3,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:45Z"
        },
        {
          "name": "Run astral-sh/setup-uv@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 4,
          "started_at": "2025-11-10T01:32:45Z",
          "completed_at": "2025-11-10T01:32:46Z"
        },
        {
          "name": "Cache uv",
          "status": "completed",
          "conclusion": "success",
          "number": 5,
          "started_at": "2025-11-10T01:32:46Z",
          "completed_at": "2025-11-10T01:32:46Z"
        },
        {
          "name": "Sync deps",
          "status": "completed",
          "conclusion": "success",
          "number": 6,
          "started_at": "2025-11-10T01:32:46Z",
          "completed_at": "2025-11-10T01:32:48Z"
        },
        {
          "name": "Install verilator (Linux)",
          "status": "in_progress",
          "conclusion": null,
          "number": 7,
          "started_at": "2025-11-10T01:32:48Z",
          "completed_at": null
        },
        {
          "name": "Attempt install delta (Linux)",
          "status": "pending",
          "conclusion": null,
          "number": 8,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install verilator (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 9,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Attempt install delta (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 10,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install packages (editable)",
          "status": "pending",
          "conclusion": null,
          "number": 11,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Unit tests",
          "status": "pending",
          "conclusion": null,
          "number": 12,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "E2E tests",
          "status": "pending",
          "conclusion": null,
          "number": 13,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Cache uv",
          "status": "pending",
          "conclusion": null,
          "number": 23,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run astral-sh/setup-uv@v4",
          "status": "pending",
          "conclusion": null,
          "number": 24,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/setup-python@v5",
          "status": "pending",
          "conclusion": null,
          "number": 25,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/checkout@v4",
          "status": "pending",
          "conclusion": null,
          "number": 26,
          "started_at": null,
          "completed_at": null
        }
      ],
      "check_run_url": "https://api.github.com/repos/curvcpu/curv-python/check-runs/54930140737",
      "labels": [
        "ubuntu-latest"
      ],
      "runner_id": 1000001083,
      "runner_name": "GitHub Actions 1000001083",
      "runner_group_id": 0,
      "runner_group_name": "GitHub Actions"
    },
    {
      "id": 54930140743,
      "run_id": 19217851608,
      "workflow_name": "experimenting with badges",
      "head_branch": "main",
      "run_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608",
      "run_attempt": 1,
      "node_id": "CR_kwDOQDTFVs8AAAAMyhduRw",
      "head_sha": "90d6bc9cd0a659c96f871a7a00989ed4f4b5cfff",
      "url": "https://api.github.com/repos/curvcpu/curv-python/actions/jobs/54930140743",
      "html_url": "https://github.com/curvcpu/curv-python/actions/runs/19217851608/job/54930140743",
      "status": "in_progress",
      "conclusion": null,
      "created_at": "2025-11-10T01:32:37Z",
      "started_at": "2025-11-10T01:32:40Z",
      "completed_at": null,
      "name": "Test (py3.12 • ubuntu-latest)",
      "steps": [
        {
          "name": "Set up job",
          "status": "completed",
          "conclusion": "success",
          "number": 1,
          "started_at": "2025-11-10T01:32:41Z",
          "completed_at": "2025-11-10T01:32:43Z"
        },
        {
          "name": "Run actions/checkout@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 2,
          "started_at": "2025-11-10T01:32:43Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Run actions/setup-python@v5",
          "status": "completed",
          "conclusion": "success",
          "number": 3,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Run astral-sh/setup-uv@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 4,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:46Z"
        },
        {
          "name": "Cache uv",
          "status": "completed",
          "conclusion": "success",
          "number": 5,
          "started_at": "2025-11-10T01:32:46Z",
          "completed_at": "2025-11-10T01:32:46Z"
        },
        {
          "name": "Sync deps",
          "status": "completed",
          "conclusion": "success",
          "number": 6,
          "started_at": "2025-11-10T01:32:46Z",
          "completed_at": "2025-11-10T01:32:49Z"
        },
        {
          "name": "Install verilator (Linux)",
          "status": "in_progress",
          "conclusion": null,
          "number": 7,
          "started_at": "2025-11-10T01:32:49Z",
          "completed_at": null
        },
        {
          "name": "Attempt install delta (Linux)",
          "status": "pending",
          "conclusion": null,
          "number": 8,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install verilator (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 9,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Attempt install delta (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 10,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install packages (editable)",
          "status": "pending",
          "conclusion": null,
          "number": 11,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Unit tests",
          "status": "pending",
          "conclusion": null,
          "number": 12,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "E2E tests",
          "status": "pending",
          "conclusion": null,
          "number": 13,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Cache uv",
          "status": "pending",
          "conclusion": null,
          "number": 23,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run astral-sh/setup-uv@v4",
          "status": "pending",
          "conclusion": null,
          "number": 24,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/setup-python@v5",
          "status": "pending",
          "conclusion": null,
          "number": 25,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/checkout@v4",
          "status": "pending",
          "conclusion": null,
          "number": 26,
          "started_at": null,
          "completed_at": null
        }
      ],
      "check_run_url": "https://api.github.com/repos/curvcpu/curv-python/check-runs/54930140743",
      "labels": [
        "ubuntu-latest"
      ],
      "runner_id": 1000001085,
      "runner_name": "GitHub Actions 1000001085",
      "runner_group_id": 0,
      "runner_group_name": "GitHub Actions"
    },
    {
      "id": 54930140745,
      "run_id": 19217851608,
      "workflow_name": "experimenting with badges",
      "head_branch": "main",
      "run_url": "https://api.github.com/repos/curvcpu/curv-python/actions/runs/19217851608",
      "run_attempt": 1,
      "node_id": "CR_kwDOQDTFVs8AAAAMyhduSQ",
      "head_sha": "90d6bc9cd0a659c96f871a7a00989ed4f4b5cfff",
      "url": "https://api.github.com/repos/curvcpu/curv-python/actions/jobs/54930140745",
      "html_url": "https://github.com/curvcpu/curv-python/actions/runs/19217851608/job/54930140745",
      "status": "in_progress",
      "conclusion": null,
      "created_at": "2025-11-10T01:32:37Z",
      "started_at": "2025-11-10T01:32:40Z",
      "completed_at": null,
      "name": "Test (py3.10 • ubuntu-latest)",
      "steps": [
        {
          "name": "Set up job",
          "status": "completed",
          "conclusion": "success",
          "number": 1,
          "started_at": "2025-11-10T01:32:41Z",
          "completed_at": "2025-11-10T01:32:42Z"
        },
        {
          "name": "Run actions/checkout@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 2,
          "started_at": "2025-11-10T01:32:42Z",
          "completed_at": "2025-11-10T01:32:43Z"
        },
        {
          "name": "Run actions/setup-python@v5",
          "status": "completed",
          "conclusion": "success",
          "number": 3,
          "started_at": "2025-11-10T01:32:43Z",
          "completed_at": "2025-11-10T01:32:43Z"
        },
        {
          "name": "Run astral-sh/setup-uv@v4",
          "status": "completed",
          "conclusion": "success",
          "number": 4,
          "started_at": "2025-11-10T01:32:43Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Cache uv",
          "status": "completed",
          "conclusion": "success",
          "number": 5,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:44Z"
        },
        {
          "name": "Sync deps",
          "status": "completed",
          "conclusion": "success",
          "number": 6,
          "started_at": "2025-11-10T01:32:44Z",
          "completed_at": "2025-11-10T01:32:47Z"
        },
        {
          "name": "Install verilator (Linux)",
          "status": "in_progress",
          "conclusion": null,
          "number": 7,
          "started_at": "2025-11-10T01:32:47Z",
          "completed_at": null
        },
        {
          "name": "Attempt install delta (Linux)",
          "status": "pending",
          "conclusion": null,
          "number": 8,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install verilator (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 9,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Attempt install delta (macOS)",
          "status": "pending",
          "conclusion": null,
          "number": 10,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Install packages (editable)",
          "status": "pending",
          "conclusion": null,
          "number": 11,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Unit tests",
          "status": "pending",
          "conclusion": null,
          "number": 12,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "E2E tests",
          "status": "pending",
          "conclusion": null,
          "number": 13,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Cache uv",
          "status": "pending",
          "conclusion": null,
          "number": 23,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run astral-sh/setup-uv@v4",
          "status": "pending",
          "conclusion": null,
          "number": 24,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/setup-python@v5",
          "status": "pending",
          "conclusion": null,
          "number": 25,
          "started_at": null,
          "completed_at": null
        },
        {
          "name": "Post Run actions/checkout@v4",
          "status": "pending",
          "conclusion": null,
          "number": 26,
          "started_at": null,
          "completed_at": null
        }
      ],
      "check_run_url": "https://api.github.com/repos/curvcpu/curv-python/check-runs/54930140745",
      "labels": [
        "ubuntu-latest"
      ],
      "runner_id": 1000001084,
      "runner_name": "GitHub Actions 1000001084",
      "runner_group_id": 0,
      "runner_group_name": "GitHub Actions"
    }
  ]
}
"""

def test_get_gh_run_by_id() -> None:
    base_indent = 2

    # Monkeypatch get_gh_run_json to return test_run_json1 exactly once 
    # on the very first call, and test_run_json2 exactly once on the second call. 
    # After that, it reverts to original version.  Ditto for get_gh_jobs_json.
    original_get_gh_run_json = globals()['get_gh_run_json']
    original_get_gh_jobs_json = globals()['get_gh_jobs_json']
    calls_to_get_gh_run_json = 0
    calls_to_get_gh_jobs_json = 0
    def _return_test_run_json_once(run_id) -> str:
        nonlocal calls_to_get_gh_run_json
        if calls_to_get_gh_run_json==0:
            calls_to_get_gh_run_json += 1
            return test_run_json1
        elif calls_to_get_gh_run_json<5:
            calls_to_get_gh_run_json += 1
            return test_run_json2
        else:
            globals()['get_gh_run_json'] = original_get_gh_run_json
            return original_get_gh_run_json(run_id)
    def _return_test_jobs_json_once(run_id) -> str:
        nonlocal calls_to_get_gh_jobs_json
        if calls_to_get_gh_jobs_json==0:
            calls_to_get_gh_jobs_json += 1
            return test_jobs_json1
        elif calls_to_get_gh_jobs_json<5:
            calls_to_get_gh_jobs_json += 1
            return test_jobs_json2
        else:
            globals()['get_gh_jobs_json'] = original_get_gh_jobs_json
            return original_get_gh_jobs_json(run_id)
    globals()['get_gh_jobs_json'] = _return_test_jobs_json_once
    globals()['get_gh_run_json'] = _return_test_run_json_once

    #
    # Actual test code
    #
    run: GhRun = GhRun.construct_from_run_json_query(19217851608)
    for new_ghjob in GhJob.construct_from_job_json_element(get_gh_jobs_json(19217851608)):
        run.upsert_job(new_ghjob)
    assert run.run_id == 19217851608
    assert run.status == GhStatus.IN_PROGRESS
    assert run.conclusion == GhConclusion.NULL
    assert run.get_progress().percent_complete == 39.00
    print(run.get_status_summary(indent=base_indent))

    print("----------------------------------------")

    run.update_run_status(get_gh_run_json(19217851608))
    for new_ghjob in GhJob.construct_from_job_json_element(get_gh_jobs_json(19217851608)):
        run.upsert_job(new_ghjob)
    assert run.run_id == 19217851608
    assert run.status == GhStatus.IN_PROGRESS
    assert run.conclusion == GhConclusion.SUCCESS
    assert run.get_progress().percent_complete == 39.00
    print(run.get_status_summary(indent=base_indent))

    print("----------------------------------------")

    run.update_run_status(get_gh_run_json(19217851608))
    for new_ghjob in GhJob.construct_from_job_json_element(get_gh_jobs_json(19217851608)):
        run.upsert_job(new_ghjob)
    assert run.run_id == 19217851608
    assert run.status == GhStatus.IN_PROGRESS
    assert run.conclusion == GhConclusion.SUCCESS
    assert run.get_progress().percent_complete == 39.00
    print(run.get_status_summary(indent=base_indent))

    print("----------------------------------------")

    run.update_run_status(get_gh_run_json(19217851608))
    for new_ghjob in GhJob.construct_from_job_json_element(get_gh_jobs_json(19217851608)):
        run.upsert_job(new_ghjob)
    assert run.run_id == 19217851608
    assert run.status == GhStatus.IN_PROGRESS
    assert run.conclusion == GhConclusion.SUCCESS
    assert run.get_progress().percent_complete == 39.00
    print(run.get_status_summary(indent=base_indent))

    print("----------------------------------------")

    run.update_run_status(get_gh_run_json(19217851608))
    for new_ghjob in GhJob.construct_from_job_json_element(get_gh_jobs_json(19217851608)):
        run.upsert_job(new_ghjob)
    assert run.run_id == 19217851608
    assert run.status == GhStatus.IN_PROGRESS
    assert run.conclusion == GhConclusion.SUCCESS
    assert run.get_progress().percent_complete == 39.00
    print(run.get_status_summary(indent=base_indent))

    print("----------------------------------------")

    run.update_run_status(get_gh_run_json(19217851608))
    for new_ghjob in GhJob.construct_from_job_json_element(get_gh_jobs_json(19217851608)):
        run.upsert_job(new_ghjob)
    assert run.run_id == 19217851608
    assert run.status == GhStatus.COMPLETED
    assert run.conclusion == GhConclusion.SUCCESS
    assert run.get_progress().percent_complete == 100.0
    print(run.get_status_summary(indent=base_indent))

    print("----------------------------------------")

    run.update_run_status(get_gh_run_json(19217851608))
    for new_ghjob in GhJob.construct_from_job_json_element(get_gh_jobs_json(19217851608)):
        run.upsert_job(new_ghjob)
    assert run.run_id == 19217851608
    assert run.status == GhStatus.COMPLETED
    assert run.conclusion == GhConclusion.SUCCESS
    assert run.get_progress().percent_complete == 100.0
    print(run.get_status_summary(indent=base_indent))

if __name__ == "__main__":
    test_get_gh_run_by_id()
