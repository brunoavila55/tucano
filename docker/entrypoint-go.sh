#!/bin/sh
set -eu

if [ -d /data/uploads ]; then
    chown tucano:tucano /data/uploads
    chmod 0750 /data/uploads
fi

exec su-exec tucano "$@"
