# Feature Specification: Personal AI Employee — Bronze Tier

**Feature Branch**: `001-bronze-tier`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "Establish basic Obsidian vault setup, implement a single filesystem watcher, enable Claude Code read/write on vault files, and integrate existing Agent Skills for processing"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Vault Foundation Setup (Priority: P1)

A developer sets up the AI Employee vault for the first time. They run a setup process and the vault is populated with the required folder structure, a Dashboard showing current status, and a Company Handbook defining processing rules. The developer opens the vault in Obsidian and sees a well-organized workspace ready for autonomous processing.

**Why this priority**: Without the vault structure, no other feature can function. This is the foundation everything else depends on.

**Independent Test**: Run the vault setup, then open `/home/safdarayub/Documents/AI_Employee_Vault` in a file browser and verify all expected folders and files exist with correct content.

**Acceptance Scenarios**:

1. **Given** no vault exists or vault is empty, **When** the developer runs the vault setup, **Then** the vault at `/home/safdarayub/Documents/AI_Employee_Vault` contains: `Dashboard.md`, `Company_Handbook.md`, and folders `Inbox/`, `Needs_Action/`, `Done/`, `Pending_Approval/`, `Approved/`, `Plans/`, `Logs/`.
2. **Given** the vault has been set up, **When** the developer opens `Dashboard.md`, **Then** it displays a status overview section with creation timestamp and empty processing history.
3. **Given** the vault has been set up, **When** the developer opens `Company_Handbook.md`, **Then** it contains categorized processing rules: which actions are routine (auto-executable), which are sensitive (require approval), and which are critical (require approval + confirmation), each with at least two concrete examples.
4. **Given** the vault already exists with user-modified files, **When** the developer runs setup again, **Then** existing files are preserved (content unchanged), only missing folders and files are created, and a setup log entry is appended to `Logs/vault_operations.jsonl`.

---

### User Story 2 — File Drop Watcher (Priority: P2)

A developer drops a file (any type) into a designated drop folder on their desktop. Within seconds, a filesystem watcher detects the new file and automatically creates a corresponding metadata markdown file in the vault's `Needs_Action/` folder. The metadata file describes what was dropped, when, and suggests a default action.

**Why this priority**: The watcher is the event trigger that makes the agent proactive rather than manual. Without it, the developer must manually create Needs_Action files.

**Independent Test**: Start the watcher, drop a test file into the drop folder, then check `Needs_Action/` for a new `.md` file with correct metadata.

**Acceptance Scenarios**:

1. **Given** the watcher is running and monitoring the configured drop folder, **When** the developer drops a `.txt` file into that folder, **Then** a new `.md` file appears in `Needs_Action/` within 5 seconds, containing YAML frontmatter with `title`, `created` (ISO 8601 timestamp), `tier: bronze`, `source: file-drop-watcher`, `priority: routine`, and `status: needs_action`.
2. **Given** the watcher is running, **When** the developer drops a `.pdf` file into the drop folder, **Then** a metadata `.md` file is created in `Needs_Action/` with the original filename referenced in the body, and the original file remains untouched in the drop folder.
3. **Given** the watcher is running, **When** the developer drops 3 files within 2 seconds, **Then** a separate metadata `.md` file is created in `Needs_Action/` for each dropped file, with no files missed or duplicated.
4. **Given** the watcher is running, **When** a non-file event occurs (folder creation, file deletion), **Then** the watcher ignores it and no `Needs_Action` file is created.
5. **Given** the watcher encounters an error creating the metadata file, **When** the error occurs, **Then** it logs the error to `Logs/errors.jsonl` and continues watching (does not crash).

---

### User Story 3 — Claude Code Vault Read/Write (Priority: P3)

A developer asks Claude Code to read a file from the vault (e.g., "show me Dashboard.md") or write/append content to a vault file (e.g., "add a status entry to Dashboard.md"). Claude Code performs the operation via the vault-interact skill, scoped to the vault path, logs the operation, and confirms the result.

**Why this priority**: Read/write is the bridge between the agent skills and the vault. It validates that the `vault-interact` skill works correctly with Claude Code's native tools.

