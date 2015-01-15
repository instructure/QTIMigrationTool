#!/bin/bash

TARGET=vendor/plugins/migration_tool

git clone "$REPO/migration_tool.git" $TARGET

if [ -f vendor/plugins/migration_tool/migration_tool.gemspec ]; then
  mv vendor/plugins/migration_tool gems/plugins/migration_tool
  TARGET=gems/plugins/migration_tool
fi

$TARGET/spec_canvas/hudson_setup.sh

#qti_migration_tool is installed by migration_tool hudson_setup.sh
set +e
rm -r vendor/plugins/qti_migration_tool
set -e
