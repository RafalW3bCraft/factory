#!/usr/bin/env bash
# load_env.sh — Safe KEY=VALUE environment parser for shell scripts (Finding S3).
# Replaces 'source .env' to prevent arbitrary code execution from malicious or
# untrusted .env files.
#
# Usage:
#   load_env_safe "/path/to/.env"

load_env_safe() {
    local env_file="${1:-.env}"
    [[ -f "$env_file" ]] || return 0

    while IFS= read -r line || [[ -n "$line" ]]; do
        # Strip trailing carriage return for CRLF support
        line="${line%$'\r'}"

        # Trim leading/trailing whitespace
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"

        # Skip empty lines and comment lines
        [[ -z "$line" || "$line" =~ ^# ]] && continue

        # Strip leading 'export ' if present
        [[ "$line" =~ ^export[[:space:]]+ ]] && line="${line#export }"

        # Match KEY=VALUE pattern
        if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            local key="${BASH_REMATCH[1]}"
            local val="${BASH_REMATCH[2]}"

            # Trim whitespace from val
            val="${val#"${val%%[![:space:]]*}"}"
            val="${val%"${val##*[![:space:]]}"}"

            # Handle double-quoted values (with optional trailing comment)
            if [[ "$val" =~ ^\"(.*)\"[[:space:]]*(#.*)?$ ]]; then
                val="${BASH_REMATCH[1]}"
            # Handle single-quoted values (with optional trailing comment)
            elif [[ "$val" =~ ^\'(.*)\'[[:space:]]*(#.*)?$ ]]; then
                val="${BASH_REMATCH[1]}"
            else
                # Unquoted: strip trailing comment if separated by space
                val="${val%% #*}"
                val="${val%"${val##*[![:space:]]}"}"
            fi

            # Export safely as a literal string
            export "$key=$val"
        fi
    done < "$env_file"
}