**Independent Test**: Ask Claude Code to read `Company_Handbook.md` and verify content is returned. Then ask it to append a test line to `Dashboard.md` and verify the line appears.

**Acceptance Scenarios**:

1. **Given** `Dashboard.md` exists in the vault, **When** the developer asks Claude Code to read it via vault-interact, **Then** the full content is displayed without modification or extra wrapping.
2. **Given** `Dashboard.md` exists in the vault, **When** the developer asks Claude Code to append "Test entry at [timestamp]", **Then** the text is appended to the file, a confirmation "Success: appended to Dashboard.md" is returned, and a log entry is written to `Logs/vault_operations.jsonl`.
3. **Given** the developer asks Claude Code to read a file that does not exist (e.g., `nonexistent.md`), **Then** a clear error message is returned: "Error: File not found: nonexistent.md".
4. **Given** the developer asks Claude Code to write to a path outside the vault (e.g., `/etc/passwd`), **Then** the operation is rejected with "Error: Path violation" and the attempt is logged to `Logs/vault_operations.jsonl`.
5. **Given** the developer asks Claude Code to list files in `Needs_Action/`, **Then** a bullet list of `.md` filenames is returned (or "folder empty" if none exist).
6. **Given** the developer asks Claude Code to move a file from `Needs_Action/` to `Done/`, **Then** the file content appears at the destination, the source is renamed to `.moved`, and both operations are logged.

---

### User Story 4 — End-to-End Skill Processing (Priority: P4)

A developer triggers the full processing pipeline: they drop a file into the drop folder, the watcher creates a `Needs_Action` file, then the developer manually triggers the `check-and-process-needs-action` skill. The system reads each `Needs_Action` file, classifies it by risk using `Company_Handbook.md` rules, creates a plan via `process-needs-action`, routes the file to `Done/` (low-risk) or `Pending_Approval/` (high-risk) via `vault-interact`, and updates `Dashboard.md` with a processing summary.

**Why this priority**: This validates the complete Bronze tier loop end-to-end. All three skills (vault-interact, process-needs-action, check-and-process-needs-action) must compose correctly.

**Independent Test**: Drop a test file, wait for watcher to create a `Needs_Action` entry, manually trigger processing, then verify the file moved to `Done/` or `Pending_Approval/`, a plan exists in `Plans/`, and `Dashboard.md` shows the processing summary.

**Acceptance Scenarios**:

1. **Given** one routine-priority file exists in `Needs_Action/`, **When** the developer triggers `check-and-process-needs-action`, **Then** a plan is created in `Plans/`, a result file appears in `Done/`, the original is moved from `Needs_Action/`, `Dashboard.md` shows "Processed 1 file. Auto-executed: 1. Pending: 0.", and `Logs/actions.jsonl` contains a corresponding entry.
2. **Given** one sensitive-priority file exists in `Needs_Action/`, **When** processing is triggered, **Then** a plan is created in `Plans/`, a proposal with approval header appears in `Pending_Approval/`, and `Dashboard.md` shows "Processed 1 file. Auto-executed: 0. Pending approval: 1."
3. **Given** three files exist in `Needs_Action/` (two routine, one sensitive), **When** processing is triggered, **Then** two files route to `Done/`, one routes to `Pending_Approval/`, three plans exist in `Plans/`, and `Dashboard.md` shows "Processed 3 files. Auto-executed: 2. Pending approval: 1."
4. **Given** `Needs_Action/` is empty, **When** processing is triggered, **Then** `Dashboard.md` is updated with "No pending actions at [timestamp]" and no errors occur.
5. **Given** a `Needs_Action` file suggests sending an email (a sensitive action), **When** processing runs in dry-run mode, **Then** no email is sent, the file routes to `Pending_Approval/` with a proposal, and the log entry shows `status: pending_approval` (not `executed`).

---

### Edge Cases

