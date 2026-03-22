#!/usr/bin/env bash
# ── VCore SecondBrain Backup ─────────────────────────────────────────────────
# Nightly backup of /SecondBrain to external drive with 30-day rolling history.
# Install with: ./install.sh
# Run manually: ./backup.sh [--dry-run]
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
SOURCE_DIR="${VCORE_SOURCE:-/SecondBrain}"
BACKUP_ROOT="${VCORE_BACKUP_ROOT:-}"         # Set in install.sh or env
KEEP_DAYS="${VCORE_KEEP_DAYS:-30}"
LOG_DIR="${VCORE_LOG_DIR:-/SecondBrain/Logs}"
LOG_FILE="${LOG_DIR}/backup.log"
MAX_LOG_SIZE_MB=10

# ── Load local config if exists ───────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${SCRIPT_DIR}/.backup-config" ]]; then
  # shellcheck source=/dev/null
  source "${SCRIPT_DIR}/.backup-config"
fi

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

# ── Helpers ────────────────────────────────────────────────────────────────────
now()       { date "+%Y-%m-%d %H:%M:%S"; }
datestamp() { date "+%Y-%m-%d"; }
timestamp() { date "+%Y%m%d_%H%M%S"; }

log() {
  local level="$1"; shift
  local msg="$*"
  local line="[$(now)] [${level}] ${msg}"
  echo "${line}"
  mkdir -p "${LOG_DIR}"
  echo "${line}" >> "${LOG_FILE}"
}

log_rotate() {
  if [[ -f "${LOG_FILE}" ]]; then
    local size_mb
    size_mb=$(du -m "${LOG_FILE}" 2>/dev/null | cut -f1)
    if [[ "${size_mb:-0}" -ge "${MAX_LOG_SIZE_MB}" ]]; then
      mv "${LOG_FILE}" "${LOG_FILE}.$(timestamp).old"
      log "INFO" "Log rotated (was ${size_mb}MB)"
    fi
  fi
}

check_source() {
  if [[ ! -d "${SOURCE_DIR}" ]]; then
    log "ERROR" "Source directory not found: ${SOURCE_DIR}"
    exit 1
  fi
}

check_backup_root() {
  if [[ -z "${BACKUP_ROOT}" ]]; then
    log "ERROR" "BACKUP_ROOT not set. Run ./install.sh first or set VCORE_BACKUP_ROOT env var."
    log "ERROR" "Example: VCORE_BACKUP_ROOT=/Volumes/MyDrive/VCoreBackups ./backup.sh"
    exit 1
  fi
  if [[ ! -d "${BACKUP_ROOT}" ]]; then
    log "WARN" "Backup root not accessible: ${BACKUP_ROOT}"
    log "WARN" "Is your external drive mounted?"
    # Try to create it (works if parent exists, e.g., local fallback)
    if mkdir -p "${BACKUP_ROOT}" 2>/dev/null; then
      log "INFO" "Created backup root: ${BACKUP_ROOT}"
    else
      log "ERROR" "Cannot create backup root. Aborting."
      exit 1
    fi
  fi
}

# ── Main backup ────────────────────────────────────────────────────────────────
do_backup() {
  local today
  today="$(datestamp)"
  local backup_dir="${BACKUP_ROOT}/${today}"

  log "INFO" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  log "INFO" "VCore SecondBrain Backup"
  log "INFO" "Source:  ${SOURCE_DIR}"
  log "INFO" "Target:  ${backup_dir}"
  log "INFO" "Dry run: ${DRY_RUN}"
  log "INFO" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if [[ "${DRY_RUN}" == "true" ]]; then
    log "INFO" "[DRY RUN] Would rsync ${SOURCE_DIR} → ${backup_dir}"
    rsync --dry-run -av --delete \
      --exclude="*.pyc" \
      --exclude="__pycache__/" \
      --exclude=".DS_Store" \
      --exclude="*.tmp" \
      "${SOURCE_DIR}/" "${backup_dir}/"
    log "INFO" "[DRY RUN] Complete — no files written"
    return 0
  fi

  mkdir -p "${backup_dir}"

  # rsync: archive, verbose, delete removed files, skip OS noise
  local rsync_log="${LOG_DIR}/rsync_$(timestamp).log"
  if rsync -av --delete \
    --exclude="*.pyc" \
    --exclude="__pycache__/" \
    --exclude=".DS_Store" \
    --exclude="*.tmp" \
    --log-file="${rsync_log}" \
    "${SOURCE_DIR}/" "${backup_dir}/"; then
    log "INFO" "Backup complete → ${backup_dir}"
  else
    log "ERROR" "rsync failed (exit $?). Check ${rsync_log}"
    exit 1
  fi

  # Write backup manifest
  local manifest="${backup_dir}/.backup-manifest.txt"
  {
    echo "VCore SecondBrain Backup Manifest"
    echo "Date:     $(now)"
    echo "Source:   ${SOURCE_DIR}"
    echo "Host:     $(hostname)"
    echo "User:     $(whoami)"
    echo ""
    echo "File count: $(find "${backup_dir}" -type f | wc -l | tr -d ' ')"
    echo "Size:       $(du -sh "${backup_dir}" | cut -f1)"
  } > "${manifest}"

  log "INFO" "Manifest written: ${manifest}"
}

# ── Rolling cleanup ────────────────────────────────────────────────────────────
do_cleanup() {
  log "INFO" "Cleaning up backups older than ${KEEP_DAYS} days..."

  local removed=0
  while IFS= read -r -d '' old_dir; do
    if [[ "${DRY_RUN}" == "true" ]]; then
      log "INFO" "[DRY RUN] Would remove: ${old_dir}"
    else
      rm -rf "${old_dir}"
      log "INFO" "Removed old backup: $(basename "${old_dir}")"
    fi
    ((removed++)) || true
  done < <(find "${BACKUP_ROOT}" -maxdepth 1 -type d -name "20??-??-??" \
    -mtime "+${KEEP_DAYS}" -print0 2>/dev/null)

  if [[ "${removed}" -eq 0 ]]; then
    log "INFO" "No old backups to remove"
  else
    log "INFO" "Removed ${removed} old backup(s)"
  fi
}

# ── Verify last backup ─────────────────────────────────────────────────────────
do_verify() {
  local today
  today="$(datestamp)"
  local backup_dir="${BACKUP_ROOT}/${today}"

  if [[ -d "${backup_dir}" ]]; then
    local count
    count=$(find "${backup_dir}" -type f | wc -l | tr -d ' ')
    log "INFO" "Verification: today's backup has ${count} files at ${backup_dir}"
  else
    log "WARN" "Verification: no backup found for today (${today})"
  fi
}

# ── Notify on macOS ────────────────────────────────────────────────────────────
notify() {
  local title="$1"
  local msg="$2"
  if command -v osascript &>/dev/null; then
    osascript -e "display notification \"${msg}\" with title \"${title}\"" 2>/dev/null || true
  fi
}

# ── Run ────────────────────────────────────────────────────────────────────────
main() {
  log_rotate
  check_source
  check_backup_root

  local start_ts
  start_ts="$(date +%s)"

  do_backup
  do_cleanup
  do_verify

  local end_ts elapsed
  end_ts="$(date +%s)"
  elapsed=$((end_ts - start_ts))

  log "INFO" "Total time: ${elapsed}s"
  log "INFO" "Next backup: tomorrow at 2:00 AM"
  log "INFO" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if [[ "${DRY_RUN}" != "true" ]]; then
    notify "VCore Backup" "SecondBrain backed up in ${elapsed}s ✅"
  fi
}

main "$@"
