#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Real production-code contracts; no Steam payload, signing or device required.
set -euo pipefail
cd "$(dirname "$0")/../.."
artifacts=$(mktemp -d "${TMPDIR:-/tmp}/ideck-mac-contracts.XXXXXX")
trap 'rm -rf "$artifacts"' EXIT
python3 experiments/mac-arm-steam/test-manifest.py
python3 experiments/mac-arm-steam/test-staging.py
python3 experiments/mac-arm-steam/test-executable-layout.py
python3 experiments/mac-arm-steam/test-cef-abi-audit.py
python3 experiments/mac-arm-steam/test-process-observer-builder.py
python3 experiments/mac-arm-steam/test-native-probe-runner.py
python3 experiments/mac-arm-steam/test-native-helper-metadata.py
python3 experiments/mac-arm-steam/test-partitionalloc-builder.py
xcrun clang -Wall -Wextra -Werror -fsanitize=address,undefined -pthread \
  experiments/mac-arm-steam/sysv-semaphore.c \
  experiments/mac-arm-steam/test-sysv-semaphore.c -o "$artifacts/sem"
"$artifacts/sem"
for contract in display-pixel-encoding display-mode-object bitmap-image-rep font-matrix-constant; do
  xcrun clang -fobjc-arc -Wall -Wextra -Werror -fsanitize=address,undefined \
    -framework Foundation "experiments/mac-arm-steam/$contract.m" \
    "experiments/mac-arm-steam/test-$contract.m" -o "$artifacts/$contract"
  "$artifacts/$contract"
done
xcrun clang -Wall -Wextra -Werror -fsanitize=address,undefined \
  experiments/mac-arm-steam/pool-layout.c experiments/mac-arm-steam/test-pool-layout.c \
  -o "$artifacts/pool-layout"
"$artifacts/pool-layout"
for contract in launch-summary tier0-observer; do
  xcrun clang -Wall -Wextra -Werror -fsanitize=address,undefined \
    experiments/mac-arm-steam/launch-summary.c "experiments/mac-arm-steam/test-$contract.c" -o "$artifacts/$contract"
  "$artifacts/$contract"
done
xcrun clang -fobjc-arc -Wall -Wextra -Werror -fsanitize=address,undefined \
  -framework Foundation -framework CoreText -framework CoreGraphics \
  experiments/mac-arm-steam/font-advancement.m experiments/mac-arm-steam/test-font-advancement.m -o "$artifacts/font-advancement"
"$artifacts/font-advancement"
xcrun clang -Wall -Wextra -Werror -fsanitize=address,undefined \
  experiments/mac-arm-steam/test-power-registration.c -o "$artifacts/power-registration"
"$artifacts/power-registration"
xcrun clang -Wall -Wextra -Werror -fsanitize=address,undefined \
  experiments/mac-arm-steam/test-exec-diagnostic.c -o "$artifacts/exec-diagnostic"
"$artifacts/exec-diagnostic"
xcrun clang -Wall -Wextra -Werror -fsanitize=address,undefined \
  experiments/mac-arm-steam/helper-path.c experiments/mac-arm-steam/test-helper-path.c -o "$artifacts/helper-path"
"$artifacts/helper-path"
# Device-only sources must also pass the actual iOS compiler/ABI checks.
for source in casefold-path.m casefold-probe.m volume-case-view.m appkit-font.m \
              tier0-process-observer.c launch-summary.c font-advancement.m power-registration.c native-process-probe.c native-vm-probe.c native-vm-range-probe.c native-small-pool-probe.c exec-diagnostic.c cef-load-probe.m helper-load-probe.m helper-path.c synthetic-helper-probe.m; do
  xcrun --sdk iphoneos clang -target arm64-apple-ios17.0 -fobjc-arc \
    -Wall -Wextra -Werror -c "experiments/mac-arm-steam/$source" -o "$artifacts/$source.o"
done
