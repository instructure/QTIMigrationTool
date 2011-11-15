#!/bin/bash


git clone "ssh://hudson@gerrit.instructure.com:29418/migration_tool.git" "vendor/plugins/migration_tool"

vendor/plugins/migration_tool/spec_canvas/hudson_setup.sh

#qti_migration_tool is installed by migration_tool hudson_setup.sh
set +e
rm -r vendor/plugins/qti_migration_tool
set -e
