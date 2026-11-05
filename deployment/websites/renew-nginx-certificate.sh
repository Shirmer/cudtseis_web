#!/bin/sh
# Install as /etc/letsencrypt/renewal-hooks/deploy/reload-nginx (root:root, 0755).
set -eu
/usr/sbin/nginx -t
/usr/bin/systemctl reload nginx
