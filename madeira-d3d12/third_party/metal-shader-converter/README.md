# Metal Shader Converter headers

The public C headers of Apple's Metal Shader Converter, copied unchanged from
the installer package the D3D12 runtime is pinned to:

- Package: `Metal Shader Converter 4.0 beta 2.pkg`
  (SHA-256 `1acc33c87ea663933df89721a998d066106685473020bcbe007cee7a16155734`)
- Source path in the package payload: `usr/local/include/`
- Matching iOS library: `app/Madeira/d3d12/libmetalirconverter.dylib`
  (SHA-256 `073f903be98e973ff38f4d79f2c48d61ef938754a77b1caedda79c9f05a068c2`)

The headers are Copyright Apple Inc. and licensed under the Apache License,
Version 2.0 (each file's own notice; the full text is `LICENSE.txt` in each
folder). `Acknowledgements.rtf` is Apple's own notice file from the same
folders. Apple's proprietary library is not covered by that licence; see
`app/Madeira/d3d12/NOTICE.txt`.

They are here so that a clean clone builds the D3D12 runtime's conversion
service (`madeira-d3d12/src/unix/madeira_ir_unix.mm`) without the
installer package. `build/madeira-d3d12/deps.sh` checks every file against
`SHA256SUMS` before using them. After a converter update, run
`build/madeira-d3d12/fetch-converter.sh` with the new package: it re-stages the
library and these headers together and rewrites `SHA256SUMS`, so the two can
never come from different versions.