- What happens when the drop folder does not exist at watcher startup? The watcher MUST create it and log a warning, or exit with a clear error message identifying the missing path.
- What happens when a `Needs_Action` file has malformed or missing YAML frontmatter? The system MUST treat it as high-risk (safe default), log a warning with the filename, and route to `Pending_Approval/`.
- What happens when two files in `Needs_Action/` have the same name? The system MUST append a timestamp suffix to the duplicate's plan and result files to prevent overwrites.
- What happens when `Dashboard.md` is open in Obsidian during an append operation? The write MUST succeed; Obsidian auto-reloads changed files on disk.
- What happens when the vault path is inaccessible (permissions error, disk full)? The system MUST log the error with the specific OS error message and exit gracefully (not crash silently or hang).
- What happens when the watcher is started but a previous instance is already running? The system MUST detect the conflict (via PID lock file in `Logs/watcher.pid`) and exit with a clear message.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create and maintain the vault folder structure with all required directories (`Inbox/`, `Needs_Action/`, `Done/`, `Pending_Approval/`, `Approved/`, `Plans/`, `Logs/`) at the configured vault path.
- **FR-002**: System MUST generate a `Dashboard.md` file with YAML frontmatter, a status overview section, and support appending timestamped processing summaries.
- **FR-003**: System MUST generate a `Company_Handbook.md` file containing categorized action rules (routine, sensitive, critical) with at least two concrete examples per category.
- **FR-004**: System MUST provide a filesystem watcher that monitors a drop folder (path configured via `DROP_FOLDER` environment variable, defaulting to `~/Desktop/DropForAI`) and creates metadata `.md` files in `Needs_Action/` for each new file detected.
- **FR-005**: The watcher MUST create metadata files with valid YAML frontmatter containing: `title`, `created` (ISO 8601), `tier: bronze`, `source: file-drop-watcher`, `priority: routine`, and `status: needs_action`.
- **FR-006**: System MUST support reading any file within the vault via the vault-interact skill and returning its content as plain text.
- **FR-007**: System MUST support writing new files and appending content to existing files within the vault via the vault-interact skill, with confirmation messages on success.
- **FR-008**: System MUST reject any file operation targeting a path outside the vault root, return a path violation error, and log the violation to `Logs/vault_operations.jsonl`.
- **FR-009**: System MUST classify `Needs_Action` files by risk level (routine → low-risk, sensitive/critical/unknown → high-risk) based on frontmatter priority and `Company_Handbook.md` rules via the process-needs-action skill.
- **FR-010**: System MUST create an action plan in `Plans/` for each processed file before executing or deferring, via the process-needs-action skill.
- **FR-011**: System MUST route low-risk files to `Done/` with a result summary and high-risk files to `Pending_Approval/` with an approval proposal header, via the vault-interact skill.
- **FR-012**: System MUST log every vault mutation (write, append, move, create) to `Logs/vault_operations.jsonl` with ISO 8601 timestamp, component, action, status, and detail fields.
- **FR-013**: System MUST log every processing action to `Logs/actions.jsonl` with timestamp, component, action, file, risk level, status, and detail fields.
- **FR-014**: System MUST update `Dashboard.md` after each processing run with a summary table showing files processed, auto-executed count, pending approval count, and error count, via the check-and-process-needs-action skill.
- **FR-015**: System MUST process a maximum of 5 files per batch run, deferring excess files to the next run with a logged warning.
- **FR-016**: System MUST NOT delete any files. Move operations use a rename-to-`.moved` pattern on the source.
- **FR-017**: System MUST preserve existing vault content during setup (idempotent initialization — create only missing folders and files, never overwrite existing ones).
- **FR-018**: System MUST operate in dry-run mode by default. No external actions (email, payments, social media posts) are executed even if a `Needs_Action` file requests them. High-risk files route to `Pending_Approval/` with a proposal instead.
- **FR-019**: The watcher MUST write a PID lock file to `Logs/watcher.pid` on startup and remove it on clean shutdown. If the lock file exists and the PID is active, the watcher MUST refuse to start.

### Key Entities

