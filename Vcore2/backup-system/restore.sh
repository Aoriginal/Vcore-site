#!/usr/bin/env bash
# ── VCore SecondBrain Restore ─────────────────────────────────────────────────
# Restore /SecondBrain from a backup snapshot.
# Usage:
#   ./restore.sh                    # lists available backups
#   ./restore.sh 2026-05-01         # restore a specific date
#   ./restore.sh latest             # restore most recent backup
#   ./restore.sh 2026-05-01 --dry-run
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${SCRIPT_DIR}/.backup-config" ]]; then
  # shellcheck source=/dev/null
  source "${SCRIPT_DIR}/.backup-config"
fi

SOURCE_DIR="${VCORE_SOURCE:-/SecondBrain}"
BACKUP_ROOT="${VCORE_BACKUP_ROOT:-}"
LOG_DIR="${VCORE_LOG_DIR:-/SecondBrain/Logs}"
LOG_FILE="${LOG_DIR}/restore.log"

now() { date "+%Y-%m-%d %H:%M:%S"; }
timestamp() { date "+%Y%m%d_%H%M%S"; }

log() {
  local level="$1"; shift
  echo "[$(now)] [${level}] $*"
  mkdir -p "${LOG_DIR}"
  echo "[$(now)] [${level}] $*" >> "${LOG_FILE}"
}

# ── List available backups ─────────────────────────────────────────────────────
list_backups() {
  if [[ -z "${BACKUP_ROOT}" ]]; then
    echo "ERROR: BACKUP_ROOT not set. Check .backup-config or run install.sh"
    exit 1
  fi
  echo ""
  echo "Available backups in ${BACKUP_ROOT}:"
  echo "────────────────────────────────────────"
  local found=0
  while IFS= read -r -d '' dir; do
    local name size count
    name="$(basename "${dir}")"
    size="$(du -sh "${dir}" 2>/dev/null | cut -f1)"
    count="$(find "${dir}" -type f ! -name '.backup-manifest.txt' | wc -l | tr -d ' ')"
    printf "  %-15s  %6s  %5s files\n" "${name}" "${size}" "${count}"
    ((found++)) || true
  done < <(find "${BACKUP_ROOT}" -maxdepth 1 -type d -name "20??-??-??" -print0 2>/dev/null | sort -z)

  if [[ "${found}" -eq 0 ]]; then
    echo "  No backups found."
  fi
  echo ""
  echo "Usage: ./restore.sh <DATE|latest> [--dry-run]"
  echo "Example: ./restore.sh 2026-05-01"
  echo "         ./restore.sh latest --dry-run"
  echo ""
}

# ── Resolve backup directory ───────────────────────────────────────────────────
resolve_backup() {
  local target="$1"

  if [[ -z "${BACKUP_ROOT}" ]]; then
    echo "ERROR: BACKUP_ROOT not set."
    exit 1
  fi

  if [[ "${target}" == "latest" ]]; then
    local latest
    latest="$(find "${BACKUP_ROOT}" -maxdepth 1 -type d -name "20??-??-??" 2>/dev/null | sort | tail -1)"
    if [[ -z "${latest}" ]]; then
      echo "ERROR: No backups found in ${BACKUP_ROOT}"
      exit 1
    fi
    echo "${latest}"
  else
    local dir="${BACKUP_ROOT}/${target}"
    if [[ ! -d "${dir}" ]]; then
      echo "ERROR: Backup not found: ${dir}"
      echo "Run ./restore.sh with no arguments to list available backups."
      exit 1
    fi
    echo "${dir}"
  fi
}

# ── Confirm prompt ─────────────────────────────────────────────────────────────
confirm() {
  local prompt="$1"
  echo ""
  echo "⚠️  ${prompt}"
  echo ""
  read -r -p "Type 'yes' to confirm: " answer
  if [[ "${answer}" != "yes" ]]; then
    echo "Aborted."
    exit 0
  fi
}

# ── Restore ────────────────────────────────────────────────────────────────────
do_restore() {
  local backup_dir="$1"
  local dry_run="$2"
  local backup_date
  backup_date="$(basename "${backup_dir}")"

  echo ""
  log "INFO" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  log "INFO" "VCore SecondBrain Restore"
  log "INFO" "Backup:  ${backup_dir} (${backup_date})"
  log "INFO" "Target:  ${SOURCE_DIR}"
  log "INFO" "Dry run: ${dry_run}"
  log "INFO" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  # Show manifest if exists
  local manifest="${backup_dir}/.backup-manifest.txt"
  if [[ -f "${manifest}" ]]; then
    echo ""
    echo "── Backup info ──"
    cat "${manifest}"
    echo ""
  fi

  if [[ "${dry_run}" == "true" ]]; then
    log "INFO" "[DRY RUN] Would rsync ${backup_dir} → ${SOURCE_DIR}"
    rsync --dry-run -av --delete \
      --exclude=".backup-manifest.txt" \
      "${backup_dir}/" "${SOURCE_DIR}/"
    log "INFO" "[DRY RUN] Complete — no files written"
    return 0
  fi

  # Safety: snapshot current state before overwriting
  if [[ -d "${SOURCE_DIR}" ]]; then
    local safety_snapshot="/tmp/SecondBrain_pre_restore_$(timestamp)"
    log "INFO" "Creating safety snapshot of current state → ${safety_snapshot}"
    cp -r "${SOURCE_DIR}" "${safety_snapshot}" 2>/dev/null || {
      log "WARN" "Could not create safety snapshot (continuing anyway)"
    }
    log "INFO" "Safety snapshot ready. If restore fails, recover from: ${safety_snapshot}"
  fi

  # Perform restore
  mkdir -p "${SOURCE_DIR}"
  if rsync -av --delete \
    --exclude=".backup-manifest.txt" \
    "${backup_dir}/" "${SOURCE_DIR}/"; then
    log "INFO" "Restore complete ✅"
    log "INFO" "Restored from: ${backup_date}"
    log "INFO" "Files: $(find "${SOURCE_DIR}" -type f | wc -l | tr -d ' ')"
  else
    log "ERROR" "rsync failed. Your pre-restore snapshot is at: ${safety_snapshot:-N/A}"
    exit 1
  fi
}

# ── Main ───────────────────────────────────────────────────────────────────────
main() {
  local target="${1:-}"
  local dry_run=false

  for arg in "$@"; do
    if [[ "${arg}" == "--dry-run" ]]; then
      dry_run=true
    fi
  done

  if [[ -z "${target}" || "${target}" == "--help" || "${target}" == "-h" ]]; then
    list_backups
    exit 0
  fi

  local backup_dir
  backup_dir="$(resolve_backup "${target}")"

  if [[ "${dry_run}" != "true" ]]; then
    confirm "This will OVERWRITE ${SOURCE_DIR} with the ${target} backup. Current data will be replaced."
  fi

  do_restore "${backup_dir}" "${dry_run}"
}

main "$@"