- **Vault**: The root workspace folder at `/home/safdarayub/Documents/AI_Employee_Vault` containing all agent data, structured into functional subfolders. Key attributes: absolute path (from `VAULT_PATH` env var), folder structure, initialization status.
- **Needs_Action File**: A markdown file with YAML frontmatter describing an event that requires processing. Key attributes: title, created timestamp, tier, source, priority, status. Lifecycle: created by watcher → classified by process-needs-action → routed by vault-interact → summarized by check-and-process-needs-action.
- **Plan**: A markdown file in `Plans/` describing the intended action for a Needs_Action file. Key attributes: source file reference, risk level, action description, expected outcome. Created by process-needs-action before any routing occurs.
- **Dashboard**: A markdown file providing a real-time overview of agent activity. Updated by check-and-process-needs-action after each processing run with summary statistics.
- **Company Handbook**: A markdown file defining the rules for action classification (routine, sensitive, critical) with concrete examples. Referenced by process-needs-action to determine risk level.

### Assumptions

- The developer has an existing local environment with the required tooling pre-installed.
- Obsidian is installed and can open the vault path as a vault.
- The drop folder path is on the same filesystem as the vault (no cross-device move issues).
- Only one instance of the watcher runs at a time (enforced via PID lock file per FR-019).
- Claude Code is available and can be invoked manually to trigger processing via check-and-process-needs-action.
- Dry-run mode is the only mode in Bronze tier (enforced via FR-018). No mechanism to switch to live mode exists at this tier.
- The three existing skills (vault-interact, process-needs-action, check-and-process-needs-action) are installed in `.claude/skills/` and available to Claude Code.

### Not in Scope

- Multiple watchers (Gmail, WhatsApp, calendar) — filesystem watcher only.
- Ralph Wiggum persistence loop or automated scheduling — manual trigger only.
- Human-in-the-loop approval execution (files land in `Pending_Approval/` but no automated action follows approval).
- CEO briefing, Odoo integration, social media posting (Gold tier).
- Cloud sync, remote VM, Git-based vault sync (Platinum tier).
- Advanced error recovery, parallel file processing, retry logic (Silver/Gold tier).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Vault setup produces all 7 required folders and 2 required files (`Dashboard.md`, `Company_Handbook.md`) on first run. On re-run against an existing vault with user-modified content, all existing files are preserved byte-for-byte and only missing items are created.
- **SC-002**: Watcher detects a dropped file and creates a corresponding `Needs_Action` metadata `.md` file within 5 seconds of the drop event, with all 6 required frontmatter fields present and valid.
- **SC-003**: All 6 vault-interact operations (read, write, append, list, move, create) complete successfully against the vault: read returns correct content, write creates the file, append adds text verified by read-back, list returns accurate filenames, move places content at destination and renames source to `.moved`, create produces a file with valid YAML frontmatter.
- **SC-004**: The three-skill pipeline (vault-interact → process-needs-action → check-and-process-needs-action) processes a single `Needs_Action` file end-to-end within 60 seconds: plan created in `Plans/`, file routed to `Done/` or `Pending_Approval/` based on risk, `Dashboard.md` updated with summary, and `Logs/actions.jsonl` contains a corresponding entry.
- **SC-005**: Batch processing of 5 files completes within 5 minutes with correct routing (routine-priority to `Done/`, sensitive/critical to `Pending_Approval/`) and `Dashboard.md` shows accurate counts matching the actual file distribution.
- **SC-006**: System runs for 10 continuous minutes with the watcher active and at least 5 files dropped and processed without any unhandled exceptions, crashes, or orphaned files (every `Needs_Action` file reaches either `Done/` or `Pending_Approval/`).
- **SC-007**: Every vault mutation (write, append, move, create) produces a corresponding log entry in `Logs/vault_operations.jsonl`. Verification: count of mutations performed equals count of log entries (100% audit coverage for mutations).
- **SC-008**: All path violation attempts (operations targeting paths outside `/home/safdarayub/Documents/AI_Employee_Vault`) are rejected with an error message and a log entry. Zero violations succeed.
- **SC-009**: When a `Needs_Action` file requests a sensitive action (e.g., "send email", "post to social media"), the system routes it to `Pending_Approval/` with a proposal — never executes the action. Verified by checking no external side effects occur and the log shows `status: pending_approval`.
